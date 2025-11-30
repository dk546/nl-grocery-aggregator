"""
Tests for product comparison and sorting logic.

This module tests the mark_cheapest and sort_products functions in aggregator.comparison.
"""

import pytest
from aggregator.models import ProductPublic
from aggregator.comparison import mark_cheapest, sort_products


@pytest.fixture
def sample_products():
    """Create sample products for testing."""
    return [
        ProductPublic(
            id="1", name="Milk", retailer="ah", price=1.50,
            price_per_unit=1.50, quantity=1.0, quantity_unit="L",
            health_tag="neutral"
        ),
        ProductPublic(
            id="2", name="Milk", retailer="jumbo", price=1.99,
            price_per_unit=1.99, quantity=1.0, quantity_unit="L",
            health_tag="neutral"
        ),
        ProductPublic(
            id="3", name="Bread", retailer="ah", price=2.00,
            price_per_unit=1.00, quantity=2.0, quantity_unit="piece",
            health_tag="neutral"
        ),
        ProductPublic(
            id="4", name="Bread", retailer="picnic", price=2.50,
            price_per_unit=1.25, quantity=2.0, quantity_unit="piece",
            health_tag="neutral"
        ),
    ]


@pytest.fixture
def products_with_missing_data():
    """Create products with missing price/price_per_unit for edge case testing."""
    return [
        ProductPublic(
            id="1", name="Product A", retailer="ah", price=1.50,
            price_per_unit=1.50, quantity=1.0, quantity_unit="L",
            health_tag="neutral"
        ),
        ProductPublic(
            id="2", name="Product B", retailer="jumbo", price=9999.0,
            price_per_unit=None, quantity=None, quantity_unit=None,
            health_tag="neutral"
        ),
        ProductPublic(
            id="3", name="Product C", retailer="picnic", price=2.00,
            price_per_unit=None, quantity=2.0, quantity_unit="piece",
            health_tag="neutral"
        ),
    ]


class TestMarkCheapest:
    """Test mark_cheapest function."""
    
    def test_mark_cheapest_distinct_prices(self, sample_products):
        """Test marking cheapest when prices are distinct."""
        result = mark_cheapest(sample_products)
        
        # Product 1 (Milk AH) should be cheapest total (1.50)
        assert result[0].is_cheapest_total is True
        assert result[1].is_cheapest_total is False  # Milk Jumbo (1.99)
        assert result[2].is_cheapest_total is False  # Bread AH (2.00)
        assert result[3].is_cheapest_total is False  # Bread Picnic (2.50)
        
        # Product 3 (Bread AH) should be cheapest per unit (1.00)
        assert result[2].is_cheapest_per_unit is True
        assert result[0].is_cheapest_per_unit is False
        assert result[1].is_cheapest_per_unit is False
        assert result[3].is_cheapest_per_unit is False
    
    def test_mark_cheapest_ties(self):
        """Test marking cheapest when multiple products have the same price."""
        products = [
            ProductPublic(
                id="1", name="Item A", retailer="ah", price=1.50,
                price_per_unit=1.50, quantity=1.0, quantity_unit="L",
                health_tag="neutral"
            ),
            ProductPublic(
                id="2", name="Item B", retailer="jumbo", price=1.50,
                price_per_unit=1.50, quantity=1.0, quantity_unit="L",
                health_tag="neutral"
            ),
        ]
        
        result = mark_cheapest(products)
        # Both should be marked as cheapest (ties allowed)
        assert result[0].is_cheapest_total is True
        assert result[1].is_cheapest_total is True
        assert result[0].is_cheapest_per_unit is True
        assert result[1].is_cheapest_per_unit is True
    
    def test_mark_cheapest_missing_prices(self, products_with_missing_data):
        """Test marking cheapest when some products have missing price_per_unit."""
        result = mark_cheapest(products_with_missing_data)
        
        # Product 1 should be cheapest total (1.50 is the minimum, ignoring 9999.0 sentinel)
        # Note: We filter out 9999.0 in the comparison logic by checking None,
        # but since price is required, we use 9999.0 as sentinel - the comparison
        # logic actually handles None, so 9999.0 won't be marked as cheapest
        # Product 2 has 9999.0 (sentinel for missing), so it should not be cheapest
        assert result[0].is_cheapest_total is True  # 1.50 is minimum valid price
        assert result[1].is_cheapest_total is False  # 9999.0 (sentinel) > 1.50
        assert result[2].is_cheapest_total is False  # 2.00 > 1.50
        
        # Product 1 should be cheapest per unit (only one with price_per_unit)
        assert result[0].is_cheapest_per_unit is True
        assert result[1].is_cheapest_per_unit is False  # Missing price_per_unit
        assert result[2].is_cheapest_per_unit is False  # Missing price_per_unit
    
    def test_mark_cheapest_empty_list(self):
        """Test marking cheapest with empty list."""
        result = mark_cheapest([])
        assert result == []
    
    def test_mark_cheapest_single_product(self):
        """Test marking cheapest with single product."""
        products = [
            ProductPublic(
                id="1", name="Item", retailer="ah", price=1.50,
                price_per_unit=1.50, quantity=1.0, quantity_unit="L",
                health_tag="neutral"
            )
        ]
        
        result = mark_cheapest(products)
        assert result[0].is_cheapest_total is True
        assert result[0].is_cheapest_per_unit is True
    
    def test_mark_cheapest_backward_compatibility(self, sample_products):
        """Test that is_cheapest is set for backward compatibility."""
        result = mark_cheapest(sample_products)
        
        # is_cheapest should equal is_cheapest_total
        assert result[0].is_cheapest == result[0].is_cheapest_total
        assert result[1].is_cheapest == result[1].is_cheapest_total


class TestSortProducts:
    """Test sort_products function."""
    
    def test_sort_price_asc(self, sample_products):
        """Test sorting by price ascending."""
        result = sort_products(sample_products, "price_asc")
        
        # Should be sorted: 1.50, 1.99, 2.00, 2.50
        assert result[0].price == 1.50
        assert result[1].price == 1.99
        assert result[2].price == 2.00
        assert result[3].price == 2.50
    
    def test_sort_price_desc(self, sample_products):
        """Test sorting by price descending."""
        result = sort_products(sample_products, "price_desc")
        
        # Should be sorted: 2.50, 2.00, 1.99, 1.50
        assert result[0].price == 2.50
        assert result[1].price == 2.00
        assert result[2].price == 1.99
        assert result[3].price == 1.50
    
    def test_sort_price_per_unit_asc(self, sample_products):
        """Test sorting by price per unit ascending."""
        result = sort_products(sample_products, "price_per_unit_asc")
        
        # Should be sorted: 1.00 (Bread AH), 1.25 (Bread Picnic), 1.50 (Milk AH), 1.99 (Milk Jumbo)
        assert result[0].price_per_unit == 1.00
        assert result[1].price_per_unit == 1.25
        assert result[2].price_per_unit == 1.50
        assert result[3].price_per_unit == 1.99
    
    def test_sort_price_per_unit_desc(self, sample_products):
        """Test sorting by price per unit descending."""
        result = sort_products(sample_products, "price_per_unit_desc")
        
        # Should be sorted: 1.99, 1.50, 1.25, 1.00
        assert result[0].price_per_unit == 1.99
        assert result[1].price_per_unit == 1.50
        assert result[2].price_per_unit == 1.25
        assert result[3].price_per_unit == 1.00
    
    def test_sort_retailer(self, sample_products):
        """Test sorting by retailer name."""
        result = sort_products(sample_products, "retailer")
        
        # Retailers should be sorted alphabetically: ah, jumbo, picnic
        retailers = [p.retailer for p in result]
        assert retailers == ["ah", "ah", "jumbo", "picnic"]
    
    def test_sort_health(self):
        """Test sorting by health tag."""
        products = [
            ProductPublic(
                id="1", name="Unhealthy", retailer="ah", price=1.00,
                health_tag="unhealthy"
            ),
            ProductPublic(
                id="2", name="Healthy", retailer="ah", price=2.00,
                health_tag="healthy"
            ),
            ProductPublic(
                id="3", name="Neutral", retailer="ah", price=1.50,
                health_tag="neutral"
            ),
        ]
        
        result = sort_products(products, "health")
        
        # Should be sorted: healthy, neutral, unhealthy
        assert result[0].health_tag == "healthy"
        assert result[1].health_tag == "neutral"
        assert result[2].health_tag == "unhealthy"
    
    def test_sort_legacy_price(self, sample_products):
        """Test that legacy 'price' sort value maps to price_asc."""
        result = sort_products(sample_products, "price")
        
        # Should behave like price_asc
        assert result[0].price == 1.50
        assert result[1].price == 1.99
    
    def test_sort_none_preserves_order(self, sample_products):
        """Test that None sort_by preserves original order."""
        result = sort_products(sample_products, None)
        
        # Should maintain original order
        assert [p.id for p in result] == ["1", "2", "3", "4"]
    
    def test_sort_empty_string_preserves_order(self, sample_products):
        """Test that empty string sort_by preserves order."""
        result = sort_products(sample_products, "")
        
        # Should maintain original order
        assert [p.id for p in result] == ["1", "2", "3", "4"]
    
    def test_sort_stable_tie_breaking(self):
        """Test that sorting is stable with tie-breaking."""
        products = [
            ProductPublic(
                id="1", name="Alpha", retailer="ah", price=1.50,
                health_tag="neutral"
            ),
            ProductPublic(
                id="2", name="Beta", retailer="jumbo", price=1.50,
                health_tag="neutral"
            ),
        ]
        
        result = sort_products(products, "price_asc")
        
        # When prices are equal, should break ties by name (alphabetical)
        assert result[0].name == "Alpha"
        assert result[1].name == "Beta"
    
    def test_sort_unknown_mode_defaults_to_price(self, sample_products):
        """Test that unknown sort mode defaults to price_asc."""
        result = sort_products(sample_products, "unknown_mode")
        
        # Should default to price_asc behavior
        assert result[0].price == 1.50
        assert result[1].price == 1.99

