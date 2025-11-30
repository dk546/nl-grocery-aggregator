# Cart Endpoints JSON Shape Verification

## Summary

✅ **All cart endpoints have been verified end-to-end via TestClient**
✅ **JSON structure matches exactly what Streamlit frontend expects**

## Verified JSON Structure

### POST /cart/add & GET /cart/view & POST /cart/remove

All three endpoints return the same `CartView` structure:

```json
{
  "items": [
    {
      "retailer": "ah",
      "product_id": "test-123",
      "name": "Test Product",
      "price_eur": 2.50,
      "quantity": 2,
      "line_total": 5.00,
      "image_url": "https://example.com/image.jpg",
      "health_tag": "healthy"
    }
  ],
  "total_price": 5.00,
  "total_by_retailer": {
    "ah": 5.00
  }
}
```

## Field-by-Field Verification

### Top-Level Fields (Required by Streamlit)

| Field | Type | Used By Streamlit | Status |
|-------|------|-------------------|--------|
| `items` | `List[CartItemOut]` | `cart_data.get("items")` | ✅ Verified |
| `total_price` | `float` | `cart_data.get("total_price", 0.0)` | ✅ Verified |
| `total_by_retailer` | `Dict[str, float]` | `cart_data.get("total_by_retailer")` | ✅ Verified |

### Item-Level Fields (Required by Streamlit)

| Field | Type | Used By Streamlit | Status |
|-------|------|-------------------|--------|
| `retailer` | `str` | `item.get("retailer", "")` | ✅ Verified |
| `product_id` | `str` | `item.get("product_id", "")` | ✅ Verified |
| `name` | `str` | Display in table | ✅ Verified |
| `price_eur` | `float` | `item.get("price_eur", 0.0)` | ✅ Verified |
| `quantity` | `int` | `item.get("quantity", 0)` | ✅ Verified |
| `line_total` | `float` | `item.get("line_total", ...)` | ✅ Verified |
| `image_url` | `Optional[str]` | Optional display | ✅ Verified |
| `health_tag` | `Optional[str]` | `item.get("health_tag")` | ✅ Verified |

## Test Results

### End-to-End Tests (TestClient)

All 5 tests pass:

1. ✅ `test_add_item_json_shape` - Verifies POST /cart/add returns correct structure
2. ✅ `test_view_cart_json_shape` - Verifies GET /cart/view with multiple retailers
3. ✅ `test_remove_item_json_shape` - Verifies POST /cart/remove updates correctly
4. ✅ `test_streamlit_basket_access_pattern` - Verifies exact Streamlit access patterns
5. ✅ `test_empty_cart_json_shape` - Verifies empty cart structure

### Streamlit Access Patterns Verified

The tests verify the exact access patterns used in `streamlit_app/pages/03_🧺_My_Basket.py`:

```python
# Top-level access
cart_data.get("items")
cart_data.get("total_price", 0.0)
cart_data.get("total_by_retailer")

# Item-level access
item.get("retailer", "")
item.get("product_id", "")
item.get("quantity", 0)
item.get("line_total", ...)
item.get("health_tag")
```

All patterns work correctly ✅

## Manual Verification

To verify manually with a running backend:

```bash
# Start backend
uvicorn api.main:app --reload --port 8000

# Run verification script
python tests/verify_cart_json_shape.py

# Or use curl:
curl -X POST http://127.0.0.1:8000/cart/add \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: test-session" \
  -d '{
    "retailer": "ah",
    "product_id": "test-1",
    "name": "Test Product",
    "price_eur": 2.50,
    "quantity": 2
  }'

curl -X GET http://127.0.0.1:8000/cart/view \
  -H "X-Session-ID: test-session"
```

## Conclusion

✅ **All cart endpoints return JSON structures that match Streamlit expectations**
✅ **All required fields are present and correctly typed**
✅ **Line totals are computed correctly**
✅ **Retailer totals are computed correctly**
✅ **Empty cart returns correct structure**

The cart API is production-ready for Streamlit frontend integration.

