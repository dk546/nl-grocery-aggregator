"""
Analytics router for event tracking and metrics endpoints.

This router provides endpoints for querying analytics events:
- GET /analytics/events/recent - Get recent events
- GET /analytics/events/counts - Get event type counts

All endpoints are designed to fail gracefully if the database is disabled
or encounters errors, returning empty data rather than raising exceptions.
"""

import json
import logging
from typing import Any, Dict

from fastapi import APIRouter, Query

from aggregator.db import db_is_enabled, db_get_recent_events, db_get_event_counts

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get(
    "/events/recent",
    summary="Get recent events",
    description="Retrieve the most recent analytics events from the database.",
)
def get_recent_events(
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of events to return")
) -> Dict[str, Any]:
    """
    Get the most recent analytics events.
    
    Args:
        limit: Maximum number of events to return (default: 100, max: 1000)
        
    Returns:
        Dictionary with:
        - db_enabled: Boolean indicating if database is enabled
        - events: List of event dictionaries with ts, event_type, session_id, payload
        
    Example response (DB enabled):
    {
        "db_enabled": true,
        "events": [
            {
                "ts": "2024-01-15T10:30:00.123456",
                "event_type": "search_performed",
                "session_id": "abc123",
                "payload": {"query": "melk", "retailers": ["ah", "jumbo"], "result_count": 10}
            }
        ]
    }
    
    Example response (DB disabled):
    {
        "db_enabled": false,
        "events": []
    }
    """
    try:
        db_enabled = db_is_enabled()
        
        if not db_enabled:
            return {
                "db_enabled": False,
                "events": [],
            }
        
        events = db_get_recent_events(limit=limit)
        
        # Convert EventRow objects to dictionaries
        events_list = []
        for event in events:
            payload_dict = None
            if event.payload:
                try:
                    payload_dict = json.loads(event.payload)
                except Exception as e:
                    logger.debug(f"Failed to parse event payload as JSON: {e}")
                    payload_dict = {"raw": event.payload}
            
            events_list.append({
                "ts": event.ts.isoformat() if hasattr(event.ts, "isoformat") else str(event.ts),
                "event_type": event.event_type,
                "session_id": event.session_id,
                "payload": payload_dict or {},
            })
        
        return {
            "db_enabled": True,
            "events": events_list,
        }
    except Exception as e:
        logger.debug(f"Error in get_recent_events: {e}")
        # Return safe fallback on any error
        return {
            "db_enabled": False,
            "events": [],
        }


@router.get(
    "/events/counts",
    summary="Get event type counts",
    description="Get counts of events by type over the last N hours.",
)
def get_event_counts(
    since_hours: int = Query(24, ge=1, le=168, description="Number of hours to look back (default: 24, max: 168)")
) -> Dict[str, Any]:
    """
    Get event type counts over the last N hours.
    
    Args:
        since_hours: Number of hours to look back (default: 24, max: 168 = 7 days)
        
    Returns:
        Dictionary with:
        - db_enabled: Boolean indicating if database is enabled
        - since_hours: Number of hours queried
        - counts: Dictionary mapping event_type to count
        
    Example response (DB enabled):
    {
        "db_enabled": true,
        "since_hours": 24,
        "counts": {
            "search_performed": 120,
            "cart_item_added": 40,
            "cart_item_removed": 5,
            "swap_clicked": 3
        }
    }
    
    Example response (DB disabled):
    {
        "db_enabled": false,
        "since_hours": 24,
        "counts": {}
    }
    """
    try:
        db_enabled = db_is_enabled()
        
        if not db_enabled:
            return {
                "db_enabled": False,
                "since_hours": since_hours,
                "counts": {},
            }
        
        counts = db_get_event_counts(since_hours=since_hours)
        
        return {
            "db_enabled": True,
            "since_hours": since_hours,
            "counts": counts,
        }
    except Exception as e:
        logger.debug(f"Error in get_event_counts: {e}")
        # Return safe fallback on any error
        return {
            "db_enabled": False,
            "since_hours": since_hours,
            "counts": {},
        }

