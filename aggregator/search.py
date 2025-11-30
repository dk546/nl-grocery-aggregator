"""
Aggregated search function that searches across multiple retailers.

This module provides the core search aggregation functionality that:
- Instantiates connectors for the selected retailers
- Performs parallel searches across retailers
- Adds health tags to each product
- Merges and sorts results based on the specified sort criteria
- Filters by health tag if requested
- Groups products by name and marks the cheapest in each group

The aggregated_search function is the main entry point for product searches
in the aggregator system, unifying results from AH, Jumbo, and Picnic.

Search flow: Streamlit -> GET /search -> aggregated_search() -> connectors.search_products() -> ProductInternal -> ProductPublic -> dict
"""

import logging
from typing import List, Dict, Any, Optional

from aggregator.models import ProductInternal, ProductPublic
from aggregator.health import tag_health
from aggregator.comparison import mark_cheapest, sort_products

from .connectors.ah_connector import AHConnector
from .connectors.jumbo_connector import JumboConnector
from .connectors.picnic_connector import PicnicConnector, PicnicAuthError

# Set up logger for search pipeline debugging
logger = logging.getLogger(__name__)


# Map retailer names to their connector classes
# Using a function to get the classes dynamically so that patches in tests work correctly
def _get_connector_map():
    """Get the connector map, accessing classes dynamically for test compatibility."""
    return {
        "ah": AHConnector,
        "jumbo": JumboConnector,
        "picnic": PicnicConnector,
    }

# Health tag priority for sorting (higher number = sorted later)
HEALTH_PRIORITY = {
    "healthy": 1,
    "neutral": 2,
    "unhealthy": 3,
}


def group_by_name_and_mark_cheapest(products: List[ProductPublic]) -> List[ProductPublic]:
    """
    Group products by normalized name and mark the cheapest in each group.
    
    Products are grouped by their name (case-insensitive). Within each group,
    the cheapest product (lowest price) is marked with is_cheapest=True,
    and all others are marked with is_cheapest=False.
    
    This function preserves the original order of products in the input list.
    Products with the same normalized name are processed together, but the
    overall relative order of products is maintained.
    
    Args:
        products: List of ProductPublic objects
        
    Returns:
        List of ProductPublic objects with is_cheapest field updated, preserving input order
        
    Examples:
        >>> products = [
        ...     ProductPublic(name="Melk", price=1.99, retailer="ah", id="ah:1", health_tag="neutral"),
        ...     ProductPublic(name="melk", price=2.50, retailer="jumbo", id="jumbo:1", health_tag="neutral"),
        ... ]
        >>> result = group_by_name_and_mark_cheapest(products)
        >>> # Melk group: cheapest (1.99) should be marked True
    """
    # Group products by normalized (lowercase) name while preserving insertion order
    groups: Dict[str, List[ProductPublic]] = {}
    group_order: List[str] = []  # Track order of groups as they appear
    
    for product in products:
        normalized_name = (product.name or "").lower().strip()
        if normalized_name not in groups:
            groups[normalized_name] = []
            group_order.append(normalized_name)
        groups[normalized_name].append(product)
    
    # Process each group in original order and mark cheapest
    result: List[ProductPublic] = []
    for normalized_name in group_order:
        group = groups[normalized_name]
        
        # Find the cheapest product in the group
        # Handle missing prices by treating them as very expensive (9999)
        cheapest_index = 0
        cheapest_price = group[0].price or 9999
        
        for i, product in enumerate(group[1:], start=1):
            price = product.price or 9999
            if price < cheapest_price:
                cheapest_price = price
                cheapest_index = i
        
        # Mark cheapest and add all products to result
        for i, product in enumerate(group):
            # Create new ProductPublic with updated is_cheapest
            product_dict = product.model_dump()
            product_dict["is_cheapest"] = (i == cheapest_index)  # Update is_cheapest
            updated_product = ProductPublic(**product_dict)
            result.append(updated_product)
    
    return result


def aggregated_search(
    query: str,
    retailers: List[str],
    size_per_retailer: int = 10,
    page: int = 0,
    sort_by: Optional[str] = None,
    health_filter: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Perform an aggregated search across multiple retailers.
    
    This function searches for products across the specified retailers, normalizes
    the results to ProductInternal, adds health tags, converts to ProductPublic,
    filters by health if requested, groups by name to mark cheapest options,
    and returns a merged, sorted list of product dictionaries.
    
    Args:
        query: Search query string (e.g., "melk", "brood")
        retailers: List of retailer identifiers to search (e.g., ["ah", "jumbo", "picnic"])
        size_per_retailer: Number of results to fetch from each retailer (default: 10)
        page: Page number for pagination (0-indexed, default: 0)
        sort_by: Sort criterion - "price", "retailer", or "health" (default: None, preserves order)
        health_filter: Optional filter for health tag - "healthy" or "unhealthy" (default: None)
        
    Returns:
        Dictionary containing:
        - results: List of product dictionaries, each containing:
            - retailer: Retailer identifier
            - id: Product identifier
            - name: Product name
            - price_eur: Price in euros (backward compatible alias for price)
            - price: Price in euros
            - unit: Unit description (legacy field)
            - unit_size: Size information (legacy field)
            - quantity: Numeric quantity
            - quantity_unit: Canonical unit (kg, g, L, mL, piece)
            - price_per_unit: Price per canonical unit
            - image_url: Product image URL
            - url: Product URL
            - health_tag: Health category ("healthy", "unhealthy", or "neutral")
            - is_cheapest: Boolean indicating if this is the cheapest option in its name group
            - raw: Raw product data from retailer API
        - connectors_status: Dictionary mapping retailer names to status strings:
            - "ok": Connector succeeded
            - "auth_error": Authentication failed (Picnic-specific)
            - "disabled": Connector not configured (missing credentials)
            - "error": Unexpected error occurred
            - "skipped": Retailer was not requested
        
        Results are sorted according to sort_by parameter:
        - "price" or "price_asc": By price (lowest first)
        - "price_desc": By price (highest first)
        - "price_per_unit_asc": By price per unit (lowest first)
        - "price_per_unit_desc": By price per unit (highest first)
        - "retailer": By retailer name (alphabetical)
        - "health": By health tag (healthy first, then neutral, then unhealthy)
        
        Partial failures are handled gracefully: if some connectors fail, results will still
        contain products from successful connectors, with connector_status indicating failures.
        
    Examples:
        >>> response = aggregated_search("melk", ["ah", "picnic"], size_per_retailer=5)
        >>> len(response["results"]) <= 10  # Up to 5 from each retailer
        True
        >>> all("health_tag" in r for r in response["results"])
        True
        >>> "connectors_status" in response
        True
    """
    logger.info("Search request: query=%r retailers=%r size_per_retailer=%d page=%d sort_by=%r health_filter=%r", 
                query, retailers, size_per_retailer, page, sort_by, health_filter)
    
    internal_products: List[ProductInternal] = []

    # Get connector map dynamically to allow test patches to work
    connector_map = _get_connector_map()
    
    # Track connector results for logging
    connector_results_count = {}
    
    # Track connector status (optional, for debugging/UI hints)
    connector_status: Dict[str, str] = {}
    
    # Iterate through requested retailers
    for retailer in retailers:
        # Skip invalid retailer names
        if retailer not in connector_map:
            logger.warning("Unknown retailer '%s', skipping...", retailer)
            continue

        try:
            # Instantiate connector for this retailer
            logger.debug("Instantiating connector for retailer: %s", retailer)
            try:
                connector = connector_map[retailer]()
            except PicnicAuthError as init_error:
                # Picnic authentication failed during initialization
                logger.warning("Picnic authentication failed; skipping Picnic: %s", str(init_error))
                connector_results_count[retailer] = 0
                connector_status[retailer] = "auth_error"
                continue
            except RuntimeError as init_error:
                # Connector initialization failed (e.g., missing API token)
                error_msg = str(init_error).lower()
                if retailer == "picnic" and ("credential" in error_msg or "not configured" in error_msg):
                    logger.warning("Picnic disabled: %s", init_error)
                    connector_status[retailer] = "disabled"
                else:
                    logger.error("Failed to initialize %s connector: %s", retailer, init_error)
                    connector_status[retailer] = "error"
                connector_results_count[retailer] = 0
                continue
            except Exception as init_error:
                logger.error("Unexpected error initializing %s connector: %s", retailer, init_error, exc_info=True)
                connector_results_count[retailer] = 0
                connector_status[retailer] = "error"
                continue
            
            # Search products for this retailer (returns List[Dict[str, Any]])
            logger.debug("Calling connector.search_products for %s with query=%r size=%d page=%d", 
                        retailer, query, size_per_retailer, page)
            try:
                items = connector.search_products(query, size=size_per_retailer, page=page)
                logger.info("Connector %s returned %d raw products", retailer, len(items) if items else 0)
                connector_results_count[retailer] = len(items) if items else 0
                # Mark as OK if search succeeded
                if retailer not in connector_status:
                    connector_status[retailer] = "ok"
            except PicnicAuthError as search_error:
                # Picnic auth error during search
                logger.warning("Picnic authentication failed; skipping Picnic results: %s", str(search_error))
                items = []
                connector_results_count[retailer] = 0
                connector_status[retailer] = "auth_error"
            except RuntimeError as search_error:
                # Config error during search
                error_msg = str(search_error).lower()
                if retailer == "picnic" and ("credential" in error_msg or "not configured" in error_msg):
                    logger.warning("Picnic disabled during search: %s", search_error)
                    connector_status[retailer] = "disabled"
                else:
                    logger.error("RuntimeError during %s search: %s", retailer, search_error)
                    connector_status[retailer] = "error"
                items = []
                connector_results_count[retailer] = 0
            except Exception as search_error:
                # Other errors during search
                logger.error("Unexpected error during %s search: %s", retailer, search_error, exc_info=True)
                items = []
                connector_results_count[retailer] = 0
                connector_status[retailer] = "error"
            
            if not items:
                logger.debug("No products returned from %s connector for query=%r", retailer, query)
                continue
            
            # Convert dicts to ProductInternal for internal processing
            mapped_count = 0
            for item in items:
                try:
                    # Create a copy to avoid modifying the original
                    item_copy = dict(item)
                    # Track if price was originally missing (for sorting/final output)
                    price_was_missing = "price" not in item_copy and "price_eur" not in item_copy
                    
                    # Normalize ID format: "{retailer}:{id}"
                    if ":" not in str(item_copy.get("id", "")):
                        item_copy["id"] = f"{retailer}:{item_copy.get('id', '')}"
                    # Ensure price is set (use price_eur if price not present, default to 9999 for missing)
                    if "price" not in item_copy:
                        item_copy["price"] = item_copy.get("price_eur", 9999.0 if price_was_missing else 0.0)
                    # Ensure price_eur is set for backward compatibility
                    if "price_eur" not in item_copy:
                        item_copy["price_eur"] = item_copy.get("price", 9999.0 if price_was_missing else 0.0)
                    # Map url to product_url if needed
                    if "product_url" not in item_copy and "url" in item_copy:
                        item_copy["product_url"] = item_copy["url"]
                    # Map raw to source_raw for ProductInternal
                    if "raw" in item_copy and "source_raw" not in item_copy:
                        item_copy["source_raw"] = item_copy["raw"]
                    # Store original price state for final output
                    item_copy["_price_was_missing"] = price_was_missing
                    
                    # Convert to ProductInternal - this may raise ValidationError if required fields are missing
                    internal_product = ProductInternal(**item_copy)
                    internal_products.append(internal_product)
                    mapped_count += 1
                except Exception as e:
                    # Log validation/conversion errors but continue processing other items
                    logger.error("Failed to convert product dict to ProductInternal for retailer %s: %s. Item: %s", 
                                retailer, e, str(item)[:200], exc_info=True)
                    continue
            
            logger.info("Connector %s: raw_count=%d mapped_to_ProductInternal=%d", 
                       retailer, connector_results_count[retailer], mapped_count)
            
            # Mark connector as OK if we got here successfully
            if retailer not in connector_status:
                connector_status[retailer] = "ok"
                
        except PicnicAuthError as e:
            # Picnic authentication error - log clearly and continue
            logger.warning("Picnic authentication failed: %s. Skipping Picnic results for this request.", e)
            connector_results_count[retailer] = 0
            connector_status[retailer] = "auth_error"
            continue
        except RuntimeError as e:
            # Connector initialization or config errors - log and continue
            error_msg = str(e).lower()
            if retailer == "picnic" and ("credential" in error_msg or "not configured" in error_msg):
                logger.warning("Picnic disabled: %s", e)
                connector_status[retailer] = "disabled"
            else:
                logger.error("RuntimeError searching %s: %s", retailer, e, exc_info=True)
            connector_results_count[retailer] = 0
            if retailer not in connector_status:
                connector_status[retailer] = "error"
            continue
        except Exception as e:
            # Log any other unexpected errors with full traceback
            logger.error("Unexpected error searching %s: %s", retailer, e, exc_info=True)
            connector_results_count[retailer] = 0
            connector_status[retailer] = "error"
            continue

    logger.info("Total ProductInternal objects before health tagging: %d (from retailers: %s)", 
                len(internal_products), connector_results_count)
    
    # Convert ProductInternal to ProductPublic and add health tags
    public_products: List[ProductPublic] = []
    conversion_errors = 0
    for internal_product in internal_products:
        try:
            # Tag health using the internal product's dict representation
            product_dict = internal_product.model_dump()
            # Ensure price_eur is in the dict for tag_health compatibility
            if "price_eur" not in product_dict:
                product_dict["price_eur"] = product_dict.get("price", 0.0)
            health_tag = tag_health(product_dict)
            
            # Convert to ProductPublic (as dict first to add price_eur, then create model)
            product_dict = {
                "id": internal_product.id,
                "retailer": internal_product.retailer,
                "name": internal_product.name,
                "brand": internal_product.brand,
                "category": internal_product.category,
                "image_url": internal_product.image_url,
                "url": internal_product.product_url,  # Map product_url to url
                "price": internal_product.price,
                "price_eur": internal_product.price,  # Set price_eur for backward compatibility
                "currency": internal_product.currency,
                "price_per_unit": internal_product.price_per_unit,
                "unit": internal_product.unit or internal_product.unit_size,  # Legacy unit field
                "unit_size": internal_product.unit_size,  # Legacy field
                "quantity": internal_product.quantity,
                "quantity_unit": internal_product.quantity_unit,
                "is_promotion": internal_product.is_promotion,
                "promo_text": internal_product.promo_text,
                "health_tag": health_tag,
                "is_cheapest": None,  # Will be set by group_by_name_and_mark_cheapest
                "is_cheapest_total": False,  # Will be set by mark_cheapest
                "is_cheapest_per_unit": False,  # Will be set by mark_cheapest
                "raw": internal_product.source_raw,
            }
            public_product = ProductPublic(**product_dict)
            public_products.append(public_product)
        except Exception as e:
            # Log conversion errors but continue
            logger.error("Failed to convert ProductInternal to ProductPublic: %s. Product ID: %s", 
                        e, internal_product.id if hasattr(internal_product, 'id') else 'unknown', exc_info=True)
            conversion_errors += 1
            continue
    
    if conversion_errors > 0:
        logger.warning("Failed to convert %d ProductInternal objects to ProductPublic", conversion_errors)
    
    logger.info("Total ProductPublic objects after conversion: %d", len(public_products))

    # Apply health filter if specified
    if health_filter:
        health_filter_lower = health_filter.lower()
        if health_filter_lower in ("healthy", "unhealthy"):
            before_filter = len(public_products)
            public_products = [p for p in public_products if p.health_tag == health_filter_lower]
            logger.info("Health filter '%s' applied: %d -> %d products", health_filter_lower, before_filter, len(public_products))
        # Note: "neutral" could also be added as a filter option if needed

    # Mark cheapest products across all results (not grouped by name)
    # This marks is_cheapest_total and is_cheapest_per_unit flags
    public_products = mark_cheapest(public_products)
    logger.debug("Marked cheapest products: total price and price per unit")
    
    # Also group by name and mark cheapest in each group (for backward compatibility)
    # This updates is_cheapest to match name-grouped logic, while keeping is_cheapest_total
    # and is_cheapest_per_unit for the new comparison logic
    before_grouping = len(public_products)
    public_products = group_by_name_and_mark_cheapest(public_products)
    logger.debug("Grouped by name: %d -> %d products (should be same)", before_grouping, len(public_products))

    # Sort results using the new comparison module
    public_products = sort_products(public_products, sort_by)
    logger.debug("Sorted products using sort_by=%r", sort_by)

    # Convert to dict format for backward compatibility with existing API
    # This maintains compatibility with the current API layer that expects dicts
    # Ensure both price and price_eur are present in the dict for backward compatibility
    results = []
    for p in public_products:
        try:
            product_dict = p.model_dump(mode="json", by_alias=True)
            # Ensure price_eur is present (backward compatibility)
            if "price_eur" not in product_dict:
                product_dict["price_eur"] = product_dict.get("price", 0.0)
            # Also ensure price is present
            if "price" not in product_dict:
                product_dict["price"] = product_dict.get("price_eur", 0.0)
            # For missing prices, ensure price_eur is 9999 (matches sorting logic expectation)
            # The test accepts either None or 9999, but sorting uses 9999, so use 9999
            if product_dict.get("price", 0) >= 9999.0:
                product_dict["price_eur"] = 9999.0
            results.append(product_dict)
        except Exception as e:
            logger.error("Failed to serialize ProductPublic to dict: %s", e, exc_info=True)
            continue
    
    logger.info("Aggregated search response size: %d products (from retailers: %s, status: %s)", 
                len(results), connector_results_count, connector_status)
    
    # Log Picnic status specifically if it's not OK
    if "picnic" in connector_status and connector_status["picnic"] != "ok":
        logger.info("Picnic status: %s (AH and Jumbo results are unaffected)", connector_status["picnic"])
    
    # Return results with connector status
    return {
        "results": results,
        "connectors_status": connector_status
    }
