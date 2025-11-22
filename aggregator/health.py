"""
Health tagging helper function for products.

This module provides a simple keyword-based health tagging system that categorizes
products as "healthy", "unhealthy", or "neutral" based on their names. The keywords
are in Dutch to match the Dutch grocery market context.

The tagging logic:
- Checks product name against lists of healthy and unhealthy keywords
- Returns "healthy" if healthy keywords are found
- Returns "unhealthy" if unhealthy keywords are found
- Returns "neutral" for all other products

This is a simple heuristic-based approach suitable for MVP. A production system
would likely use more sophisticated methods (ML models, nutrition databases, etc.).
"""

# Keywords for unhealthy products (Dutch grocery context)
UNHEALTHY = [
    "chips", "chocolade", "chocolate", "cola", "frisdrank", "snoep", "snoepjes",
    "bier", "wine", "wijn", "candy", "koekjes", "cookies", "snoepgoed",
    "friet", "patat", "saus", "mayonaise", "pizza", "hamburger",
    "taart", "cake", "gebak", "ijs", "ice cream", "fris",
    "suiker", "sugar", "zoet", "sweet", "gefrituurd", "fried"
]

# Keywords for healthy products (Dutch grocery context)
HEALTHY = [
    "groente", "groenten", "fruit", "vegetable", "vegetables",
    "salade", "salad", "noten", "nuts", "walnoten", "almond",
    "volkoren", "whole grain", "wholegrain", "volkorenbrood",
    "yoghurt", "kwark", "quark", "kwark",
    "vis", "fish", "zalm", "salmon", "tonijn", "tuna",
    "kip", "chicken", "kalkoen", "turkey",
    "water", "thee", "tea", "koffie", "coffee"  # beverages
]


def tag_health(product: dict) -> str:
    """
    Tag a product as healthy, unhealthy, or neutral based on its name.
    
    This function performs simple keyword matching on the product name to determine
    a health category. It checks against predefined lists of healthy and unhealthy
    keywords (in Dutch and English for the Dutch market).
    
    Args:
        product: Product dictionary containing at least a "name" key
        
    Returns:
        Health tag as string: "healthy", "unhealthy", or "neutral"
        
    Examples:
        >>> tag_health({"name": "Verse groente mix"})
        'healthy'
        >>> tag_health({"name": "Lay's chips paprika"})
        'unhealthy'
        >>> tag_health({"name": "Melk"})
        'neutral'
    """
    name = (product.get("name") or "").lower()

    # Check for healthy keywords first (higher priority)
    if any(keyword in name for keyword in HEALTHY):
        return "healthy"
    
    # Check for unhealthy keywords
    if any(keyword in name for keyword in UNHEALTHY):
        return "unhealthy"
    
    # Default to neutral
    return "neutral"
