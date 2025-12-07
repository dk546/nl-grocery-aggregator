"""
In-memory cart store for managing shopping carts per session.

This module provides an in-memory cart management system that stores carts
keyed by session_id. This is suitable for MVP/development but should be
replaced with a persistent store (database, Redis, etc.) for production.

The cart store:
- Maintains a dictionary of carts indexed by session_id
- Provides operations to get, add items to, and remove items from carts
- Automatically creates a new cart if one doesn't exist for a session

Note: This is a simple in-memory implementation. Carts will be lost on server
restart. For production, consider using Redis or a database-backed solution.
"""

from typing import Dict

from .models import Cart, CartItem

# In-memory store: session_id -> Cart
# Used as fallback when DATABASE_URL is not set
# In production with DATABASE_URL set, carts are stored in Postgres
CART_STORE: Dict[str, Cart] = {}


def get_cart(session_id: str) -> Cart:
    """
    Retrieve the cart for a given session_id.
    
    If no cart exists for the session_id, a new empty cart is created and returned.
    
    Uses database storage if DATABASE_URL is set, otherwise falls back to in-memory storage.
    
    Args:
        session_id: Unique identifier for the user session
        
    Returns:
        Cart instance for the session (existing or newly created)
    """
    # Try database first if enabled
    try:
        from .db import db_is_enabled, db_get_cart_items
        
        if db_is_enabled():
            # Fetch items from database
            items_data = db_get_cart_items(session_id)
            
            # Convert to CartItem objects and build Cart
            cart_items = {}
            for item_data in items_data:
                item = CartItem(**item_data)
                key = f"{item.retailer}:{item.product_id}"
                cart_items[key] = item
            
            return Cart(items=cart_items)
    except Exception as e:
        # If DB fails, fall back to in-memory store
        logger = __import__("logging").getLogger(__name__)
        logger.debug(f"Database cart fetch failed, falling back to in-memory: {e}")
    
    # Fallback to in-memory store
    if session_id not in CART_STORE:
        CART_STORE[session_id] = Cart(items={})
    return CART_STORE[session_id]


def add_to_cart(session_id: str, item_data: dict) -> Cart:
    """
    Add an item to the cart for a given session.
    
    Creates a CartItem from the provided item_data dictionary and adds it to the cart.
    If an item with the same retailer and product_id already exists, quantities are
    accumulated.
    
    Uses database storage if DATABASE_URL is set, otherwise falls back to in-memory storage.
    
    Args:
        session_id: Unique identifier for the user session
        item_data: Dictionary containing cart item data (must match CartItem fields):
            - retailer: Retailer identifier
            - product_id: Product identifier
            - name: Product name
            - price_eur: Price per unit
            - quantity: Quantity to add (default: 1)
            - image_url: Product image URL (optional)
            - health_tag: Health tag (optional)
            
    Returns:
        Updated Cart instance after adding the item
        
    Raises:
        ValidationError: If item_data doesn't match CartItem schema
    """
    cart = get_cart(session_id)
    item = CartItem(**item_data)
    cart.add(item)
    
    # Persist to database if enabled
    try:
        from .db import db_is_enabled, db_replace_cart
        
        if db_is_enabled():
            # Convert cart items to list of dicts for database
            items_list = [item.model_dump() for item in cart.items.values()]
            db_replace_cart(session_id, items_list)
    except Exception as e:
        # If DB fails, continue with in-memory (already updated)
        logger = __import__("logging").getLogger(__name__)
        logger.debug(f"Database cart update failed, using in-memory only: {e}")
    
    return cart


def remove_from_cart(session_id: str, retailer: str, product_id: str, qty: int = 1) -> Cart:
    """
    Remove an item from the cart or reduce its quantity.
    
    Removes the specified quantity of an item from the cart. If the quantity to remove
    is greater than or equal to the item's quantity, the item is completely removed.
    
    Uses database storage if DATABASE_URL is set, otherwise falls back to in-memory storage.
    
    Args:
        session_id: Unique identifier for the user session
        retailer: Retailer identifier
        product_id: Product identifier
        qty: Quantity to remove (default: 1)
        
    Returns:
        Updated Cart instance after removing/reducing the item
        
    Note:
        If the item doesn't exist in the cart, the operation is a no-op (no error raised).
    """
    cart = get_cart(session_id)
    cart.remove(retailer, product_id, qty)
    
    # Persist to database if enabled
    try:
        from .db import db_is_enabled, db_replace_cart
        
        if db_is_enabled():
            # Convert cart items to list of dicts for database
            items_list = [item.model_dump() for item in cart.items.values()]
            db_replace_cart(session_id, items_list)
    except Exception as e:
        # If DB fails, continue with in-memory (already updated)
        logger = __import__("logging").getLogger(__name__)
        logger.debug(f"Database cart update failed, using in-memory only: {e}")
    
    return cart


def replace_cart(session_id: str, items: list[dict]) -> Cart:
    """
    Replace the entire cart contents with a new list of items.
    
    This clears all existing items and adds the provided items. Useful for applying
    saved basket templates.
    
    Uses database storage if DATABASE_URL is set, otherwise falls back to in-memory storage.
    
    Args:
        session_id: Unique identifier for the user session
        items: List of item dictionaries (must match CartItem fields)
        
    Returns:
        Updated Cart instance with new items
        
    Raises:
        ValidationError: If any item_data doesn't match CartItem schema
    """
    # Create a new empty cart
    cart = Cart(items={})
    
    # Add all items
    for item_data in items:
        item = CartItem(**item_data)
        cart.add(item)
    
    # Persist to database if enabled
    try:
        from .db import db_is_enabled, db_replace_cart
        
        if db_is_enabled():
            # Convert cart items to list of dicts for database
            items_list = [item.model_dump() for item in cart.items.values()]
            db_replace_cart(session_id, items_list)
        else:
            # Fallback to in-memory store
            CART_STORE[session_id] = cart
    except Exception as e:
        # If DB fails, fall back to in-memory store
        logger = __import__("logging").getLogger(__name__)
        logger.debug(f"Database cart replace failed, falling back to in-memory: {e}")
        CART_STORE[session_id] = cart
    
    # Log basket update event (non-blocking)
    try:
        from aggregator.events import log_event
        log_event(
            "basket_updated",
            session_id=session_id,
            payload={
                "total_items": len(cart.items),
                "total_value": cart.total(),
                "update_type": "replace",
            },
        )
    except Exception:
        pass  # Non-blocking
    
    return cart

