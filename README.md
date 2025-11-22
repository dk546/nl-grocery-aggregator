# NL Grocery Aggregator (MVP)

An Instacart-inspired backend prototype for the Dutch market.

The goal is to let users search and compare products across multiple supermarkets
(Albert Heijn, Jumbo, Picnic), maintain a virtual cart, and expose everything
via a FastAPI API. The project is focused on **learning API integrations,
aggregators, and backend design**, not on production readiness.

## Features (Sprint 1 scope)

- Unified product search across multiple retailers (starting with those that have usable APIs/wrappers)
- Normalised product schema (name, price, retailer, image URL, etc.)
- Basic "healthy / neutral / unhealthy" tagging based on simple rules
- In-memory virtual cart per session
- FastAPI backend with endpoints for search, cart and delivery slots
- Sandbox scripts to experiment with each retailer API directly

## Project Structure

```text
aggregator/
  connectors/
  cart.py
  search.py
  health.py
  models.py

api/
  main.py

sandbox/
  sandbox_ah.py
  sandbox_jumbo.py
  sandbox_picnic.py

tests/
  ...

Setup
# 1. create and activate a virtual environment (conda or venv)
pip install -r requirements.txt


Create a .env file in the project root for Picnic:

PICNIC_USERNAME=your_email_here
PICNIC_PASSWORD=your_password_here
PICNIC_COUNTRY_CODE=NL

Running sandboxes
python sandbox/sandbox_picnic.py
python sandbox/sandbox_ah.py
python sandbox/sandbox_jumbo.py

FastAPI (coming in later steps)
uvicorn api.main:app --reload


⚠️ This project uses unofficial wrappers around supermarket APIs.
It is for education and prototyping only. Respect retailer terms of use,
don’t hammer their servers, and do not deploy without proper legal review.


We’ll extend this later when the FastAPI endpoints and connectors are in.

---

## 4️⃣ Sandbox scripts

Now let’s add the three sandbox files.

> These are **just to learn the data shapes**. They don’t have to be perfect yet.

### 4.1 `sandbox/__init__.py`

If it’s empty, that’s fine; just keep it there.

---

### 4.2 `sandbox/sandbox_picnic.py`

This one should definitely work if credentials are correct.

```python
"""
Sandbox: test python-picnic-api.

Run:
    python sandbox/sandbox_picnic.py
"""

import os
from pprint import pprint

from dotenv import load_dotenv
from python_picnic_api import PicnicAPI


def get_picnic_client() -> PicnicAPI:
    """Create an authenticated PicnicAPI client from .env variables."""
    # Load from project-root .env
    load_dotenv()

    username = os.getenv("PICNIC_USERNAME")
    password = os.getenv("PICNIC_PASSWORD")
    country_code = os.getenv("PICNIC_COUNTRY_CODE", "NL")

    if not username or not password:
        raise RuntimeError(
            "PICNIC_USERNAME and PICNIC_PASSWORD must be set in .env at project root."
        )

    return PicnicAPI(username=username, password=password, country_code=country_code)


def test_search(query: str = "melk") -> None:
    print(f"\n=== Picnic search for {query!r} ===")
    client = get_picnic_client()
    results = client.search(query)

    if not results:
        print("No results from Picnic search.")
        return

    print(f"Result groups: {len(results)}")

    group = results[0]
    items = group.get("items", [])
    print(f"Items in first group: {len(items)} (showing up to 5)\n")

    for item in items[:5]:
        # display_price is in cents
        price_eur = item.get("display_price", 0) / 100
        print(f"- {item.get('name')}  |  €{price_eur:.2f}")
        pprint(item)
        print("-" * 80)


def test_delivery_slots() -> None:
    print("\n=== Picnic delivery slots ===")
    client = get_picnic_client()
    slots = client.get_delivery_slots()

    if not slots:
        print("No delivery slots returned.")
        return

    print(f"Got {len(slots)} slots (showing up to 5):\n")
    for slot in slots[:5]:
        pprint(slot)
        print("-" * 80)


if __name__ == "__main__":
    try:
        test_search()
        test_delivery_slots()
    except Exception as exc:
        print(f"Error while testing Picnic API: {exc}")