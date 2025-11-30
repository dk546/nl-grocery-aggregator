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
        Backend URL string. Defaults to http://localhost:8000 for local development.
        On Render, BACKEND_URL should be explicitly set in the environment.
        
    For local development:
        - If BACKEND_URL is set in .env, use that value
        - Otherwise, default to http://localhost:8000
        
    For Render/production:
        - Set BACKEND_URL environment variable in Render dashboard to the backend service URL
        - Example: https://nl-grocery-aggregator.onrender.com
    """
    return os.getenv("BACKEND_URL", "http://localhost:8000")


@st.cache_data(ttl=60)  # Cache for 60 seconds to avoid hitting backend too frequently
def get_health_status() -> Optional[Dict[str, Any]]:
    """
    Check backend health status by calling root endpoint.
    
    Returns:
        Dictionary with normalized status info:
        {
            "status": "ok",
            "raw": {...},  # Full response from backend
            "docs_url": "/docs"  # URL to API documentation
        }
        Or None if backend is unreachable.
        
    # TODO: Update to call GET /health endpoint when it exists in the backend.
        Currently uses root endpoint (/) which returns basic API info.
        When /health endpoint is available, this function should be updated to:
        - Call GET {BACKEND_URL}/health instead of /
        - Parse health metrics, uptime, connector status, etc.
    """
    try:
        backend_url = get_backend_url()
        response = requests.get(f"{backend_url}/", timeout=5)
        response.raise_for_status()
        data = response.json()
        return {
            "status": "ok",
            "raw": data,
            "docs_url": data.get("docs", "/docs")
        }
    except requests.exceptions.RequestException:
        # Don't log errors here - let the UI component handle it
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
        retailers: List of retailer identifiers (e.g., ["ah", "jumbo", "picnic"]). 
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
        retailer: Retailer identifier (ah, jumbo, picnic)
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

