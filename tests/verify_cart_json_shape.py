"""
Manual verification script for cart endpoint JSON shape.

This script demonstrates the expected JSON structure returned by cart endpoints
and can be used to verify against a running backend server.

Usage:
    # Make sure backend is running: uvicorn api.main:app --reload --port 8000
    python tests/verify_cart_json_shape.py

Expected JSON structure matches what Streamlit frontend expects.
"""

import requests
import json


BASE_URL = "http://127.0.0.1:8000"
SESSION_ID = "verify-json-shape-session"


def verify_cart_add():
    """Verify POST /cart/add returns correct JSON shape."""
    print("=" * 60)
    print("Testing POST /cart/add")
    print("=" * 60)
    
    item_data = {
        "retailer": "ah",
        "product_id": "verify-1",
        "name": "Verification Product",
        "price_eur": 2.50,
        "quantity": 2,
        "image_url": "https://example.com/image.jpg",
        "health_tag": "healthy"
    }
    
    response = requests.post(
        f"{BASE_URL}/cart/add",
        json=item_data,
        headers={"X-Session-ID": SESSION_ID}
    )
    
    print(f"Status Code: {response.status_code}")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    data = response.json()
    print("\nResponse JSON:")
    print(json.dumps(data, indent=2))
    
    # Verify structure matches Streamlit expectations
    assert "items" in data, "Missing 'items' field"
    assert "total_price" in data, "Missing 'total_price' field"
    assert "total_by_retailer" in data, "Missing 'total_by_retailer' field"
    
    assert isinstance(data["items"], list), "'items' must be a list"
    assert len(data["items"]) == 1, "Should have 1 item"
    
    item = data["items"][0]
    required_fields = ["retailer", "product_id", "name", "price_eur", "quantity", "line_total"]
    for field in required_fields:
        assert field in item, f"Item missing required field: {field}"
    
    # Verify line_total is computed correctly
    assert item["line_total"] == item["price_eur"] * item["quantity"], \
        f"line_total should be {item['price_eur'] * item['quantity']}, got {item['line_total']}"
    
    print("\n✅ All fields present and correctly formatted!")
    return data


def verify_cart_view():
    """Verify GET /cart/view returns correct JSON shape."""
    print("\n" + "=" * 60)
    print("Testing GET /cart/view")
    print("=" * 60)
    
    response = requests.get(
        f"{BASE_URL}/cart/view",
        headers={"X-Session-ID": SESSION_ID}
    )
    
    print(f"Status Code: {response.status_code}")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    data = response.json()
    print("\nResponse JSON:")
    print(json.dumps(data, indent=2))
    
    # Verify structure
    assert "items" in data, "Missing 'items' field"
    assert "total_price" in data, "Missing 'total_price' field"
    assert "total_by_retailer" in data, "Missing 'total_by_retailer' field"
    
    print("\n✅ Cart view structure is correct!")
    return data


def verify_cart_remove():
    """Verify POST /cart/remove returns correct JSON shape."""
    print("\n" + "=" * 60)
    print("Testing POST /cart/remove")
    print("=" * 60)
    
    response = requests.post(
        f"{BASE_URL}/cart/remove?retailer=ah&product_id=verify-1&qty=1",
        headers={"X-Session-ID": SESSION_ID}
    )
    
    print(f"Status Code: {response.status_code}")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    data = response.json()
    print("\nResponse JSON:")
    print(json.dumps(data, indent=2))
    
    # Verify structure
    assert "items" in data, "Missing 'items' field"
    assert "total_price" in data, "Missing 'total_price' field"
    assert "total_by_retailer" in data, "Missing 'total_by_retailer' field"
    
    # Verify quantity was reduced
    assert len(data["items"]) == 1, "Should still have 1 item"
    assert data["items"][0]["quantity"] == 1, "Quantity should be reduced to 1"
    
    print("\n✅ Remove endpoint structure is correct!")


def main():
    """Run all verification tests."""
    print("Cart JSON Shape Verification")
    print("=" * 60)
    print(f"Base URL: {BASE_URL}")
    print(f"Session ID: {SESSION_ID}")
    print()
    
    try:
        # Test cart add
        verify_cart_add()
        
        # Test cart view
        verify_cart_view()
        
        # Test cart remove
        verify_cart_remove()
        
        print("\n" + "=" * 60)
        print("✅ ALL VERIFICATIONS PASSED!")
        print("=" * 60)
        print("\nThe JSON structure matches what Streamlit frontend expects:")
        print("- items: List of cart items with all required fields")
        print("- total_price: Total price of all items")
        print("- total_by_retailer: Dict mapping retailer to total")
        print("- Each item has: retailer, product_id, name, price_eur, quantity, line_total")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Could not connect to backend.")
        print("Make sure the backend is running:")
        print("  uvicorn api.main:app --reload --port 8000")
    except AssertionError as e:
        print(f"\n❌ VERIFICATION FAILED: {e}")
        raise
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        raise


if __name__ == "__main__":
    main()

