"""
Backend API Client Module.

This module is the **single source of truth** for all backend API communication.
All HTTP calls to the FastAPI backend should go through functions in this module.

Key principles:
- Centralized error handling for network issues
- Consistent timeout and retry logic
- Graceful degradation when backend is unavailable
- Type hints for better IDE support and documentation

# NOTE: When adding new endpoints, follow this pattern:
    - Create a function that takes parameters needed for the endpoint
    - Use requests.get/post/put/delete with proper error handling
    - Return parsed JSON (dict) or None on error
    - Log errors via st.error or st.warning for user visibility
    - Never let exceptions bubble up to crash the Streamlit app

# TODO: When backend adds more endpoints (e.g., /health, /recipes), add them here:
    - get_health_status() - should call GET /health when available
    - get_recipes() - for future recipe recommendations
    - get_delivery_slots() - wrapper for /delivery/slots endpoint
    - add_to_cart_backend() - POST /cart/add with session management
    - remove_from_cart_backend() - POST /cart/remove with session management
    - view_cart_backend() - GET /cart/view with session management
"""

import os
from typing import Any, Dict, List, Optional

import requests
import streamlit as st


def get_backend_url() -> str:
    """
    Get the backend API base URL from environment variable or use default.
    
    Returns:
        Backend URL string with trailing slash removed. Defaults to http://localhost:8000 for local development.
        On Render, BACKEND_URL should be explicitly set in the environment.
        
    For local development:
        - If BACKEND_URL is set in .env, use that value
        - Otherwise, default to http://localhost:8000
        
    For Render/production:
        - Set BACKEND_URL environment variable in Render dashboard to the backend service URL
        - Example: https://nl-grocery-aggregator.onrender.com
        - Trailing slashes are automatically removed
    """
    url = os.getenv("BACKEND_URL", "http://localhost:8000")
    return url.rstrip("/")


@st.cache_data(ttl=60)  # Cache for 60 seconds to avoid hitting backend too frequently
def get_health_status() -> Optional[Dict[str, Any]]:
    """
    Check backend health status by calling /health endpoint.
    
    Returns:
        Dictionary with normalized status info:
        {
            "status": "ok",
            "raw": {...},  # Full response from /health endpoint
            "docs_url": "/docs"  # URL to API documentation
        }
        Or None if backend is unreachable.
        
    The function gracefully handles connection errors, timeouts, and non-200 responses.
    The UI components can check for status == "ok" to determine if backend is online.
    """
    try:
        backend_url = get_backend_url()
        response = requests.get(f"{backend_url}/health", timeout=5)
        response.raise_for_status()
        data = response.json()
        
        # Validate that we got a proper health response
        if data.get("status") == "ok":
            return {
                "status": "ok",
                "raw": data,
                "docs_url": "/docs"  # Default docs URL
            }
        else:
            # Health endpoint returned but status is not "ok"
            return None
    except requests.exceptions.Timeout:
        # Backend is too slow - treat as offline
        return None
    except requests.exceptions.ConnectionError:
        # Cannot connect to backend (DNS, network, etc.)
        return None
    except requests.exceptions.HTTPError:
        # Non-200 response - backend may be unhealthy
        return None
    except requests.exceptions.RequestException:
        # Any other request error
        return None


def search_products(
    query: str,
    retailers: Optional[List[str]] = None,
    sort_by: Optional[str] = None,
    health_filter: Optional[str] = None,
    size: Optional[int] = None,
    page: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    """
    Search for products across retailers using the backend API.
    
    Args:
        query: Search query string (e.g., "melk", "brood")
        retailers: List of retailer identifiers (e.g., ["ah", "jumbo", "picnic", "dirk"]). 
                   Defaults to all retailers if None.
        sort_by: Sort criterion - "price", "retailer", or "health" (optional)
        health_filter: Filter by health tag - "healthy" or "unhealthy" (optional)
        size: Number of results per retailer (optional, default: 10)
        page: Page number for pagination (optional, default: 0)
        
    Returns:
        Dictionary with "results" key containing list of products, or None on error.
        Each product dict contains: id, retailer, name, price_eur, unit, unit_size,
        image_url, url, health_tag, is_cheapest, etc.
    """
    backend_url = get_backend_url()
    
    # Build query parameters - only include non-None values
    params: Dict[str, Any] = {"q": query}
    
    if retailers:
        # Convert list to comma-separated string as expected by backend
        params["retailers"] = ",".join(retailers)
    if sort_by:
        params["sort_by"] = sort_by
    if health_filter:  # Only send if not None/empty
        params["health_filter"] = health_filter
    if size is not None:
        params["size"] = size
    if page is not None:
        # Backend expects 0-indexed page numbers
        params["page"] = page
    
    try:
        response = requests.get(
            f"{backend_url}/search",
            params=params,
            timeout=45
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        st.error("Request timed out. The backend may be slow or unreachable.")
        return None
    except requests.exceptions.ConnectionError:
        st.error("Could not connect to backend. Please check your connection and that the backend is running.")
        return None
    except requests.exceptions.HTTPError as e:
        st.error(f"Backend returned an error: {e.response.status_code} - {e.response.text}")
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"An error occurred while searching: {str(e)}")
        return None


@st.cache_data(ttl=30)  # Cache for 30 seconds to avoid over-calling
def get_cart_summary(session_id: str) -> Optional[Dict[str, Any]]:
    """
    Lightweight summary of the cart for the given session_id.
    
    Returns:
        Dictionary with:
        - total_items: Total number of items in cart
        - total_cost_eur: Total cost of cart in euros
        Or None if cart is empty or error occurred.
    """
    try:
        backend_url = get_backend_url()
        response = requests.get(
            f"{backend_url}/cart/view",
            headers={"X-Session-ID": session_id},
            timeout=5
        )
        response.raise_for_status()
        data = response.json()
        
        items = data.get("items", [])
        total_items = len(items)
        total_cost = data.get("total_price", 0.0)
        
        if total_items == 0:
            return None
        
        return {
            "total_items": total_items,
            "total_cost_eur": total_cost,
        }
    except requests.exceptions.RequestException:
        # Fail silently - basket summary is a nice-to-have
        return None


def get_price_history(retailer: str, product_id: str) -> Optional[Dict[str, Any]]:
    """
    Get price history for a product (demo feature).
    
    Args:
        retailer: Retailer identifier (ah, jumbo, picnic, dirk)
        product_id: Product identifier (may include retailer prefix)
        
    Returns:
        Dictionary with status, retailer, product_id, and points list, or None on error.
    """
    try:
        backend_url = get_backend_url()
        response = requests.get(
            f"{backend_url}/price-history/{retailer}/{product_id}",
            timeout=5
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException:
        # Fail silently - price history is a demo feature
        return None


def get_delivery_slots(retailer: str = "picnic") -> Optional[List[Dict[str, Any]]]:
    """
    Get available delivery slots for a retailer.
    
    Args:
        retailer: Retailer identifier (default: "picnic")
        
    Returns:
        List of delivery slot dictionaries, or None on error.
        
    # TODO: Add UI integration for delivery slot selection in basket/checkout flow.
    """
    backend_url = get_backend_url()
    
    try:
        response = requests.get(
            f"{backend_url}/delivery/slots",
            params={"retailer": retailer},
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.warning(f"Could not fetch delivery slots for {retailer}: {str(e)}")
        return None


def add_to_cart_backend(
    session_id: str,
    retailer: str,
    product_id: str,
    name: str,
    price_eur: float,
    quantity: int = 1,
    image_url: Optional[str] = None,
    health_tag: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Add an item to the shopping cart via backend API.
    
    Args:
        session_id: Session identifier for cart isolation
        retailer: Retailer identifier (ah, jumbo, picnic, dirk)
        product_id: Product identifier from retailer
        name: Product name
        price_eur: Price per unit in euros
        quantity: Quantity to add (default: 1)
        image_url: Optional product image URL
        health_tag: Optional health tag
        
    Returns:
        CartView dictionary with items and total, or None on error.
    """
    backend_url = get_backend_url()
    
    payload = {
        "retailer": retailer,
        "product_id": product_id,
        "name": name,
        "price_eur": price_eur,
        "quantity": quantity,
    }
    
    if image_url:
        payload["image_url"] = image_url
    if health_tag:
        payload["health_tag"] = health_tag
    
    try:
        response = requests.post(
            f"{backend_url}/cart/add",
            json=payload,
            headers={"X-Session-ID": session_id},
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to add item to cart: {str(e)}")
        return None


def remove_from_cart_backend(
    session_id: str,
    retailer: str,
    product_id: str,
    qty: int = 1,
) -> Optional[Dict[str, Any]]:
    """
    Remove an item from the shopping cart via backend API.
    
    Args:
        session_id: Session identifier
        retailer: Retailer identifier
        product_id: Product identifier
        qty: Quantity to remove (default: 1)
        
    Returns:
        Updated CartView dictionary, or None on error.
    """
    backend_url = get_backend_url()
    
    try:
        response = requests.post(
            f"{backend_url}/cart/remove",
            params={"retailer": retailer, "product_id": product_id, "qty": qty},
            headers={"X-Session-ID": session_id},
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to remove item from cart: {str(e)}")
        return None


def update_cart_item_quantity(
    session_id: str,
    retailer: str,
    product_id: str,
    original_quantity: int,
    new_quantity: int,
    item_data: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """
    Update the quantity of a cart item by calculating the difference and using add/remove endpoints.
    
    This function implements quantity updates by:
    - If new_qty > original_qty: adds the difference via /cart/add
    - If new_qty < original_qty: removes the difference via /cart/remove
    - If new_qty == 0: removes the entire item via /cart/remove
    
    Args:
        session_id: Session identifier
        retailer: Retailer identifier
        product_id: Product identifier
        original_quantity: Current quantity in cart
        new_quantity: Desired new quantity (0 to remove item)
        item_data: Dict containing item fields needed for add (name, price_eur, image_url, health_tag)
        
    Returns:
        Updated CartView dictionary, or None on error.
    """
    if new_quantity == 0:
        # Remove entire item
        return remove_from_cart_backend(session_id, retailer, product_id, qty=original_quantity)
    elif new_quantity > original_quantity:
        # Add more items
        qty_to_add = new_quantity - original_quantity
        return add_to_cart_backend(
            session_id=session_id,
            retailer=retailer,
            product_id=product_id,
            name=item_data.get("name", ""),
            price_eur=item_data.get("price_eur", item_data.get("price", 0.0)),
            quantity=qty_to_add,
            image_url=item_data.get("image_url"),
            health_tag=item_data.get("health_tag"),
        )
    elif new_quantity < original_quantity:
        # Remove some items
        qty_to_remove = original_quantity - new_quantity
        return remove_from_cart_backend(session_id, retailer, product_id, qty=qty_to_remove)
    else:
        # No change
        return None


def view_cart_backend(session_id: str) -> Optional[Dict[str, Any]]:
    """
    View the current shopping cart via backend API.
    
    Args:
        session_id: Session identifier
        
    Returns:
        CartView dictionary with items and total, or None on error.
    """
    backend_url = get_backend_url()
    
    try:
        response = requests.get(
            f"{backend_url}/cart/view",
            headers={"X-Session-ID": session_id},
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.warning(f"Could not fetch cart: {str(e)}")
        return None


def get_basket_savings(session_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch potential savings and suggestions for the current basket.
    
    Args:
        session_id: Session identifier
        
    Returns:
        BasketSavingsResponse dictionary with potential_savings_total and suggestions,
        or None on error.
    """
    backend_url = get_backend_url()
    
    try:
        response = requests.get(
            f"{backend_url}/basket/savings",
            headers={"X-Session-ID": session_id},
            timeout=15  # Longer timeout as this may involve multiple searches
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.warning(f"Could not fetch basket savings: {str(e)}")
        return None


def _session_headers(session_id: str) -> Dict[str, str]:
    """Helper to create session headers."""
    return {"X-Session-ID": session_id}


def list_basket_templates(session_id: str) -> Optional[Dict[str, Any]]:
    """
    List all saved basket templates for a session.
    
    Args:
        session_id: Session identifier
        
    Returns:
        BasketTemplateListResponse dictionary, or None on error.
    """
    backend_url = get_backend_url()
    
    try:
        response = requests.get(
            f"{backend_url}/api/basket/templates",
            headers=_session_headers(session_id),
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.warning(f"Could not fetch basket templates: {str(e)}")
        return None


def save_basket_template(session_id: str, name: str) -> Optional[Dict[str, Any]]:
    """
    Save the current basket as a named template.
    
    Args:
        session_id: Session identifier
        name: Template name
        
    Returns:
        SaveBasketTemplateResponse dictionary, or None on error.
    """
    backend_url = get_backend_url()
    
    try:
        response = requests.post(
            f"{backend_url}/api/basket/templates",
            headers=_session_headers(session_id),
            json={"name": name},
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.warning(f"Could not save basket template: {str(e)}")
        return None


def apply_basket_template(session_id: str, template_id: str) -> Optional[Dict[str, Any]]:
    """
    Apply a saved template to replace the current basket.
    
    Args:
        session_id: Session identifier
        template_id: Template identifier
        
    Returns:
        BasketTemplate dictionary, or None on error.
    """
    backend_url = get_backend_url()
    
    try:
        response = requests.post(
            f"{backend_url}/api/basket/templates/{template_id}/apply",
            headers=_session_headers(session_id),
            timeout=15  # Longer timeout as this may involve multiple cart operations
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.warning(f"Could not apply basket template: {str(e)}")
        return None


def delete_basket_template(session_id: str, template_id: str) -> bool:
    """
    Delete a saved basket template.
    
    Args:
        session_id: Session identifier
        template_id: Template identifier
        
    Returns:
        True if successful, False otherwise.
    """
    backend_url = get_backend_url()
    
    try:
        response = requests.delete(
            f"{backend_url}/api/basket/templates/{template_id}",
            headers=_session_headers(session_id),
            timeout=10
        )
        return response.status_code in (200, 204)
    except requests.exceptions.RequestException:
        return False


def get_recent_events(limit: int = 100) -> Dict[str, Any]:
    """
    Get recent analytics events from the backend.
    
    Args:
        limit: Maximum number of events to return (default: 100)
        
    Returns:
        Dictionary with:
        - db_enabled: Boolean indicating if database is enabled
        - events: List of event dictionaries
        Or safe fallback structure if backend is unreachable.
    """
    try:
        backend_url = get_backend_url()
        response = requests.get(
            f"{backend_url}/analytics/events/recent",
            params={"limit": limit},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        
        # Ensure basic structure
        if not isinstance(data, dict):
            raise ValueError("Unexpected events payload shape")
        
        if "db_enabled" not in data:
            data["db_enabled"] = False
        if "events" not in data or not isinstance(data["events"], list):
            data["events"] = []
        
        return data
    except Exception:
        # Return safe fallback structure
        return {
            "db_enabled": False,
            "events": [],
        }


def get_event_counts(since_hours: int = 24) -> Dict[str, Any]:
    """
    Get event type counts over the last N hours.
    
    Args:
        since_hours: Number of hours to look back (default: 24)
        
    Returns:
        Dictionary with:
        - db_enabled: Boolean indicating if database is enabled
        - since_hours: Number of hours queried
        - counts: Dictionary mapping event_type to count
        Or safe fallback structure if backend is unreachable.
    """
    try:
        backend_url = get_backend_url()
        response = requests.get(
            f"{backend_url}/analytics/events/counts",
            params={"since_hours": since_hours},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        
        # Ensure basic structure
        if not isinstance(data, dict):
            raise ValueError("Unexpected counts payload shape")
        
        if "db_enabled" not in data:
            data["db_enabled"] = False
        if "counts" not in data:
            data["counts"] = {}
        
        return data
    except Exception:
        # Return safe fallback structure
        return {
            "db_enabled": False,
            "since_hours": since_hours,
            "counts": {},
        }

