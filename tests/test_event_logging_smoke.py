"""
Smoke test for event logging - ensures log_event never raises exceptions.

To run tests:
    conda activate supermarkt-env
    pytest tests/test_event_logging_smoke.py -v
"""

import pytest


def test_event_logging_never_raises():
    """
    Verify that log_event() never raises exceptions, even with invalid inputs.
    
    This is a critical smoke test to ensure analytics failures never break the app.
    """
    from aggregator.events import log_event
    
    # Test with valid inputs
    try:
        log_event("test_event", session_id="abc123", payload={"x": 1})
    except Exception as exc:
        pytest.fail(f"log_event should not raise, but raised: {exc}")
    
    # Test with None values
    try:
        log_event("test_event", session_id=None, payload=None)
    except Exception as exc:
        pytest.fail(f"log_event should not raise with None values, but raised: {exc}")
    
    # Test with invalid payload (non-dict)
    try:
        log_event("test_event", session_id="test", payload="not a dict")
    except Exception as exc:
        pytest.fail(f"log_event should not raise with invalid payload, but raised: {exc}")
    
    # Test with empty event name
    try:
        log_event("", session_id="test", payload={})
    except Exception as exc:
        pytest.fail(f"log_event should not raise with empty event name, but raised: {exc}")

