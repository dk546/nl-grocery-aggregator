from typing import Dict
from .models import Cart, CartItem

_CARTS: Dict[str, Cart] = {}  # session_id -> Cart


def get_cart(session_id: str) -> Cart:
    if session_id not in _CARTS:
        _CARTS[session_id] = Cart(items={})
    return _CARTS[session_id]


def add_to_cart(session_id: str, item_data: dict) -> Cart:
    cart = get_cart(session_id)
    item = CartItem(**item_data)
    cart.add_item(item)
    return cart


def remove_from_cart(session_id: str, retailer: str, product_id: str, quantity: int = 1) -> Cart:
    cart = get_cart(session_id)
    cart.remove_item(retailer, product_id, quantity)
    return cart
