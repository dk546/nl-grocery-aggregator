"""
Pydantic schemas for FastAPI request and response models.

This module defines the Pydantic models used for API request validation and
response serialization. These schemas ensure type safety and automatic API
documentation generation.

The schemas include:
- ProductBase: Base product schema with all normalized fields (backward compatible)
- SearchResponse: List of ProductBase items
- CartItemInput: Input model for adding items to cart
- CartView: Response model for viewing cart with items and total

# NOTE: ProductBase is maintained for backward compatibility with the existing API contract.
    It should match the structure returned by aggregator.search.aggregated_search().
    The underlying product models are defined in aggregator.models (ProductInternal, ProductPublic).
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ConfigDict
from aggregator.models import CartItem


class ProductBase(BaseModel):
    """
    Base product schema representing a normalized product from any retailer.
    
    This model represents a product from any retailer (AH, Jumbo, Picnic) in a unified format.
    All fields match what aggregated_search returns, including health_tag, is_cheapest,
    and raw data.
    
    This schema is backward compatible with the existing API contract while supporting
    the new normalized product schema from aggregator.models.ProductPublic.
    """
    id: str = Field(..., description="Unique product identifier")
    retailer: str = Field(..., description="Retailer identifier (ah, jumbo, or picnic)")
    name: str = Field(..., description="Product name")
    price_eur: float = Field(..., ge=0, description="Price per unit in euros")
    price: Optional[float] = Field(None, ge=0, description="Price per unit in euros (alias for price_eur)")
    unit: Optional[str] = Field(None, description="Unit description (e.g., 'per stuk', 'per kg')")
    unit_size: Optional[str] = Field(None, description="Size information (e.g., '500ml', '1kg')")
    quantity: Optional[float] = Field(None, ge=0, description="Total quantity represented by this product")
    quantity_unit: Optional[str] = Field(None, description="Unit used for quantity (kg, g, L, mL, piece)")
    price_per_unit: Optional[float] = Field(None, ge=0, description="Price per canonical unit (per kg, per L, or per piece)")
    image_url: Optional[str] = Field(None, description="URL to product image")
    url: Optional[str] = Field(None, description="URL to product page on retailer website")
    health_tag: str = Field(..., description="Health category: 'healthy', 'unhealthy', or 'neutral'")
    is_cheapest: Optional[bool] = Field(None, description="Whether this is the cheapest option in its name group")
    raw: Optional[Dict[str, Any]] = Field(None, description="Raw product data from retailer API (if available)")
    
    model_config = ConfigDict(
        populate_by_name=True,  # Allow access by both field name and alias
        json_schema_extra={
            "example": {
                "id": "ah:12345",
                "retailer": "ah",
                "name": "Melk Halfvol",
                "price": 1.99,
                "price_eur": 1.99,
                "unit": "per stuk",
                "unit_size": "1L",
                "quantity": 1.0,
                "quantity_unit": "L",
                "price_per_unit": 1.99,
                "image_url": "https://example.com/image.jpg",
                "url": "https://ah.nl/product/12345",
                "health_tag": "neutral",
                "is_cheapest": True,
                "raw": {}
            }
        }
    )


class SearchResponse(BaseModel):
    """
    Response model for product search endpoint.
    
    Contains a list of normalized products matching the search query and connector status information.
    """
    results: List[ProductBase] = Field(..., description="List of products matching the search query")
    connectors_status: Dict[str, str] = Field(
        default_factory=dict,
        description="Status of each connector: 'ok', 'auth_error', 'disabled', 'error', or 'skipped'"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "results": [
                    {
                        "id": "12345",
                        "retailer": "ah",
                        "name": "Melk Halfvol",
                        "price_eur": 1.99,
                        "unit": "per stuk",
                        "unit_size": "1L",
                        "image_url": "https://example.com/image.jpg",
                        "url": "https://ah.nl/product/12345",
                        "health_tag": "neutral",
                        "is_cheapest": True,
                        "raw": {}
                    }
                ]
            }
        }
    )


class CartItemInput(BaseModel):
    """
    Input model for adding an item to the shopping cart.
    
    This model validates the data required to add a product to the cart.
    """
    retailer: str = Field(..., description="Retailer identifier (ah, jumbo, or picnic)")
    product_id: str = Field(..., description="Unique product identifier from the retailer")
    name: str = Field(..., description="Product name")
    price_eur: float = Field(..., ge=0, description="Price per unit in euros")
    quantity: int = Field(1, ge=1, description="Quantity to add to cart (default: 1)")
    image_url: Optional[str] = Field(None, description="URL to product image")
    health_tag: Optional[str] = Field(None, description="Health category tag (optional)")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "retailer": "ah",
                "product_id": "12345",
                "name": "Melk Halfvol",
                "price_eur": 1.99,
                "quantity": 2,
                "image_url": "https://example.com/image.jpg",
                "health_tag": "neutral"
            }
        }
    )


class CartItemOut(BaseModel):
    """
    Output model for a cart item with computed line total.
    
    This extends CartItem with a computed line_total field for convenience.
    """
    retailer: str
    product_id: str
    name: str
    price_eur: float
    quantity: int
    image_url: Optional[str] = None
    health_tag: Optional[str] = None
    line_total: float = Field(..., description="Computed total: price_eur * quantity")


class CartView(BaseModel):
    """
    Response model for viewing the shopping cart.
    
    Contains the cart items as a list, the calculated total price, and totals grouped by retailer.
    """
    items: List[CartItemOut] = Field(..., description="List of cart items with line totals")
    total_price: float = Field(..., ge=0, description="Total price of all items in the cart (in euros)")
    total_by_retailer: Dict[str, float] = Field(..., description="Total price grouped by retailer (e.g., {'ah': 5.29, 'jumbo': 3.49})")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [
                    {
                        "retailer": "ah",
                        "product_id": "12345",
                        "name": "Melk Halfvol",
                        "price_eur": 1.99,
                        "quantity": 2,
                        "image_url": "https://example.com/image.jpg",
                        "health_tag": "neutral",
                        "line_total": 3.98
                    }
                ],
                "total_price": 3.98,
                "total_by_retailer": {"ah": 3.98}
            }
        }
    )



