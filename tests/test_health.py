"""
Tests for the health tagging functionality.

This module tests the tag_health function which categorizes products
as "healthy", "unhealthy", or "neutral" based on their names.
"""

import pytest

from aggregator.health import tag_health


class TestHealthTagging:
    """Test cases for health tagging functionality."""
    
    def test_tag_chips_as_unhealthy(self):
        """Test that products with 'chips' in name are tagged as unhealthy."""
        product = {"name": "Lay's chips paprika"}
        assert tag_health(product) == "unhealthy"
    
    def test_tag_chocolate_as_unhealthy(self):
        """Test that products with 'chocolate' in name are tagged as unhealthy."""
        product = {"name": "Milka Chocolate"}
        assert tag_health(product) == "unhealthy"
    
    def test_tag_candy_as_unhealthy(self):
        """Test that products with 'candy' in name are tagged as unhealthy."""
        product = {"name": "Candy bars"}
        assert tag_health(product) == "unhealthy"
    
    def test_tag_fruit_as_healthy(self):
        """Test that products with 'fruit' in name are tagged as healthy."""
        product = {"name": "Fresh fruit salad"}
        assert tag_health(product) == "healthy"
    
    def test_tag_vegetable_as_healthy(self):
        """Test that products with 'vegetable' in name are tagged as healthy."""
        product = {"name": "Mixed vegetables"}
        assert tag_health(product) == "healthy"
    
    def test_tag_salad_as_healthy(self):
        """Test that products with 'salad' in name are tagged as healthy."""
        product = {"name": "Caesar salad"}
        assert tag_health(product) == "healthy"
    
    def test_tag_milk_as_neutral(self):
        """Test that neutral products like milk are tagged as neutral."""
        product = {"name": "Melk"}
        assert tag_health(product) == "neutral"
    
    def test_tag_bread_as_neutral(self):
        """Test that neutral products like bread are tagged as neutral."""
        product = {"name": "Brood"}
        assert tag_health(product) == "neutral"
    
    def test_tag_case_insensitive(self):
        """Test that health tagging is case insensitive."""
        assert tag_health({"name": "CHIPS"}) == "unhealthy"
        assert tag_health({"name": "FRUIT"}) == "healthy"
        assert tag_health({"name": "Milk"}) == "neutral"
    
    def test_tag_healthy_priority_over_unhealthy(self):
        """Test that healthy keywords take priority over unhealthy keywords."""
        # If a product contains both healthy and unhealthy keywords,
        # healthy should win (based on implementation order)
        product = {"name": "Fruit chips"}  # Contains both "fruit" and "chips"
        # The implementation checks healthy keywords first
        assert tag_health(product) == "healthy"
    
    def test_tag_empty_name(self):
        """Test that empty or missing name defaults to neutral."""
        assert tag_health({"name": ""}) == "neutral"
        assert tag_health({"name": None}) == "neutral"
        assert tag_health({}) == "neutral"
    
    def test_tag_dutch_keywords(self):
        """Test that Dutch keywords are properly recognized."""
        # Dutch unhealthy keywords
        assert tag_health({"name": "Snoep"}) == "unhealthy"
        assert tag_health({"name": "Koekjes"}) == "unhealthy"
        assert tag_health({"name": "Bier"}) == "unhealthy"
        
        # Dutch healthy keywords
        assert tag_health({"name": "Groente"}) == "healthy"
        assert tag_health({"name": "Noten"}) == "healthy"
        assert tag_health({"name": "Volkoren"}) == "healthy"
    
    def test_tag_product_with_multiple_keywords(self):
        """Test products with multiple keywords in the name."""
        # Multiple unhealthy keywords
        assert tag_health({"name": "Chocolate chips cookies"}) == "unhealthy"
        
        # Multiple healthy keywords
        assert tag_health({"name": "Fresh fruit and vegetable salad"}) == "healthy"
        
        # Mixed keywords (healthy should win)
        assert tag_health({"name": "Fruit yogurt with sugar"}) == "healthy"

