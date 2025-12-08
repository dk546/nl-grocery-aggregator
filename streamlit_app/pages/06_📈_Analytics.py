"""
Analytics Dashboard Page - Internal event analytics visualization.

This page provides an internal analytics dashboard for viewing event metrics
and recent events. This is a demo/experimental feature for internal use only.
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Any

# Ensure the streamlit_app directory is in the Python path
streamlit_app_dir = Path(__file__).parent.parent
if str(streamlit_app_dir) not in sys.path:
    sys.path.insert(0, str(streamlit_app_dir))

# Add project root to path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import pandas as pd
import streamlit as st

from utils.api_client import get_recent_events, get_event_counts, get_health_status

# Page configuration
st.set_page_config(page_title="Analytics (internal)", page_icon="📈")

# Page header
st.title("📈 Analytics (internal)")
st.caption(
    "Experimental event analytics from Postgres. "
    "This is a demo dashboard – not production analytics."
)

# Optional: show backend/db status at the top
try:
    health = get_health_status()
    if health:
        db_enabled_health = health.get("raw", {}).get("db_enabled", False)
        backend_status = health.get("status", "unknown")
        
        st.markdown(f"**Backend status:** `{backend_status}`")
        st.markdown(
            "✅ Database persistence is enabled."
            if db_enabled_health
            else "⚪ Database persistence is disabled or in fallback mode."
        )
    else:
        st.info("Could not fetch health status. Analytics are best-effort only.")
except Exception:
    st.info("Could not fetch health status. Analytics are best-effort only.")

st.divider()

# Section 1: Event counts (bar chart)
st.subheader("Event counts")

since_hours = st.select_slider(
    "Time window (hours)",
    options=[6, 12, 24, 48, 72, 168],  # 168 = 7 days
    value=24,
)

counts_data = get_event_counts(since_hours=since_hours)

if not counts_data.get("db_enabled", False):
    st.info(
        "Database persistence is disabled or analytics are not available. "
        "No event counts to show."
    )
else:
    counts = counts_data.get("counts", {})
    if not counts:
        st.info("No events recorded in this time window.")
    else:
        # Summary metrics row
        total_events = sum(counts.values())
        searches = counts.get("search_performed", 0)
        cart_adds = counts.get("cart_item_added", 0)
        swaps = counts.get("swap_clicked", 0)
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total events", total_events)
        col2.metric("Searches", searches)
        col3.metric("Cart adds", cart_adds)
        col4.metric("Swaps", swaps)
        
        st.write("")  # Add spacing
        
        counts_df = (
            pd.DataFrame(
                [{"event_type": k, "count": v} for k, v in counts.items()]
            )
            .sort_values("count", ascending=False)
        )
        st.write("Event counts by type:")
        st.dataframe(counts_df, use_container_width=True)
        
        # Simple bar chart using Streamlit
        st.bar_chart(
            counts_df.set_index("event_type")["count"]
        )

st.divider()

# Section 2: Recent events table
st.subheader("Recent events")

limit = st.select_slider(
    "Number of recent events",
    options=[50, 100, 200, 500],
    value=100,
)

events_data = get_recent_events(limit=limit)

if not events_data.get("db_enabled", False):
    st.info(
        "Database persistence is disabled or analytics are not available. "
        "No recent events to show."
    )
else:
    events = events_data.get("events", [])
    if not events:
        st.info("No recent events found.")
    else:
        # Extract unique event types for filtering
        event_types = sorted({e.get("event_type") for e in events if e.get("event_type")})
        
        # Event type filter
        if event_types:
            selected_event_type = st.selectbox(
                "Filter by event type",
                options=["(all)"] + event_types,
                index=0,
            )
        else:
            selected_event_type = "(all)"
        
        # Apply filter
        filtered_events = [
            e for e in events
            if selected_event_type == "(all)" or e.get("event_type") == selected_event_type
        ]
        
        if not filtered_events:
            st.info("No events match this filter.")
        else:
            # Normalize into a DataFrame
            events_df = pd.json_normalize(filtered_events)
            
            # Helper function for payload formatting
            def _format_payload(p: Any) -> str:
                if isinstance(p, dict):
                    try:
                        s = json.dumps(p, ensure_ascii=False, indent=None)
                    except Exception:
                        s = str(p)
                else:
                    s = str(p)
                # Truncate for readability
                return s if len(s) <= 200 else s[:200] + "..."
            
            # Ensure predictable columns: ts, event_type, session_id, payload
            # (payload is dict; convert to short JSON string for display)
            if "payload" in events_df.columns:
                events_df["payload"] = events_df["payload"].apply(_format_payload)
            
            # Select and display columns (use whatever keys exist in the response)
            display_columns = []
            if "ts" in events_df.columns:
                display_columns.append("ts")
            elif "timestamp" in events_df.columns:
                display_columns.append("timestamp")
            
            if "event_type" in events_df.columns:
                display_columns.append("event_type")
            elif "event" in events_df.columns:
                display_columns.append("event")
            
            if "session_id" in events_df.columns:
                display_columns.append("session_id")
            
            if "payload" in events_df.columns:
                display_columns.append("payload")
            
            # Rename columns for display
            rename_map = {
                "ts": "Timestamp",
                "timestamp": "Timestamp",
                "event_type": "Event Type",
                "event": "Event Type",
                "session_id": "Session ID",
                "payload": "Payload",
            }
            
            display_df = events_df[display_columns].rename(columns=rename_map)
            
            st.dataframe(
                display_df,
                use_container_width=True,
            )
            
            # CSV download button
            try:
                csv_data = display_df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="📥 Download recent events as CSV",
                    data=csv_data,
                    file_name="recent_events.csv",
                    mime="text/csv",
                )
            except Exception:
                # Non-blocking: if CSV generation fails, just skip the button
                pass

st.divider()

# Section 3: Explanation / Observations
st.subheader("What can we do with this?")

st.markdown(
    """
This internal dashboard is meant to **illustrate how event data can power analytics**:

- Track how often users search vs. add to cart.
- Monitor whether smart swaps are actually used.
- See how often recipe-based journeys occur.
- Prototype funnels like "search → view swaps → add to cart → checkout".

In a real production setup, these events could feed:

- A more advanced analytics warehouse (e.g. BigQuery, Snowflake).
- Marketing attribution / growth experiments.
- Personalization and recommendations.
"""
)

st.divider()

# Last updated timestamp
st.caption(
    f"Last updated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"
)
