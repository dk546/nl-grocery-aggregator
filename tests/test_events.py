"""
Tests for the event logging utility.
"""

import json
import os
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from aggregator.events import EVENT_LOG_FILE, log_event


class TestEventLogging:
    """Test event logging functionality."""
    
    def test_log_event_writes_valid_json(self):
        """Test that log_event writes valid JSON lines."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_log_file = Path(tmpdir) / "test_events.log"
            
            with patch("aggregator.events.EVENT_LOG_FILE", str(test_log_file)):
                # Log a test event
                log_event(
                    "test_event",
                    session_id="test_session_123",
                    payload={"key": "value", "number": 42},
                )
                
                # Verify file was created
                assert test_log_file.exists()
                
                # Read and parse the logged line
                with open(test_log_file, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    assert len(lines) == 1
                    
                    # Parse JSON
                    record = json.loads(lines[0].strip())
                    
                    # Verify structure
                    assert "ts" in record
                    assert "event" in record
                    assert "session_id" in record
                    assert "payload" in record
                    
                    # Verify values
                    assert record["event"] == "test_event"
                    assert record["session_id"] == "test_session_123"
                    assert record["payload"]["key"] == "value"
                    assert record["payload"]["number"] == 42
                    
                    # Verify timestamp is recent (within last 5 seconds)
                    current_time = time.time()
                    assert abs(record["ts"] - current_time) < 5
    
    def test_log_event_handles_none_session_id(self):
        """Test that log_event handles None session_id."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_log_file = Path(tmpdir) / "test_events.log"
            
            with patch("aggregator.events.EVENT_LOG_FILE", str(test_log_file)):
                log_event("test_event", session_id=None, payload={"test": True})
                
                with open(test_log_file, "r", encoding="utf-8") as f:
                    record = json.loads(f.readline().strip())
                    assert record["session_id"] is None
    
    def test_log_event_handles_empty_payload(self):
        """Test that log_event handles empty/None payload."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_log_file = Path(tmpdir) / "test_events.log"
            
            with patch("aggregator.events.EVENT_LOG_FILE", str(test_log_file)):
                log_event("test_event", session_id="test", payload=None)
                
                with open(test_log_file, "r", encoding="utf-8") as f:
                    record = json.loads(f.readline().strip())
                    assert record["payload"] == {}
    
    def test_log_event_fails_silently_on_error(self):
        """Test that log_event doesn't raise exceptions on file errors."""
        # Mock open to raise an exception
        with patch("builtins.open", side_effect=PermissionError("Access denied")):
            # Should not raise
            log_event("test_event", session_id="test", payload={"test": True})
        
        # Mock json.dumps to raise an exception
        with patch("json.dumps", side_effect=Exception("JSON error")):
            # Should not raise
            log_event("test_event", session_id="test", payload={"test": True})
    
    def test_log_event_appends_multiple_events(self):
        """Test that log_event appends multiple events correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_log_file = Path(tmpdir) / "test_events.log"
            
            with patch("aggregator.events.EVENT_LOG_FILE", str(test_log_file)):
                # Log multiple events
                log_event("event1", session_id="test", payload={"num": 1})
                log_event("event2", session_id="test", payload={"num": 2})
                log_event("event3", session_id="test", payload={"num": 3})
                
                # Verify all events were logged
                with open(test_log_file, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    assert len(lines) == 3
                    
                    # Verify each line is valid JSON
                    for i, line in enumerate(lines, 1):
                        record = json.loads(line.strip())
                        assert record["event"] == f"event{i}"
                        assert record["payload"]["num"] == i

