"""
Pydantic models for cart and cart items.

This module defines the data models for the shopping cart system using Pydantic
for data validation and serialization. The Cart model manages a dictionary of
CartItem objects keyed by "retailer:product_id" for efficient lookups and updates.

The models support:
- Adding items to cart (with quantity accumulation for duplicates)
- Removing items from cart (with quantity reduction)
- Calculating total price across all items
- Validating data types and required fields
"""

from typing import Dict, Optional

from pydantic import BaseModel


class CartItem(BaseModel):
    """
    Model representing a single item in the shopping cart.
    
    Attributes:
        retailer: Retailer identifier (e.g., "ah", "jumbo", "picnic")
        product_id: Unique product identifier from the retailer
        name: Product name (for display purposes)
        price_eur: Price per unit in euros
        quantity: Number of units in cart (default: 1)
        image_url: URL to product image (optional)
        health_tag: Health category tag ("healthy", "unhealthy", "neutral", optional)
    """
    retailer: str
    product_id: str
    name: str
    price_eur: float
    quantity: int = 1
    image_url: Optional[str] = None
    health_tag: Optional[str] = None

    @property
    def total_price(self) -> float:
        """
        Calculate the total price for this item (price * quantity).
        
        Returns:
            Total price in euros (price_eur * quantity)
        """
        return self.price_eur * self.quantity


class Cart(BaseModel):
    """
    Model representing a shopping cart.
    
    The cart stores items in a dictionary keyed by "retailer:product_id" to enable
    efficient lookups and automatic quantity accumulation for duplicate items.
    
    Attributes:
        items: Dictionary mapping "retailer:product_id" to CartItem objects
    """
    items: Dict[str, CartItem] = {}

    def add(self, item: CartItem) -> None:
        """
        Add an item to the cart.
        
        If an item with the same retailer and product_id already exists, the quantities
        are accumulated. Otherwise, a new item is added to the cart.
        
        Args:
            item: CartItem to add to the cart
        """
        key = f"{item.retailer}:{item.product_id}"
        if key in self.items:
            # Accumulate quantity if item already exists
            self.items[key].quantity += item.quantity
        else:
            # Add new item
            self.items[key] = item

    def remove(self, retailer: str, product_id: str, qty: int = 1) -> None:
        """
        Remove an item from the cart or reduce its quantity.
        
        If the quantity to remove is greater than or equal to the item's quantity,
        the item is completely removed from the cart.
        
        Args:
            retailer: Retailer identifier
            product_id: Product identifier
            qty: Quantity to remove (default: 1)
        """
        key = f"{retailer}:{product_id}"
        if key not in self.items:
            return

        # Reduce quantity
        self.items[key].quantity -= qty
        
        # Remove item if quantity reaches zero or below
        if self.items[key].quantity <= 0:
            del self.items[key]

    def total(self) -> float:
        """
        Calculate the total price of all items in the cart.
        
        Returns:
            Total price in euros (sum of all item total_price values)
        """
        return sum(i.total_price for i in self.items.values())
