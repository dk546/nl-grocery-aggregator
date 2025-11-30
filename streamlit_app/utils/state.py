"""
Basket State Management Module.

This module wraps Streamlit's session_state to provide a clean API for managing
the shopping basket/cart. The basket is stored as a list of product dictionaries
in st.session_state.

Each basket item is a dictionary with:
- `id`: unique string identifier for the item (generated from product_id + retailer, or synthetic)
- `name`: product name
- `retailer`: retailer code (ah, jumbo, picnic)
- `price`: numeric price in euros
- `price_eur`: alias for price (for backward compatibility)
- `unit_price`: optional numeric unit price
- `health_tag`: optional string ("healthy", "unhealthy", "neutral")
- `product_id`: original product ID from retailer
- `quantity`: integer quantity (default: 1)
- Other optional fields: image_url, url, unit, unit_size, etc.

# NOTE: This module uses session_state, so the basket persists only for the current
    Streamlit session. When the user refreshes the page or starts a new session,
    the basket is reset.

# TODO: Future enhancements:
    - Quantities per item (currently supports quantity field, but UI may need work)
    - Weekly planner mode: assign items to specific days/meals
    - Recipe-based additions: add all ingredients from a recipe at once
    - Price optimization suggestions: swap items for cheaper alternatives
    - Health score tracking over time
    - Basket history/previous weeks
    - Save/load basket presets
    - Export basket to shopping list formats
    - Sync basket with backend cart API (POST /cart/add, GET /cart/view)
"""

import hashlib
from typing import Any, Dict, List, Optional

import streamlit as st

# Session state key for the basket
BASKET_KEY = "basket"


def _generate_item_id(item: Dict[str, Any]) -> str:
    """
    Generate a unique ID for a basket item.
    
    Prefers explicit product_id + retailer combination.
    Falls back to a hash of name + retailer + price if no product_id available.
    
    Args:
        item: Product dictionary with at least retailer and name/price
        
    Returns:
        Unique string identifier
    """
    product_id = item.get("product_id") or item.get("id")
    retailer = item.get("retailer", "")
    
    if product_id and retailer:
        return f"{retailer}:{product_id}"
    
    # Fallback: hash of name + retailer + price
    name = item.get("name", "")
    price = item.get("price") or item.get("price_eur", 0)
    key_string = f"{retailer}:{name}:{price}"
    return hashlib.md5(key_string.encode()).hexdigest()[:12]


def init_basket() -> None:
    """
    Ensure the basket exists in session state and is initialized as an empty list.
    
    Call this at the start of any page that uses the basket to ensure it's initialized.
    """
    if BASKET_KEY not in st.session_state:
        st.session_state[BASKET_KEY] = []


def get_basket() -> List[Dict[str, Any]]:
    """
    Get the current shopping basket from session state.
    
    Automatically initializes the basket if it doesn't exist.
    
    Returns:
        List of product dictionaries in the basket. Each dict contains at minimum:
        id, name, retailer, price (or price_eur), and optionally quantity, health_tag, etc.
    """
    init_basket()
    return st.session_state[BASKET_KEY]


def set_basket(items: List[Dict[str, Any]]) -> None:
    """
    Replace the entire basket with a new list of items.
    
    Args:
        items: List of product dictionaries. Each item will have an 'id' field generated
               if not already present.
    """
    init_basket()
    # Ensure all items have IDs
    for item in items:
        if "id" not in item:
            item["id"] = _generate_item_id(item)
    st.session_state[BASKET_KEY] = items


def add_to_basket(item: Dict[str, Any]) -> None:
    """
    Add an item to the shopping basket.
    
    If an item with the same ID already exists, we skip adding (no duplicates).
    This keeps the basket simple. In the future, quantities can be handled separately.
    
    Args:
        item: Product dictionary containing at minimum:
              - name: str
              - retailer: str
              - price or price_eur: float
              - Optional: product_id, health_tag, image_url, unit, unit_size, etc.
              
    # NOTE: Currently avoids duplicates based on item ID. For future quantity support,
        we could update this to increment quantity instead of skipping.
    
    # TODO: Add option to allow duplicates or merge quantities for same item.
    # TODO: Add validation to ensure item has required fields (name, retailer, price).
    """
    init_basket()
    
    # Generate ID if not present
    if "id" not in item:
        item["id"] = _generate_item_id(item)
    
    item_id = item["id"]
    
    # Check if item already exists (by ID)
    basket = get_basket()
    existing_item_ids = {basket_item.get("id") for basket_item in basket}
    
    if item_id in existing_item_ids:
        # Skip adding duplicate - item already in basket
        # TODO: In future, could increment quantity here instead
        return
    
    # Ensure price_eur exists (for backward compatibility)
    if "price_eur" not in item and "price" in item:
        item["price_eur"] = item["price"]
    elif "price" not in item and "price_eur" in item:
        item["price"] = item["price_eur"]
    
    # Set default quantity if not specified
    if "quantity" not in item:
        item["quantity"] = 1
    
    # Add new item
    basket.append(item.copy())


def remove_from_basket(item_id: str) -> None:
    """
    Remove an item from the basket by its ID.
    
    Args:
        item_id: Unique identifier of the item to remove
        
    # NOTE: This removes the entire item. For quantity reduction, see TODO below.
    
    # TODO: Add support for removing specific quantities instead of entire item.
    """
    init_basket()
    basket = get_basket()
    st.session_state[BASKET_KEY] = [item for item in basket if item.get("id") != item_id]


def clear_basket() -> None:
    """Clear all items from the shopping basket."""
    init_basket()
    st.session_state[BASKET_KEY] = []


def basket_summary() -> Dict[str, Any]:
    """
    Compute and return a summary of the basket contents.
    
    Returns:
        Dictionary with:
        - count_items: number of items in basket
        - total_price: sum of all item prices (considering quantity)
        - unique_retailers: set of retailer codes
        - unique_retailer_count: number of unique retailers
        - total_quantity: sum of all quantities
    """
    basket = get_basket()
    
    total_price = 0.0
    retailers = set()
    total_quantity = 0
    
    for item in basket:
        # Calculate item total (price * quantity)
        price = item.get("price") or item.get("price_eur", 0.0)
        quantity = item.get("quantity", 1)
        total_price += float(price) * quantity
        
        # Track retailers
        retailer = item.get("retailer")
        if retailer:
            retailers.add(retailer)
        
        # Sum quantities
        total_quantity += quantity
    
    return {
        "count_items": len(basket),
        "total_price": total_price,
        "unique_retailers": retailers,
        "unique_retailer_count": len(retailers),
        "total_quantity": total_quantity,
    }


# Backward compatibility: keep old function names for now
def get_basket_total() -> float:
    """
    Calculate total price of all items in basket (considering quantities).
    
    Returns:
        Total price in euros.
    """
    return basket_summary()["total_price"]


def get_basket_retailers() -> List[str]:
    """
    Get unique list of retailers represented in the basket.
    
    Returns:
        List of unique retailer identifiers, sorted.
    """
    return sorted(list(basket_summary()["unique_retailers"]))


# Legacy session ID function (kept for backward compatibility if needed elsewhere)
def get_session_id() -> str:
    """
    Get or create a session ID for cart isolation.
    
    Returns:
        Session ID string. Uses Streamlit's built-in session ID if available,
        otherwise defaults to a local session key.
    """
    if "session_id" not in st.session_state:
        st.session_state.session_id = f"streamlit-{id(st.session_state)}"
    return st.session_state.session_id
