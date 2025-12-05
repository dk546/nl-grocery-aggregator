"""
Internal event logging utility for tracking key user actions.

This module provides lightweight, non-blocking event logging for analytics purposes.
Events are logged as JSON lines to a local file for later processing/analysis.

Note: This is a simple MVP implementation. In production, this should be replaced
with a proper logging infrastructure (e.g., structured logging to a database,
event streaming service, or analytics platform).

Key principles:
- Non-blocking: Logging failures should never break the application
- Structured: Events are logged as JSON for easy parsing
- Lightweight: Minimal overhead on request processing
"""

import json
import time
from typing import Any, Dict, Optional

# Event log file path (relative to project root)
# In production, this should be configurable or use proper logging infrastructure
EVENT_LOG_FILE = "events.log"


def log_event(
    event: str,
    session_id: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Log an event as a JSON line.
    
    Events are logged in a structured format suitable for later analysis:
    {
        "ts": timestamp (Unix time),
        "event": event name (e.g., "search_performed", "cart_items_added"),
        "session_id": session identifier (if available),
        "payload": event-specific data dictionary
    }
    
    Args:
        event: Event name/type (e.g., "search_performed", "cart_items_added")
        session_id: Session identifier (optional)
        payload: Event-specific data dictionary (optional)
    
    Examples:
        >>> log_event("search_performed", session_id="abc123", payload={"query": "melk", "result_count": 10})
        >>> log_event("cart_items_added", session_id="abc123", payload={"retailer": "ah", "quantity": 2})
    
    Note:
        This function is designed to fail silently. If logging fails for any reason
        (file permission errors, disk full, etc.), the exception is caught and ignored
        to ensure analytics never break the application.
    """
    try:
        record = {
            "ts": time.time(),
            "event": event,
            "session_id": session_id,
            "payload": payload or {},
        }
        
        # Write as JSON line (one JSON object per line, UTF-8 encoded)
        line = json.dumps(record, ensure_ascii=False)
        
        with open(EVENT_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        # Fail silently; analytics should never break the app
        # In production, you might want to log this to application logs at DEBUG level
        pass

