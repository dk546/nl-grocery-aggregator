"""
Tests for the aggregated search functionality.

This module tests the aggregated_search function which searches across multiple
retailers, normalizes results, adds health tags, and sorts by price.
All connectors are mocked to avoid real API calls.
"""

from unittest.mock import Mock, patch
from typing import List, Dict, Any

import pytest

from aggregator.search import aggregated_search


class TestAggregatedSearch:
    """Test cases for aggregated search functionality."""
    
    @patch("aggregator.search.AHConnector")
    @patch("aggregator.search.JumboConnector")
    @patch("aggregator.search.PicnicConnector")
    def test_aggregated_search_merges_results(self, mock_picnic, mock_jumbo, mock_ah):
        """Test that aggregated_search merges results from multiple retailers."""
        # Setup mock connectors
        mock_ah_instance = Mock()
        mock_ah_instance.search_products.return_value = [
            {
                "retailer": "ah",
                "id": "1",
                "name": "AH Product",
                "price_eur": 1.99,
                "unit": "per stuk",
                "unit_size": "500ml",
                "image_url": None,
                "url": "https://ah.nl/product/1",
                "raw": {}
            }
        ]
        mock_ah.return_value = mock_ah_instance
        
        mock_jumbo_instance = Mock()
        mock_jumbo_instance.search_products.return_value = [
            {
                "retailer": "jumbo",
                "id": "2",
                "name": "Jumbo Product",
                "price_eur": 2.50,
                "unit": "per stuk",
                "unit_size": "1L",
                "image_url": None,
                "url": "https://jumbo.nl/product/2",
                "raw": {}
            }
        ]
        mock_jumbo.return_value = mock_jumbo_instance
        
        mock_picnic_instance = Mock()
        mock_picnic_instance.search_products.return_value = []
        mock_picnic.return_value = mock_picnic_instance
        
        # Perform search
        response = aggregated_search(
            query="melk",
            retailers=["ah", "jumbo"],
            size_per_retailer=10,
            page=0
        )
        
        # Verify results are merged
        results = response["results"]
        assert len(results) == 2
        assert results[0]["retailer"] == "ah"
        assert results[1]["retailer"] == "jumbo"
        
        # Verify connectors were called
        mock_ah_instance.search_products.assert_called_once_with("melk", size=10, page=0)
        mock_jumbo_instance.search_products.assert_called_once_with("melk", size=10, page=0)
    
    @patch("aggregator.search.AHConnector")
    @patch("aggregator.search.JumboConnector")
    @patch("aggregator.search.PicnicConnector")
    def test_aggregated_search_adds_health_tag(self, mock_picnic, mock_jumbo, mock_ah):
        """Test that aggregated_search adds health_tag to all products."""
        # Setup mock connector with products that should be tagged
        mock_ah_instance = Mock()
        mock_ah_instance.search_products.return_value = [
            {
                "retailer": "ah",
                "id": "1",
                "name": "Fresh fruit salad",
                "price_eur": 3.99,
                "raw": {}
            },
            {
                "retailer": "ah",
                "id": "2",
                "name": "Lay's chips",
                "price_eur": 1.99,
                "raw": {}
            },
            {
                "retailer": "ah",
                "id": "3",
                "name": "Melk",
                "price_eur": 1.49,
                "raw": {}
            }
        ]
        mock_ah.return_value = mock_ah_instance
        
        # Mock other connectors to return empty
        mock_jumbo.return_value.search_products.return_value = []
        mock_picnic.return_value.search_products.return_value = []
        
        # Perform search
        response = aggregated_search(
            query="test",
            retailers=["ah"],
            size_per_retailer=10,
            page=0
        )
        
        # Extract results from response
        results = response["results"]
        
        # Verify health tags are added
        assert len(results) == 3
        assert results[0]["health_tag"] == "healthy"  # fruit
        assert results[1]["health_tag"] == "unhealthy"  # chips
        assert results[2]["health_tag"] == "neutral"  # melk
    
    @patch("aggregator.search.AHConnector")
    @patch("aggregator.search.JumboConnector")
    @patch("aggregator.search.PicnicConnector")
    def test_aggregated_search_sorts_by_price(self, mock_picnic, mock_jumbo, mock_ah):
        """Test that aggregated_search sorts results by price_eur."""
        # Setup mock connectors with products at different prices
        mock_ah_instance = Mock()
        mock_ah_instance.search_products.return_value = [
            {
                "retailer": "ah",
                "id": "1",
                "name": "Expensive Product",
                "price_eur": 5.99,
                "raw": {}
            },
            {
                "retailer": "ah",
                "id": "2",
                "name": "Cheap Product",
                "price_eur": 0.99,
                "raw": {}
            }
        ]
        mock_ah.return_value = mock_ah_instance
        
        mock_jumbo_instance = Mock()
        mock_jumbo_instance.search_products.return_value = [
            {
                "retailer": "jumbo",
                "id": "3",
                "name": "Medium Product",
                "price_eur": 3.50,
                "raw": {}
            }
        ]
        mock_jumbo.return_value = mock_jumbo_instance
        
        mock_picnic_instance = Mock()
        mock_picnic_instance.search_products.return_value = []
        mock_picnic.return_value = mock_picnic_instance
        
        # Perform search
        response = aggregated_search(
            query="test",
            retailers=["ah", "jumbo"],
            size_per_retailer=10,
            page=0,
            sort_by="price"
        )

        # Verify results are sorted by price (lowest first)
        results = response["results"]
        assert len(results) == 3
        assert results[0]["price_eur"] == 0.99  # Cheapest first
        # Extract results from response
        results = response["results"]
        assert results[1]["price_eur"] == 3.50
        assert results[2]["price_eur"] == 5.99  # Most expensive last
    
    @patch("aggregator.search.AHConnector")
    @patch("aggregator.search.JumboConnector")
    @patch("aggregator.search.PicnicConnector")
    def test_aggregated_search_handles_missing_prices(self, mock_picnic, mock_jumbo, mock_ah):
        """Test that aggregated_search handles products with missing prices."""
        # Setup mock connector with product missing price
        mock_ah_instance = Mock()
        mock_ah_instance.search_products.return_value = [
            {
                "retailer": "ah",
                "id": "1",
                "name": "Product with price",
                "price_eur": 2.50,
                "raw": {}
            },
            {
                "retailer": "ah",
                "id": "2",
                "name": "Product without price",
                "raw": {}
            }
        ]
        mock_ah.return_value = mock_ah_instance
        
        # Mock other connectors
        mock_jumbo.return_value.search_products.return_value = []
        mock_picnic.return_value.search_products.return_value = []
        
        # Perform search
        response = aggregated_search(
            query="test",
            retailers=["ah"],
            size_per_retailer=10,
            page=0
        )

        # Verify results include both products
        results = response["results"]
        assert len(results) == 2
        # Product with missing price should be sorted last (price defaults to 9999)
        assert results[0]["price_eur"] == 2.50
        # Extract results from response
        results = response["results"]
        assert results[1].get("price_eur") is None or results[1]["price_eur"] == 9999
    
    @patch("aggregator.search.AHConnector")
    @patch("aggregator.search.JumboConnector")
    @patch("aggregator.search.PicnicConnector")
    def test_aggregated_search_skips_invalid_retailers(self, mock_picnic, mock_jumbo, mock_ah):
        """Test that aggregated_search skips invalid retailer names."""
        # Setup mock connector
        mock_ah_instance = Mock()
        mock_ah_instance.search_products.return_value = [
            {
                "retailer": "ah",
                "id": "1",
                "name": "AH Product",
                "price_eur": 1.99,
                "raw": {}
            }
        ]
        mock_ah.return_value = mock_ah_instance
        
        # Perform search with invalid retailer
        response = aggregated_search(
            query="test",
            retailers=["ah", "invalid_retailer"],
            size_per_retailer=10,
            page=0
        )

        # Verify only valid retailer was searched
        results = response["results"]
        assert len(results) == 1
        assert results[0]["retailer"] == "ah"
        # Invalid retailer should not cause errors
    
    @patch("aggregator.search.AHConnector")
    @patch("aggregator.search.JumboConnector")
    @patch("aggregator.search.PicnicConnector")
    def test_aggregated_search_handles_connector_errors(self, mock_picnic, mock_jumbo, mock_ah):
        """Test that aggregated_search handles connector errors gracefully."""
        # Setup mock connectors - one fails, one succeeds
        mock_ah_instance = Mock()
        mock_ah_instance.search_products.side_effect = RuntimeError("Connection failed")
        mock_ah.return_value = mock_ah_instance
        
        mock_jumbo_instance = Mock()
        mock_jumbo_instance.search_products.return_value = [
            {
                "retailer": "jumbo",
                "id": "1",
                "name": "Jumbo Product",
                "price_eur": 2.50,
                "raw": {}
            }
        ]
        mock_jumbo.return_value = mock_jumbo_instance
        
        mock_picnic_instance = Mock()
        mock_picnic_instance.search_products.return_value = []
        mock_picnic.return_value = mock_picnic_instance
        
        # Perform search - should continue even if one connector fails
        response = aggregated_search(
            query="test",
            retailers=["ah", "jumbo"],
            size_per_retailer=10,
            page=0
        )

        # Verify we still get results from the working connector
        # Extract results from response
        results = response["results"]
        assert len(results) == 1
        assert results[0]["retailer"] == "jumbo"
    
    @patch("aggregator.search.AHConnector")
    @patch("aggregator.search.JumboConnector")
    @patch("aggregator.search.PicnicConnector")
    def test_aggregated_search_all_retailers(self, mock_picnic, mock_jumbo, mock_ah):
        """Test aggregated_search with all three retailers."""
        # Setup all mock connectors
        mock_ah_instance = Mock()
        mock_ah_instance.search_products.return_value = [
            {"retailer": "ah", "id": "1", "name": "AH Product", "price_eur": 1.99, "raw": {}}
        ]
        mock_ah.return_value = mock_ah_instance
        
        mock_jumbo_instance = Mock()
        mock_jumbo_instance.search_products.return_value = [
            {"retailer": "jumbo", "id": "2", "name": "Jumbo Product", "price_eur": 2.50, "raw": {}}
        ]
        mock_jumbo.return_value = mock_jumbo_instance
        
        mock_picnic_instance = Mock()
        mock_picnic_instance.search_products.return_value = [
            {"retailer": "picnic", "id": "3", "name": "Picnic Product", "price_eur": 3.00, "raw": {}}
        ]
        mock_picnic.return_value = mock_picnic_instance
        
        # Perform search
        response = aggregated_search(
            query="test",
            retailers=["ah", "jumbo", "picnic"],
            size_per_retailer=10,
            page=0
        )

        # Verify all retailers are searched
        results = response["results"]
        assert len(results) == 3
        retailers = [r["retailer"] for r in results]
        assert "ah" in retailers
        assert "jumbo" in retailers
        assert "picnic" in retailers
        
        # Verify results are sorted by price
        # Extract results from response
        results = response["results"]
        assert results[0]["price_eur"] == 1.99  # AH
        assert results[1]["price_eur"] == 2.50  # Jumbo
        assert results[2]["price_eur"] == 3.00  # Picnic
    
    @patch("aggregator.search.AHConnector")
    @patch("aggregator.search.JumboConnector")
    @patch("aggregator.search.PicnicConnector")
    def test_aggregated_search_empty_results(self, mock_picnic, mock_jumbo, mock_ah):
        """Test aggregated_search with no results."""
        # Setup all mock connectors to return empty
        mock_ah.return_value.search_products.return_value = []
        mock_jumbo.return_value.search_products.return_value = []
        mock_picnic.return_value.search_products.return_value = []
        
        # Perform search
        response = aggregated_search(
            query="nonexistent",
            retailers=["ah", "jumbo", "picnic"],
            size_per_retailer=10,
            page=0
        )
        
        # Verify empty results
        results = response["results"]
        assert len(results) == 0
        assert results == []
    
    @patch("aggregator.search.AHConnector")
    @patch("aggregator.search.JumboConnector")
    @patch("aggregator.search.PicnicConnector")
    def test_aggregated_search_sorts_by_retailer(self, mock_picnic, mock_jumbo, mock_ah):
        """Test that aggregated_search sorts results by retailer (alphabetical)."""
        # Setup mock connectors with products from different retailers
        mock_ah_instance = Mock()
        mock_ah_instance.search_products.return_value = [
            {"retailer": "ah", "id": "1", "name": "AH Product", "price_eur": 2.50, "raw": {}}
        ]
        mock_ah.return_value = mock_ah_instance
        
        mock_jumbo_instance = Mock()
        mock_jumbo_instance.search_products.return_value = [
            {"retailer": "jumbo", "id": "2", "name": "Jumbo Product", "price_eur": 1.99, "raw": {}}
        ]
        mock_jumbo.return_value = mock_jumbo_instance
        
        mock_picnic_instance = Mock()
        mock_picnic_instance.search_products.return_value = [
            {"retailer": "picnic", "id": "3", "name": "Picnic Product", "price_eur": 3.00, "raw": {}}
        ]
        mock_picnic.return_value = mock_picnic_instance
        
        # Perform search with sort_by="retailer"
        response = aggregated_search(
            query="test",
            retailers=["ah", "jumbo", "picnic"],
            size_per_retailer=10,
            page=0,
            sort_by="retailer"
        )

        # Verify results are sorted by retailer (alphabetical: ah, jumbo, picnic)
        results = response["results"]
        assert len(results) == 3
        assert results[0]["retailer"] == "ah"
        # Extract results from response
        results = response["results"]
        assert results[1]["retailer"] == "jumbo"
        assert results[2]["retailer"] == "picnic"
    
    @patch("aggregator.search.AHConnector")
    @patch("aggregator.search.JumboConnector")
    @patch("aggregator.search.PicnicConnector")
    def test_aggregated_search_sorts_by_health(self, mock_picnic, mock_jumbo, mock_ah):
        """Test that aggregated_search sorts results by health (healthy first, then neutral, then unhealthy)."""
        # Setup mock connector with products of different health tags
        mock_ah_instance = Mock()
        mock_ah_instance.search_products.return_value = [
            {"retailer": "ah", "id": "1", "name": "Unhealthy Product - chips", "price_eur": 1.99, "raw": {}},
            {"retailer": "ah", "id": "2", "name": "Neutral Product - melk", "price_eur": 2.50, "raw": {}},
            {"retailer": "ah", "id": "3", "name": "Healthy Product - fruit", "price_eur": 3.00, "raw": {}},
            {"retailer": "ah", "id": "4", "name": "Another Healthy Product - salad", "price_eur": 4.00, "raw": {}},
        ]
        mock_ah.return_value = mock_ah_instance
        
        # Mock other connectors
        mock_jumbo.return_value.search_products.return_value = []
        mock_picnic.return_value.search_products.return_value = []
        
        # Perform search with sort_by="health"
        response = aggregated_search(
            query="test",
            retailers=["ah"],
            size_per_retailer=10,
            page=0,
            sort_by="health"
        )

        # Verify results are sorted by health: healthy first, then neutral, then unhealthy
        results = response["results"]
        assert len(results) == 4
        assert results[0]["health_tag"] == "healthy"
        # Extract results from response
        results = response["results"]
        assert results[1]["health_tag"] == "healthy"
        assert results[2]["health_tag"] == "neutral"
        assert results[3]["health_tag"] == "unhealthy"
        
        # Within same health tag, should be sorted by price (secondary sort)
        assert results[0]["price_eur"] == 3.00  # First healthy (cheaper)
        assert results[1]["price_eur"] == 4.00  # Second healthy (more expensive)
    
    @patch("aggregator.search.AHConnector")
    @patch("aggregator.search.JumboConnector")
    @patch("aggregator.search.PicnicConnector")
    def test_aggregated_search_health_filter_healthy(self, mock_picnic, mock_jumbo, mock_ah):
        """Test that health_filter="healthy" returns only healthy products."""
        # Setup mock connector with products of different health tags
        mock_ah_instance = Mock()
        mock_ah_instance.search_products.return_value = [
            {"retailer": "ah", "id": "1", "name": "Fresh fruit", "price_eur": 3.99, "raw": {}},
            {"retailer": "ah", "id": "2", "name": "Lay's chips", "price_eur": 1.99, "raw": {}},
            {"retailer": "ah", "id": "3", "name": "Melk", "price_eur": 1.49, "raw": {}},
            {"retailer": "ah", "id": "4", "name": "Mixed salad", "price_eur": 2.99, "raw": {}},
        ]
        mock_ah.return_value = mock_ah_instance
        
        # Mock other connectors
        mock_jumbo.return_value.search_products.return_value = []
        mock_picnic.return_value.search_products.return_value = []
        
        # Perform search with health_filter="healthy"
        response = aggregated_search(
            query="test",
            retailers=["ah"],
            size_per_retailer=10,
            page=0,
            health_filter="healthy"
        )

        # Verify only healthy products are returned
        results = response["results"]
        assert len(results) == 2
        assert all(r["health_tag"] == "healthy" for r in results)
        # Extract results from response
        results = response["results"]
        assert results[0]["name"] in ["Fresh fruit", "Mixed salad"]
        assert results[1]["name"] in ["Fresh fruit", "Mixed salad"]
    
    @patch("aggregator.search.AHConnector")
    @patch("aggregator.search.JumboConnector")
    @patch("aggregator.search.PicnicConnector")
    def test_aggregated_search_health_filter_unhealthy(self, mock_picnic, mock_jumbo, mock_ah):
        """Test that health_filter="unhealthy" returns only unhealthy products."""
        # Setup mock connector with products of different health tags
        mock_ah_instance = Mock()
        mock_ah_instance.search_products.return_value = [
            {"retailer": "ah", "id": "1", "name": "Fresh fruit", "price_eur": 3.99, "raw": {}},
            {"retailer": "ah", "id": "2", "name": "Lay's chips", "price_eur": 1.99, "raw": {}},
            {"retailer": "ah", "id": "3", "name": "Chocolate bar", "price_eur": 2.50, "raw": {}},
            {"retailer": "ah", "id": "4", "name": "Melk", "price_eur": 1.49, "raw": {}},
        ]
        mock_ah.return_value = mock_ah_instance
        
        # Mock other connectors
        mock_jumbo.return_value.search_products.return_value = []
        mock_picnic.return_value.search_products.return_value = []
        
        # Perform search with health_filter="unhealthy"
        response = aggregated_search(
            query="test",
            retailers=["ah"],
            size_per_retailer=10,
            page=0,
            health_filter="unhealthy"
        )

        # Verify only unhealthy products are returned
        results = response["results"]
        assert len(results) == 2
        assert all(r["health_tag"] == "unhealthy" for r in results)
        # Extract results from response
        results = response["results"]
        assert results[0]["name"] in ["Lay's chips", "Chocolate bar"]
        assert results[1]["name"] in ["Lay's chips", "Chocolate bar"]
    
    @patch("aggregator.search.AHConnector")
    @patch("aggregator.search.JumboConnector")
    @patch("aggregator.search.PicnicConnector")
    def test_aggregated_search_health_filter_none(self, mock_picnic, mock_jumbo, mock_ah):
        """Test that health_filter=None returns all products regardless of health tag."""
        # Setup mock connector with products of different health tags
        mock_ah_instance = Mock()
        mock_ah_instance.search_products.return_value = [
            {"retailer": "ah", "id": "1", "name": "Fresh fruit", "price_eur": 3.99, "raw": {}},
            {"retailer": "ah", "id": "2", "name": "Lay's chips", "price_eur": 1.99, "raw": {}},
            {"retailer": "ah", "id": "3", "name": "Melk", "price_eur": 1.49, "raw": {}},
        ]
        mock_ah.return_value = mock_ah_instance
        
        # Mock other connectors
        mock_jumbo.return_value.search_products.return_value = []
        mock_picnic.return_value.search_products.return_value = []
        
        # Perform search without health_filter
        response = aggregated_search(
            query="test",
            retailers=["ah"],
            size_per_retailer=10,
            page=0,
            health_filter=None
        )
        
        # Extract results from response
        results = response["results"]
        
        # Verify all products are returned
        assert len(results) == 3
        health_tags = [r["health_tag"] for r in results]
        assert "healthy" in health_tags
        assert "unhealthy" in health_tags
        assert "neutral" in health_tags
    
    @patch("aggregator.search.AHConnector")
    @patch("aggregator.search.JumboConnector")
    @patch("aggregator.search.PicnicConnector")
    def test_aggregated_search_marks_cheapest_in_group(self, mock_picnic, mock_jumbo, mock_ah):
        """Test that group_by_name_and_mark_cheapest marks the cheapest product in each name group."""
        # Setup mock connectors with products that have same names (different retailers)
        mock_ah_instance = Mock()
        mock_ah_instance.search_products.return_value = [
            {"retailer": "ah", "id": "1", "name": "Melk", "price_eur": 1.99, "raw": {}}
        ]
        mock_ah.return_value = mock_ah_instance
        
        mock_jumbo_instance = Mock()
        mock_jumbo_instance.search_products.return_value = [
            {"retailer": "jumbo", "id": "2", "name": "Melk", "price_eur": 1.49, "raw": {}}
        ]
        mock_jumbo.return_value = mock_jumbo_instance
        
        mock_picnic_instance = Mock()
        mock_picnic_instance.search_products.return_value = [
            {"retailer": "picnic", "id": "3", "name": "Melk", "price_eur": 2.50, "raw": {}}
        ]
        mock_picnic.return_value = mock_picnic_instance
        
        # Perform search
        response = aggregated_search(
            query="melk",
            retailers=["ah", "jumbo", "picnic"],
            size_per_retailer=10,
            page=0
        )

        # Verify all products have is_cheapest field
        results = response["results"]
        assert len(results) == 3
        assert all("is_cheapest" in r for r in results)
        
        # Verify cheapest (jumbo at 1.49) is marked as cheapest
        cheapest_product = [r for r in results if r["is_cheapest"] is True][0]
        assert cheapest_product["retailer"] == "jumbo"
        assert cheapest_product["price_eur"] == 1.49
        
        # Verify others are marked as not cheapest
        not_cheapest = [r for r in results if r["is_cheapest"] is False]
        assert len(not_cheapest) == 2
        assert all(r["price_eur"] > 1.49 for r in not_cheapest)
    
    @patch("aggregator.search.AHConnector")
    @patch("aggregator.search.JumboConnector")
    @patch("aggregator.search.PicnicConnector")
    def test_aggregated_search_marks_cheapest_case_insensitive(self, mock_picnic, mock_jumbo, mock_ah):
        """Test that grouping by name is case-insensitive."""
        # Setup mock connectors with products that have same names but different case
        mock_ah_instance = Mock()
        mock_ah_instance.search_products.return_value = [
            {"retailer": "ah", "id": "1", "name": "Melk", "price_eur": 2.50, "raw": {}}
        ]
        mock_ah.return_value = mock_ah_instance
        
        mock_jumbo_instance = Mock()
        mock_jumbo_instance.search_products.return_value = [
            {"retailer": "jumbo", "id": "2", "name": "melk", "price_eur": 1.99, "raw": {}},  # lowercase
            {"retailer": "jumbo", "id": "3", "name": "MELK", "price_eur": 2.20, "raw": {}}  # uppercase
        ]
        mock_jumbo.return_value = mock_jumbo_instance
        
        # Mock picnic
        mock_picnic.return_value.search_products.return_value = []
        
        # Perform search
        response = aggregated_search(
            query="melk",
            retailers=["ah", "jumbo"],
            size_per_retailer=10,
            page=0
        )
        
        # Verify all three products are in the same group (case-insensitive)
        # The cheapest (1.99) should be marked as cheapest
        # Extract results from response
        results = response["results"]
        assert len(results) == 3
        
        # All should be grouped together (case-insensitive)
        # The cheapest should be marked
        cheapest_product = [r for r in results if r["is_cheapest"] is True][0]
        assert cheapest_product["price_eur"] == 1.99
        assert cheapest_product["retailer"] == "jumbo"
    
    @patch("aggregator.search.AHConnector")
    @patch("aggregator.search.JumboConnector")
    @patch("aggregator.search.PicnicConnector")
    def test_aggregated_search_marks_cheapest_single_product_per_group(self, mock_picnic, mock_jumbo, mock_ah):
        """Test that products with unique names are marked as cheapest (only one in group)."""
        # Setup mock connector with products that have different names
        mock_ah_instance = Mock()
        mock_ah_instance.search_products.return_value = [
            {"retailer": "ah", "id": "1", "name": "Product A", "price_eur": 1.99, "raw": {}},
            {"retailer": "ah", "id": "2", "name": "Product B", "price_eur": 2.50, "raw": {}},
            {"retailer": "ah", "id": "3", "name": "Product C", "price_eur": 3.00, "raw": {}},
        ]
        mock_ah.return_value = mock_ah_instance
        
        # Mock other connectors
        mock_jumbo.return_value.search_products.return_value = []
        mock_picnic.return_value.search_products.return_value = []
        
        # Perform search
        response = aggregated_search(
            query="test",
            retailers=["ah"],
            size_per_retailer=10,
            page=0
        )

        # Verify all products are marked as cheapest (each is only one in its group)
        results = response["results"]
        assert len(results) == 3
        assert all(r["is_cheapest"] is True for r in results)
    
    @patch("aggregator.search.AHConnector")
    @patch("aggregator.search.JumboConnector")
    @patch("aggregator.search.PicnicConnector")
    def test_aggregated_search_health_filter_with_sorting(self, mock_picnic, mock_jumbo, mock_ah):
        """Test that health_filter works correctly with different sort options."""
        # Setup mock connector with mixed health products
        mock_ah_instance = Mock()
        mock_ah_instance.search_products.return_value = [
            {"retailer": "ah", "id": "1", "name": "Healthy fruit", "price_eur": 3.00, "raw": {}},
            {"retailer": "ah", "id": "2", "name": "Healthy salad", "price_eur": 2.00, "raw": {}},
            {"retailer": "ah", "id": "3", "name": "Unhealthy chips", "price_eur": 1.50, "raw": {}},
            {"retailer": "ah", "id": "4", "name": "Unhealthy chocolate", "price_eur": 2.50, "raw": {}},
        ]
        mock_ah.return_value = mock_ah_instance
        
        # Mock other connectors
        mock_jumbo.return_value.search_products.return_value = []
        mock_picnic.return_value.search_products.return_value = []
        
        # Perform search with health_filter and sort_by="price"
        response = aggregated_search(
            query="test",
            retailers=["ah"],
            size_per_retailer=10,
            page=0,
            sort_by="price",
            health_filter="healthy"
        )

        # Verify only healthy products are returned, sorted by price
        # Extract results from response
        results = response["results"]
        assert len(results) == 2
        assert all(r["health_tag"] == "healthy" for r in results)
        assert results[0]["price_eur"] == 2.00  # Cheaper healthy product first
        assert results[1]["price_eur"] == 3.00  # More expensive healthy product second


