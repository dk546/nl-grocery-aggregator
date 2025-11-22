from typing import Dict, Any
from pydantic import BaseModel


class CartItem(BaseModel):
    retailer: str
    product_id: str
    name: str
    price_eur: float
    quantity: int = 1
    image_url: str | None = None
    health_tag: str | None = None

    @property
    def total_price(self) -> float:
        return self.price_eur * self.quantity


class Cart(BaseModel):
    items: Dict[str, CartItem] = {}  # key: {retailer}:{product_id}

    def add_item(self, item: CartItem) -> None:
        key = f"{item.retailer}:{item.product_id}"
        if key in self.items:
            self.items[key].quantity += item.quantity
        else:
            self.items[key] = item

    def remove_item(self, retailer: str, product_id: str, quantity: int = 1) -> None:
        key = f"{retailer}:{product_id}"
        if key not in self.items:
            return
        self.items[key].quantity -= quantity
        if self.items[key].quantity <= 0:
            del self.items[key]

    def total(self) -> float:
        return sum(i.total_price for i in self.items.values())
