"""
Picnic connector using python-picnic-api library.

This connector interfaces with Picnic's product API through python-picnic-api to search
for products, normalize them into a unified format, and retrieve delivery slots.

The connector:
- Uses python-picnic-api to authenticate with Picnic API (requires credentials in .env)
- Searches for products and normalizes results into the aggregator's standard format
- Retrieves delivery slots information for Picnic delivery windows
- Handles Picnic-specific data structures and converts prices from cents to euros
- Provides robust error handling for authentication and API errors
"""

import logging
import os
from typing import Any, Dict, List, Optional

from python_picnic_api import PicnicAPI

from aggregator.models import ProductInternal
from aggregator.utils.units import parse_quantity_and_unit, canonicalize_unit, compute_price_per_unit

from .base import BaseConnector

logger = logging.getLogger(__name__)


class PicnicAuthError(Exception):
    """
    Exception raised when Picnic authentication fails.
    
    This exception is raised when:
    - Invalid credentials are provided
    - Authentication request returns 401/403
    - API indicates authentication failure
    """
    pass

# Note: Environment variables should be loaded by api.config module early in the application lifecycle.
# For local development, .env is loaded when api.config is imported (in api/main.py or streamlit_app/app.py).
# For tests, environment is typically patched before imports, so .env won't interfere.


def _validate_picnic_env() -> tuple[str, str, str]:
    """
    Validate that required Picnic environment variables are set.
    
    Returns:
        Tuple of (username, password, country_code)
        
    Raises:
        RuntimeError: If PICNIC_USERNAME or PICNIC_PASSWORD are missing
    """
    username = os.getenv("PICNIC_USERNAME")
    password = os.getenv("PICNIC_PASSWORD")
    country_code = os.getenv("PICNIC_COUNTRY_CODE", "NL")
    
    if not username or not password:
        raise RuntimeError(
            "Picnic credentials not configured. Set PICNIC_USERNAME and PICNIC_PASSWORD "
            "in .env or environment variables.\n"
            "For local development, add to .env file at project root:\n"
            "PICNIC_USERNAME=your_email@example.com\n"
            "PICNIC_PASSWORD=your_password_here\n"
            "PICNIC_COUNTRY_CODE=NL\n\n"
            "For production, set these in your deployment environment (e.g., Render dashboard)."
        )
    
    return username, password, country_code


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
        country_code: Optional[str] = None,
    ):
        """
        Initialize the Picnic connector with API client.
        
        Credential resolution precedence:
        - If both `username` and `password` are provided explicitly, use those.
        - Otherwise, read credentials from environment variables via `_validate_picnic_env()`.
        
        Country code resolution (in order):
        1. Explicit `country_code` argument (if provided and truthy)
        2. `PICNIC_COUNTRY_CODE` environment variable
        3. Default: "NL"
        
        Args:
            username: Picnic username (optional, reads from PICNIC_USERNAME env if not provided)
            password: Picnic password (optional, reads from PICNIC_PASSWORD env if not provided)
            country_code: Country code for Picnic API (optional, defaults to PICNIC_COUNTRY_CODE env or "NL")
            
        Raises:
            RuntimeError: If Picnic credentials are missing (when both username and password are not explicitly provided)
            PicnicAuthError: If authentication fails during client initialization
        """
        # If both username and password are explicitly provided, use them
        if username and password:
            # Explicit credentials provided - validate they're not empty strings
            if not username.strip() or not password.strip():
                raise RuntimeError(
                    "Picnic username and password cannot be empty. "
                    "Provide valid credentials or omit both to use environment variables."
                )
            # Resolve country_code: explicit arg > env > default "NL"
            country_code = country_code or os.getenv("PICNIC_COUNTRY_CODE", "NL")
        else:
            # Not both provided - use _validate_picnic_env() as single source of truth
            username, password, env_country_code = _validate_picnic_env()
            # Country code: explicit arg > env (from _validate_picnic_env) > default "NL"
            country_code = country_code or env_country_code or "NL"

        # Initialize Picnic API client
        # Note: python-picnic-api may authenticate lazily on the first API call (e.g., search),
        # so authentication errors may first appear during search_products() rather than here.
        try:
            self.client = PicnicAPI(
                username=username,
                password=password,
                country_code=country_code,
            )
            logger.debug("Picnic connector initialized successfully (country_code=%r)", country_code)
        except Exception as e:
            error_msg = str(e).lower()
            # Check if this looks like an authentication error
            if any(keyword in error_msg for keyword in ["auth", "login", "credential", "unauthorized", "401", "403"]):
                # Use original message if it already clearly indicates authentication error, otherwise add context
                original_msg = str(e).strip()
                if any(phrase in error_msg for phrase in ["picnic authentication", "authentication failed", "auth error"]):
                    clean_msg = original_msg
                else:
                    clean_msg = f"Picnic authentication failed: {original_msg}"
                logger.error("Picnic authentication failed during initialization: %s", clean_msg, exc_info=True)
                raise PicnicAuthError(clean_msg) from e
            else:
                logger.error("Unexpected error initializing Picnic client: %s", e, exc_info=True)
                raise RuntimeError(f"Failed to initialize Picnic client: {e}") from e

    def search_products(self, query: str, size: int = 10, page: int = 0) -> List[Dict[str, Any]]:
        """
        Search for products on Picnic.
        
        Args:
            query: Search query string (e.g., "melk", "brood")
            size: Number of results to return per page
            page: Page number (0-indexed)
            
        Returns:
            List of normalized product dictionaries, each containing at minimum:
            - retailer: "picnic"
            - id: Product identifier (original external ID for backward compatibility)
            - name: Product name
            - price_eur: Price in euros (converted from cents)
            - price: Price in euros (normalized field)
            - unit: Unit quantity description (legacy field)
            - unit_size: Size information (legacy field)
            - quantity: Numeric quantity (if parseable)
            - quantity_unit: Canonical unit (kg, g, L, mL, piece, etc.)
            - price_per_unit: Price per canonical unit (if computable)
            - image_url: URL to product image (constructed from image_id)
            - url: Product URL (if available)
            - raw: Raw product data from Picnic API
            
            Additional fields may include: brand, category, is_promotion, promo_text, etc.
            
        Note:
            Raises PicnicAuthError on authentication failures (caller should handle gracefully).
            Raises RuntimeError on configuration errors (missing credentials).
            Returns empty list on non-auth network/API errors.
        """
        try:
            logger.info("Picnic connector: searching for query=%r size=%d page=%d", query, size, page)
            raw = self.client.search(query)
            
            if not raw or not isinstance(raw, list):
                logger.debug("Picnic connector: empty or invalid search result")
                return []

            products: List[ProductInternal] = []
            # Picnic search returns a list of groups; we process the first group
            group = raw[0] if len(raw) > 0 else {}
            items = group.get("items", [])
            
            logger.debug("Picnic connector: found %d items in search result", len(items))

            for item in items:
                # Only process single articles (skip bundles, offers, etc.)
                if item.get("type") != "SINGLE_ARTICLE":
                    continue

                # Picnic prices are in cents, convert to euros
                price_cents = item.get("display_price", 0) or item.get("price", 0)
                price = float(price_cents) / 100.0
                
                # Extract identifiers
                external_id = str(item.get("id") or "")
                product_id = f"{self.retailer}:{external_id}"
                
                # Extract basic product info
                name = item.get("name") or ""
                brand = item.get("brand") or None
                category = item.get("category") or None
                
                # Construct image URL from image_id
                image_id = item.get("image_id")
                image_url = None
                if image_id:
                    image_url = f"https://storefront-prod.nl.picnicinternational.com/static/images/{image_id}"
                
                product_url = item.get("url") or item.get("link") or None
                
                # Parse quantity and unit
                # Picnic provides unit_quantity and unit_size separately
                unit_size_str = item.get("unit_size") or item.get("size") or ""
                unit_quantity_str = item.get("unit_quantity") or ""
                
                # Combine unit_quantity and unit_size if both exist
                if unit_quantity_str and unit_size_str:
                    combined_size = f"{unit_quantity_str} {unit_size_str}"
                elif unit_size_str:
                    combined_size = unit_size_str
                elif unit_quantity_str:
                    combined_size = unit_quantity_str
                else:
                    combined_size = ""
                
                quantity, quantity_unit = parse_quantity_and_unit(combined_size)
                
                # Legacy unit field (for backward compatibility)
                unit = unit_quantity_str or ""
                
                # Compute price per unit if we have quantity information
                price_per_unit, price_per_unit_type = compute_price_per_unit(
                    price, quantity, quantity_unit
                )
                
                # Extract promotion info
                is_promotion = bool(item.get("discount") or item.get("promotion"))
                promo_text = None
                if is_promotion:
                    promo_text = item.get("discount") or item.get("promotion")
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
                    unit_size=combined_size,
                )
                # Convert to dict for backward compatibility with tests
                product_dict = product_internal.model_dump()
                product_dict["price_eur"] = price
                product_dict["unit_size"] = combined_size
                product_dict["url"] = product_url
                # For backward compatibility, use original external_id instead of normalized "{retailer}:{id}"
                product_dict["id"] = external_id
                # Map source_raw to raw for backward compatibility
                if "source_raw" in product_dict:
                    product_dict["raw"] = product_dict.pop("source_raw")
                products.append(product_dict)

            # Apply pagination
            start = page * size
            end = start + size
            paginated_products = products[start:end]
            
            logger.info("Picnic connector: query=%r returned %d products (after pagination)", 
                       query, len(paginated_products))
            return paginated_products

        except PicnicAuthError as e:
            # Re-raise auth errors so aggregator can handle them specifically
            logger.warning("Picnic authentication failed; skipping Picnic results for this request: %s", e)
            raise
        except RuntimeError as e:
            # Re-raise config errors
            logger.warning("Picnic disabled: %s", e)
            raise
        except Exception as e:
            # Log other errors (network, API errors, etc.) and return empty list
            error_msg = str(e).lower()
            # Check if this might be an auth error that wasn't caught earlier
            if any(keyword in error_msg for keyword in ["auth", "login", "credential", "unauthorized", "401", "403"]):
                # Use original message if it already clearly indicates authentication error, otherwise add context
                original_msg = str(e).strip()
                if any(phrase in error_msg for phrase in ["picnic authentication", "authentication failed", "auth error"]):
                    clean_msg = original_msg
                else:
                    clean_msg = f"Picnic authentication failed: {original_msg}"
                logger.warning("Picnic authentication error (detected from exception): %s", clean_msg)
                raise PicnicAuthError(clean_msg) from e
            else:
                logger.error("Unexpected error searching Picnic products: %s", e, exc_info=True)
                return []

    def get_delivery_slots(self) -> Any:
        """
        Get delivery slots for Picnic.
        
        Retrieves available delivery time slots from Picnic API. The format depends
        on what python-picnic-api returns, typically a list of slot dictionaries.
        
        Returns:
            Delivery slots structure from Picnic API (typically a list of slot dictionaries)
            or empty list if no slots are available or an unexpected error occurs.
            
        Raises:
            PicnicAuthError: If authentication fails when fetching delivery slots
            RuntimeError: If credentials are not configured
        """
        try:
            return self.client.get_delivery_slots()
        except PicnicAuthError:
            # Re-raise auth errors so caller can handle them specially
            logger.warning("Picnic authentication failed when fetching delivery slots")
            raise
        except RuntimeError as e:
            # Re-raise config errors
            logger.warning("Picnic disabled when fetching delivery slots: %s", e)
            raise
        except Exception as e:
            # Check if this might be an auth error
            error_msg = str(e).lower()
            if any(keyword in error_msg for keyword in ["auth", "login", "credential", "unauthorized", "401", "403"]):
                # Use original message if it already clearly indicates authentication error, otherwise add context
                original_msg = str(e).strip()
                if any(phrase in error_msg for phrase in ["picnic authentication", "authentication failed", "auth error"]):
                    clean_msg = original_msg
                else:
                    clean_msg = f"Picnic authentication failed: {original_msg}"
                logger.warning("Picnic authentication error (detected from exception) when fetching delivery slots: %s", clean_msg)
                raise PicnicAuthError(clean_msg) from e
            else:
                logger.error("Unexpected error retrieving Picnic delivery slots: %s", e, exc_info=True)
                return []
