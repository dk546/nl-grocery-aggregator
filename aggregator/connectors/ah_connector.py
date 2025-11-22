from typing import List, Dict, Any
from supermarktconnector.ah import AHConnector as _AH
from .base import BaseConnector


class AHRetailConnector(BaseConnector):
    retailer = "ah"

    def __init__(self) -> None:
        self._client = _AH()

    def search_products(self, query: str, size: int = 10, page: int = 0) -> List[Dict[str, Any]]:
        raw = self._client.search_products(query=query, size=size, page=page)
        data = raw.get("products", {}).get("data", [])

        normalized: List[Dict[str, Any]] = []
        for item in data:
            price_cents = item.get("prices", {}).get("price", {}).get("amount")
            image_url = None
            primary_view = item.get("imageInfo", {}).get("primaryView") or []
            if primary_view:
                image_url = primary_view[0].get("url")

            normalized.append(
                {
                    "retailer": self.retailer,
                    "id": item.get("id"),
                    "name": item.get("title"),
                    "price_eur": (price_cents or 0) / 100.0,
                    "unit": item.get("quantity"),
                    "image_url": image_url,
                    "raw": item,  # keep raw payload for debugging
                }
            )
        return normalized

    def get_delivery_slots(self):
        # Jumbo delivery slots are not exposed in this library – you can mock for now.
        return []
