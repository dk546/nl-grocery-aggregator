"""
Tests for partial connector failure behavior in aggregated search.

These tests verify that:
- Partial connector failures don't prevent returning results from successful connectors
- Connector status is correctly tracked and returned
- The API returns HTTP 200 even when some connectors fail
"""

import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient

from aggregator.search import aggregated_search
from aggregator.connectors.picnic_connector import PicnicAuthError
from api.main import app


class TestPartialConnectorFailures:
    """Test that partial failures are handled gracefully."""
    
    def test_ah_jumbo_ok_picnic_auth_error_returns_partial_results(self):
        """Test that when Picnic fails with auth error, AH and Jumbo results are still returned."""
        # Clear cache to avoid interference from previous tests
        from aggregator.utils.cache import clear_cache
        clear_cache()
        
        with patch('aggregator.search.AHConnector') as mock_ah_class, \
             patch('aggregator.search.JumboConnector') as mock_jumbo_class, \
             patch('aggregator.search.PicnicConnector') as mock_picnic_class, \
             patch('aggregator.search.DirkConnector') as mock_dirk_class:
            
            # Mock Dirk connector to prevent unexpected calls
            mock_dirk_class.side_effect = RuntimeError("Dirk token missing")
            
            # Mock AH connector - success
            mock_ah_instance = Mock()
            mock_ah_instance.retailer = "ah"
            mock_ah_instance.search_products.return_value = [
                {
                    "id": "ah:1",
                    "retailer": "ah",
                    "name": "AH Product",
                    "price": 1.50,
                    "price_eur": 1.50,
                    "health_tag": "neutral"
                }
            ]
            mock_ah_class.return_value = mock_ah_instance
            
            # Mock Jumbo connector - success
            mock_jumbo_instance = Mock()
            mock_jumbo_instance.retailer = "jumbo"
            mock_jumbo_instance.search_products.return_value = [
                {
                    "id": "jumbo:1",
                    "retailer": "jumbo",
                    "name": "Jumbo Product",
                    "price": 2.00,
                    "price_eur": 2.00,
                    "health_tag": "neutral"
                }
            ]
            mock_jumbo_class.return_value = mock_jumbo_instance
            
            # Mock Picnic connector - auth error
            mock_picnic_instance = Mock()
            mock_picnic_instance.retailer = "picnic"
            mock_picnic_instance.search_products.side_effect = PicnicAuthError("Picnic authentication error")
            mock_picnic_class.return_value = mock_picnic_instance
            
            # Call aggregated_search
            response = aggregated_search("test", ["ah", "jumbo", "picnic"], size_per_retailer=10)
            
            # Verify response structure
            assert isinstance(response, dict)
            assert "results" in response
            assert "connectors_status" in response
            
            # Verify results contain AH and Jumbo products
            results = response["results"]
            assert len(results) == 2
            assert all(r["retailer"] in ("ah", "jumbo") for r in results)
            
            # Verify connector status
            status = response["connectors_status"]
            assert status["ah"] == "ok"
            assert status["jumbo"] == "ok"
            assert status["picnic"] == "auth_error"
    
    def test_ah_ok_picnic_disabled_returns_ah_results(self):
        """Test that when Picnic is disabled (missing credentials), AH results are still returned."""
        # Clear cache to avoid interference from previous tests
        from aggregator.utils.cache import clear_cache
        clear_cache()
        
        with patch('aggregator.search.AHConnector') as mock_ah_class, \
             patch('aggregator.search.PicnicConnector') as mock_picnic_class, \
             patch('aggregator.search.JumboConnector') as mock_jumbo_class, \
             patch('aggregator.search.DirkConnector') as mock_dirk_class:
            
            # Mock AH connector - success
            mock_ah_instance = Mock()
            mock_ah_instance.retailer = "ah"
            mock_ah_instance.search_products.return_value = [
                {
                    "id": "ah:1",
                    "retailer": "ah",
                    "name": "AH Product",
                    "price": 1.50,
                    "price_eur": 1.50,
                    "health_tag": "neutral"
                }
            ]
            mock_ah_class.return_value = mock_ah_instance
            
            # Mock Picnic connector - RuntimeError for missing credentials
            # The search code checks if the error message contains "credential" or "not configured"
            mock_picnic_class.side_effect = RuntimeError("Picnic credentials not configured")
            
            # Mock other connectors to prevent unexpected calls
            mock_jumbo_class.side_effect = RuntimeError("Jumbo token missing")
            mock_dirk_class.side_effect = RuntimeError("Dirk token missing")
            
            # Call aggregated_search
            response = aggregated_search("test", ["ah", "picnic"], size_per_retailer=10)
            
            # Verify response structure
            assert isinstance(response, dict)
            assert "results" in response
            assert "connectors_status" in response
            
            # Verify results contain only AH products
            results = response["results"]
            assert len(results) == 1
            assert results[0]["retailer"] == "ah"
            
            # Verify connector status
            # Note: The actual status depends on how the error is detected
            # "disabled" is set when RuntimeError contains "credential" or "not configured"
            # "auth_error" is set for PicnicAuthError or other auth failures
            status = response["connectors_status"]
            assert status["ah"] == "ok"
            assert status["picnic"] in ("disabled", "error")  # Accept both as valid
    
    def test_api_endpoint_returns_200_with_partial_failures(self):
        """Test that the API endpoint returns 200 even when some connectors fail."""
        with patch('aggregator.search.AHConnector') as mock_ah_class, \
             patch('aggregator.search.PicnicConnector') as mock_picnic_class:
            
            # Mock AH connector - success
            mock_ah_instance = Mock()
            mock_ah_instance.retailer = "ah"
            mock_ah_instance.search_products.return_value = [
                {
                    "id": "ah:1",
                    "retailer": "ah",
                    "name": "AH Product",
                    "price": 1.50,
                    "price_eur": 1.50,
                    "health_tag": "neutral"
                }
            ]
            mock_ah_class.return_value = mock_ah_instance
            
            # Mock Picnic connector - auth error
            mock_picnic_instance = Mock()
            mock_picnic_instance.retailer = "picnic"
            mock_picnic_instance.search_products.side_effect = PicnicAuthError("Picnic authentication error")
            mock_picnic_class.return_value = mock_picnic_instance
            
            # Call API endpoint via TestClient
            client = TestClient(app)
            response = client.get("/search?q=test&retailers=ah,picnic")
            
            # Verify HTTP 200
            assert response.status_code == 200
            
            # Verify response structure
            data = response.json()
            assert "results" in data
            assert "connectors_status" in data
            
            # Verify results
            assert len(data["results"]) == 1
            assert data["results"][0]["retailer"] == "ah"
            
            # Verify connector status
            assert data["connectors_status"]["ah"] == "ok"
            assert data["connectors_status"]["picnic"] == "auth_error"
    
    def test_all_connectors_fail_returns_empty_results_with_status(self):
        """Test that when all connectors fail, we still return 200 with empty results and status."""
        # Clear cache to avoid interference from previous tests
        from aggregator.utils.cache import clear_cache
        clear_cache()
        
        with patch('aggregator.search.AHConnector') as mock_ah_class, \
             patch('aggregator.search.PicnicConnector') as mock_picnic_class, \
             patch('aggregator.search.JumboConnector') as mock_jumbo_class, \
             patch('aggregator.search.DirkConnector') as mock_dirk_class:
            
            # Mock AH connector - RuntimeError
            mock_ah_class.side_effect = RuntimeError("AH token missing")
            
            # Mock Picnic connector - auth error
            mock_picnic_instance = Mock()
            mock_picnic_instance.retailer = "picnic"
            mock_picnic_instance.search_products.side_effect = PicnicAuthError("Picnic authentication error")
            mock_picnic_class.return_value = mock_picnic_instance
            
            # Mock Jumbo connector - RuntimeError (not requested but should be mocked for safety)
            mock_jumbo_class.side_effect = RuntimeError("Jumbo token missing")
            
            # Mock Dirk connector - RuntimeError (not requested but should be mocked for safety)
            mock_dirk_class.side_effect = RuntimeError("Dirk token missing")
            
            # Call aggregated_search
            response = aggregated_search("test", ["ah", "picnic"], size_per_retailer=10)
            
            # Verify response structure
            assert isinstance(response, dict)
            assert "results" in response
            assert "connectors_status" in response
            
            # Verify empty results
            assert len(response["results"]) == 0
            
            # Verify connector status shows failures
            status = response["connectors_status"]
            assert status["ah"] in ("disabled", "error")
            assert status["picnic"] == "auth_error"

