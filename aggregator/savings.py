"""
Savings finder module for analyzing basket items and finding cheaper alternatives.

This module provides functionality to:
- Search for cheaper alternatives to items in the shopping basket
- Calculate potential savings by comparing prices (per unit and total)
- Return structured suggestions that can be applied to the basket

The savings logic uses the existing aggregated_search infrastructure to find
alternatives, ensuring consistency with the main search functionality and benefiting
from the TTL cache.
"""

import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

# Minimum price difference to consider a suggestion (in euros per unit)
# This avoids noise from tiny price differences
MIN_PRICE_DIFFERENCE_PER_UNIT = 0.01  # 1 cent minimum


@dataclass
class SavingsSuggestion:
    """A single savings opportunity suggestion."""
    type: str  # e.g., "cheaper_alternative", "healthier_alternative"
    current_item_name: str
    alternative_item_name: str
    savings_amount: float | None = None
    health_delta: str | None = None
    title: str | None = None


def find_basket_savings(
    basket_items: List[Dict[str, Any]],
    search_fn: Callable[[str, List[str], int, int, Optional[str], Optional[str]], Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Find cheaper alternatives for items in the basket and calculate potential savings.
    
    For each basket item, this function:
    1. Searches for products with the same name
    2. Filters to products that are cheaper (per unit, if available, else total price)
    3. Selects the best alternative (cheapest per unit, then cheapest total)
    4. Calculates estimated savings
    
    Args:
        basket_items: List of basket item dictionaries, each containing:
            - retailer: Retailer identifier
            - product_id: Product identifier
            - name: Product name
            - price_eur: Price per unit
            - quantity: Quantity in basket
            - line_total: Current total for this item
            - price_per_unit: Optional price per canonical unit
            - health_tag: Optional health tag
        search_fn: Function matching aggregated_search signature:
            (query: str, retailers: List[str], size_per_retailer: int, page: int,
             sort_by: Optional[str], health_filter: Optional[str]) -> Dict[str, Any]
    
    Returns:
        Dictionary with:
        - potential_savings_total: float - Total potential savings across all suggestions
        - suggestions: List[Dict] - List of savings suggestions, each containing:
            - current: Dict with current item details
            - alternative: Dict with alternative product details
            - estimated_line_total: float - Estimated total for alternative
            - estimated_savings: float - Estimated savings (current - alternative)
    
    Examples:
        >>> from aggregator.search import aggregated_search
        >>> basket = [{"name": "Melk", "retailer": "ah", "product_id": "123", 
        ...            "price_eur": 2.50, "quantity": 2, "line_total": 5.00}]
        >>> savings = find_basket_savings(basket, aggregated_search)
        >>> "potential_savings_total" in savings
        True
    """
    if not basket_items:
        return {
            "potential_savings_total": 0.0,
            "suggestions": []
        }
    
    suggestions: List[Dict[str, Any]] = []
    
    for basket_item in basket_items:
        try:
            suggestion = _find_cheaper_alternative(basket_item, search_fn)
            if suggestion:
                suggestions.append(suggestion)
        except Exception as e:
            # Log error but continue processing other items
            logger.warning(
                "Error finding alternative for basket item %s (%s): %s",
                basket_item.get("name", "unknown"),
                basket_item.get("product_id", "unknown"),
                str(e),
                exc_info=True
            )
            continue
    
    # Calculate total potential savings
    potential_savings_total = sum(
        s.get("estimated_savings", 0.0) for s in suggestions
    )
    
    return {
        "potential_savings_total": round(potential_savings_total, 2),
        "suggestions": suggestions
    }


def _find_cheaper_alternative(
    basket_item: Dict[str, Any],
    search_fn: Callable[[str, List[str], int, int, Optional[str], Optional[str]], Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """
    Find a cheaper alternative for a single basket item.
    
    Args:
        basket_item: Basket item dictionary
        search_fn: Search function (aggregated_search)
    
    Returns:
        Suggestion dictionary or None if no cheaper alternative found
    """
    # Extract current item details
    current_name = basket_item.get("name", "").strip()
    current_retailer = basket_item.get("retailer", "")
    current_product_id = str(basket_item.get("product_id", ""))
    current_price_eur = float(basket_item.get("price_eur", 0.0))
    current_price_per_unit = basket_item.get("price_per_unit")
    if current_price_per_unit is not None:
        current_price_per_unit = float(current_price_per_unit)
    current_quantity = int(basket_item.get("quantity", 1))
    current_line_total = float(basket_item.get("line_total", current_price_eur * current_quantity))
    
    if not current_name or current_price_eur <= 0:
        # Skip items without name or invalid price
        return None
    
    # Search for alternatives using the product name
    # Sort by price_per_unit_asc to get cheapest per unit first
    try:
        search_results = search_fn(
            query=current_name,
            retailers=["ah", "jumbo", "picnic", "dirk"],  # Search all retailers
            size_per_retailer=20,
            page=0,
            sort_by="price_per_unit_asc",  # Prefer per-unit price comparison
            health_filter=None  # Don't filter by health for savings analysis
        )
    except Exception as e:
        logger.debug("Search failed for '%s': %s", current_name, str(e))
        return None
    
    if not search_results or "results" not in search_results:
        return None
    
    products = search_results.get("results", [])
    if not products:
        return None
    
    # Find cheaper alternatives
    best_alternative = None
    best_alt_price_per_unit = None
    best_alt_price_eur = None
    
    for product in products:
        # Skip if it's the same product
        product_id = str(product.get("id", ""))
        # Handle both "retailer:id" and just "id" formats
        product_id_clean = product_id.split(":")[-1] if ":" in product_id else product_id
        current_product_id_clean = current_product_id.split(":")[-1] if ":" in current_product_id else current_product_id
        
        if product_id_clean == current_product_id_clean and product.get("retailer", "") == current_retailer:
            # Same product - skip
            continue
        
        # Get price information
        alt_price_eur = float(product.get("price_eur") or product.get("price", 0.0))
        alt_price_per_unit = product.get("price_per_unit")
        if alt_price_per_unit is not None:
            alt_price_per_unit = float(alt_price_per_unit)
        
        if alt_price_eur <= 0:
            continue
        
        # Determine if this is cheaper
        is_cheaper = False
        
        if current_price_per_unit is not None and alt_price_per_unit is not None:
            # Compare per-unit prices (more accurate for different sizes)
            price_diff = current_price_per_unit - alt_price_per_unit
            if price_diff >= MIN_PRICE_DIFFERENCE_PER_UNIT:
                is_cheaper = True
                comparison_price = alt_price_per_unit
        else:
            # Fall back to total price comparison
            price_diff = current_price_eur - alt_price_eur
            if price_diff >= MIN_PRICE_DIFFERENCE_PER_UNIT:
                is_cheaper = True
                comparison_price = alt_price_eur
        
        if not is_cheaper:
            continue
        
        # Select best alternative (lowest per-unit price, then lowest total price)
        if best_alternative is None:
            best_alternative = product
            best_alt_price_per_unit = alt_price_per_unit
            best_alt_price_eur = alt_price_eur
        else:
            # Compare: prefer lower per-unit price if both have it, else lower total price
            if best_alt_price_per_unit is not None and alt_price_per_unit is not None:
                if alt_price_per_unit < best_alt_price_per_unit:
                    best_alternative = product
                    best_alt_price_per_unit = alt_price_per_unit
                    best_alt_price_eur = alt_price_eur
            elif alt_price_eur < best_alt_price_eur:
                best_alternative = product
                best_alt_price_per_unit = alt_price_per_unit
                best_alt_price_eur = alt_price_eur
    
    if best_alternative is None:
        return None
    
    # Calculate estimated savings
    estimated_line_total = best_alt_price_eur * current_quantity
    estimated_savings = current_line_total - estimated_line_total
    
    if estimated_savings <= 0:
        return None
    
    # Build suggestion
    return {
        "current": {
            "retailer": current_retailer,
            "product_id": current_product_id,
            "name": current_name,
            "quantity": current_quantity,
            "price_eur": current_price_eur,
            "price_per_unit": current_price_per_unit,
            "line_total": current_line_total,
            "image_url": basket_item.get("image_url"),
            "health_tag": basket_item.get("health_tag"),
        },
        "alternative": {
            "retailer": best_alternative.get("retailer", ""),
            "product_id": str(best_alternative.get("id", "")),  # Keep full ID format (may be "retailer:id")
            "name": best_alternative.get("name", ""),
            "price_eur": best_alt_price_eur,
            "price_per_unit": best_alt_price_per_unit,
            "image_url": best_alternative.get("image_url"),
            "health_tag": best_alternative.get("health_tag"),
        },
        "estimated_line_total": round(estimated_line_total, 2),
        "estimated_savings": round(estimated_savings, 2),
    }


def get_savings_opportunities_for_basket(basket_items: List[Dict[str, Any]]) -> list[SavingsSuggestion]:
    """
    Compute a small list of savings opportunities for the given basket items.
    
    Non-invasive: read-only view, does not mutate the cart.
    
    Args:
        basket_items: List of basket item dictionaries from the cart
        
    Returns:
        List of SavingsSuggestion objects, limited to top 5 suggestions
    """
    try:
        from aggregator.search import aggregated_search
        
        if not basket_items:
            return []
        
        # Find savings using existing logic
        savings_result = find_basket_savings(basket_items, aggregated_search)
        
        suggestions_raw = savings_result.get("suggestions", [])
        
        # Convert to SavingsSuggestion objects
        suggestions = []
        for s in suggestions_raw[:5]:  # Limit to top 5
            current = s.get("current", {})
            alternative = s.get("alternative", {})
            
            # Determine type based on health delta
            current_health = current.get("health_tag")
            alt_health = alternative.get("health_tag")
            
            suggestion_type = "cheaper_alternative"
            health_delta_str = None
            
            if current_health and alt_health:
                if current_health == "unhealthy" and alt_health in ("healthy", "neutral"):
                    suggestion_type = "healthier_alternative"
                    health_delta_str = f"Improve from {current_health} to {alt_health}"
                elif current_health == "neutral" and alt_health == "healthy":
                    suggestion_type = "healthier_alternative"
                    health_delta_str = f"Improve from {current_health} to {alt_health}"
            
            # Build title
            savings_amount = s.get("estimated_savings", 0.0)
            title = f"Save €{savings_amount:.2f}"
            if health_delta_str:
                title += f" & improve health"
            
            suggestion = SavingsSuggestion(
                type=suggestion_type,
                current_item_name=current.get("name", "Current item"),
                alternative_item_name=alternative.get("name", "Alternative item"),
                savings_amount=savings_amount,
                health_delta=health_delta_str,
                title=title,
            )
            suggestions.append(suggestion)
        
        return suggestions
        
    except Exception as e:
        # Fail quietly - suggestions are a nice-to-have
        logger.debug("Error computing savings opportunities: %s", str(e), exc_info=True)
        return []


def get_savings_opportunities_for_session(session_id: str) -> list[SavingsSuggestion]:
    """
    Compute a small list of savings opportunities for the current basket.
    
    Non-invasive: read-only view, does not mutate the cart.
    
    Args:
        session_id: Session identifier for the cart
        
    Returns:
        List of SavingsSuggestion objects, limited to top 5 suggestions
    """
    try:
        # Import here to avoid circular dependencies
        from aggregator.cart import get_cart
        
        # Get cart for session
        cart = get_cart(session_id)
        
        if not cart.items:
            return []
        
        # Convert cart items to list of dicts for find_basket_savings
        basket_items = []
        for cart_item in cart.items.values():
            item_dict = {
                "retailer": cart_item.retailer,
                "product_id": cart_item.product_id,
                "name": cart_item.name,
                "price_eur": cart_item.price_eur,
                "quantity": cart_item.quantity,
                "line_total": cart_item.total_price,
                "image_url": cart_item.image_url,
                "health_tag": cart_item.health_tag,
            }
            basket_items.append(item_dict)
        
        # Use the basket-based helper
        return get_savings_opportunities_for_basket(basket_items)
        
    except Exception as e:
        # Fail quietly - suggestions are a nice-to-have
        logger.debug("Error computing savings opportunities: %s", str(e), exc_info=True)
        return []

