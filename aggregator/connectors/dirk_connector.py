"""
Dirk connector using Apify scraper actor.

This connector interfaces with Dirk's product data through Apify's
harvestedge/dirk-supermarket-scraper to search for products and normalize them
into a unified format compatible with the aggregator system.

The connector:
- Uses ApifyClient to run the harvestedge/dirk-supermarket-scraper actor
- Searches products by query string via the actor's keyterms input
- Filters results where supermarket == "Dirk" (or appropriate field)
- Normalizes product data into a standard format with fields: retailer, id, name, price_eur, etc.
- Returns empty list for delivery slots (Dirk delivery not integrated in this MVP)

Requires APIFY_TOKEN in .env file. Actor ID defaults to harvestedge/dirk-supermarket-scraper
but can be overridden via APIFY_DIRK_ACTOR_ID environment variable.
"""

import logging
import os
from typing import Any, Dict, List, Optional

from apify_client import ApifyClient

from aggregator.models import ProductInternal
from aggregator.utils.units import parse_quantity_and_unit, canonicalize_unit, compute_price_per_unit

from .base import BaseConnector

logger = logging.getLogger(__name__)

# Note: Environment variables should be loaded by api.config module early in the application lifecycle.
# For local development, .env is loaded when api.config is imported (in api/main.py or streamlit_app/app.py).
# For tests, environment is typically patched before imports, so .env won't interfere.


class DirkConnector(BaseConnector):
    """
    Connector for Dirk retailer using Apify scraper actor.
    
    Integrates with Apify's harvestedge/dirk-supermarket-scraper to search and retrieve
    product information from Dirk, normalizing results into the unified format expected
    by the aggregator.
    
    The actor is run via ApifyClient, which requires an APIFY_TOKEN to be set
    in the environment or .env file.
    """
    retailer = "dirk"

    def __init__(
        self,
        apify_token: Optional[str] = None,
        actor_id: Optional[str] = None,
    ) -> None:
        """
        Initialize the Dirk connector with ApifyClient.
        
        Args:
            apify_token: Apify API token (optional, reads from APIFY_TOKEN env var if not provided)
            actor_id: Apify actor ID (optional, reads from APIFY_DIRK_ACTOR_ID env var or defaults to harvestedge/dirk-supermarket-scraper)
        
        Raises:
            RuntimeError: If APIFY_TOKEN is not set or client initialization fails.
        """
        # Check if token is provided as parameter first
        if apify_token:
            token = apify_token
        else:
            # Read from environment variable (loaded from .env by api.config for local dev, or from Render env for production)
            token = os.getenv("APIFY_TOKEN")
        
        if not token:
            raise RuntimeError(
                "APIFY_TOKEN is not set. Please add it to your .env file at the project root:\n"
                "APIFY_TOKEN=your_apify_token_here\n\n"
                "For local development, ensure api.config is imported early (it should be imported in api/main.py).\n"
                "For production, set APIFY_TOKEN in your deployment environment (e.g., Render dashboard)."
            )
        
        self.actor_id = actor_id or os.getenv("APIFY_DIRK_ACTOR_ID", "harvestedge/dirk-supermarket-scraper")
        
        try:
            self.client = ApifyClient(token)
        except Exception as e:
            raise RuntimeError(f"Failed to initialize ApifyClient: {e}") from e

    def search_products(self, query: str, size: int = 10, page: int = 0) -> List[Dict[str, Any]]:
        """
        Search for products on Dirk via Apify actor.
        
        This method runs the Apify actor with the search query, filters results
        to only include Dirk products, and normalizes them into the standard format.
        
        Args:
            query: Search query string (e.g., "melk", "brood")
            size: Number of results to return per page
            page: Page number (0-indexed) for pagination
            
        Returns:
            List of normalized product dictionaries with keys:
            - retailer: "dirk"
            - id: Product identifier (from item["id"] or item["url"])
            - name: Product name
            - price_eur: Price in euros (float, parsed from price_eur string)
            - unit: Unit description
            - unit_size: Size information
            - image_url: URL to product image (if available, otherwise None)
            - url: Product URL on Dirk website
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
            
            logger.debug("Running Apify actor %s with query: %s...", self.actor_id, query)
            run = self.client.actor(self.actor_id).call(run_input=run_input)
            
            # Get the dataset ID from the run result
            dataset_id = run["defaultDatasetId"]
            
            # Read items from the dataset
            items: List[Dict[str, Any]] = []
            for item in self.client.dataset(dataset_id).iterate_items():
                # Filter for Dirk products only
                # The actor may use "supermarket" field or similar
                if item.get("supermarket") == "Dirk" or item.get("retailer") == "dirk":
                    items.append(item)
            
            # Apply pagination
            start = page * size
            end = start + size
            page_items = items[start:end]
            
            logger.debug("Dirk connector: processing %d page items", len(page_items))
            
            # Normalize results to ProductInternal
            normalized: List[Dict[str, Any]] = []
            parse_errors = 0
            for item in page_items:
                # Extract and parse price - handle string format "1,99" or "1.99"
                price_str = item.get("price_eur") or item.get("price") or "0"
                try:
                    # Replace comma with dot for European number format
                    price = float(str(price_str).replace(",", "."))
                except (ValueError, AttributeError):
                    logger.warning("Dirk connector: Failed to parse price '%s', defaulting to 0.0", price_str)
                    price = 0.0
                
                # Extract identifiers
                external_id = str(item.get("id") or item.get("url") or "")
                if not external_id:
                    logger.warning("Dirk connector: Item has no id or url, skipping: %s", str(item)[:100])
                    parse_errors += 1
                    continue
                
                product_id = f"{self.retailer}:{external_id}"
                
                # Extract basic product info
                name = item.get("name") or ""
                if not name:
                    logger.warning("Dirk connector: Item has no name, skipping: id=%s", external_id)
                    parse_errors += 1
                    continue
                
                brand = item.get("brand") or None
                category = item.get("category") or None
                
                # Extract media and links
                image_url = item.get("image_url") or item.get("image") or None
                product_url = item.get("url") or None
                
                # Parse quantity and unit from unit_size
                unit_size_str = item.get("unit_size") or ""
                try:
                    quantity, quantity_unit = parse_quantity_and_unit(unit_size_str)
                except Exception as e:
                    logger.debug("Dirk connector: Unit parsing failed for '%s': %s", unit_size_str, e)
                    quantity, quantity_unit = None, None
                
                # Legacy unit field (for backward compatibility)
                unit = item.get("unit") or ""
                
                # Compute price per unit if we have quantity information
                try:
                    price_per_unit, price_per_unit_type = compute_price_per_unit(
                        price, quantity, quantity_unit
                    )
                except Exception as e:
                    logger.debug("Dirk connector: Price per unit computation failed: %s", e)
                    price_per_unit, price_per_unit_type = None, None
                
                # Extract promotion info
                is_promotion = bool(item.get("discount") or item.get("promo") or item.get("promotion"))
                promo_text = None
                if is_promotion:
                    promo_text = item.get("promo") or item.get("discount") or item.get("promotion")
                    # Convert to string if it's not already (handles dict, float, int, etc.)
                    if promo_text is not None:
                        if isinstance(promo_text, dict):
                            promo_text = str(promo_text)
                        elif not isinstance(promo_text, str):
                            # Convert numeric types (float, int) and other types to string
                            promo_text = str(promo_text)
                        # If empty string, set to None
                        if promo_text == "":
                            promo_text = None
                
                # Build ProductInternal
                product_internal = ProductInternal(
                    id=product_id,
                    retailer=self.retailer,
                    name=name,
                    brand=brand,
                    category=category,
                    image_url=image_url,
                    product_url=product_url,
                    price=price,
                    currency="EUR",
                    price_per_unit=price_per_unit,
                    unit=canonicalize_unit(price_per_unit_type) if price_per_unit_type else None,
                    quantity=quantity,
                    quantity_unit=quantity_unit,
                    is_promotion=is_promotion,
                    promo_text=promo_text,
                    source_raw=item,
                    # Legacy fields for backward compatibility
                    price_eur=price,
                    unit_size=unit_size_str,
                )
                # Convert to dict for backward compatibility with tests
                # aggregated_search will convert back to ProductInternal
                product_dict = product_internal.model_dump()
                # Ensure legacy fields are present (use original values, not normalized)
                product_dict["price_eur"] = price
                product_dict["unit"] = unit  # Keep original unit, not canonicalized
                product_dict["unit_size"] = unit_size_str
                product_dict["url"] = product_url or ""  # Map product_url to url, convert None to ""
                product_dict["image_url"] = image_url or None  # Keep None for image_url
                # For backward compatibility, use original external_id instead of normalized "{retailer}:{id}"
                product_dict["id"] = external_id
                # Map source_raw to raw for backward compatibility
                if "source_raw" in product_dict:
                    product_dict["raw"] = product_dict.pop("source_raw")
                normalized.append(product_dict)
            
            return normalized
            
        except KeyError as e:
            raise RuntimeError(
                f"Unexpected response format from Apify actor {self.actor_id}: missing key {e}. "
                "The actor may have changed its output format."
            ) from e
        except Exception as e:
            raise RuntimeError(
                f"Error searching Dirk products via Apify actor {self.actor_id}: {e}. "
                "Check your APIFY_TOKEN and ensure the actor is accessible."
            ) from e

    def get_delivery_slots(self) -> Any:
        """
        Get delivery slots for Dirk.
        
        Currently not implemented as Dirk delivery integration is not part of this MVP.
        
        Returns:
            Empty list (placeholder for future implementation)
        """
        return []

