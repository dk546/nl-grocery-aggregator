# aggregator/events.py
"""
Event logging for NL Grocery Aggregator.

Responsibilities:
- Provide a single log_event(...) function that:
  - Tries to write events to the DB via db_log_event() when DB is enabled.
  - Always writes a JSONL record to events.log for backward compatibility.
  - Never raises exceptions (analytics are strictly non-blocking).

- Provide small helper functions for common event types:
  - log_search_performed(...)
  - log_cart_items_added(...)
  - log_cart_items_removed(...)
  - log_swap_clicked(...)
  - log_recipe_viewed(...)
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .db import db_is_enabled, db_log_event

logger = logging.getLogger(__name__)

# Keep file-based MVP behavior: JSONL file with one event per line.
# If you previously had a different path, adjust this constant to match.
EVENT_LOG_FILE = Path("events.log")


def _ensure_log_file_directory() -> None:
    """
    Ensure the directory for EVENT_LOG_FILE exists.
    Swallow all exceptions to keep logging non-blocking.
    """
    try:
        EVENT_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        # Non-critical: if this fails, we'll try writing anyway and swallow errors later.
        pass


def _write_to_file(record: Dict[str, Any]) -> None:
    """
    Append a single JSON record to events.log as JSONL.
    Never raise exceptions.
    """
    try:
        _ensure_log_file_directory()
        with EVENT_LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as exc:
        # Last-resort: log at debug level, never raise.
        logger.debug("Failed to write event to file fallback: %s", exc)


def log_event(
    event: str,
    session_id: Optional[str],
    payload: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Core event logger.

    Behavior:
    - Build a record with keys: ts, event, session_id, payload.
      This preserves the original file-based structure.
    - If db_is_enabled() is True, attempt to log to DB via db_log_event().
      Any DB error is swallowed and we still write to file.
    - Always write the JSONL record to events.log for debugging / backward compatibility.
    - Never raise exceptions.
    """
    ts = datetime.now(timezone.utc).isoformat()
    payload = payload or {}

    record = {
        "ts": ts,
        "event": event,
        "session_id": session_id,
        "payload": payload,
    }

    # 1) Try DB first (if enabled)
    if db_is_enabled():
        try:
            db_log_event(
                event_type=event,
                session_id=session_id,
                payload=payload,
            )
        except Exception as exc:
            # DB failures must never break the app; log at debug and continue.
            logger.debug("db_log_event failed (event=%s): %s", event, exc)

    # 2) Always write to file fallback
    _write_to_file(record)


# ---------------------------------------------------------------------------
# Helper functions for common event types
# ---------------------------------------------------------------------------

def log_search_performed(
    session_id: Optional[str],
    query: str,
    retailer_codes: List[str],
    result_count: int,
) -> None:
    """
    Log a search_performed event.

    payload:
    {
        "query": "...",
        "retailers": ["ah", "jumbo", ...],
        "result_count": 42
    }
    """
    payload = {
        "query": query,
        "retailers": retailer_codes,
        "result_count": result_count,
    }
    log_event("search_performed", session_id, payload)


def log_cart_items_added(
    session_id: Optional[str],
    retailer: str,
    count: int,
    item_ids: Optional[List[str]] = None,
) -> None:
    """
    Log a cart_item_added event.

    payload:
    {
        "retailer": "ah",
        "count": 3,
        "item_ids": ["sku1", "sku2", ...]  # optional
    }
    """
    payload = {
        "retailer": retailer,
        "count": count,
    }
    if item_ids is not None:
        payload["item_ids"] = item_ids

    log_event("cart_item_added", session_id, payload)


def log_cart_items_removed(
    session_id: Optional[str],
    retailer: Optional[str],
    count: int,
    item_ids: Optional[List[str]] = None,
) -> None:
    """
    Log an item_removed event (or multiple items removed at once).

    payload:
    {
        "retailer": "ah" or None,
        "count": 1,
        "item_ids": ["sku1", ...]  # optional
    }
    """
    payload = {
        "retailer": retailer,
        "count": count,
    }
    if item_ids is not None:
        payload["item_ids"] = item_ids

    log_event("item_removed", session_id, payload)


def log_cart_cleared(
    session_id: Optional[str],
    previous_count: int,
) -> None:
    """
    Log a cart_cleared event.

    payload:
    {
        "previous_count": 12
    }
    """
    payload = {
        "previous_count": previous_count,
    }
    log_event("cart_cleared", session_id, payload)


def log_swap_clicked(
    session_id: Optional[str],
    from_item_id: str,
    to_item_id: str,
    retailer: Optional[str],
    savings_amount: Optional[float],
    health_delta: Optional[float],
) -> None:
    """
    Log a swap_clicked event.

    payload:
    {
        "retailer": "ah" or None,
        "from_item_id": "...",
        "to_item_id": "...",
        "savings_amount": 0.75,      # € saved, optional
        "health_delta": 2.5          # health score improvement, optional
    }
    """
    payload: Dict[str, Any] = {
        "retailer": retailer,
        "from_item_id": from_item_id,
        "to_item_id": to_item_id,
    }
    if savings_amount is not None:
        payload["savings_amount"] = savings_amount
    if health_delta is not None:
        payload["health_delta"] = health_delta

    log_event("swap_clicked", session_id, payload)


def log_recipe_viewed(
    session_id: Optional[str],
    recipe_id: str,
    recipe_name: str,
    associated_items_count: Optional[int] = None,
) -> None:
    """
    Log a recipe_viewed event.

    payload:
    {
        "recipe_id": "...",
        "recipe_name": "...",
        "associated_items_count": 7  # optional
    }
    """
    payload: Dict[str, Any] = {
        "recipe_id": recipe_id,
        "recipe_name": recipe_name,
    }
    if associated_items_count is not None:
        payload["associated_items_count"] = associated_items_count

    log_event("recipe_viewed", session_id, payload)


def log_recipe_planned(
    session_id: Optional[str],
    recipe_id: str,
    title: str,
) -> None:
    """
    Log a recipe_planned event.

    payload:
    {
        "recipe_id": "...",
        "title": "..."
    }
    """
    payload: Dict[str, Any] = {
        "recipe_id": recipe_id,
        "title": title,
    }

    log_event("recipe_planned", session_id, payload)


def log_meal_planned_on_day(
    session_id: Optional[str],
    recipe_id: str,
    day: str,
) -> None:
    """
    Log a meal_planned_on_day event.

    payload:
    {
        "recipe_id": "...",
        "day": "Mon"  # or other day of week
    }
    """
    payload: Dict[str, Any] = {
        "recipe_id": recipe_id,
        "day": day,
    }

    log_event("meal_planned_on_day", session_id, payload)


def log_meal_plan_sent_to_cart(
    session_id: Optional[str],
    recipe_count: int,
    total_estimated_price_eur: float,
) -> None:
    """
    Log a meal_plan_sent_to_cart event.

    payload:
    {
        "recipe_count": 5,
        "total_estimated_price_eur": 25.50
    }
    """
    payload: Dict[str, Any] = {
        "recipe_count": recipe_count,
        "total_estimated_price_eur": total_estimated_price_eur,
    }

    log_event("meal_plan_sent_to_cart", session_id, payload)
