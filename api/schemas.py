"""
Pydantic schemas for FastAPI request and response models.

This module defines the Pydantic models used for API request validation and
response serialization. These schemas ensure type safety and automatic API
documentation generation.

The schemas include:
- Product: Normalized product representation for search results
- SearchResponse: Complete search response with products and metadata
- CartItemInput: Input model for adding items to cart
- CartViewResponse: Response model for viewing cart with total
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class Product(BaseModel):
    """
    Normalized product representation returned from search.
    
    This model represents a product from any retailer in a unified format.
    All products from AH, Jumbo, and Picnic are normalized into this structure.
    """
    retailer: str = Field(..., description="Retailer identifier (ah, jumbo, or picnic)")
    id: str = Field(..., description="Unique product identifier from the retailer")
    name: str = Field(..., description="Product name")
    price_eur: float = Field(..., ge=0, description="Price per unit in euros")
    unit: Optional[str] = Field(None, description="Unit description (e.g., 'per stuk', 'per kg')")
    unit_size: Optional[str] = Field(None, description="Size information (e.g., '500ml', '1kg')")
    image_url: Optional[str] = Field(None, description="URL to product image")
    url: Optional[str] = Field(None, description="URL to product page on retailer website")
    health_tag: str = Field(..., description="Health category: 'healthy', 'unhealthy', or 'neutral'")
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "retailer": "ah",
                "id": "12345",
                "name": "Melk Halfvol",
                "price_eur": 1.99,
                "unit": "per stuk",
                "unit_size": "1L",
                "image_url": "https://example.com/image.jpg",
                "url": "https://ah.nl/product/12345",
                "health_tag": "neutral"
            }
        }


class SearchResponse(BaseModel):
    """
    Response model for product search endpoint.
    
    Contains the search results along with metadata about the search.
    """
    query: str = Field(..., description="The search query that was executed")
    count: int = Field(..., ge=0, description="Total number of products found")
    results: List[Product] = Field(..., description="List of products matching the search query")
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "query": "melk",
                "count": 15,
                "results": [
                    {
                        "retailer": "ah",
                        "id": "12345",
                        "name": "Melk Halfvol",
                        "price_eur": 1.99,
                        "unit": "per stuk",
                        "unit_size": "1L",
                        "image_url": "https://example.com/image.jpg",
                        "url": "https://ah.nl/product/12345",
                        "health_tag": "neutral"
                    }
                ]
            }
        }


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
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
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


class CartViewResponse(BaseModel):
    """
    Response model for viewing the shopping cart.
    
    Contains the cart contents along with the calculated total price.
    """
    cart: dict = Field(..., description="Cart contents as a dictionary of items")
    total: float = Field(..., ge=0, description="Total price of all items in the cart (in euros)")
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "cart": {
                    "items": {
                        "ah:12345": {
                            "retailer": "ah",
                            "product_id": "12345",
                            "name": "Melk Halfvol",
                            "price_eur": 1.99,
                            "quantity": 2,
                            "image_url": "https://example.com/image.jpg",
                            "health_tag": "neutral"
                        }
                    }
                },
                "total": 3.98
            }
        }

