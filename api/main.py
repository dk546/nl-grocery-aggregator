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

# Import config early to load .env file before any other code accesses environment variables
# This ensures local development uses .env file, while Render uses platform env vars
import api.config  # noqa: F401

import time
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Header, Query, HTTPException, status

from aggregator.search import aggregated_search
from aggregator.cart import get_cart, add_to_cart, remove_from_cart, replace_cart
from aggregator.models import CartItem, Cart
from aggregator.templates import (
    list_templates_for_session,
    save_template_for_session,
    get_template_for_session,
    delete_template_for_session,
)
from aggregator.events import log_event
from aggregator.connectors.ah_connector import AHConnector
from aggregator.connectors.jumbo_connector import JumboConnector
from aggregator.connectors.picnic_connector import PicnicConnector
from api.schemas import (
    ProductBase,
    SearchResponse,
    CartItemInput,
    CartView,
    CartItemOut,
    BasketSavingsResponse,
    BasketTemplate,
    BasketTemplateListResponse,
    SaveBasketTemplateRequest,
    SaveBasketTemplateResponse,
)

# Track app start time for uptime calculation
_APP_START_TIME = time.time()

app = FastAPI(
    title="NL Grocery Aggregator API",
    description="Backend API for aggregating grocery products from Albert Heijn, Jumbo, Picnic, and Dirk",
    version="1.0.0",
    tags_metadata=[
        {
            "name": "search",
            "description": "Search for products across multiple retailers (AH, Jumbo, Picnic, Dirk).",
        },
        {
            "name": "cart",
            "description": "Manage shopping cart items. Use X-Session-ID header for cart session management.",
        },
        {
            "name": "delivery",
            "description": "Get delivery slots for retailers (currently only Picnic supported).",
        },
        {
            "name": "health",
            "description": "Health check and monitoring endpoints.",
        },
    ],
)

# Valid retailer identifiers
VALID_RETAILERS = {"ah", "jumbo", "picnic", "dirk"}

# Initialize database if DATABASE_URL is set
try:
    from aggregator.db import db_is_enabled, init_db
    
    if db_is_enabled():
        try:
            init_db()
        except Exception as e:
            # Log error but don't crash the app - fallback to in-memory/file storage
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Database initialization failed, using fallback storage: {e}")
except ImportError:
    # SQLAlchemy not installed - that's fine, we'll use fallback storage
    pass


def get_session(x_session_id: Optional[str] = Header(None, alias="X-Session-ID")) -> str:
    """
    Get session ID from the X-Session-ID header.
    
    Args:
        x_session_id: Session ID from X-Session-ID header
        
    Returns:
        Session ID string
        
    Raises:
        HTTPException 400: If session ID is not provided
    """
    if not x_session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Session-ID header is required for cart operations. Please provide a session identifier.",
            headers={"X-Session-ID": "required"}
        )
    return x_session_id


def dict_to_product(product_dict: Dict[str, Any]) -> ProductBase:
    """
    Convert a product dictionary from aggregated_search to a ProductBase model.
    
    Args:
        product_dict: Dictionary containing product data from aggregated_search
                     (now comes from ProductPublic.model_dump(), so includes both price and price_eur)
        
    Returns:
        ProductBase model instance with all fields including is_cheapest and raw
    """
    # Extract price - prefer price_eur for backward compatibility, fallback to price
    price_value = product_dict.get("price_eur") or product_dict.get("price") or 0.0
    
    return ProductBase(
        id=str(product_dict.get("id", "")),
        retailer=product_dict.get("retailer", ""),
        name=product_dict.get("name", ""),
        price=float(price_value),  # Use price field
        price_eur=float(price_value),  # Also set price_eur alias
        unit=product_dict.get("unit"),
        unit_size=product_dict.get("unit_size"),
        quantity=product_dict.get("quantity"),
        quantity_unit=product_dict.get("quantity_unit"),
        price_per_unit=product_dict.get("price_per_unit"),
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
    description="Search for products across Albert Heijn, Jumbo, Picnic, and Dirk. Results are normalized, "
                "health-tagged, grouped by name with cheapest marked, and sorted according to sort_by parameter.",
)
def search(
    q: str = Query(..., min_length=1, description="Search query string (e.g., 'melk', 'brood')"),
    retailers: str = Query(
        "picnic,ah,jumbo",
        description="Comma-separated list of retailers to search. Valid values: ah, jumbo, picnic, dirk"
    ),
    size: int = Query(10, ge=1, le=50, description="Number of results per retailer (max: 50)"),
    page: int = Query(0, ge=0, description="Page number (0-indexed)"),
    sort_by: Optional[str] = Query(
        "price",
        description="Sort criterion: 'price' or 'price_asc' (lowest first), 'price_desc' (highest first), "
                    "'price_per_unit_asc' (lowest per unit first), 'price_per_unit_desc' (highest per unit first), "
                    "'retailer' (alphabetical), or 'health' (healthy first)"
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
        sort_by: Sort criterion - "price"/"price_asc", "price_desc", "price_per_unit_asc", 
                "price_per_unit_desc", "retailer", or "health" (default: "price")
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
            detail="At least one retailer must be specified. Valid retailers: ah, jumbo, picnic, dirk"
        )
    
    # Validate retailer names
    invalid_retailers = [r for r in retailer_list if r not in VALID_RETAILERS]
    if invalid_retailers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid retailer(s): {', '.join(invalid_retailers)}. Valid retailers: {', '.join(sorted(VALID_RETAILERS))}"
        )
    
    # Validate sort_by parameter (accept both legacy and new format)
    valid_sort_options = {
        "price", "price_asc", "price_desc",
        "price_per_unit", "price_per_unit_asc", "price_per_unit_desc",
        "retailer", "health"
    }
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
        search_response = aggregated_search(
            q,  # positional: query
            retailer_list,  # positional: retailers
            size_per_retailer=size,
            page=page,
            sort_by=sort_by or "price",
            health_filter=health_filter
        )
        
        # Extract results and connector status from response
        results_dicts = search_response.get("results", [])
        connectors_status = search_response.get("connectors_status", {})
        
        # Convert dictionaries to ProductBase models
        products = [dict_to_product(p) for p in results_dicts]
        
        # Log search event
        try:
            session = get_session(None)  # Try to get session if available (may be None for search)
            log_event(
                "search_performed",
                session_id=session,
                payload={
                    "query": q,
                    "retailers": retailer_list,
                    "result_count": len(products),
                    "size": size,
                    "page": page,
                    "sort_by": sort_by or "price",
                    "health_filter": health_filter,
                },
            )
        except Exception:
            # Non-blocking: log search even if session extraction fails
            log_event(
                "search_performed",
                session_id=None,
                payload={
                    "query": q,
                    "retailers": retailer_list,
                    "result_count": len(products),
                },
            )
        
        return SearchResponse(results=products, connectors_status=connectors_status)
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
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID", description="Session identifier (required)"),
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
        
        # Log cart item addition event
        try:
            log_event(
                "cart_items_added",
                session_id=session,
                payload={
                    "retailer": cart_item.retailer,
                    "product_id": cart_item.product_id,
                    "name": cart_item.name,
                    "quantity": cart_item.quantity,
                    "price_eur": cart_item.price_eur,
                    "health_tag": cart_item.health_tag,
                },
            )
        except Exception:
            pass  # Non-blocking
        
        # Convert Cart to CartView format with CartItemOut (includes line_total)
        items_out = [
            CartItemOut(
                retailer=item.retailer,
                product_id=item.product_id,
                name=item.name,
                price_eur=item.price_eur,
                quantity=item.quantity,
                image_url=item.image_url,
                health_tag=item.health_tag,
                line_total=item.total_price
            )
            for item in cart.items.values()
        ]
        
        return CartView(
            items=items_out,
            total_price=cart.total(),
            total_by_retailer=cart.total_by_retailer()
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
    retailer: str = Query(..., description="Retailer identifier (ah, jumbo, picnic, or dirk)"),
    product_id: str = Query(..., min_length=1, description="Product identifier"),
    qty: int = Query(1, ge=1, description="Quantity to remove (default: 1)"),
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID", description="Session identifier (required)"),
) -> CartView:
    """
    Remove an item from the shopping cart or reduce its quantity.
    
    Removes the specified quantity of an item from the cart. If the quantity to remove
    is greater than or equal to the item's quantity, the item is completely removed.
    
    Args:
        retailer: Retailer identifier (ah, jumbo, picnic, or dirk)
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
        
        # Log cart item removal event
        try:
            log_event(
                "cart_items_removed",
                session_id=session,
                payload={
                    "retailer": retailer_lower,
                    "product_id": product_id,
                    "quantity_removed": qty,
                },
            )
        except Exception:
            pass  # Non-blocking
        
        # Convert Cart to CartView format with CartItemOut (includes line_total)
        items_out = [
            CartItemOut(
                retailer=item.retailer,
                product_id=item.product_id,
                name=item.name,
                price_eur=item.price_eur,
                quantity=item.quantity,
                image_url=item.image_url,
                health_tag=item.health_tag,
                line_total=item.total_price
            )
            for item in cart.items.values()
        ]
        
        return CartView(
            items=items_out,
            total_price=cart.total(),
            total_by_retailer=cart.total_by_retailer()
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
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID", description="Session identifier (required)"),
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
        
        # Convert Cart to CartView format with CartItemOut (includes line_total)
        items_out = [
            CartItemOut(
                retailer=item.retailer,
                product_id=item.product_id,
                name=item.name,
                price_eur=item.price_eur,
                quantity=item.quantity,
                image_url=item.image_url,
                health_tag=item.health_tag,
                line_total=item.total_price
            )
            for item in cart.items.values()
        ]
        
        return CartView(
            items=items_out,
            total_price=cart.total(),
            total_by_retailer=cart.total_by_retailer()
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
    retailer: str = Query("picnic", description="Retailer identifier (ah, jumbo, picnic, or dirk)"),
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


@app.get(
    "/basket/savings",
    response_model=BasketSavingsResponse,
    tags=["cart"],
    summary="Find cheaper alternatives for basket items",
    description="Analyze the current basket and find cheaper alternatives for each item, "
                "calculating potential savings. Uses aggregated_search to find alternatives.",
)
def get_basket_savings(
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID", description="Session identifier (required)"),
) -> BasketSavingsResponse:
    """
    Get potential savings by finding cheaper alternatives for basket items.
    
    This endpoint:
    1. Loads the current basket for the session
    2. Searches for cheaper alternatives for each item
    3. Calculates estimated savings
    4. Returns suggestions sorted by potential savings
    
    Args:
        x_session_id: Session ID from X-Session-ID header (required)
        
    Returns:
        BasketSavingsResponse containing:
        - potential_savings_total: Total estimated savings across all suggestions
        - suggestions: List of savings suggestions with current/alternative products
        
    Raises:
        HTTPException 400: If session ID is not provided
        HTTPException 500: If there's an error analyzing savings
        
    Example:
        ```bash
        GET /basket/savings
        Header: X-Session-ID: user123
        ```
    """
    session = get_session(x_session_id)
    
    try:
        # Get current basket
        cart = get_cart(session)
        
        if not cart.items:
            # Empty basket - return empty response
            return BasketSavingsResponse(
                potential_savings_total=0.0,
                suggestions=[]
            )
        
        # Convert cart items to dict format for savings analysis
        basket_items = []
        for item in cart.items.values():
            item_dict = {
                "retailer": item.retailer,
                "product_id": item.product_id,
                "name": item.name,
                "price_eur": item.price_eur,
                "quantity": item.quantity,
                "line_total": item.total_price,
                "image_url": item.image_url,
                "health_tag": item.health_tag,
                # Note: price_per_unit may not be available in cart items,
                # but savings logic will handle None gracefully
                "price_per_unit": None,  # Cart items don't store this, but search results will have it
            }
            basket_items.append(item_dict)
        
        # Call savings finder
        from aggregator.savings import find_basket_savings
        
        savings_result = find_basket_savings(
            basket_items=basket_items,
            search_fn=aggregated_search,
        )
        
        # Convert to response model
        suggestions = []
        for sug in savings_result.get("suggestions", []):
            current_dict = sug.get("current", {})
            alt_dict = sug.get("alternative", {})
            
            suggestions.append(
                SavingsSuggestion(
                    current=SavingsProduct(
                        retailer=current_dict.get("retailer", ""),
                        product_id=str(current_dict.get("product_id", "")),
                        name=current_dict.get("name", ""),
                        price_eur=float(current_dict.get("price_eur", 0.0)),
                        price_per_unit=current_dict.get("price_per_unit"),
                        quantity=current_dict.get("quantity"),
                        line_total=current_dict.get("line_total"),
                        image_url=current_dict.get("image_url"),
                        health_tag=current_dict.get("health_tag"),
                    ),
                    alternative=SavingsProduct(
                        retailer=alt_dict.get("retailer", ""),
                        product_id=str(alt_dict.get("product_id", "")),
                        name=alt_dict.get("name", ""),
                        price_eur=float(alt_dict.get("price_eur", 0.0)),
                        price_per_unit=alt_dict.get("price_per_unit"),
                        image_url=alt_dict.get("image_url"),
                        health_tag=alt_dict.get("health_tag"),
                    ),
                    estimated_line_total=float(sug.get("estimated_line_total", 0.0)),
                    estimated_savings=float(sug.get("estimated_savings", 0.0)),
                )
            )
        
        basket_savings_response = BasketSavingsResponse(
            potential_savings_total=float(savings_result.get("potential_savings_total", 0.0)),
            suggestions=suggestions
        )
        
        # Log savings analysis event
        try:
            log_event(
                "savings_analysis_run",
                session_id=session,
                payload={
                    "suggestions_count": len(suggestions),
                    "potential_savings_total": float(savings_result.get("potential_savings_total", 0.0)),
                    "basket_items_count": len(cart.items),
                },
            )
        except Exception:
            pass  # Non-blocking
        
        return basket_savings_response
        
    except HTTPException:
        # Re-raise HTTP exceptions (e.g., missing session ID)
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error analyzing basket savings: {str(e)}"
        ) from e


@app.get(
    "/api/basket/templates",
    response_model=BasketTemplateListResponse,
    tags=["cart"],
    summary="List saved basket templates",
    description="Retrieve all saved basket templates for the current session.",
)
def list_basket_templates(
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID", description="Session identifier (required)"),
) -> BasketTemplateListResponse:
    """List all saved basket templates for a session."""
    session = get_session(x_session_id)
    templates = list_templates_for_session(session)
    
    # Convert to Pydantic models
    pydantic_templates = []
    for t in templates:
        template_items = []
        for item in t.items:
            line_total = item.get("line_total") or (float(item.get("price_eur", 0.0)) * int(item.get("quantity", 1)))
            from api.schemas import BasketTemplateItem
            template_items.append(
                BasketTemplateItem(
                    retailer=item.get("retailer", ""),
                    product_id=str(item.get("product_id", "")),
                    name=item.get("name", ""),
                    price_eur=float(item.get("price_eur", 0.0)),
                    quantity=int(item.get("quantity", 1)),
                    line_total=line_total,
                    health_tag=item.get("health_tag"),
                    image_url=item.get("image_url"),
                )
            )
        pydantic_templates.append(
            BasketTemplate(
                id=t.id,
                name=t.name,
                created_at=t.created_at,
                items=template_items,
            )
        )
    
    return BasketTemplateListResponse(templates=pydantic_templates)


@app.post(
    "/api/basket/templates",
    response_model=SaveBasketTemplateResponse,
    tags=["cart"],
    summary="Save current basket as a template",
    description="Save the current basket contents as a named template for reuse.",
)
def save_basket_template(
    payload: SaveBasketTemplateRequest,
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID", description="Session identifier (required)"),
) -> SaveBasketTemplateResponse:
    """Save the current basket as a named template."""
    session = get_session(x_session_id)
    cart = get_cart(session)
    
    if not cart.items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot save an empty basket as a template."
        )
    
    # Convert cart items to dict format
    items = []
    for item in cart.items.values():
        items.append({
            "retailer": item.retailer,
            "product_id": item.product_id,
            "name": item.name,
            "price_eur": item.price_eur,
            "quantity": item.quantity,
            "line_total": item.total_price,
            "image_url": item.image_url,
            "health_tag": item.health_tag,
        })
    
    # Save template
    template = save_template_for_session(session, payload.name, items)
    
    # Convert to Pydantic model
    template_items = []
    for item in template.items:
        from api.schemas import BasketTemplateItem
        template_items.append(
            BasketTemplateItem(
                retailer=item.get("retailer", ""),
                product_id=str(item.get("product_id", "")),
                name=item.get("name", ""),
                price_eur=float(item.get("price_eur", 0.0)),
                quantity=int(item.get("quantity", 1)),
                line_total=item.get("line_total"),
                health_tag=item.get("health_tag"),
                image_url=item.get("image_url"),
            )
        )
    
    p_template = BasketTemplate(
        id=template.id,
        name=template.name,
        created_at=template.created_at,
        items=template_items,
    )
    
    # Log template save event
    try:
        log_event(
            "template_saved",
            session_id=session,
            payload={
                "template_name": template.name,
                "template_id": template.id,
                "item_count": len(template.items),
            },
        )
    except Exception:
        pass  # Non-blocking
    
    return SaveBasketTemplateResponse(template=p_template)


@app.post(
    "/api/basket/templates/{template_id}/apply",
    response_model=BasketTemplate,
    tags=["cart"],
    summary="Apply a saved basket template",
    description="Replace the current basket contents with a saved template.",
)
def apply_basket_template(
    template_id: str,
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID", description="Session identifier (required)"),
) -> BasketTemplate:
    """Apply a saved template to replace the current basket."""
    session = get_session(x_session_id)
    template = get_template_for_session(session, template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found."
        )
    
    # Replace cart with template items (logging happens inside replace_cart)
    replace_cart(session, template.items)
    
    # Log template applied event
    try:
        cart_after = get_cart(session)
        log_event(
            "template_applied",
            session_id=session,
            payload={
                "template_name": template.name,
                "template_id": template.id,
                "item_count": len(template.items),
                "basket_total_items": len(cart_after.items),
                "basket_total_value": cart_after.total(),
            },
        )
    except Exception:
        pass  # Non-blocking
    
    # Convert to Pydantic model
    template_items = []
    for item in template.items:
        from api.schemas import BasketTemplateItem
        template_items.append(
            BasketTemplateItem(
                retailer=item.get("retailer", ""),
                product_id=str(item.get("product_id", "")),
                name=item.get("name", ""),
                price_eur=float(item.get("price_eur", 0.0)),
                quantity=int(item.get("quantity", 1)),
                line_total=item.get("line_total"),
                health_tag=item.get("health_tag"),
                image_url=item.get("image_url"),
            )
        )
    
    return BasketTemplate(
        id=template.id,
        name=template.name,
        created_at=template.created_at,
        items=template_items,
    )


@app.delete(
    "/api/basket/templates/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["cart"],
    summary="Delete a saved basket template",
    description="Delete a saved basket template.",
)
def delete_basket_template(
    template_id: str,
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID", description="Session identifier (required)"),
) -> None:
    """Delete a saved template."""
    session = get_session(x_session_id)
    delete_template_for_session(session, template_id)
    return


@app.get("/health", tags=["health"])
def health():
    """
    Health check endpoint for monitoring and status checks.
    
    Returns:
        Dictionary with status, API metadata, uptime information, and database status.
        Always returns 200 OK if the endpoint is reachable.
    """
    uptime_seconds = int(time.time() - _APP_START_TIME)
    
    # Check database status
    db_enabled = False
    try:
        from aggregator.db import db_is_enabled
        db_enabled = db_is_enabled()
    except Exception:
        # If db_is_enabled() raises any error, treat as fallback mode
        db_enabled = False
    
    return {
        "status": "ok",
        "name": "NL Grocery Aggregator API",
        "version": "1.0.0",
        "description": "Backend API for aggregating grocery products from Albert Heijn, Jumbo, Picnic, and Dirk",
        "uptime_seconds": uptime_seconds,
        "db_enabled": db_enabled,
    }


@app.get("/price-history/{retailer}/{product_id}", tags=["search"])
def price_history(retailer: str, product_id: str, limit: int = Query(30, ge=1, le=100)):
    """
    Demo price history endpoint.
    
    Returns recent prices for this product based on previous searches in this environment.
    Data is based on previous searches and resets on backend restart.
    
    This is a demo feature - data is stored in a local file and is ephemeral.
    
    Args:
        retailer: Retailer identifier (ah, jumbo, picnic, dirk)
        product_id: Product identifier (may include retailer prefix like "ah:123" or just "123")
        limit: Maximum number of price points to return (default: 30, max: 100)
        
    Returns:
        Dictionary with:
        - status: "ok"
        - retailer: Retailer identifier
        - product_id: Product identifier
        - points: List of price points, each with "ts" (timestamp) and "price_eur"
    """
    try:
        from aggregator.price_history import get_price_history
        
        points = get_price_history(product_id=product_id, retailer=retailer, limit=limit)
        
        return {
            "status": "ok",
            "retailer": retailer,
            "product_id": product_id,
            "points": [
                {"ts": p.ts, "price_eur": p.price_eur}
                for p in points
            ],
            "demo_note": "This is a demo feature. Data resets when the backend restarts.",
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving price history: {str(e)}"
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
        "description": "Backend API for aggregating grocery products from Albert Heijn, Jumbo, Picnic, and Dirk",
        "docs": "/docs",
    }
