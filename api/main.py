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

from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Header, Query, HTTPException, status

from aggregator.search import aggregated_search
from aggregator.cart import get_cart, add_to_cart, remove_from_cart
from aggregator.models import CartItem, Cart
from aggregator.connectors.ah_connector import AHConnector
from aggregator.connectors.jumbo_connector import JumboConnector
from aggregator.connectors.picnic_connector import PicnicConnector
from api.schemas import ProductBase, SearchResponse, CartItemInput, CartView

app = FastAPI(
    title="NL Grocery Aggregator API",
    description="Backend API for aggregating grocery products from Albert Heijn, Jumbo, and Picnic",
    version="1.0.0",
    tags_metadata=[
        {
            "name": "search",
            "description": "Search for products across multiple retailers (AH, Jumbo, Picnic).",
        },
        {
            "name": "cart",
            "description": "Manage shopping cart items. Use X-Session-ID header for cart session management.",
        },
        {
            "name": "delivery",
            "description": "Get delivery slots for retailers (currently only Picnic supported).",
        },
    ],
)

# Valid retailer identifiers
VALID_RETAILERS = {"ah", "jumbo", "picnic"}


def get_session(x_session_id: Optional[str] = Header(None, alias="X-Session-ID")) -> str:
    """
    Get or create a session ID from the X-Session-ID header.
    
    Args:
        x_session_id: Session ID from X-Session-ID header (optional)
        
    Returns:
        Session ID string (uses "demo-user" as default if not provided)
    """
    return x_session_id or "demo-user"


def dict_to_product(product_dict: Dict[str, Any]) -> ProductBase:
    """
    Convert a product dictionary from aggregated_search to a ProductBase model.
    
    Args:
        product_dict: Dictionary containing product data from aggregated_search
        
    Returns:
        ProductBase model instance with all fields including is_cheapest and raw
    """
    return ProductBase(
        id=str(product_dict.get("id", "")),
        retailer=product_dict.get("retailer", ""),
        name=product_dict.get("name", ""),
        price_eur=float(product_dict.get("price_eur", 0.0)),
        unit=product_dict.get("unit"),
        unit_size=product_dict.get("unit_size"),
        image_url=product_dict.get("image_url"),
        url=product_dict.get("url"),
        health_tag=product_dict.get("health_tag", "neutral"),
        is_cheapest=product_dict.get("is_cheapest"),
        raw=product_dict.get("raw"),
    )


@app.get(
    "/search",
    response_model=SearchResponse,
    tags=["search"],
    summary="Search for products across multiple retailers",
    description="Search for products across Albert Heijn, Jumbo, and Picnic. Results are normalized, "
                "health-tagged, grouped by name with cheapest marked, and sorted according to sort_by parameter.",
)
def search(
    q: str = Query(..., min_length=1, description="Search query string (e.g., 'melk', 'brood')"),
    retailers: str = Query(
        "picnic,ah,jumbo",
        description="Comma-separated list of retailers to search. Valid values: ah, jumbo, picnic"
    ),
    size: int = Query(10, ge=1, le=50, description="Number of results per retailer (max: 50)"),
    page: int = Query(0, ge=0, description="Page number (0-indexed)"),
    sort_by: Optional[str] = Query(
        "price",
        description="Sort criterion: 'price' (lowest first), 'retailer' (alphabetical), or 'health' (healthy first)"
    ),
    health_filter: Optional[str] = Query(
        None,
        description="Filter by health tag: 'healthy' or 'unhealthy' (optional)"
    ),
) -> SearchResponse:
    """
    Search for products across multiple retailers.
    
    Searches the specified retailers for products matching the query string,
    aggregates the results, adds health tags, filters by health if requested,
    groups by name to mark cheapest options, and returns a merged, sorted list.
    
    Args:
        q: Search query string (minimum 1 character)
        retailers: Comma-separated list of retailer identifiers (e.g., "ah,jumbo,picnic")
        size: Number of results to return per retailer (1-50)
        page: Page number for pagination (0-indexed)
        sort_by: Sort criterion - "price", "retailer", or "health" (default: "price")
        health_filter: Optional filter for health tag - "healthy" or "unhealthy"
        
    Returns:
        SearchResponse containing:
        - results: List of ProductBase models, sorted and filtered according to parameters
        
    Raises:
        HTTPException 400: If no valid retailers are specified or invalid retailer names provided
        HTTPException 500: If search fails due to connector errors
        
    Example:
        ```bash
        GET /search?q=melk&retailers=ah,picnic&size=5&sort_by=price&health_filter=healthy
        ```
    """
    # Parse and validate retailers
    retailer_list = [r.strip().lower() for r in retailers.split(",") if r.strip()]
    
    if not retailer_list:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one retailer must be specified. Valid retailers: ah, jumbo, picnic"
        )
    
    # Validate retailer names
    invalid_retailers = [r for r in retailer_list if r not in VALID_RETAILERS]
    if invalid_retailers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid retailer(s): {', '.join(invalid_retailers)}. Valid retailers: {', '.join(sorted(VALID_RETAILERS))}"
        )
    
    # Validate sort_by parameter
    valid_sort_options = {"price", "retailer", "health"}
    if sort_by and sort_by.lower() not in valid_sort_options:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid sort_by: '{sort_by}'. Valid options: {', '.join(sorted(valid_sort_options))}"
        )
    
    # Validate health_filter if provided
    if health_filter:
        health_filter_lower = health_filter.lower()
        if health_filter_lower not in ("healthy", "unhealthy"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid health_filter: '{health_filter}'. Valid options: 'healthy', 'unhealthy'"
            )
    
    try:
        # Perform aggregated search with all parameters
        # Note: query and retailers are positional args to match test expectations
        results_dicts = aggregated_search(
            q,  # positional: query
            retailer_list,  # positional: retailers
            size_per_retailer=size,
            page=page,
            sort_by=sort_by or "price",
            health_filter=health_filter
        )
        
        # Convert dictionaries to ProductBase models
        products = [dict_to_product(p) for p in results_dicts]
        
        return SearchResponse(results=products)
    except RuntimeError as e:
        # Handle connector errors specifically
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error connecting to retailer services: {str(e)}"
        ) from e
    except Exception as e:
        # Handle any other unexpected errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error performing search: {str(e)}"
        ) from e


@app.post(
    "/cart/add",
    response_model=CartView,
    tags=["cart"],
    summary="Add an item to the shopping cart",
    description="Add a product to the shopping cart for the current session. If the item already "
                "exists in the cart, quantities are accumulated. Use X-Session-ID header for session management.",
)
def add_item(
    item: CartItemInput,
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID", description="Session identifier (defaults to 'demo-user')"),
) -> CartView:
    """
    Add an item to the shopping cart.
    
    Adds a product to the cart for the given session. If the item already exists
    in the cart, its quantity is accumulated.
    
    Args:
        item: CartItemInput model containing cart item data
        x_session_id: Session ID from X-Session-ID header (optional, defaults to "demo-user")
        
    Returns:
        CartView containing:
        - items: List of CartItem objects in the cart
        - total: Total price of all items in euros
        
    Raises:
        HTTPException 400: If cart item data is invalid or retailer is invalid
        HTTPException 500: If there's an error adding the item to cart
        
    Example:
        ```bash
        POST /cart/add
        Header: X-Session-ID: user123
        Body: {
            "retailer": "ah",
            "product_id": "12345",
            "name": "Melk",
            "price_eur": 1.99,
            "quantity": 2
        }
        ```
    """
    # Validate retailer
    if item.retailer.lower() not in VALID_RETAILERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid retailer: {item.retailer}. Valid retailers: {', '.join(sorted(VALID_RETAILERS))}"
        )
    
    session = get_session(x_session_id)
    
    try:
        # Convert CartItemInput to CartItem and add to cart
        cart_item = CartItem(
            retailer=item.retailer.lower(),
            product_id=item.product_id,
            name=item.name,
            price_eur=item.price_eur,
            quantity=item.quantity,
            image_url=item.image_url,
            health_tag=item.health_tag,
        )
        
        cart = add_to_cart(session, cart_item.model_dump())
        
        # Convert Cart to CartView format
        return CartView(
            items=list(cart.items.values()),
            total=cart.total()
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid cart item data: {str(e)}"
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error adding item to cart: {str(e)}"
        ) from e


@app.post(
    "/cart/remove",
    response_model=CartView,
    tags=["cart"],
    summary="Remove an item from the shopping cart",
    description="Remove an item from the cart or reduce its quantity. If the quantity to remove "
                "exceeds the item's quantity, the item is completely removed.",
)
def remove_item(
    retailer: str = Query(..., description="Retailer identifier (ah, jumbo, or picnic)"),
    product_id: str = Query(..., min_length=1, description="Product identifier"),
    qty: int = Query(1, ge=1, description="Quantity to remove (default: 1)"),
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID", description="Session identifier (defaults to 'demo-user')"),
) -> CartView:
    """
    Remove an item from the shopping cart or reduce its quantity.
    
    Removes the specified quantity of an item from the cart. If the quantity to remove
    is greater than or equal to the item's quantity, the item is completely removed.
    
    Args:
        retailer: Retailer identifier (ah, jumbo, or picnic)
        product_id: Product identifier (minimum 1 character)
        qty: Quantity to remove (default: 1, minimum: 1)
        x_session_id: Session ID from X-Session-ID header (optional, defaults to "demo-user")
        
    Returns:
        CartView containing:
        - items: List of CartItem objects remaining in the cart
        - total: Updated total price of all items in euros
        
    Raises:
        HTTPException 400: If retailer is invalid
        HTTPException 500: If there's an error removing the item from cart
        
    Example:
        ```bash
        POST /cart/remove?retailer=ah&product_id=12345&qty=1
        Header: X-Session-ID: user123
        ```
    """
    # Validate retailer
    retailer_lower = retailer.lower()
    if retailer_lower not in VALID_RETAILERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid retailer: {retailer}. Valid retailers: {', '.join(sorted(VALID_RETAILERS))}"
        )
    
    session = get_session(x_session_id)
    
    try:
        cart = remove_from_cart(session, retailer_lower, product_id, qty)
        
        # Convert Cart to CartView format
        return CartView(
            items=list(cart.items.values()),
            total=cart.total()
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error removing item from cart: {str(e)}"
        ) from e


@app.get(
    "/cart/view",
    response_model=CartView,
    tags=["cart"],
    summary="View the current shopping cart",
    description="Retrieve the contents of the shopping cart for the current session along with the total price.",
)
def view_cart(
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID", description="Session identifier (defaults to 'demo-user')"),
) -> CartView:
    """
    View the current shopping cart for a session.
    
    Returns the cart contents along with the total price.
    
    Args:
        x_session_id: Session ID from X-Session-ID header (optional, defaults to "demo-user")
        
    Returns:
        CartView containing:
        - items: List of CartItem objects in the cart
        - total: Total price of all items in the cart (in euros)
        
    Raises:
        HTTPException 500: If there's an error retrieving the cart
        
    Example:
        ```bash
        GET /cart/view
        Header: X-Session-ID: user123
        ```
    """
    session = get_session(x_session_id)
    
    try:
        cart = get_cart(session)
        
        # Convert Cart to CartView format
        return CartView(
            items=list(cart.items.values()),
            total=cart.total()
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving cart: {str(e)}"
        ) from e


@app.get(
    "/delivery/slots",
    tags=["delivery"],
    summary="Get delivery slots for a retailer",
    description="Retrieve available delivery slots for the specified retailer. "
                "Currently only Picnic supports delivery slots.",
    response_model=List[dict],
)
def get_slots(
    retailer: str = Query("picnic", description="Retailer identifier (ah, jumbo, or picnic)"),
) -> Any:
    """
    Get available delivery slots for a retailer.
    
    Currently only Picnic supports delivery slots. AH and Jumbo return empty lists
    as delivery integration is not yet implemented for those retailers.
    
    Args:
        retailer: Retailer identifier (default: "picnic")
        
    Returns:
        List of delivery slot dictionaries (retailer-specific format) or empty list
        
    Raises:
        HTTPException 400: If retailer is invalid
        HTTPException 500: If there's an error retrieving delivery slots
        
    Example:
        ```bash
        GET /delivery/slots?retailer=picnic
        ```
    """
    retailer_lower = retailer.lower()
    
    # Validate retailer
    if retailer_lower not in VALID_RETAILERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid retailer: {retailer}. Valid retailers: {', '.join(sorted(VALID_RETAILERS))}"
        )
    
    try:
        if retailer_lower == "picnic":
            connector = PicnicConnector()
            slots = connector.get_delivery_slots()
            return slots if isinstance(slots, list) else []
        elif retailer_lower == "ah":
            connector = AHConnector()
            slots = connector.get_delivery_slots()
            return slots if isinstance(slots, list) else []
        elif retailer_lower == "jumbo":
            connector = JumboConnector()
            slots = connector.get_delivery_slots()
            return slots if isinstance(slots, list) else []
        else:
            return []
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving {retailer_lower} delivery slots: {str(e)}"
        ) from e


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
