"""
Product and cart models for the aggregator system.

This module defines the canonical product schemas used throughout the aggregator.
All connectors must map their raw product data into ProductInternal first, then
into ProductPublic for API responses.

# NOTE: ProductPublic is the canonical response schema used by the API.
    All connectors must map their raw product data into ProductInternal first,
    then into ProductPublic. The frontend (Streamlit app) expects fields like
    price_eur, name, retailer, unit, unit_size, image_url, url, health_tag, is_cheapest.

Current field expectations:
- Frontend expects: price_eur, name, retailer, unit, unit_size, image_url, url, health_tag, is_cheapest
- AH connector returns: id, name, price_eur, unit, unit_size, image_url, url, raw
- Jumbo connector returns: id, name, price_eur, unit, unit_size, image_url, url, raw  
- Picnic connector returns: id, name, price_eur (from cents), unit_quantity, unit_size, image_url (constructed), url, raw
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ConfigDict


class ProductInternal(BaseModel):
    """
    Internal product model for use within the aggregator system.
    
    This model can include extra raw fields, intermediate parsed fields, or
    connector-specific metadata beyond what's exposed in ProductPublic.
    """
    # Core identifiers
    id: str = Field(..., description="Unique product identifier (format: '{retailer}:{external_id}')")
    retailer: str = Field(..., description="Retailer identifier (ah, jumbo, picnic)")
    
    # Basic product info
    name: str = Field(..., description="Product name")
    brand: Optional[str] = Field(None, description="Product brand name")
    category: Optional[str] = Field(None, description="Product category")
    
    # Media and links
    image_url: Optional[str] = Field(None, description="URL to product image")
    product_url: Optional[str] = Field(None, description="Link to retailer product page")
    
    # Pricing
    price: float = Field(..., ge=0, description="Total price for the item as sold (in currency)")
    currency: str = Field(default="EUR", description="Currency code (e.g., EUR)")
    price_per_unit: Optional[float] = Field(None, ge=0, description="Price per canonical unit (per kg, per L, or per piece)")
    
    # Quantity and units
    unit: Optional[str] = Field(None, description="Canonical unit for price_per_unit (kg, g, L, mL, piece)")
    quantity: Optional[float] = Field(None, ge=0, description="Total quantity represented by this product (e.g., 500 grams, 1 liter, 6 pieces)")
    quantity_unit: Optional[str] = Field(None, description="Unit used for quantity (kg, g, L, mL, piece)")
    
    # Promotions
    is_promotion: bool = Field(default=False, description="Whether item is currently on sale/promo")
    promo_text: Optional[str] = Field(None, description="Short promo text if available")
    
    # Raw data and metadata
    source_raw: Optional[Dict[str, Any]] = Field(None, description="Raw product data from connector (for debugging)")
    
    # Legacy/compatibility fields (kept for backward compatibility during transition)
    price_eur: Optional[float] = Field(None, ge=0, description="Price in EUR (deprecated, use 'price' instead)")
    unit_size: Optional[str] = Field(None, description="Legacy size string (deprecated, use quantity + quantity_unit instead)")
    
    model_config = ConfigDict(extra="allow")  # Allow extra fields for connector-specific data


class ProductPublic(BaseModel):
    """
    Public API product model returned to clients (frontend).
    
    This is the clean, stable contract that the frontend relies on.
    Fields are normalized and consistent across all retailers.
    """
    # Core identifiers
    id: str = Field(..., description="Unique product identifier")
    retailer: str = Field(..., description="Retailer identifier (ah, jumbo, picnic)")
    
    # Basic product info
    name: str = Field(..., description="Product name")
    brand: Optional[str] = Field(None, description="Product brand name")
    category: Optional[str] = Field(None, description="Product category")
    
    # Media and links
    image_url: Optional[str] = Field(None, description="URL to product image")
    url: Optional[str] = Field(None, description="URL to product page on retailer website")
    
    # Pricing (backward compatible: both price and price_eur available)
    price: float = Field(..., ge=0, description="Price per unit in euros")
    price_eur: Optional[float] = Field(None, ge=0, description="Price per unit in euros (backward compatible, equals price)")
    currency: str = Field(default="EUR", description="Currency code")
    price_per_unit: Optional[float] = Field(None, ge=0, description="Price per canonical unit (per kg, per L, or per piece)")
    
    # Quantity and units (backward compatible: unit and unit_size for legacy frontend)
    unit: Optional[str] = Field(None, description="Unit description (e.g., 'per stuk', 'per kg') - legacy field")
    unit_size: Optional[str] = Field(None, description="Size information (e.g., '500ml', '1kg') - legacy field")
    quantity: Optional[float] = Field(None, ge=0, description="Total quantity represented by this product")
    quantity_unit: Optional[str] = Field(None, description="Unit used for quantity (kg, g, L, mL, piece)")
    
    # Promotions
    is_promotion: bool = Field(default=False, description="Whether item is currently on sale")
    promo_text: Optional[str] = Field(None, description="Short promo text if available")
    
    # Aggregator-added fields (not from connectors)
    health_tag: str = Field(..., description="Health category: 'healthy', 'unhealthy', or 'neutral'")
    is_cheapest: Optional[bool] = Field(None, description="Whether this is the cheapest option (backward compatible, equals is_cheapest_total)")
    is_cheapest_total: bool = Field(default=False, description="Whether this has the lowest total price across all results")
    is_cheapest_per_unit: bool = Field(default=False, description="Whether this has the lowest price_per_unit across all results (where price_per_unit is available)")
    
    # Raw data (optional, for debugging)
    raw: Optional[Dict[str, Any]] = Field(None, description="Raw product data from retailer API (if available)")
    
    model_config = ConfigDict(
        populate_by_name=True,  # Allow access by both field name and alias
        json_schema_extra={
            "example": {
                "id": "ah:12345",
                "retailer": "ah",
                "name": "Melk Halfvol",
                "brand": "AH",
                "price": 1.99,
                "price_eur": 1.99,
                "currency": "EUR",
                "price_per_unit": 1.99,
                "unit": "per stuk",
                "unit_size": "1L",
                "quantity": 1.0,
                "quantity_unit": "L",
                "is_promotion": False,
                "health_tag": "neutral",
                "is_cheapest": True,
                "is_cheapest_total": True,
                "is_cheapest_per_unit": False,
                "image_url": "https://example.com/image.jpg",
                "url": "https://ah.nl/product/12345",
            }
        }
    )
    
    def model_post_init(self, __context: Any) -> None:
        """Ensure price_eur is set from price if not provided."""
        if self.price_eur is None:
            # Use object.__setattr__ because Pydantic models are frozen by default
            object.__setattr__(self, "price_eur", self.price)


# Cart models (kept for backward compatibility)
class CartItem(BaseModel):
    """Cart item model for shopping cart functionality."""
    retailer: str = Field(..., description="Retailer identifier")
    product_id: str = Field(..., description="Product identifier")
    name: str = Field(..., description="Product name")
    price_eur: float = Field(..., ge=0, description="Price per unit in euros")
    quantity: int = Field(1, ge=1, description="Quantity in cart")
    image_url: Optional[str] = Field(None, description="Product image URL")
    health_tag: Optional[str] = Field(None, description="Health category tag")
    
    @property
    def total_price(self) -> float:
        """Calculate total price for this cart item (price * quantity)."""
        return self.price_eur * self.quantity
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "retailer": "ah",
                "product_id": "12345",
                "name": "Melk Halfvol",
                "price_eur": 1.99,
                "quantity": 2,
                "health_tag": "neutral"
            }
        }
    )


class Cart(BaseModel):
    """Shopping cart model."""
    items: Dict[str, CartItem] = Field(default_factory=dict, description="Cart items keyed by retailer:product_id")
    
    model_config = ConfigDict(extra="allow", frozen=False)  # Allow mutations
    
    def add(self, item: CartItem) -> None:
        """Add an item to the cart or accumulate quantity if it already exists."""
        key = f"{item.retailer}:{item.product_id}"
        if key in self.items:
            # Accumulate quantity
            existing_item = self.items[key]
            item_dict = existing_item.model_dump()
            item_dict["quantity"] = existing_item.quantity + item.quantity
            self.items[key] = CartItem(**item_dict)
        else:
            # Add new item
            self.items[key] = item
    
    def remove(self, retailer: str, product_id: str, qty: int = 1) -> None:
        """Remove an item from the cart or reduce its quantity."""
        key = f"{retailer}:{product_id}"
        if key in self.items:
            existing_item = self.items[key]
            new_quantity = existing_item.quantity - qty
            if new_quantity <= 0:
                # Remove item completely
                del self.items[key]
            else:
                # Reduce quantity
                item_dict = existing_item.model_dump()
                item_dict["quantity"] = new_quantity
                self.items[key] = CartItem(**item_dict)
    
    def total(self) -> float:
        """Calculate total price of all items in cart."""
        return sum(item.price_eur * item.quantity for item in self.items.values())
    
    def total_by_retailer(self) -> Dict[str, float]:
        """
        Calculate total price grouped by retailer.
        
        Returns:
            Dictionary mapping retailer identifier to total price (e.g., {"ah": 5.29, "jumbo": 3.49})
        """
        totals: Dict[str, float] = {}
        for item in self.items.values():
            retailer = item.retailer
            line_total = item.price_eur * item.quantity
            totals[retailer] = totals.get(retailer, 0.0) + line_total
        return totals
