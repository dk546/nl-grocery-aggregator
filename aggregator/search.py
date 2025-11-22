"""
Aggregated search function that searches across multiple retailers.

This module provides the core search aggregation functionality that:
- Instantiates connectors for the selected retailers
- Performs parallel searches across retailers
- Adds health tags to each product
- Merges and sorts results based on the specified sort criteria

The aggregated_search function is the main entry point for product searches
in the aggregator system, unifying results from AH, Jumbo, and Picnic.
"""

from typing import List, Dict, Any

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


def aggregated_search(
    query: str,
    retailers: List[str],
    size_per_retailer: int = 10,
    page: int = 0,
    sort_by: str = "price",
) -> List[Dict[str, Any]]:
    """
    Perform an aggregated search across multiple retailers.
    
    This function searches for products across the specified retailers, normalizes
    the results, adds health tags, and returns a merged, sorted list of products.
    
    Args:
        query: Search query string (e.g., "melk", "brood")
        retailers: List of retailer identifiers to search (e.g., ["ah", "jumbo", "picnic"])
        size_per_retailer: Number of results to fetch from each retailer (default: 10)
        page: Page number for pagination (0-indexed, default: 0)
        sort_by: Sort criterion - currently only "price" is supported (default: "price")
        
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
        - raw: Raw product data from retailer API
        
        Results are sorted by price (lowest first) if sort_by="price".
        
    Examples:
        >>> results = aggregated_search("melk", ["ah", "picnic"], size_per_retailer=5)
        >>> len(results) <= 10  # Up to 5 from each retailer
        True
        >>> all("health_tag" in r for r in results)
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

    # Sort results based on sort_by parameter
    if sort_by == "price":
        # Sort by price (lowest first), handle missing prices by putting them last
        results.sort(key=lambda x: x.get("price_eur") or 9999)
    # Future: Add more sort options (e.g., "name", "health", "retailer")

    return results
