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

# Maximum price increase (as percentage) to consider for healthier alternatives
# e.g., 0.10 = 10% - won't suggest healthier if price is more than 10% higher
MAX_PRICE_INCREASE_FOR_HEALTHIER = 0.10

# Health tag ordering for comparison (higher number = healthier)
HEALTH_ORDER = {
    "unhealthy": 0,
    "neutral": 1,
    "healthy": 2,
}


def _is_healthier(new_tag: str, current_tag: str) -> bool:
    """
    Check if new_tag represents a healthier option than current_tag.
    
    Args:
        new_tag: Health tag of the alternative product
        current_tag: Health tag of the current item
        
    Returns:
        True if new_tag is healthier than current_tag, False otherwise
    """
    new_order = HEALTH_ORDER.get(new_tag or "neutral", 1)
    current_order = HEALTH_ORDER.get(current_tag or "neutral", 1)
    return new_order > current_order


@dataclass
class SavingsSuggestion:
    """A single savings opportunity suggestion."""
    type: str  # "cheaper", "healthier", "cheaper_and_healthier"
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
    
    # Also look for healthier-only alternatives (when no cheaper option found)
    for basket_item in basket_items:
        try:
            # Check if we already have a suggestion for this item (cheaper)
            item_suggestions = [s for s in suggestions if s.get("current", {}).get("product_id") == str(basket_item.get("product_id", ""))]
            if item_suggestions:
                # Already have a cheaper suggestion, skip healthier-only
                continue
            
            # Try to find a healthier alternative
            healthier_suggestion = _find_healthier_alternative(basket_item, search_fn)
            if healthier_suggestion:
                suggestions.append(healthier_suggestion)
        except Exception as e:
            logger.warning(
                "Error finding healthier alternative for basket item %s (%s): %s",
                basket_item.get("name", "unknown"),
                basket_item.get("product_id", "unknown"),
                str(e),
                exc_info=True
            )
            continue
    
    # Deduplicate suggestions - prefer cheaper_and_healthier > cheaper > healthier
    # Group by current product_id and keep the best suggestion
    suggestion_map: Dict[str, Dict[str, Any]] = {}
    for suggestion in suggestions:
        current_product_id = suggestion.get("current", {}).get("product_id", "")
        if not current_product_id:
            continue
        
        existing = suggestion_map.get(current_product_id)
        if not existing:
            suggestion_map[current_product_id] = suggestion
        else:
            # Prioritize: cheaper_and_healthier > cheaper > healthier
            existing_type = existing.get("type", "cheaper")
            new_type = suggestion.get("type", "cheaper")
            
            priority = {
                "cheaper_and_healthier": 3,
                "cheaper": 2,
                "healthier": 1,
            }
            
            if priority.get(new_type, 0) > priority.get(existing_type, 0):
                suggestion_map[current_product_id] = suggestion
    
    # Convert back to list
    deduplicated_suggestions = list(suggestion_map.values())
    
    # Recalculate total savings (only for cheaper suggestions)
    potential_savings_total = sum(
        s.get("estimated_savings", 0.0) 
        for s in deduplicated_suggestions 
        if s.get("estimated_savings") is not None and s.get("estimated_savings", 0.0) > 0
    )
    
    return {
        "potential_savings_total": round(potential_savings_total, 2),
        "suggestions": deduplicated_suggestions
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
    
    # Check if alternative is also healthier
    current_health = basket_item.get("health_tag") or "neutral"
    alt_health = best_alternative.get("health_tag") or "neutral"
    is_also_healthier = _is_healthier(alt_health, current_health)
    
    # Determine suggestion type
    suggestion_type = "cheaper"
    if is_also_healthier:
        suggestion_type = "cheaper_and_healthier"
    
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
            "health_tag": current_health,
        },
        "alternative": {
            "retailer": best_alternative.get("retailer", ""),
            "product_id": str(best_alternative.get("id", "")),  # Keep full ID format (may be "retailer:id")
            "name": best_alternative.get("name", ""),
            "price_eur": best_alt_price_eur,
            "price_per_unit": best_alt_price_per_unit,
            "image_url": best_alternative.get("image_url"),
            "health_tag": alt_health,
        },
        "estimated_line_total": round(estimated_line_total, 2),
        "estimated_savings": round(estimated_savings, 2),
        "type": suggestion_type,
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
            
            # Get type from suggestion dict (already set by find_basket_savings)
            suggestion_type = s.get("type", "cheaper")
            
            # Build health delta string if not already present
            health_delta_str = s.get("health_delta")
            if not health_delta_str:
                current_health = current.get("health_tag") or "neutral"
                alt_health = alternative.get("health_tag") or "neutral"
                if current_health != alt_health:
                    health_delta_str = f"{current_health} → {alt_health}"
            
            # Build title based on type
            savings_amount = s.get("estimated_savings")
            title_parts = []
            
            if suggestion_type == "cheaper_and_healthier":
                if savings_amount and savings_amount > 0:
                    title_parts.append(f"Save €{savings_amount:.2f}")
                title_parts.append("& improve health")
            elif suggestion_type == "healthier":
                if savings_amount and savings_amount > 0:
                    title_parts.append(f"Save €{savings_amount:.2f}")
                title_parts.append("Healthier choice")
            else:  # cheaper
                if savings_amount and savings_amount > 0:
                    title_parts.append(f"Save €{savings_amount:.2f}")
                else:
                    title_parts.append("Cheaper option")
            
            title = " ".join(title_parts) if title_parts else "Suggested swap"
            
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

