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
# In production, this would be replaced with Redis, database, etc.
CART_STORE: Dict[str, Cart] = {}


def get_cart(session_id: str) -> Cart:
    """
    Retrieve the cart for a given session_id.
    
    If no cart exists for the session_id, a new empty cart is created and returned.
    
    Args:
        session_id: Unique identifier for the user session
        
    Returns:
        Cart instance for the session (existing or newly created)
    """
    if session_id not in CART_STORE:
        CART_STORE[session_id] = Cart(items={})
    return CART_STORE[session_id]


def add_to_cart(session_id: str, item_data: dict) -> Cart:
    """
    Add an item to the cart for a given session.
    
    Creates a CartItem from the provided item_data dictionary and adds it to the cart.
    If an item with the same retailer and product_id already exists, quantities are
    accumulated.
    
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
    return cart


def remove_from_cart(session_id: str, retailer: str, product_id: str, qty: int = 1) -> Cart:
    """
    Remove an item from the cart or reduce its quantity.
    
    Removes the specified quantity of an item from the cart. If the quantity to remove
    is greater than or equal to the item's quantity, the item is completely removed.
    
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
    return cart

