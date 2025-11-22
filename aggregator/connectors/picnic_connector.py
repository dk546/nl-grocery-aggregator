"""
Picnic connector using python-picnic-api library.

This connector interfaces with Picnic's product API through python-picnic-api to search
for products, normalize them into a unified format, and retrieve delivery slots.

The connector:
- Uses python-picnic-api to authenticate with Picnic API (requires credentials in .env)
- Searches for products and normalizes results into the aggregator's standard format
- Retrieves delivery slots information for Picnic delivery windows
- Handles Picnic-specific data structures and converts prices from cents to euros
"""

import os
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from python_picnic_api import PicnicAPI

from .base import BaseConnector


class PicnicConnector(BaseConnector):
    """
    Connector for Picnic retailer using python-picnic-api library.
    
    Integrates with Picnic's product API to search and retrieve product information,
    normalizing results into the unified format expected by the aggregator.
    
    Requires credentials in .env file:
    - PICNIC_USERNAME: Picnic account username
    - PICNIC_PASSWORD: Picnic account password
    - PICNIC_COUNTRY_CODE: Country code (default: "NL")
    """
    retailer = "picnic"

    def __init__(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        country_code: str = "NL",
    ):
        """
        Initialize the Picnic connector with API client.
        
        Args:
            username: Picnic username (optional, reads from .env if not provided)
            password: Picnic password (optional, reads from .env if not provided)
            country_code: Country code for Picnic API (default: "NL")
            
        Raises:
            RuntimeError: If Picnic credentials are missing from .env or provided parameters
        """
        load_dotenv()
        username = username or os.getenv("PICNIC_USERNAME")
        password = password or os.getenv("PICNIC_PASSWORD")
        country_code = country_code or os.getenv("PICNIC_COUNTRY_CODE", "NL")

        if not username or not password:
            raise RuntimeError(
                "Picnic credentials missing. Please add PICNIC_USERNAME and PICNIC_PASSWORD "
                "to your .env file at the project root."
            )

        self.client = PicnicAPI(
            username=username,
            password=password,
            country_code=country_code,
        )

    def search_products(self, query: str, size: int = 10, page: int = 0) -> List[Dict[str, Any]]:
        """
        Search for products on Picnic.
        
        Args:
            query: Search query string (e.g., "melk", "brood")
            size: Number of results to return per page
            page: Page number (0-indexed)
            
        Returns:
            List of normalized product dictionaries with keys:
            - retailer: "picnic"
            - id: Product identifier
            - name: Product name
            - price_eur: Price in euros (converted from cents)
            - unit: Unit quantity description
            - unit_size: Size information
            - image_url: URL to product image (constructed from image_id)
            - url: Product URL (if available)
            - raw: Raw product data from Picnic API
        """
        try:
            raw = self.client.search(query)
            if not raw or not isinstance(raw, list):
                return []

            products = []
            # Picnic search returns a list of groups; we process the first group
            group = raw[0] if len(raw) > 0 else {}
            items = group.get("items", [])

            for item in items:
                # Only process single articles (skip bundles, offers, etc.)
                if item.get("type") != "SINGLE_ARTICLE":
                    continue

                # Picnic prices are in cents, convert to euros
                price_cents = item.get("display_price", 0) or item.get("price", 0)
                price_eur = float(price_cents) / 100.0
                
                # Construct image URL from image_id
                image_id = item.get("image_id")
                image_url = None
                if image_id:
                    image_url = f"https://storefront-prod.nl.picnicinternational.com/static/images/{image_id}"

                products.append(
                    {
                        "retailer": self.retailer,
                        "id": str(item.get("id") or ""),
                        "name": item.get("name") or "",
                        "price_eur": price_eur,
                        "unit": item.get("unit_quantity") or "",
                        "unit_size": item.get("unit_size") or item.get("size") or "",
                        "image_url": image_url,
                        "url": item.get("url") or item.get("link") or "",
                        "raw": item,
                    }
                )

            # Apply pagination
            start = page * size
            end = start + size
            return products[start:end]
            
        except Exception as e:
            # Log error and return empty list to prevent breaking the aggregator
            print(f"Error searching Picnic products: {e}")
            return []

    def get_delivery_slots(self) -> Any:
        """
        Get delivery slots for Picnic.
        
        Retrieves available delivery time slots from Picnic API. The format depends
        on what python-picnic-api returns, typically a list of slot dictionaries.
        
        Returns:
            Delivery slots structure from Picnic API (typically a list of slot dictionaries)
            or empty list if no slots are available or an error occurs.
        """
        try:
            return self.client.get_delivery_slots()
        except Exception as e:
            print(f"Error retrieving Picnic delivery slots: {e}")
            return []
