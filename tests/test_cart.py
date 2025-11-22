"""
Tests for cart and cart item models.

This module tests the Cart and CartItem models including:
- Adding items to cart
- Quantity accumulation for duplicate items
- Removing items from cart
- Total price calculation
"""

import pytest

from aggregator.models import Cart, CartItem


class TestCartItem:
    """Test cases for CartItem model."""
    
    def test_create_cart_item(self):
        """Test creating a CartItem with required fields."""
        item = CartItem(
            retailer="ah",
            product_id="123",
            name="Test Product",
            price_eur=1.99
        )
        assert item.retailer == "ah"
        assert item.product_id == "123"
        assert item.name == "Test Product"
        assert item.price_eur == 1.99
        assert item.quantity == 1  # Default quantity
    
    def test_cart_item_default_quantity(self):
        """Test that CartItem defaults to quantity 1."""
        item = CartItem(
            retailer="ah",
            product_id="123",
            name="Test Product",
            price_eur=1.99
        )
        assert item.quantity == 1
    
    def test_cart_item_custom_quantity(self):
        """Test creating CartItem with custom quantity."""
        item = CartItem(
            retailer="ah",
            product_id="123",
            name="Test Product",
            price_eur=1.99,
            quantity=5
        )
        assert item.quantity == 5
    
    def test_cart_item_total_price(self):
        """Test that total_price property calculates correctly."""
        item = CartItem(
            retailer="ah",
            product_id="123",
            name="Test Product",
            price_eur=2.50,
            quantity=3
        )
        assert item.total_price == 7.50
    
    def test_cart_item_total_price_single_quantity(self):
        """Test total_price with quantity 1."""
        item = CartItem(
            retailer="ah",
            product_id="123",
            name="Test Product",
            price_eur=1.99,
            quantity=1
        )
        assert item.total_price == 1.99


class TestCart:
    """Test cases for Cart model."""
    
    def test_create_empty_cart(self):
        """Test creating an empty cart."""
        cart = Cart()
        assert len(cart.items) == 0
        assert cart.total() == 0.0
    
    def test_add_item_to_cart(self):
        """Test adding a single item to cart."""
        cart = Cart()
        item = CartItem(
            retailer="ah",
            product_id="123",
            name="Test Product",
            price_eur=1.99
        )
        cart.add(item)
        
        assert len(cart.items) == 1
        assert "ah:123" in cart.items
        assert cart.items["ah:123"].quantity == 1
        assert cart.total() == 1.99
    
    def test_add_multiple_items_to_cart(self):
        """Test adding multiple different items to cart."""
        cart = Cart()
        
        item1 = CartItem(
            retailer="ah",
            product_id="123",
            name="Product 1",
            price_eur=1.99
        )
        item2 = CartItem(
            retailer="jumbo",
            product_id="456",
            name="Product 2",
            price_eur=2.50
        )
        
        cart.add(item1)
        cart.add(item2)
        
        assert len(cart.items) == 2
        assert "ah:123" in cart.items
        assert "jumbo:456" in cart.items
        assert cart.total() == 4.49
    
    def test_add_duplicate_item_accumulates_quantity(self):
        """Test that adding the same item twice accumulates quantity."""
        cart = Cart()
        
        item1 = CartItem(
            retailer="ah",
            product_id="123",
            name="Test Product",
            price_eur=1.99,
            quantity=2
        )
        item2 = CartItem(
            retailer="ah",
            product_id="123",
            name="Test Product",
            price_eur=1.99,
            quantity=3
        )
        
        cart.add(item1)
        cart.add(item2)
        
        # Should have only one entry with accumulated quantity
        assert len(cart.items) == 1
        assert cart.items["ah:123"].quantity == 5  # 2 + 3
        assert cart.total() == 9.95  # 5 * 1.99
    
    def test_remove_item_reduces_quantity(self):
        """Test that removing an item reduces its quantity."""
        cart = Cart()
        
        item = CartItem(
            retailer="ah",
            product_id="123",
            name="Test Product",
            price_eur=1.99,
            quantity=5
        )
        cart.add(item)
        
        # Remove 2 items
        cart.remove("ah", "123", qty=2)
        
        assert cart.items["ah:123"].quantity == 3
        assert cart.total() == 5.97  # 3 * 1.99
    
    def test_remove_item_deletes_at_zero(self):
        """Test that removing all items deletes the item from cart."""
        cart = Cart()
        
        item = CartItem(
            retailer="ah",
            product_id="123",
            name="Test Product",
            price_eur=1.99,
            quantity=3
        )
        cart.add(item)
        
        # Remove all items
        cart.remove("ah", "123", qty=3)
        
        assert len(cart.items) == 0
        assert "ah:123" not in cart.items
        assert cart.total() == 0.0
    
    def test_remove_item_deletes_when_quantity_exceeds(self):
        """Test that removing more than available quantity deletes the item."""
        cart = Cart()
        
        item = CartItem(
            retailer="ah",
            product_id="123",
            name="Test Product",
            price_eur=1.99,
            quantity=2
        )
        cart.add(item)
        
        # Remove more than available
        cart.remove("ah", "123", qty=5)
        
        assert len(cart.items) == 0
        assert "ah:123" not in cart.items
        assert cart.total() == 0.0
    
    def test_remove_nonexistent_item(self):
        """Test that removing a nonexistent item does nothing."""
        cart = Cart()
        
        # Try to remove item that doesn't exist
        cart.remove("ah", "999", qty=1)
        
        assert len(cart.items) == 0
        assert cart.total() == 0.0
    
    def test_cart_total_with_multiple_items(self):
        """Test total calculation with multiple items and quantities."""
        cart = Cart()
        
        cart.add(CartItem(
            retailer="ah",
            product_id="123",
            name="Product 1",
            price_eur=1.99,
            quantity=2
        ))
        cart.add(CartItem(
            retailer="jumbo",
            product_id="456",
            name="Product 2",
            price_eur=2.50,
            quantity=3
        ))
        cart.add(CartItem(
            retailer="picnic",
            product_id="789",
            name="Product 3",
            price_eur=3.00,
            quantity=1
        ))
        
        # Total: (1.99 * 2) + (2.50 * 3) + (3.00 * 1) = 3.98 + 7.50 + 3.00 = 14.48
        assert cart.total() == pytest.approx(14.48, rel=1e-2)
    
    def test_cart_total_empty_cart(self):
        """Test that empty cart returns zero total."""
        cart = Cart()
        assert cart.total() == 0.0
    
    def test_cart_total_after_modifications(self):
        """Test total calculation after adding and removing items."""
        cart = Cart()
        
        # Add items
        cart.add(CartItem(
            retailer="ah",
            product_id="123",
            name="Product 1",
            price_eur=1.99,
            quantity=5
        ))
        assert cart.total() == 9.95
        
        # Remove some
        cart.remove("ah", "123", qty=2)
        assert cart.total() == 5.97
        
        # Add more
        cart.add(CartItem(
            retailer="ah",
            product_id="123",
            name="Product 1",
            price_eur=1.99,
            quantity=1
        ))
        assert cart.total() == 7.96
        
        # Remove all
        cart.remove("ah", "123", qty=10)
        assert cart.total() == 0.0
    
    def test_cart_key_format(self):
        """Test that cart items are keyed by 'retailer:product_id'."""
        cart = Cart()
        
        item = CartItem(
            retailer="ah",
            product_id="123",
            name="Test Product",
            price_eur=1.99
        )
        cart.add(item)
        
        # Verify the key format
        assert "ah:123" in cart.items
        assert "ah:123" == f"{item.retailer}:{item.product_id}"

