"""
Pydantic schemas for FastAPI request and response models.

This module defines the Pydantic models used for API request validation and
response serialization. These schemas ensure type safety and automatic API
documentation generation.

The schemas include:
- ProductBase: Base product schema with all normalized fields
- SearchResponse: List of ProductBase items
- CartItemInput: Input model for adding items to cart
- CartView: Response model for viewing cart with items and total
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
    """
    id: str = Field(..., description="Unique product identifier from the retailer")
    retailer: str = Field(..., description="Retailer identifier (ah, jumbo, or picnic)")
    name: str = Field(..., description="Product name")
    price_eur: float = Field(..., ge=0, description="Price per unit in euros")
    unit: Optional[str] = Field(None, description="Unit description (e.g., 'per stuk', 'per kg')")
    unit_size: Optional[str] = Field(None, description="Size information (e.g., '500ml', '1kg')")
    image_url: Optional[str] = Field(None, description="URL to product image")
    url: Optional[str] = Field(None, description="URL to product page on retailer website")
    health_tag: str = Field(..., description="Health category: 'healthy', 'unhealthy', or 'neutral'")
    is_cheapest: Optional[bool] = Field(None, description="Whether this is the cheapest option in its name group")
    raw: Optional[Dict[str, Any]] = Field(None, description="Raw product data from retailer API (if available)")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
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
        }
    )


class SearchResponse(BaseModel):
    """
    Response model for product search endpoint.
    
    Contains a list of normalized products matching the search query.
    """
    results: List[ProductBase] = Field(..., description="List of products matching the search query")
    
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


class CartView(BaseModel):
    """
    Response model for viewing the shopping cart.
    
    Contains the cart items as a list and the calculated total price.
    """
    items: List[CartItem] = Field(..., description="List of cart items")
    total: float = Field(..., ge=0, description="Total price of all items in the cart (in euros)")
    
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
                        "health_tag": "neutral"
                    }
                ],
                "total": 3.98
            }
        }
    )



