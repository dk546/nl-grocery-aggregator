import os
from typing import List, Dict, Any, Optional

from dotenv import load_dotenv
from python_picnic_api import PicnicAPI

from .base import BaseConnector

load_dotenv()


class PicnicRetailConnector(BaseConnector):
    retailer = "picnic"

    def __init__(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        country_code: str = "NL",
    ) -> None:
        username = username or os.getenv("PICNIC_USERNAME")
        password = password or os.getenv("PICNIC_PASSWORD")

        if not username or not password:
            raise ValueError("PICNIC_USERNAME and PICNIC_PASSWORD must be set")

        self._client = PicnicAPI(
            username=username,
            password=password,
            country_code=country_code,
        )

    def search_products(self, query: str, size: int = 10, page: int = 0) -> List[Dict[str, Any]]:
        raw_results = self._client.search(query)
        if not raw_results:
            return []

        items = []
        # picnic.search returns a list of categories/results; we dig into 'items'
        for group in raw_results:
            for item in group.get("items", []):
                if item.get("type") != "SINGLE_ARTICLE":
                    continue

                price_cents = item.get("price")
                image_id = item.get("image_id")
                image_url = (
                    f"https://storefront-prod.nl.picnicinternational.com/static/images/{image_id}"
                    if image_id
                    else None
                )

                items.append(
                    {
                        "retailer": self.retailer,
                        "id": item.get("id"),
                        "name": item.get("name"),
                        "price_eur": (price_cents or 0) / 100.0,
                        "unit": item.get("unit_quantity"),
                        "image_url": image_url,
                        "raw": item,
                    }
                )

        # Basic pagination: just slice for now
        start = page * size
        end = start + size
        return items[start:end]

    def get_delivery_slots(self):
        return self._client.get_delivery_slots()
