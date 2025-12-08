"""
Tests for event logging and database integration.

These tests verify that:
- Event logging works with and without DATABASE_URL
- DB functions fail gracefully when DB is disabled
- Events are logged without breaking the application

To run tests:
    conda activate supermarkt-env
    pytest tests/test_events_db.py -v
"""

import os
import pytest
from unittest.mock import patch, MagicMock


def test_db_is_enabled_without_database_url():
    """Test that db_is_enabled() returns False when DATABASE_URL is not set."""
    # Temporarily unset DATABASE_URL if it exists
    original_value = os.environ.pop("DATABASE_URL", None)
    try:
        # Reload the module to pick up the change
        import importlib
        from aggregator import db
        importlib.reload(db)
        
        assert db.db_is_enabled() is False
    finally:
        # Restore original value
        if original_value:
            os.environ["DATABASE_URL"] = original_value
        # Reload module again
        import importlib
        from aggregator import db
        importlib.reload(db)


def test_db_get_recent_events_without_db():
    """Test that db_get_recent_events() returns empty list when DB is disabled."""
    with patch("aggregator.db.db_is_enabled", return_value=False):
        from aggregator.db import db_get_recent_events
        
        result = db_get_recent_events(limit=100)
        assert result == []


def test_db_get_event_counts_without_db():
    """Test that db_get_event_counts() returns empty dict when DB is disabled."""
    with patch("aggregator.db.db_is_enabled", return_value=False):
        from aggregator.db import db_get_event_counts
        
        result = db_get_event_counts(since_hours=24)
        assert result == {}


def test_log_event_never_raises():
    """Test that log_event() never raises exceptions, even on errors."""
    from aggregator.events import log_event
    
    # Should not raise even with invalid inputs or when DB/file operations fail
    try:
        log_event("test_event", session_id=None, payload=None)
        log_event("test_event", session_id="test", payload={"key": "value"})
    except Exception as e:
        pytest.fail(f"log_event() raised an exception: {e}")


def test_log_event_helper_functions():
    """Test that helper functions for common event types work."""
    from aggregator.events import (
        log_search_performed,
        log_cart_items_added,
        log_cart_items_removed,
        log_cart_cleared,
        log_swap_clicked,
        log_recipe_viewed,
    )
    
    # These should all work without raising
    try:
        log_search_performed("session123", "melk", ["ah", "jumbo"], 10)
        log_cart_items_added("session123", "ah", 2, item_ids=["prod1", "prod2"])
        log_cart_items_removed("session123", "ah", 1, item_ids=["prod1"])
        log_cart_cleared("session123", previous_count=5)
        log_swap_clicked(
            "session123",
            from_item_id="prod1",
            to_item_id="prod2",
            retailer="ah",
            savings_amount=2.50,
            health_delta=1.5,
        )
        log_recipe_viewed("session123", "recipe1", "Pasta Carbonara", associated_items_count=5)
    except Exception as e:
        pytest.fail(f"Event helper function raised an exception: {e}")


def test_db_log_event_handles_errors_gracefully():
    """Test that db_log_event() handles errors without raising."""
    from aggregator import db
    
    # Mock db_is_enabled to return True
    with patch.object(db, "db_is_enabled", return_value=True):
        with patch.object(db, "get_db_session") as mock_session:
            # Simulate a database error
            mock_session.side_effect = Exception("Database connection failed")
            
            # Should not raise
            try:
                db.db_log_event("test_event", "session123", {"key": "value"})
            except Exception as e:
                pytest.fail(f"db_log_event() raised an exception: {e}")


@pytest.mark.skipif(
    os.getenv("DATABASE_URL") is None,
    reason="DATABASE_URL not set - skipping integration test"
)
def test_db_log_event_with_real_db():
    """Integration test: verify events can be logged to database when available."""
    from aggregator.db import db_is_enabled, db_log_event, db_get_recent_events
    
    if not db_is_enabled():
        pytest.skip("Database not enabled - skipping integration test")
    
    # Log a test event
    db_log_event(
        event_type="test_event",
        session_id="test_session_integration",
        payload={"test": "data"},
    )
    
    # Try to retrieve it (may not appear immediately due to transaction timing)
    # This is just a smoke test - we're verifying no exceptions are raised
    events = db_get_recent_events(limit=10)
    assert isinstance(events, list)  # Should return a list, even if empty

