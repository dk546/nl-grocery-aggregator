"""
Tests for retailer connectors using mocked Apify clients.

These tests mock the ApifyClient to avoid making real API calls during testing.
The tests verify that:
- Connectors properly initialize with environment variables
- Search methods normalize items into expected format
- Pagination logic works correctly
- Error handling is robust
"""

import os
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List

import pytest

from aggregator.connectors.ah_connector import AHConnector
from aggregator.connectors.jumbo_connector import JumboConnector
from aggregator.connectors.picnic_connector import PicnicConnector


class TestAHConnector:
    """Tests for AH connector using Apify actor."""
    
    @patch.dict(os.environ, {"APIFY_TOKEN": "test-token"})
    @patch("aggregator.connectors.ah_connector.ApifyClient")
    def test_initialization(self, mock_apify_client):
        """Test AH connector initializes correctly with Apify token."""
        connector = AHConnector()
        
        # Verify ApifyClient was called with token
        mock_apify_client.assert_called_once_with("test-token")
        assert connector.retailer == "ah"
        assert connector.actor_id == "harvestedge/my-actor"
    
    @patch.dict(os.environ, {"APIFY_TOKEN": "test-token", "APIFY_AH_ACTOR_ID": "custom/actor"})
    @patch("aggregator.connectors.ah_connector.ApifyClient")
    def test_initialization_with_custom_actor_id(self, mock_apify_client):
        """Test AH connector uses custom actor ID from env var."""
        connector = AHConnector()
        assert connector.actor_id == "custom/actor"
    
    @patch.dict(os.environ, {})
    def test_initialization_missing_token(self):
        """Test AH connector raises error when token is missing."""
        with pytest.raises(RuntimeError, match="APIFY_TOKEN is not set"):
            AHConnector()
    
    @patch.dict(os.environ, {"APIFY_TOKEN": "test-token"})
    @patch("aggregator.connectors.ah_connector.ApifyClient")
    def test_search_products_normalizes_results(self, mock_apify_client_class):
        """Test search_products normalizes Apify actor results correctly."""
        # Mock Apify client and actor run
        mock_client = Mock()
        mock_actor = Mock()
        mock_run = Mock()
        mock_run.__getitem__ = Mock(return_value="dataset-123")
        mock_actor.call.return_value = mock_run
        
        mock_dataset = Mock()
        mock_client.actor.return_value = mock_actor
        mock_client.dataset.return_value = mock_dataset
        
        # Mock dataset items
        mock_items = [
            {
                "supermarket": "AH",
                "id": "123",
                "name": "Test Product",
                "price_eur": "1,99",
                "url": "https://ah.nl/product/123",
                "unit": "per stuk",
                "unit_size": "500ml",
            },
            {
                "supermarket": "AH",
                "id": "456",
                "name": "Another Product",
                "price_eur": "2.50",
                "url": "https://ah.nl/product/456",
            },
        ]
        mock_dataset.iterate_items.return_value = iter(mock_items)
        
        mock_apify_client_class.return_value = mock_client
        
        # Test search
        connector = AHConnector()
        results = connector.search_products("melk", size=10, page=0)
        
        # Verify actor was called correctly
        mock_actor.call.assert_called_once()
        call_kwargs = mock_actor.call.call_args[1]["run_input"]
        assert call_kwargs["keyterms"] == ["melk"]
        
        # Verify results are normalized
        assert len(results) == 2
        assert results[0]["retailer"] == "ah"
        assert results[0]["id"] == "123"
        assert results[0]["name"] == "Test Product"
        assert results[0]["price_eur"] == 1.99
        assert results[0]["unit"] == "per stuk"
        assert "raw" in results[0]
    
    @patch.dict(os.environ, {"APIFY_TOKEN": "test-token"})
    @patch("aggregator.connectors.ah_connector.ApifyClient")
    def test_search_products_filters_non_ah_products(self, mock_apify_client_class):
        """Test search_products filters out non-AH products."""
        mock_client = Mock()
        mock_actor = Mock()
        mock_run = Mock()
        mock_run.__getitem__ = Mock(return_value="dataset-123")
        mock_actor.call.return_value = mock_run
        
        mock_dataset = Mock()
        mock_client.actor.return_value = mock_actor
        mock_client.dataset.return_value = mock_dataset
        
        # Mix of AH and non-AH products
        mock_items = [
            {"supermarket": "AH", "id": "1", "name": "AH Product"},
            {"supermarket": "Jumbo", "id": "2", "name": "Jumbo Product"},
            {"supermarket": "AH", "id": "3", "name": "Another AH Product"},
        ]
        mock_dataset.iterate_items.return_value = iter(mock_items)
        
        mock_apify_client_class.return_value = mock_client
        
        connector = AHConnector()
        results = connector.search_products("test", size=10, page=0)
        
        # Should only return AH products
        assert len(results) == 2
        assert all(r["retailer"] == "ah" for r in results)
        assert results[0]["name"] == "AH Product"
        assert results[1]["name"] == "Another AH Product"
    
    @patch.dict(os.environ, {"APIFY_TOKEN": "test-token"})
    @patch("aggregator.connectors.ah_connector.ApifyClient")
    def test_search_products_pagination(self, mock_apify_client_class):
        """Test search_products pagination works correctly."""
        mock_client = Mock()
        mock_actor = Mock()
        mock_run = Mock()
        mock_run.__getitem__ = Mock(return_value="dataset-123")
        mock_actor.call.return_value = mock_run
        
        mock_dataset = Mock()
        mock_client.actor.return_value = mock_actor
        mock_client.dataset.return_value = mock_dataset
        
        # Create 10 items
        mock_items = [
            {"supermarket": "AH", "id": str(i), "name": f"Product {i}", "price_eur": str(i)}
            for i in range(10)
        ]
        mock_dataset.iterate_items.return_value = iter(mock_items)
        
        mock_apify_client_class.return_value = mock_client
        
        connector = AHConnector()
        
        # Page 0, size 5
        results_page0 = connector.search_products("test", size=5, page=0)
        assert len(results_page0) == 5
        
        # Page 1, size 5
        results_page1 = connector.search_products("test", size=5, page=1)
        assert len(results_page1) == 5
        assert results_page1[0]["id"] == "5"  # Should start at index 5


class TestJumboConnector:
    """Tests for Jumbo connector using Apify actor."""
    
    @patch.dict(os.environ, {"APIFY_TOKEN": "test-token"})
    @patch("aggregator.connectors.jumbo_connector.ApifyClient")
    def test_initialization(self, mock_apify_client):
        """Test Jumbo connector initializes correctly."""
        connector = JumboConnector()
        
        mock_apify_client.assert_called_once_with("test-token")
        assert connector.retailer == "jumbo"
        assert connector.actor_id == "harvestedge/jumbo-supermarket-scraper"
    
    @patch.dict(os.environ, {"APIFY_TOKEN": "test-token", "APIFY_JUMBO_ACTOR_ID": "custom/jumbo-actor"})
    @patch("aggregator.connectors.jumbo_connector.ApifyClient")
    def test_initialization_with_custom_actor_id(self, mock_apify_client):
        """Test Jumbo connector uses custom actor ID from env var."""
        connector = JumboConnector()
        assert connector.actor_id == "custom/jumbo-actor"
    
    @patch.dict(os.environ, {"APIFY_TOKEN": "test-token"})
    @patch("aggregator.connectors.jumbo_connector.ApifyClient")
    def test_search_products_normalizes_results(self, mock_apify_client_class):
        """Test Jumbo search_products normalizes results correctly."""
        mock_client = Mock()
        mock_actor = Mock()
        mock_run = Mock()
        mock_run.__getitem__ = Mock(return_value="dataset-123")
        mock_actor.call.return_value = mock_run
        
        mock_dataset = Mock()
        mock_client.actor.return_value = mock_actor
        mock_client.dataset.return_value = mock_dataset
        
        mock_items = [
            {
                "supermarket": "Jumbo",
                "id": "789",
                "name": "Jumbo Product",
                "price_eur": "3,50",
                "url": "https://jumbo.com/product/789",
            },
        ]
        mock_dataset.iterate_items.return_value = iter(mock_items)
        
        mock_apify_client_class.return_value = mock_client
        
        connector = JumboConnector()
        results = connector.search_products("melk", size=10, page=0)
        
        assert len(results) == 1
        assert results[0]["retailer"] == "jumbo"
        assert results[0]["id"] == "789"
        assert results[0]["name"] == "Jumbo Product"
        assert results[0]["price_eur"] == 3.50


class TestPicnicConnector:
    """Tests for Picnic connector (still using python-picnic-api)."""
    
    @patch.dict(os.environ, {
        "PICNIC_USERNAME": "test@example.com",
        "PICNIC_PASSWORD": "testpass",
        "PICNIC_COUNTRY_CODE": "NL"
    })
    @patch("aggregator.connectors.picnic_connector.PicnicAPI")
    def test_initialization(self, mock_picnic_api_class):
        """Test Picnic connector initializes correctly."""
        connector = PicnicConnector()
        
        mock_picnic_api_class.assert_called_once_with(
            username="test@example.com",
            password="testpass",
            country_code="NL"
        )
        assert connector.retailer == "picnic"
    
    @patch.dict(os.environ, {})
    def test_initialization_missing_credentials(self):
        """Test Picnic connector raises error when credentials are missing."""
        with pytest.raises(RuntimeError, match="credentials missing"):
            PicnicConnector()

