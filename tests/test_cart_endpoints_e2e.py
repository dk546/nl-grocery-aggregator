"""
End-to-end tests for cart endpoints verifying JSON shape matches Streamlit expectations.

This test module verifies that:
1. Cart endpoints return the correct JSON structure
2. The JSON shape matches what Streamlit frontend expects
3. All fields are present and correctly formatted
"""

import pytest
from fastapi.testclient import TestClient
from api.main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


class TestCartEndpointsE2E:
    """End-to-end tests for cart endpoints."""
    
    def test_add_item_json_shape(self, client):
        """Test that POST /cart/add returns JSON matching Streamlit expectations."""
        session_id = "test-e2e-session-add"
        
        item_data = {
            "retailer": "ah",
            "product_id": "test-123",
            "name": "Test Milk",
            "price_eur": 1.99,
            "quantity": 2,
            "image_url": "https://example.com/image.jpg",
            "health_tag": "neutral"
        }
        
        response = client.post(
            "/cart/add",
            json=item_data,
            headers={"X-Session-ID": session_id}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify top-level structure (what Streamlit expects)
        assert "items" in data
        assert "total_price" in data
        assert "total_by_retailer" in data
        
        # Verify items is a list
        assert isinstance(data["items"], list)
        assert len(data["items"]) == 1
        
        # Verify item structure (what Streamlit uses)
        item = data["items"][0]
        assert "retailer" in item
        assert "product_id" in item
        assert "name" in item
        assert "price_eur" in item
        assert "quantity" in item
        assert "line_total" in item  # Required by Streamlit for display
        assert "image_url" in item
        assert "health_tag" in item
        
        # Verify values
        assert item["retailer"] == "ah"
        assert item["product_id"] == "test-123"
        assert item["name"] == "Test Milk"
        assert item["price_eur"] == 1.99
        assert item["quantity"] == 2
        assert item["line_total"] == pytest.approx(3.98, rel=1e-2)  # 2 * 1.99
        assert item["image_url"] == "https://example.com/image.jpg"
        assert item["health_tag"] == "neutral"
        
        # Verify totals
        assert data["total_price"] == pytest.approx(3.98, rel=1e-2)
        assert "ah" in data["total_by_retailer"]
        assert data["total_by_retailer"]["ah"] == pytest.approx(3.98, rel=1e-2)
    
    def test_view_cart_json_shape(self, client):
        """Test that GET /cart/view returns JSON matching Streamlit expectations."""
        session_id = "test-e2e-session-view"
        
        # First add items from multiple retailers
        client.post(
            "/cart/add",
            json={
                "retailer": "ah",
                "product_id": "ah-1",
                "name": "AH Product",
                "price_eur": 2.50,
                "quantity": 1,
                "health_tag": "healthy"
            },
            headers={"X-Session-ID": session_id}
        )
        
        client.post(
            "/cart/add",
            json={
                "retailer": "jumbo",
                "product_id": "jumbo-1",
                "name": "Jumbo Product",
                "price_eur": 3.00,
                "quantity": 2,
                "health_tag": "neutral"
            },
            headers={"X-Session-ID": session_id}
        )
        
        # View cart
        response = client.get(
            "/cart/view",
            headers={"X-Session-ID": session_id}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify top-level structure
        assert "items" in data
        assert "total_price" in data
        assert "total_by_retailer" in data
        
        # Verify items structure
        assert isinstance(data["items"], list)
        assert len(data["items"]) == 2
        
        # Verify each item has required fields
        for item in data["items"]:
            assert "retailer" in item
            assert "product_id" in item
            assert "name" in item
            assert "price_eur" in item
            assert "quantity" in item
            assert "line_total" in item
            assert "health_tag" in item  # Can be None but must exist
            
            # Verify line_total is computed correctly
            expected_line_total = item["price_eur"] * item["quantity"]
            assert item["line_total"] == pytest.approx(expected_line_total, rel=1e-2)
        
        # Verify totals
        expected_total = 2.50 + (3.00 * 2)  # 8.50
        assert data["total_price"] == pytest.approx(expected_total, rel=1e-2)
        
        # Verify total_by_retailer
        assert "ah" in data["total_by_retailer"]
        assert "jumbo" in data["total_by_retailer"]
        assert data["total_by_retailer"]["ah"] == pytest.approx(2.50, rel=1e-2)
        assert data["total_by_retailer"]["jumbo"] == pytest.approx(6.00, rel=1e-2)
    
    def test_remove_item_json_shape(self, client):
        """Test that POST /cart/remove returns JSON matching Streamlit expectations."""
        session_id = "test-e2e-session-remove"
        
        # Add item
        client.post(
            "/cart/add",
            json={
                "retailer": "ah",
                "product_id": "remove-test",
                "name": "Item to Remove",
                "price_eur": 5.00,
                "quantity": 3
            },
            headers={"X-Session-ID": session_id}
        )
        
        # Remove one
        response = client.post(
            "/cart/remove?retailer=ah&product_id=remove-test&qty=1",
            headers={"X-Session-ID": session_id}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "items" in data
        assert "total_price" in data
        assert "total_by_retailer" in data
        
        # Verify updated quantity
        assert len(data["items"]) == 1
        assert data["items"][0]["quantity"] == 2
        assert data["items"][0]["line_total"] == pytest.approx(10.00, rel=1e-2)  # 2 * 5.00
        assert data["total_price"] == pytest.approx(10.00, rel=1e-2)
    
    def test_streamlit_basket_access_pattern(self, client):
        """Test the exact access pattern used by Streamlit My Basket page."""
        session_id = "test-streamlit-pattern"
        
        # Add items
        client.post(
            "/cart/add",
            json={
                "retailer": "ah",
                "product_id": "streamlit-1",
                "name": "Streamlit Test Item",
                "price_eur": 1.50,
                "quantity": 2,
                "health_tag": "healthy"
            },
            headers={"X-Session-ID": session_id}
        )
        
        # View cart (like Streamlit does)
        response = client.get(
            "/cart/view",
            headers={"X-Session-ID": session_id}
        )
        
        assert response.status_code == 200
        cart_data = response.json()
        
        # Simulate Streamlit's access pattern
        # From My_Basket.py: cart_data.get("items")
        basket = cart_data.get("items")
        assert basket is not None
        assert isinstance(basket, list)
        assert len(basket) > 0
        
        # From My_Basket.py: cart_data.get("total_price", 0.0)
        total_price = cart_data.get("total_price", 0.0)
        assert total_price > 0
        
        # From My_Basket.py: cart_data.get("total_by_retailer")
        total_by_retailer = cart_data.get("total_by_retailer")
        assert total_by_retailer is not None
        assert isinstance(total_by_retailer, dict)
        
        # From My_Basket.py: item.get("retailer", "")
        # From My_Basket.py: item.get("product_id", "")
        # From My_Basket.py: item.get("quantity", 0)
        # From My_Basket.py: item.get("line_total", ...)
        # From My_Basket.py: item.get("health_tag")
        for item in basket:
            retailer = item.get("retailer", "")
            product_id = item.get("product_id", "")
            quantity = item.get("quantity", 0)
            line_total = item.get("line_total")
            health_tag = item.get("health_tag")
            
            assert retailer != ""
            assert product_id != ""
            assert quantity > 0
            assert line_total is not None
            # health_tag can be None, but key must exist
            assert "health_tag" in item
    
    def test_empty_cart_json_shape(self, client):
        """Test that empty cart returns correct JSON structure."""
        session_id = "test-empty-cart"
        
        response = client.get(
            "/cart/view",
            headers={"X-Session-ID": session_id}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure even for empty cart
        assert "items" in data
        assert "total_price" in data
        assert "total_by_retailer" in data
        
        assert isinstance(data["items"], list)
        assert len(data["items"]) == 0
        assert data["total_price"] == 0.0
        assert isinstance(data["total_by_retailer"], dict)
        assert len(data["total_by_retailer"]) == 0

