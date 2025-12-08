"""
Tests for analytics API endpoints.

Note: run tests with:
    conda activate supermarkt-env
    pytest
"""

from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_analytics_recent_events_endpoint_ok():
    """
    Test that /analytics/events/recent endpoint responds correctly
    and never raises exceptions, even when DB is disabled.
    """
    resp = client.get("/analytics/events/recent")
    assert resp.status_code == 200
    data = resp.json()
    
    # Verify response structure
    assert "db_enabled" in data
    assert "events" in data
    assert isinstance(data["events"], list)
    
    # Verify db_enabled is a boolean
    assert isinstance(data["db_enabled"], bool)


def test_analytics_recent_events_endpoint_with_limit():
    """
    Test that limit parameter works correctly.
    """
    # Test with default limit
    resp = client.get("/analytics/events/recent")
    assert resp.status_code == 200
    
    # Test with custom limit
    resp = client.get("/analytics/events/recent?limit=50")
    assert resp.status_code == 200
    data = resp.json()
    assert "events" in data
    assert isinstance(data["events"], list)
    
    # Test with max limit
    resp = client.get("/analytics/events/recent?limit=1000")
    assert resp.status_code == 200


def test_analytics_recent_events_endpoint_limit_validation():
    """
    Test that limit parameter validation works (must be between 1 and 1000).
    """
    # Test with limit too low
    resp = client.get("/analytics/events/recent?limit=0")
    assert resp.status_code == 422  # Validation error
    
    # Test with limit too high
    resp = client.get("/analytics/events/recent?limit=1001")
    assert resp.status_code == 422  # Validation error


def test_analytics_event_counts_endpoint_ok():
    """
    Test that /analytics/events/counts endpoint responds correctly
    and never raises exceptions, even when DB is disabled.
    """
    resp = client.get("/analytics/events/counts")
    assert resp.status_code == 200
    data = resp.json()
    
    # Verify response structure
    assert "db_enabled" in data
    assert "since_hours" in data
    assert "counts" in data
    
    # Verify types
    assert isinstance(data["db_enabled"], bool)
    assert isinstance(data["since_hours"], int)
    assert isinstance(data["counts"], dict)


def test_analytics_event_counts_endpoint_with_since_hours():
    """
    Test that since_hours parameter works correctly.
    """
    # Test with default since_hours
    resp = client.get("/analytics/events/counts")
    assert resp.status_code == 200
    data = resp.json()
    assert data["since_hours"] == 24
    
    # Test with custom since_hours
    resp = client.get("/analytics/events/counts?since_hours=12")
    assert resp.status_code == 200
    data = resp.json()
    assert data["since_hours"] == 12
    
    # Test with max since_hours
    resp = client.get("/analytics/events/counts?since_hours=168")
    assert resp.status_code == 200
    data = resp.json()
    assert data["since_hours"] == 168


def test_analytics_event_counts_endpoint_since_hours_validation():
    """
    Test that since_hours parameter validation works (must be between 1 and 168).
    """
    # Test with since_hours too low
    resp = client.get("/analytics/events/counts?since_hours=0")
    assert resp.status_code == 422  # Validation error
    
    # Test with since_hours too high
    resp = client.get("/analytics/events/counts?since_hours=169")
    assert resp.status_code == 422  # Validation error


def test_analytics_endpoints_never_raise_exceptions():
    """
    Ensure analytics endpoints never raise exceptions, even if DB operations fail.
    This is critical for non-blocking analytics behavior.
    """
    # These should all return 200 with safe fallback structures
    # even if DB is disabled or unavailable
    
    resp1 = client.get("/analytics/events/recent")
    assert resp1.status_code == 200
    
    resp2 = client.get("/analytics/events/counts")
    assert resp2.status_code == 200
    
    # Verify both have expected structure
    data1 = resp1.json()
    data2 = resp2.json()
    
    assert "db_enabled" in data1
    assert "events" in data1
    
    assert "db_enabled" in data2
    assert "counts" in data2


def test_analytics_recent_events_response_structure():
    """
    Test the structure of recent events response when DB is enabled or disabled.
    """
    resp = client.get("/analytics/events/recent?limit=10")
    assert resp.status_code == 200
    data = resp.json()
    
    # Should always have these fields
    assert "db_enabled" in data
    assert "events" in data
    
    # If events exist, verify their structure
    if data["events"]:
        for event in data["events"]:
            assert "ts" in event
            assert "event_type" in event
            assert "session_id" in event or event["session_id"] is None
            assert "payload" in event
            assert isinstance(event["payload"], dict)


def test_analytics_event_counts_response_structure():
    """
    Test the structure of event counts response when DB is enabled or disabled.
    """
    resp = client.get("/analytics/events/counts?since_hours=24")
    assert resp.status_code == 200
    data = resp.json()
    
    # Should always have these fields
    assert "db_enabled" in data
    assert "since_hours" in data
    assert "counts" in data
    
    # Verify counts is a dictionary mapping strings to integers
    assert isinstance(data["counts"], dict)
    if data["counts"]:
        for event_type, count in data["counts"].items():
            assert isinstance(event_type, str)
            assert isinstance(count, int)
            assert count >= 0

