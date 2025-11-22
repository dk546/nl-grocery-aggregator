"""
Tests for connector normalization functionality.

This module tests that connectors (AH, Jumbo) properly normalize Apify actor
results into the standard product format. Tests use mocked Apify clients and
fake item dictionaries to avoid real network calls.
"""

from unittest.mock import Mock, patch, MagicMock
from typing import List, Dict, Any

import pytest

from aggregator.connectors.ah_connector import AHConnector
from aggregator.connectors.jumbo_connector import JumboConnector


class TestAHConnectorNormalization:
    """Test cases for AH connector normalization."""
    
    @patch("aggregator.connectors.ah_connector.ApifyClient")
    @patch.dict("os.environ", {"APIFY_TOKEN": "test-token"})
    def test_normalize_ah_product(self, mock_apify_client_class):
        """Test that AH connector normalizes a product correctly."""
        # Create fake Apify items
        fake_apify_items = [
            {
                "supermarket": "AH",
                "id": "12345",
                "name": "AH Melk Halfvol",
                "price_eur": "1,99",
                "unit": "per stuk",
                "unit_size": "1L",
                "image_url": "https://ah.nl/image.jpg",
                "url": "https://ah.nl/product/12345"
            }
        ]
        
        # Mock Apify client and dataset iteration
        mock_client = Mock()
        mock_actor = Mock()
        mock_run = Mock()
        mock_run.__getitem__ = Mock(return_value="dataset-123")
        mock_run.get = Mock(return_value="dataset-123")
        mock_actor.call.return_value = mock_run
        
        mock_dataset = Mock()
        mock_dataset.iterate_items.return_value = iter(fake_apify_items)
        mock_client.actor.return_value = mock_actor
        mock_client.dataset.return_value = mock_dataset
        
        mock_apify_client_class.return_value = mock_client
        
        # Test normalization
        connector = AHConnector()
        results = connector.search_products("melk", size=10, page=0)
        
        # Verify normalization
        assert len(results) == 1
        product = results[0]
        
        assert product["retailer"] == "ah"
        assert product["id"] == "12345"
        assert product["name"] == "AH Melk Halfvol"
        assert product["price_eur"] == 1.99  # Should be converted from "1,99"
        assert product["unit"] == "per stuk"
        assert product["unit_size"] == "1L"
        assert product["image_url"] == "https://ah.nl/image.jpg"
        assert product["url"] == "https://ah.nl/product/12345"
        assert "raw" in product  # Raw data should be included
    
    @patch("aggregator.connectors.ah_connector.ApifyClient")
    @patch.dict("os.environ", {"APIFY_TOKEN": "test-token"})
    def test_normalize_ah_product_all_fields(self, mock_apify_client_class):
        """Test that AH connector normalizes all expected fields."""
        fake_apify_items = [
            {
                "supermarket": "AH",
                "id": "999",
                "name": "Test Product",
                "price_eur": "2.50",
                "unit": "per kg",
                "unit_size": "500g",
                "image_url": "https://example.com/img.jpg",
                "url": "https://ah.nl/product/999"
            }
        ]
        
        # Mock Apify client
        mock_client = Mock()
        mock_actor = Mock()
        mock_run = Mock()
        mock_run.__getitem__ = Mock(return_value="dataset-123")
        mock_actor.call.return_value = mock_run
        
        mock_dataset = Mock()
        mock_dataset.iterate_items.return_value = iter(fake_apify_items)
        mock_client.actor.return_value = mock_actor
        mock_client.dataset.return_value = mock_dataset
        
        mock_apify_client_class.return_value = mock_client
        
        # Test normalization
        connector = AHConnector()
        results = connector.search_products("test", size=10, page=0)
        
        # Verify all expected fields are present
        assert len(results) == 1
        product = results[0]
        
        required_fields = [
            "retailer", "id", "name", "price_eur", "unit", 
            "unit_size", "image_url", "url", "raw"
        ]
        for field in required_fields:
            assert field in product, f"Missing field: {field}"
        
        # Verify field values
        assert product["retailer"] == "ah"
        assert product["price_eur"] == 2.50
        assert isinstance(product["price_eur"], float)
    
    @patch("aggregator.connectors.ah_connector.ApifyClient")
    @patch.dict("os.environ", {"APIFY_TOKEN": "test-token"})
    def test_normalize_ah_filters_non_ah_products(self, mock_apify_client_class):
        """Test that AH connector filters out non-AH products."""
        # Mix of AH and non-AH products
        fake_apify_items = [
            {"supermarket": "AH", "id": "1", "name": "AH Product", "price_eur": "1.99", "url": "https://ah.nl/1"},
            {"supermarket": "Jumbo", "id": "2", "name": "Jumbo Product", "price_eur": "2.50", "url": "https://jumbo.nl/2"},
            {"supermarket": "AH", "id": "3", "name": "Another AH Product", "price_eur": "3.00", "url": "https://ah.nl/3"},
        ]
        
        # Mock Apify client
        mock_client = Mock()
        mock_actor = Mock()
        mock_run = Mock()
        mock_run.__getitem__ = Mock(return_value="dataset-123")
        mock_actor.call.return_value = mock_run
        
        mock_dataset = Mock()
        mock_dataset.iterate_items.return_value = iter(fake_apify_items)
        mock_client.actor.return_value = mock_actor
        mock_client.dataset.return_value = mock_dataset
        
        mock_apify_client_class.return_value = mock_client
        
        # Test filtering
        connector = AHConnector()
        results = connector.search_products("test", size=10, page=0)
        
        # Verify only AH products are returned
        assert len(results) == 2
        assert all(r["retailer"] == "ah" for r in results)
        assert results[0]["id"] == "1"
        assert results[1]["id"] == "3"
    
    @patch("aggregator.connectors.ah_connector.ApifyClient")
    @patch.dict("os.environ", {"APIFY_TOKEN": "test-token"})
    def test_normalize_ah_handles_missing_fields(self, mock_apify_client_class):
        """Test that AH connector handles missing optional fields gracefully."""
        # Product with minimal fields
        fake_apify_items = [
            {
                "supermarket": "AH",
                "id": "123",
                "name": "Minimal Product"
                # Missing: price_eur, unit, unit_size, image_url, url
            }
        ]
        
        # Mock Apify client
        mock_client = Mock()
        mock_actor = Mock()
        mock_run = Mock()
        mock_run.__getitem__ = Mock(return_value="dataset-123")
        mock_actor.call.return_value = mock_run
        
        mock_dataset = Mock()
        mock_dataset.iterate_items.return_value = iter(fake_apify_items)
        mock_client.actor.return_value = mock_actor
        mock_client.dataset.return_value = mock_dataset
        
        mock_apify_client_class.return_value = mock_client
        
        # Test normalization with missing fields
        connector = AHConnector()
        results = connector.search_products("test", size=10, page=0)
        
        # Verify normalization handles missing fields
        assert len(results) == 1
        product = results[0]
        
        assert product["retailer"] == "ah"
        assert product["id"] == "123"
        assert product["name"] == "Minimal Product"
        assert product["price_eur"] == 0.0  # Default for missing price
        assert product["unit"] == ""  # Default for missing unit
        assert product["unit_size"] == ""  # Default for missing unit_size
        assert product["image_url"] is None  # Default for missing image_url
        assert product["url"] == ""  # Default for missing url


class TestJumboConnectorNormalization:
    """Test cases for Jumbo connector normalization."""
    
    @patch("aggregator.connectors.jumbo_connector.ApifyClient")
    @patch.dict("os.environ", {"APIFY_TOKEN": "test-token"})
    def test_normalize_jumbo_product(self, mock_apify_client_class):
        """Test that Jumbo connector normalizes a product correctly."""
        # Create fake Apify items
        fake_apify_items = [
            {
                "supermarket": "Jumbo",
                "id": "54321",
                "name": "Jumbo Brood",
                "price_eur": "2,50",
                "unit": "per stuk",
                "unit_size": "800g",
                "image_url": "https://jumbo.nl/image.jpg",
                "url": "https://jumbo.nl/product/54321"
            }
        ]
        
        # Mock Apify client and dataset iteration
        mock_client = Mock()
        mock_actor = Mock()
        mock_run = Mock()
        mock_run.__getitem__ = Mock(return_value="dataset-456")
        mock_run.get = Mock(return_value="dataset-456")
        mock_actor.call.return_value = mock_run
        
        mock_dataset = Mock()
        mock_dataset.iterate_items.return_value = iter(fake_apify_items)
        mock_client.actor.return_value = mock_actor
        mock_client.dataset.return_value = mock_dataset
        
        mock_apify_client_class.return_value = mock_client
        
        # Test normalization
        connector = JumboConnector()
        results = connector.search_products("brood", size=10, page=0)
        
        # Verify normalization
        assert len(results) == 1
        product = results[0]
        
        assert product["retailer"] == "jumbo"
        assert product["id"] == "54321"
        assert product["name"] == "Jumbo Brood"
        assert product["price_eur"] == 2.50  # Should be converted from "2,50"
        assert product["unit"] == "per stuk"
        assert product["unit_size"] == "800g"
        assert product["image_url"] == "https://jumbo.nl/image.jpg"
        assert product["url"] == "https://jumbo.nl/product/54321"
        assert "raw" in product  # Raw data should be included
    
    @patch("aggregator.connectors.jumbo_connector.ApifyClient")
    @patch.dict("os.environ", {"APIFY_TOKEN": "test-token"})
    def test_normalize_jumbo_product_all_fields(self, mock_apify_client_class):
        """Test that Jumbo connector normalizes all expected fields."""
        fake_apify_items = [
            {
                "supermarket": "Jumbo",
                "id": "888",
                "name": "Jumbo Test Product",
                "price_eur": "3.75",
                "unit": "per stuk",
                "unit_size": "1kg",
                "image_url": "https://example.com/jumbo.jpg",
                "url": "https://jumbo.nl/product/888"
            }
        ]
        
        # Mock Apify client
        mock_client = Mock()
        mock_actor = Mock()
        mock_run = Mock()
        mock_run.__getitem__ = Mock(return_value="dataset-456")
        mock_actor.call.return_value = mock_run
        
        mock_dataset = Mock()
        mock_dataset.iterate_items.return_value = iter(fake_apify_items)
        mock_client.actor.return_value = mock_actor
        mock_client.dataset.return_value = mock_dataset
        
        mock_apify_client_class.return_value = mock_client
        
        # Test normalization
        connector = JumboConnector()
        results = connector.search_products("test", size=10, page=0)
        
        # Verify all expected fields are present
        assert len(results) == 1
        product = results[0]
        
        required_fields = [
            "retailer", "id", "name", "price_eur", "unit", 
            "unit_size", "image_url", "url", "raw"
        ]
        for field in required_fields:
            assert field in product, f"Missing field: {field}"
        
        # Verify field values
        assert product["retailer"] == "jumbo"
        assert product["price_eur"] == 3.75
        assert isinstance(product["price_eur"], float)
    
    @patch("aggregator.connectors.jumbo_connector.ApifyClient")
    @patch.dict("os.environ", {"APIFY_TOKEN": "test-token"})
    def test_normalize_jumbo_filters_non_jumbo_products(self, mock_apify_client_class):
        """Test that Jumbo connector filters out non-Jumbo products."""
        # Mix of Jumbo and non-Jumbo products
        fake_apify_items = [
            {"supermarket": "AH", "id": "1", "name": "AH Product", "price_eur": "1.99", "url": "https://ah.nl/1"},
            {"supermarket": "Jumbo", "id": "2", "name": "Jumbo Product", "price_eur": "2.50", "url": "https://jumbo.nl/2"},
            {"supermarket": "Jumbo", "id": "3", "name": "Another Jumbo Product", "price_eur": "3.00", "url": "https://jumbo.nl/3"},
            {"retailer": "jumbo", "id": "4", "name": "Jumbo with retailer field", "price_eur": "4.00", "url": "https://jumbo.nl/4"},
        ]
        
        # Mock Apify client
        mock_client = Mock()
        mock_actor = Mock()
        mock_run = Mock()
        mock_run.__getitem__ = Mock(return_value="dataset-456")
        mock_actor.call.return_value = mock_run
        
        mock_dataset = Mock()
        mock_dataset.iterate_items.return_value = iter(fake_apify_items)
        mock_client.actor.return_value = mock_actor
        mock_client.dataset.return_value = mock_dataset
        
        mock_apify_client_class.return_value = mock_client
        
        # Test filtering
        connector = JumboConnector()
        results = connector.search_products("test", size=10, page=0)
        
        # Verify only Jumbo products are returned (by supermarket or retailer field)
        assert len(results) == 3  # Should filter out AH product
        assert all(r["retailer"] == "jumbo" for r in results)
        assert results[0]["id"] == "2"
        assert results[1]["id"] == "3"
        assert results[2]["id"] == "4"  # Also accepts "retailer" field
    
    @patch("aggregator.connectors.jumbo_connector.ApifyClient")
    @patch.dict("os.environ", {"APIFY_TOKEN": "test-token"})
    def test_normalize_jumbo_handles_price_formats(self, mock_apify_client_class):
        """Test that Jumbo connector handles different price formats."""
        fake_apify_items = [
            {"supermarket": "Jumbo", "id": "1", "name": "Product 1", "price_eur": "1,99", "url": ""},
            {"supermarket": "Jumbo", "id": "2", "name": "Product 2", "price_eur": "2.50", "url": ""},
            {"supermarket": "Jumbo", "id": "3", "name": "Product 3", "price": "3,75", "url": ""},  # Uses "price" field
        ]
        
        # Mock Apify client
        mock_client = Mock()
        mock_actor = Mock()
        mock_run = Mock()
        mock_run.__getitem__ = Mock(return_value="dataset-456")
        mock_actor.call.return_value = mock_run
        
        mock_dataset = Mock()
        mock_dataset.iterate_items.return_value = iter(fake_apify_items)
        mock_client.actor.return_value = mock_actor
        mock_client.dataset.return_value = mock_dataset
        
        mock_apify_client_class.return_value = mock_client
        
        # Test price normalization
        connector = JumboConnector()
        results = connector.search_products("test", size=10, page=0)
        
        # Verify prices are normalized correctly
        assert len(results) == 3
        assert results[0]["price_eur"] == 1.99  # "1,99" -> 1.99
        assert results[1]["price_eur"] == 2.50  # "2.50" -> 2.50
        assert results[2]["price_eur"] == 3.75  # "3,75" from "price" field -> 3.75
    
    @patch("aggregator.connectors.jumbo_connector.ApifyClient")
    @patch.dict("os.environ", {"APIFY_TOKEN": "test-token"})
    def test_normalize_jumbo_handles_missing_fields(self, mock_apify_client_class):
        """Test that Jumbo connector handles missing optional fields gracefully."""
        # Product with minimal fields
        fake_apify_items = [
            {
                "supermarket": "Jumbo",
                "id": "456",
                "name": "Minimal Jumbo Product"
                # Missing: price_eur, unit, unit_size, image_url, url
            }
        ]
        
        # Mock Apify client
        mock_client = Mock()
        mock_actor = Mock()
        mock_run = Mock()
        mock_run.__getitem__ = Mock(return_value="dataset-456")
        mock_actor.call.return_value = mock_run
        
        mock_dataset = Mock()
        mock_dataset.iterate_items.return_value = iter(fake_apify_items)
        mock_client.actor.return_value = mock_actor
        mock_client.dataset.return_value = mock_dataset
        
        mock_apify_client_class.return_value = mock_client
        
        # Test normalization with missing fields
        connector = JumboConnector()
        results = connector.search_products("test", size=10, page=0)
        
        # Verify normalization handles missing fields
        assert len(results) == 1
        product = results[0]
        
        assert product["retailer"] == "jumbo"
        assert product["id"] == "456"
        assert product["name"] == "Minimal Jumbo Product"
        assert product["price_eur"] == 0.0  # Default for missing price
        assert product["unit"] == ""  # Default for missing unit
        assert product["unit_size"] == ""  # Default for missing unit_size
        assert product["image_url"] is None  # Default for missing image_url
        assert product["url"] == ""  # Default for missing url

