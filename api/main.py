"""
FastAPI application for the NL Grocery Aggregator API.

This module defines the REST API endpoints for the grocery aggregator backend:
- GET /search: Search for products across multiple retailers
- POST /cart/add: Add an item to the shopping cart
- POST /cart/remove: Remove an item from the shopping cart
- GET /cart/view: View the current shopping cart
- GET /delivery/slots: Get delivery slots for a retailer

The API uses session-based cart management via the X-Session-ID header. If no
header is provided, a default session ID is used (for development/testing).

Run the API with:
    uvicorn api.main:app --reload

Access API documentation at:
    http://localhost:8000/docs (Swagger UI)
    http://localhost:8000/redoc (ReDoc)
"""

from typing import Optional

from fastapi import FastAPI, Header, Query, HTTPException

from aggregator.search import aggregated_search
from aggregator.cart import get_cart, add_to_cart, remove_from_cart
from aggregator.connectors.ah_connector import AHConnector
from aggregator.connectors.jumbo_connector import JumboConnector
from aggregator.connectors.picnic_connector import PicnicConnector

app = FastAPI(
    title="NL Grocery Aggregator API",
    description="Backend API for aggregating grocery products from Albert Heijn, Jumbo, and Picnic",
    version="1.0.0",
)


def get_session(x_session_id: Optional[str] = None) -> str:
    """
    Get or create a session ID from the X-Session-ID header.
    
    Args:
        x_session_id: Session ID from X-Session-ID header (optional)
        
    Returns:
        Session ID string (uses "demo-user" as default if not provided)
    """
    return x_session_id or "demo-user"


@app.get("/search")
def search(
    q: str = Query(..., description="Search query string (e.g., 'melk', 'brood')"),
    retailers: str = Query("picnic,ah,jumbo", description="Comma-separated list of retailers to search"),
    size: int = Query(10, ge=1, description="Number of results per retailer"),
    page: int = Query(0, ge=0, description="Page number (0-indexed)"),
):
    """
    Search for products across multiple retailers.
    
    Searches the specified retailers for products matching the query string,
    aggregates the results, adds health tags, and returns a merged, sorted list.
    
    Args:
        q: Search query string
        retailers: Comma-separated list of retailer identifiers (e.g., "ah,jumbo,picnic")
        size: Number of results to return per retailer
        page: Page number for pagination (0-indexed)
        
    Returns:
        Dictionary containing:
        - results: List of product dictionaries, sorted by price
        
    Example:
        GET /search?q=melk&retailers=ah,picnic&size=5
    """
    retailer_list = [r.strip().lower() for r in retailers.split(",") if r.strip()]
    if not retailer_list:
        raise HTTPException(status_code=400, detail="At least one retailer must be specified")
    
    results = aggregated_search(q, retailer_list, size_per_retailer=size, page=page)
    return {"results": results, "count": len(results), "query": q}


@app.post("/cart/add")
def add_item(
    item: dict,
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID", description="Session identifier"),
):
    """
    Add an item to the shopping cart.
    
    Adds a product to the cart for the given session. If the item already exists
    in the cart, its quantity is accumulated.
    
    Args:
        item: Dictionary containing cart item data:
            - retailer: Retailer identifier (required)
            - product_id: Product identifier (required)
            - name: Product name (required)
            - price_eur: Price per unit (required)
            - quantity: Quantity to add (optional, default: 1)
            - image_url: Product image URL (optional)
            - health_tag: Health tag (optional)
        x_session_id: Session ID from X-Session-ID header (optional)
        
    Returns:
        Updated Cart instance (Pydantic model, automatically serialized to JSON)
        
    Example:
        POST /cart/add
        Header: X-Session-ID: user123
        Body: {
            "retailer": "ah",
            "product_id": "12345",
            "name": "Melk",
            "price_eur": 1.99,
            "quantity": 2
        }
    """
    session = get_session(x_session_id)
    try:
        cart = add_to_cart(session, item)
        return cart
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid cart item data: {str(e)}") from e


@app.post("/cart/remove")
def remove_item(
    retailer: str = Query(..., description="Retailer identifier"),
    product_id: str = Query(..., description="Product identifier"),
    qty: int = Query(1, ge=1, description="Quantity to remove"),
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID", description="Session identifier"),
):
    """
    Remove an item from the shopping cart or reduce its quantity.
    
    Removes the specified quantity of an item from the cart. If the quantity to remove
    is greater than or equal to the item's quantity, the item is completely removed.
    
    Args:
        retailer: Retailer identifier
        product_id: Product identifier
        qty: Quantity to remove (default: 1)
        x_session_id: Session ID from X-Session-ID header (optional)
        
    Returns:
        Updated Cart instance after removal
        
    Example:
        POST /cart/remove?retailer=ah&product_id=12345&qty=1
        Header: X-Session-ID: user123
    """
    session = get_session(x_session_id)
    cart = remove_from_cart(session, retailer, product_id, qty)
    return cart


@app.get("/cart/view")
def view_cart(
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID", description="Session identifier"),
):
    """
    View the current shopping cart for a session.
    
    Returns the cart contents along with the total price.
    
    Args:
        x_session_id: Session ID from X-Session-ID header (optional)
        
    Returns:
        Dictionary containing:
        - cart: Cart instance with all items
        - total: Total price of all items in the cart (in euros)
        
    Example:
        GET /cart/view
        Header: X-Session-ID: user123
    """
    session = get_session(x_session_id)
    cart = get_cart(session)
    return {"cart": cart, "total": cart.total()}


@app.get("/delivery/slots")
def get_slots(
    retailer: str = Query("picnic", description="Retailer identifier (e.g., 'picnic')"),
):
    """
    Get available delivery slots for a retailer.
    
    Currently only supports Picnic. Returns delivery slot information in a
    retailer-specific format.
    
    Args:
        retailer: Retailer identifier (currently only "picnic" is supported)
        
    Returns:
        Delivery slots structure (retailer-specific format) or empty list
        
    Example:
        GET /delivery/slots?retailer=picnic
    """
    retailer = retailer.lower()
    
    if retailer == "picnic":
        try:
            connector = PicnicConnector()
            return connector.get_delivery_slots()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error retrieving Picnic delivery slots: {str(e)}") from e
    elif retailer == "ah":
        try:
            connector = AHConnector()
            return connector.get_delivery_slots()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error retrieving AH delivery slots: {str(e)}") from e
    elif retailer == "jumbo":
        try:
            connector = JumboConnector()
            return connector.get_delivery_slots()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error retrieving Jumbo delivery slots: {str(e)}") from e
    else:
        raise HTTPException(status_code=400, detail=f"Delivery slots not available for retailer: {retailer}")


@app.get("/")
def root():
    """
    Root endpoint providing API information.
    
    Returns:
        Dictionary with API name and version
    """
    return {
        "name": "NL Grocery Aggregator API",
        "version": "1.0.0",
        "description": "Backend API for aggregating grocery products from Albert Heijn, Jumbo, and Picnic",
        "docs": "/docs",
    }
