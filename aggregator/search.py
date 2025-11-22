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
"""

from typing import List, Dict, Any, Optional
from collections import defaultdict

from .connectors.ah_connector import AHConnector
from .connectors.jumbo_connector import JumboConnector
from .connectors.picnic_connector import PicnicConnector
from .health import tag_health


# Map retailer names to their connector classes
CONNECTOR_MAP = {
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


def group_by_name_and_mark_cheapest(products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Group products by normalized name and mark the cheapest in each group.
    
    Products are grouped by their name (case-insensitive). Within each group,
    the cheapest product (lowest price_eur) is marked with is_cheapest=True,
    and all others are marked with is_cheapest=False.
    
    Args:
        products: List of product dictionaries, each must have "name" and "price_eur" keys
        
    Returns:
        List of product dictionaries with added "is_cheapest" field
        
    Examples:
        >>> products = [
        ...     {"name": "Melk", "price_eur": 1.99, "retailer": "ah"},
        ...     {"name": "melk", "price_eur": 2.50, "retailer": "jumbo"},
        ...     {"name": "Bread", "price_eur": 1.50, "retailer": "ah"}
        ... ]
        >>> result = group_by_name_and_mark_cheapest(products)
        >>> # Melk group: cheapest (1.99) should be marked True
        >>> # Bread group: only one item, should be marked True
    """
    # Group products by normalized (lowercase) name
    groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    
    for product in products:
        normalized_name = (product.get("name") or "").lower().strip()
        groups[normalized_name].append(product)
    
    # Process each group and mark cheapest
    result = []
    for normalized_name, group in groups.items():
        # Find the cheapest product in the group
        # Handle missing prices by treating them as very expensive (9999)
        cheapest_index = 0
        cheapest_price = group[0].get("price_eur") or 9999
        
        for i, product in enumerate(group[1:], start=1):
            price = product.get("price_eur") or 9999
            if price < cheapest_price:
                cheapest_price = price
                cheapest_index = i
        
        # Mark cheapest and add all products to result
        for i, product in enumerate(group):
            product["is_cheapest"] = (i == cheapest_index)
            result.append(product)
    
    return result


def aggregated_search(
    query: str,
    retailers: List[str],
    size_per_retailer: int = 10,
    page: int = 0,
    sort_by: str = "price",
    health_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Perform an aggregated search across multiple retailers.
    
    This function searches for products across the specified retailers, normalizes
    the results, adds health tags, filters by health if requested, groups by name
    to mark cheapest options, and returns a merged, sorted list of products.
    
    Args:
        query: Search query string (e.g., "melk", "brood")
        retailers: List of retailer identifiers to search (e.g., ["ah", "jumbo", "picnic"])
        size_per_retailer: Number of results to fetch from each retailer (default: 10)
        page: Page number for pagination (0-indexed, default: 0)
        sort_by: Sort criterion - "price", "retailer", or "health" (default: "price")
        health_filter: Optional filter for health tag - "healthy" or "unhealthy" (default: None)
        
    Returns:
        List of product dictionaries, each containing:
        - retailer: Retailer identifier
        - id: Product identifier
        - name: Product name
        - price_eur: Price in euros
        - unit: Unit description
        - unit_size: Size information
        - image_url: Product image URL
        - url: Product URL
        - health_tag: Health category ("healthy", "unhealthy", or "neutral")
        - is_cheapest: Boolean indicating if this is the cheapest option in its name group
        - raw: Raw product data from retailer API
        
        Results are sorted according to sort_by parameter:
        - "price": By price (lowest first)
        - "retailer": By retailer name (alphabetical)
        - "health": By health tag (healthy first, then neutral, then unhealthy)
        
    Examples:
        >>> results = aggregated_search("melk", ["ah", "picnic"], size_per_retailer=5)
        >>> len(results) <= 10  # Up to 5 from each retailer
        True
        >>> all("health_tag" in r for r in results)
        True
        >>> all("is_cheapest" in r for r in results)
        True
    """
    results = []

    # Iterate through requested retailers
    for retailer in retailers:
        # Skip invalid retailer names
        if retailer not in CONNECTOR_MAP:
            print(f"Warning: Unknown retailer '{retailer}', skipping...")
            continue

        try:
            # Instantiate connector for this retailer
            connector = CONNECTOR_MAP[retailer]()
            
            # Search products for this retailer
            items = connector.search_products(query, size=size_per_retailer, page=page)

            # Add health tag to each product and append to results
            for item in items:
                item["health_tag"] = tag_health(item)
                results.append(item)
                
        except Exception as e:
            # Log error but continue with other retailers
            print(f"Error searching {retailer}: {e}")
            continue

    # Apply health filter if specified
    if health_filter:
        health_filter_lower = health_filter.lower()
        if health_filter_lower in ("healthy", "unhealthy"):
            results = [r for r in results if r.get("health_tag") == health_filter_lower]
        # Note: "neutral" could also be added as a filter option if needed

    # Group by name and mark cheapest in each group
    results = group_by_name_and_mark_cheapest(results)

    # Sort results based on sort_by parameter
    if sort_by == "price":
        # Sort by price (lowest first), handle missing prices by putting them last
        results.sort(key=lambda x: x.get("price_eur") or 9999)
    elif sort_by == "retailer":
        # Sort by retailer name (alphabetical)
        results.sort(key=lambda x: x.get("retailer", "").lower())
    elif sort_by == "health":
        # Sort by health tag: healthy first, then neutral, then unhealthy
        results.sort(key=lambda x: (
            HEALTH_PRIORITY.get(x.get("health_tag", "neutral"), 2),
            x.get("price_eur") or 9999  # Secondary sort by price for same health tag
        ))
    # Default to price sorting if sort_by is unrecognized
    else:
        results.sort(key=lambda x: x.get("price_eur") or 9999)

    return results
