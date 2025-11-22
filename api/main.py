from typing import List, Optional
from fastapi import FastAPI, Query, Header, HTTPException

from aggregator.search import aggregated_search
from aggregator.cart import get_cart, add_to_cart, remove_from_cart
from aggregator.connectors.picnic_connector import PicnicRetailConnector

app = FastAPI(title="NL Supermarket Aggregator MVP")


def get_session_id(x_session_id: Optional[str]) -> str:
    # For now, use a dummy or header-based session id
    return x_session_id or "demo-user"


@app.get("/search")
def search(
    q: str = Query(..., description="Search query"),
    retailers: str = Query("ah,jumbo,picnic"),
    size: int = Query(10, ge=1, le=50),
    page: int = Query(0, ge=0),
):
    retailer_list = [r.strip() for r in retailers.split(",") if r.strip()]
    results = aggregated_search(q, retailer_list, size_per_retailer=size, page=page)
    return {"query": q, "results": results}


@app.post("/cart/add")
def cart_add(
    item: dict,
    x_session_id: Optional[str] = Header(default=None),
):
    session_id = get_session_id(x_session_id)
    cart = add_to_cart(session_id, item)
    return {"session_id": session_id, "cart": cart}


@app.post("/cart/remove")
def cart_remove(
    retailer: str,
    product_id: str,
    quantity: int = 1,
    x_session_id: Optional[str] = Header(default=None),
):
    session_id = get_session_id(x_session_id)
    cart = remove_from_cart(session_id, retailer, product_id, quantity)
    return {"session_id": session_id, "cart": cart}


@app.get("/cart/view")
def cart_view(
    x_session_id: Optional[str] = Header(default=None),
):
    session_id = get_session_id(x_session_id)
    cart = get_cart(session_id)
    return {"session_id": session_id, "cart": cart, "total": cart.total()}


@app.get("/delivery/slots")
def delivery_slots(
    retailer: str = Query(...),
):
    if retailer == "picnic":
        connector = PicnicRetailConnector()
        slots = connector.get_delivery_slots()
        return {"retailer": retailer, "slots": slots}
    else:
        # Mock for now
        return {"retailer": retailer, "slots": []}
