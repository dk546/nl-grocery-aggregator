"""
Tests for Picnic connector error handling and robustness.

This module tests that the Picnic connector:
- Handles missing credentials gracefully
- Handles authentication errors gracefully
- Returns empty lists instead of crashing
- Logs errors appropriately
"""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock

from aggregator.connectors.picnic_connector import (
    PicnicConnector,
    PicnicAuthError,
    _validate_picnic_env
)


class TestPicnicConnectorValidation:
    """Test credential validation."""
    
    def test_validate_picnic_env_missing_username(self):
        """Test that missing PICNIC_USERNAME raises RuntimeError."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(RuntimeError) as exc_info:
                _validate_picnic_env()
            assert "PICNIC_USERNAME" in str(exc_info.value)
            assert "PICNIC_PASSWORD" in str(exc_info.value)
    
    def test_validate_picnic_env_missing_password(self):
        """Test that missing PICNIC_PASSWORD raises RuntimeError."""
        with patch.dict(os.environ, {"PICNIC_USERNAME": "test@example.com"}, clear=True):
            with pytest.raises(RuntimeError) as exc_info:
                _validate_picnic_env()
            assert "PICNIC_PASSWORD" in str(exc_info.value)
    
    def test_validate_picnic_env_success(self):
        """Test that valid credentials return correctly."""
        with patch.dict(os.environ, {
            "PICNIC_USERNAME": "test@example.com",
            "PICNIC_PASSWORD": "testpass",
            "PICNIC_COUNTRY_CODE": "NL"
        }, clear=True):
            username, password, country_code = _validate_picnic_env()
            assert username == "test@example.com"
            assert password == "testpass"
            assert country_code == "NL"
    
    def test_validate_picnic_env_default_country_code(self):
        """Test that country code defaults to NL."""
        with patch.dict(os.environ, {
            "PICNIC_USERNAME": "test@example.com",
            "PICNIC_PASSWORD": "testpass"
        }, clear=True):
            username, password, country_code = _validate_picnic_env()
            assert country_code == "NL"


class TestPicnicConnectorInitialization:
    """Test connector initialization with various credential scenarios."""
    
    def test_init_missing_credentials_raises_runtime_error(self):
        """Test that missing credentials raise RuntimeError."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(RuntimeError) as exc_info:
                PicnicConnector()
            assert "PICNIC_USERNAME" in str(exc_info.value) or "not configured" in str(exc_info.value)
    
    def test_init_with_valid_credentials(self):
        """Test that valid credentials allow initialization."""
        with patch.dict(os.environ, {
            "PICNIC_USERNAME": "test@example.com",
            "PICNIC_PASSWORD": "testpass"
        }, clear=True):
            with patch('aggregator.connectors.picnic_connector.PicnicAPI') as mock_api:
                mock_api.return_value = Mock()
                connector = PicnicConnector()
                assert connector.retailer == "picnic"
                mock_api.assert_called_once_with(
                    username="test@example.com",
                    password="testpass",
                    country_code="NL"
                )
    
    def test_init_auth_error_during_initialization(self):
        """Test that auth errors during initialization raise PicnicAuthError."""
        with patch.dict(os.environ, {
            "PICNIC_USERNAME": "test@example.com",
            "PICNIC_PASSWORD": "wrongpass"
        }, clear=True):
            with patch('aggregator.connectors.picnic_connector.PicnicAPI') as mock_api:
                # Simulate auth error during PicnicAPI initialization
                mock_api.side_effect = Exception("Authentication failed: invalid credentials")
                
                with pytest.raises(PicnicAuthError):
                    PicnicConnector()


class TestPicnicConnectorSearch:
    """Test search_products error handling."""
    
    @pytest.fixture
    def mock_picnic_client(self):
        """Create a mock PicnicAPI client."""
        mock_client = Mock()
        return mock_client
    
    def test_search_products_success(self, mock_picnic_client):
        """Test successful search returns products."""
        with patch.dict(os.environ, {
            "PICNIC_USERNAME": "test@example.com",
            "PICNIC_PASSWORD": "testpass"
        }, clear=True):
            with patch('aggregator.connectors.picnic_connector.PicnicAPI', return_value=mock_picnic_client):
                # Mock successful search response
                mock_picnic_client.search.return_value = [
                    {
                        "items": [
                            {
                                "type": "SINGLE_ARTICLE",
                                "id": "123",
                                "name": "Test Product",
                                "display_price": 199,  # 1.99 EUR in cents
                                "unit_size": "1L",
                                "unit_quantity": "1"
                            }
                        ]
                    }
                ]
                
                connector = PicnicConnector()
                results = connector.search_products("test", size=10, page=0)
                
                assert len(results) == 1
                assert results[0]["name"] == "Test Product"
                assert results[0]["price_eur"] == 1.99
    
    def test_search_products_auth_error(self, mock_picnic_client):
        """Test that auth errors during search raise PicnicAuthError."""
        with patch.dict(os.environ, {
            "PICNIC_USERNAME": "test@example.com",
            "PICNIC_PASSWORD": "testpass"
        }, clear=True):
            with patch('aggregator.connectors.picnic_connector.PicnicAPI', return_value=mock_picnic_client):
                # Mock auth error during search
                mock_picnic_client.search.side_effect = Exception("401 Unauthorized")
                
                connector = PicnicConnector()
                
                with pytest.raises(PicnicAuthError):
                    connector.search_products("test")
    
    def test_search_products_returns_empty_list_on_general_error(self, mock_picnic_client):
        """Test that non-auth errors return empty list."""
        with patch.dict(os.environ, {
            "PICNIC_USERNAME": "test@example.com",
            "PICNIC_PASSWORD": "testpass"
        }, clear=True):
            with patch('aggregator.connectors.picnic_connector.PicnicAPI', return_value=mock_picnic_client):
                # Mock network error (not auth-related)
                mock_picnic_client.search.side_effect = Exception("Network timeout")
                
                connector = PicnicConnector()
                results = connector.search_products("test")
                
                # Should return empty list, not raise
                assert results == []
    
    def test_search_products_empty_response(self, mock_picnic_client):
        """Test that empty search results return empty list."""
        with patch.dict(os.environ, {
            "PICNIC_USERNAME": "test@example.com",
            "PICNIC_PASSWORD": "testpass"
        }, clear=True):
            with patch('aggregator.connectors.picnic_connector.PicnicAPI', return_value=mock_picnic_client):
                mock_picnic_client.search.return_value = []
                
                connector = PicnicConnector()
                results = connector.search_products("test")
                
                assert results == []


class TestPicnicConnectorIntegration:
    """Test Picnic connector integration with aggregator."""
    
    def test_search_handles_picnic_auth_error_gracefully(self):
        """Test that aggregated_search handles PicnicAuthError without crashing."""
        from aggregator.search import aggregated_search
        
        # Mock connectors to simulate Picnic auth error
        with patch('aggregator.search.PicnicConnector') as mock_picnic_class:
            mock_picnic_instance = Mock()
            mock_picnic_instance.search_products.side_effect = PicnicAuthError("Auth failed")
            mock_picnic_class.side_effect = lambda: mock_picnic_instance
            
            # Mock AH and Jumbo to return some products
            with patch('aggregator.search.AHConnector') as mock_ah_class:
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
                
                # Should not raise, should return AH products only
                response = aggregated_search("test", ["ah", "picnic"], size_per_retailer=10)
                
                # Should have AH products
                assert isinstance(response, dict)
                assert "results" in response
                assert "connectors_status" in response
                results = response["results"]
                assert len(results) > 0
                assert all(p["retailer"] == "ah" for p in results)
                assert response["connectors_status"]["picnic"] == "auth_error"
    
    def test_search_handles_picnic_missing_credentials_gracefully(self):
        """Test that aggregated_search handles missing Picnic credentials without crashing."""
        from aggregator.search import aggregated_search
        
        # Mock Picnic connector to raise RuntimeError for missing credentials
        with patch('aggregator.search.PicnicConnector') as mock_picnic_class:
            mock_picnic_class.side_effect = RuntimeError("Picnic credentials not configured")
            
            # Mock AH to return products
            with patch('aggregator.search.AHConnector') as mock_ah_class:
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
                
                # Should not raise, should return AH products only
                response = aggregated_search("test", ["ah", "picnic"], size_per_retailer=10)
                
                # Should have AH products
                assert isinstance(response, dict)
                assert "results" in response
                assert "connectors_status" in response
                results = response["results"]
                assert len(results) > 0
                assert all(p["retailer"] == "ah" for p in results)
                # Missing credentials should result in "disabled" status
                assert response["connectors_status"]["picnic"] == "disabled"

