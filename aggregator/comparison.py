"""
Comparison and sorting utilities for products.

This module provides functions for marking cheapest products and sorting product lists
across all results, not just within name groups. This allows the backend to be the
source of truth for price comparisons and cheapest-highlighting.

Key functions:
- mark_cheapest: Marks products with is_cheapest_total and is_cheapest_per_unit flags
- sort_products: Sorts products by various criteria with stable tie-breaking
"""

from typing import List, Optional
from aggregator.models import ProductPublic


def mark_cheapest(products: List[ProductPublic]) -> List[ProductPublic]:
    """
    Mark cheapest products across all results (not grouped by name).
    
    This function identifies and marks:
    - is_cheapest_total: Products with the lowest total price (price field)
    - is_cheapest_per_unit: Products with the lowest price_per_unit (where available)
    
    Rules:
    - Products with missing price are ignored for is_cheapest_total
    - Products with missing price_per_unit are ignored for is_cheapest_per_unit
    - Ties are allowed (multiple products can have the same flag set to True)
    - If no products qualify for a metric, all flags for that metric remain False
    
    Args:
        products: List of ProductPublic objects to analyze
        
    Returns:
        List of ProductPublic objects with is_cheapest_total and is_cheapest_per_unit
        flags updated. Input list is not mutated; new objects are created.
        
    Examples:
        >>> from aggregator.models import ProductPublic
        >>> products = [
        ...     ProductPublic(id="1", name="Milk", retailer="ah", price=1.50, price_per_unit=1.50, quantity=1.0, quantity_unit="L", health_tag="neutral"),
        ...     ProductPublic(id="2", name="Milk", retailer="jumbo", price=1.99, price_per_unit=1.99, quantity=1.0, quantity_unit="L", health_tag="neutral"),
        ... ]
        >>> result = mark_cheapest(products)
        >>> result[0].is_cheapest_total
        True
        >>> result[1].is_cheapest_total
        False
    """
    if not products:
        return products
    
    # Find minimum total price (ignore None/missing prices and 9999.0 sentinel)
    # Note: price is required, but 9999.0 is used as a sentinel for missing prices in sorting
    valid_prices = [p.price for p in products if p.price is not None and p.price < 9999.0]
    min_total_price = min(valid_prices) if valid_prices else None
    
    # Find minimum price_per_unit (ignore None/missing)
    valid_price_per_unit = [p.price_per_unit for p in products if p.price_per_unit is not None]
    min_price_per_unit = min(valid_price_per_unit) if valid_price_per_unit else None
    
    # Create new ProductPublic objects with updated flags
    result: List[ProductPublic] = []
    for product in products:
        # Determine is_cheapest_total
        is_cheapest_total = False
        if min_total_price is not None and product.price is not None and product.price < 9999.0:
            # Use small epsilon for float comparison
            is_cheapest_total = abs(product.price - min_total_price) < 0.001
        
        # Determine is_cheapest_per_unit
        is_cheapest_per_unit = False
        if min_price_per_unit is not None and product.price_per_unit is not None:
            is_cheapest_per_unit = abs(product.price_per_unit - min_price_per_unit) < 0.001
        
        # Create new product with updated flags
        product_dict = product.model_dump()
        product_dict["is_cheapest_total"] = is_cheapest_total
        product_dict["is_cheapest_per_unit"] = is_cheapest_per_unit
        # Keep existing is_cheapest for backward compatibility (set to is_cheapest_total)
        product_dict["is_cheapest"] = is_cheapest_total
        
        result.append(ProductPublic(**product_dict))
    
    return result


def sort_products(products: List[ProductPublic], sort_by: Optional[str] = None) -> List[ProductPublic]:
    """
    Sort products by the specified criterion with stable tie-breaking.
    
    Supported sort modes:
    - "price_asc": Price low to high
    - "price_desc": Price high to low
    - "price_per_unit_asc": Price per unit low to high
    - "price_per_unit_desc": Price per unit high to low
    - "retailer": Retailer name alphabetical
    - "health": Health tag (healthy first, then neutral, then unhealthy)
    - None or empty string: No sorting (preserves input order)
    
    Tie-breaking (applied when primary sort values are equal):
    - For price sorts: break ties by name (alphabetical), then retailer
    - For price_per_unit sorts: break ties by name, then retailer
    - For retailer sorts: break ties by name, then price
    - For health sorts: break ties by price, then name
    
    Args:
        products: List of ProductPublic objects to sort
        sort_by: Sort mode string (see supported modes above)
        
    Returns:
        New sorted list of ProductPublic objects. Input list is not mutated.
        
    Examples:
        >>> from aggregator.models import ProductPublic
        >>> products = [
        ...     ProductPublic(id="1", name="Milk", retailer="ah", price=2.0, health_tag="neutral"),
        ...     ProductPublic(id="2", name="Bread", retailer="jumbo", price=1.5, health_tag="neutral"),
        ... ]
        >>> sorted_prods = sort_products(products, "price_asc")
        >>> sorted_prods[0].name
        'Bread'
    """
    if not products or not sort_by:
        # Return a copy to avoid mutating input
        return list(products)
    
    # Normalize sort_by (handle legacy values)
    sort_by_lower = sort_by.lower()
    
    # Map legacy/aliased sort values to canonical modes
    sort_mode_map = {
        "price": "price_asc",
        "price_low_high": "price_asc",
        "price_high_low": "price_desc",
        "price_per_unit": "price_per_unit_asc",
        "retailer": "retailer",
        "health": "health",
    }
    
    canonical_sort = sort_mode_map.get(sort_by_lower, sort_by_lower)
    
    # Health priority for sorting
    health_priority = {
        "healthy": 1,
        "neutral": 2,
        "unhealthy": 3,
    }
    
    # Create a copy for sorting
    sorted_products = list(products)
    
    if canonical_sort == "price_asc":
        sorted_products.sort(key=lambda x: (
            x.price if x.price is not None else 9999,
            (x.name or "").lower(),
            x.retailer.lower()
        ))
    elif canonical_sort == "price_desc":
        sorted_products.sort(key=lambda x: (
            -(x.price if x.price is not None else -1),  # Negate for descending
            (x.name or "").lower(),
            x.retailer.lower()
        ))
    elif canonical_sort == "price_per_unit_asc":
        sorted_products.sort(key=lambda x: (
            x.price_per_unit if x.price_per_unit is not None else 9999,
            (x.name or "").lower(),
            x.retailer.lower()
        ))
    elif canonical_sort == "price_per_unit_desc":
        sorted_products.sort(key=lambda x: (
            -(x.price_per_unit if x.price_per_unit is not None else -1),
            (x.name or "").lower(),
            x.retailer.lower()
        ))
    elif canonical_sort == "retailer":
        sorted_products.sort(key=lambda x: (
            x.retailer.lower(),
            (x.name or "").lower(),
            x.price if x.price is not None else 9999
        ))
    elif canonical_sort == "health":
        sorted_products.sort(key=lambda x: (
            health_priority.get(x.health_tag, 2),
            x.price if x.price is not None else 9999,
            (x.name or "").lower()
        ))
    else:
        # Unknown sort mode: default to price_asc
        sorted_products.sort(key=lambda x: (
            x.price if x.price is not None else 9999,
            (x.name or "").lower(),
            x.retailer.lower()
        ))
    
    return sorted_products

