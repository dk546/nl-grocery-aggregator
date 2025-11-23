"""
Albert Heijn (AH) connector using Apify scraper actor.

This connector interfaces with Albert Heijn's product data through Apify's
harvestedge/my-actor scraper to search for products and normalize them into
a unified format compatible with the aggregator system.

The connector:
- Uses ApifyClient to run the harvestedge/my-actor actor
- Searches products by query string via the actor's keyterms input
- Filters results where supermarket == "AH"
- Normalizes product data into a standard format with fields: retailer, id, name, price_eur, etc.
- Returns empty list for delivery slots (AH delivery not integrated in this MVP)

Requires APIFY_TOKEN in .env file. Actor ID defaults to harvestedge/my-actor
but can be overridden via APIFY_AH_ACTOR_ID environment variable.
"""

import os
from typing import Any, Dict, List, Optional

from apify_client import ApifyClient
from dotenv import load_dotenv

from .base import BaseConnector


class AHConnector(BaseConnector):
    """
    Connector for Albert Heijn retailer using Apify scraper actor.
    
    Integrates with Apify's harvestedge/my-actor to search and retrieve product
    information from Albert Heijn, normalizing results into the unified format
    expected by the aggregator.
    
    The actor is run via ApifyClient, which requires an APIFY_TOKEN to be set
    in the environment or .env file.
    """
    retailer = "ah"

    def __init__(
        self,
        apify_token: Optional[str] = None,
        actor_id: Optional[str] = None,
    ) -> None:
        """
        Initialize the AH connector with ApifyClient.
        
        Args:
            apify_token: Apify API token (optional, reads from APIFY_TOKEN env var if not provided)
            actor_id: Apify actor ID (optional, reads from APIFY_AH_ACTOR_ID env var or defaults to harvestedge/my-actor)
        
        Raises:
            RuntimeError: If APIFY_TOKEN is not set or client initialization fails.
        """
        # Check if token is provided as parameter first
        if not apify_token:
            # Check environment variable (including any values from .env already loaded)
            token = os.getenv("APIFY_TOKEN")
            # Only try loading .env if token is not in environment and not explicitly cleared
            if not token:
                # Try loading from .env file (this won't override existing env vars)
                load_dotenv(override=False)
                token = os.getenv("APIFY_TOKEN")
        
        if not token:
            raise RuntimeError(
                "APIFY_TOKEN is not set. Please add it to your .env file at the project root:\n"
                "APIFY_TOKEN=your_apify_token_here"
            )
        
        self.actor_id = actor_id or os.getenv("APIFY_AH_ACTOR_ID", "harvestedge/my-actor")
        
        try:
            self.client = ApifyClient(token)
        except Exception as e:
            raise RuntimeError(f"Failed to initialize ApifyClient: {e}") from e

    def search_products(self, query: str, size: int = 10, page: int = 0) -> List[Dict[str, Any]]:
        """
        Search for products on Albert Heijn via Apify actor.
        
        This method runs the Apify actor with the search query, filters results
        to only include AH products, and normalizes them into the standard format.
        
        Args:
            query: Search query string (e.g., "melk", "brood")
            size: Number of results to return per page
            page: Page number (0-indexed) for pagination
            
        Returns:
            List of normalized product dictionaries with keys:
            - retailer: "ah"
            - id: Product identifier (from item["id"] or item["url"])
            - name: Product name
            - price_eur: Price in euros (float, parsed from price_eur string)
            - unit: Unit description
            - unit_size: Size information
            - image_url: URL to product image (if available, otherwise None)
            - url: Product URL on AH website
            - raw: Raw product data from Apify actor
            
        Raises:
            RuntimeError: If the Apify actor run fails or times out.
        """
        if size <= 0:
            return []

        try:
            # Calculate max_results needed for pagination
            # We fetch enough results to cover the requested page
            max_results = min(size * (page + 1), 200)  # Cap at 200 to avoid huge requests
            
            # Run the Apify actor with search query
            run_input = {
                "keyterms": [query],
                "maxResults": max_results,
            }
            
            print(f"Running Apify actor {self.actor_id} with query: {query}...")
            run = self.client.actor(self.actor_id).call(run_input=run_input)
            
            # Get the dataset ID from the run result
            dataset_id = run["defaultDatasetId"]
            
            # Read items from the dataset
            items: List[Dict[str, Any]] = []
            for item in self.client.dataset(dataset_id).iterate_items():
                # Filter for AH products only
                if item.get("supermarket") == "AH":
                    items.append(item)
            
            # Apply pagination
            start = page * size
            end = start + size
            page_items = items[start:end]
            
            # Normalize results to standard format
            normalized: List[Dict[str, Any]] = []
            for item in page_items:
                # Extract price - handle string format "1,99" or "1.99"
                price_str = item.get("price_eur") or item.get("price") or "0"
                try:
                    # Replace comma with dot for European number format
                    price_eur = float(str(price_str).replace(",", "."))
                except (ValueError, AttributeError):
                    price_eur = 0.0
                
                # Extract image URL if available
                image_url = item.get("image_url") or item.get("image") or None
                
                normalized.append(
                    {
                        "retailer": self.retailer,
                        "id": str(item.get("id") or item.get("url") or ""),
                        "name": item.get("name") or "",
                        "price_eur": price_eur,
                        "unit": item.get("unit") or "",
                        "unit_size": item.get("unit_size") or "",
                        "image_url": image_url,
                        "url": item.get("url") or "",
                        "raw": item,
                    }
                )
            
            return normalized
            
        except KeyError as e:
            raise RuntimeError(
                f"Unexpected response format from Apify actor {self.actor_id}: missing key {e}. "
                "The actor may have changed its output format."
            ) from e
        except Exception as e:
            raise RuntimeError(
                f"Error searching AH products via Apify actor {self.actor_id}: {e}. "
                "Check your APIFY_TOKEN and ensure the actor is accessible."
            ) from e

    def get_delivery_slots(self) -> Any:
        """
        Get delivery slots for Albert Heijn.
        
        Currently not implemented as AH delivery integration is not part of this MVP.
        
        Returns:
            Empty list (placeholder for future implementation)
        """
        return []

