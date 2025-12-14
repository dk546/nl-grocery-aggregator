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

import json
import pandas as pd
import streamlit as st
from datetime import datetime, timezone
from typing import Any

from utils.api_client import get_recent_events, get_event_counts, get_health_status
from ui.styles import load_global_styles
from ui.layout import page_header, section, card, kpi_row
from ui.feedback import show_empty_state
from ui.charts import (
    build_funnel,
    build_time_series,
    build_event_mix_stacked
)

# Inject global CSS styling
load_global_styles()

# Page configuration
st.set_page_config(page_title="Analytics (internal)", page_icon="📈")

# Page header
page_header(
    title="📈 Analytics (internal)",
    subtitle="Experimental event analytics dashboard for internal use only."
)

# Backend/db status (compact, as caption)
try:
    health = get_health_status()
    if health:
        db_enabled_health = health.get("raw", {}).get("db_enabled", False)
        backend_status = health.get("status", "unknown")
        status_text = f"Backend: {backend_status} | " + (
            "✅ Database enabled" if db_enabled_health else "⚪ Database disabled/fallback"
        )
        st.caption(status_text)
    else:
        st.caption("⚠️ Could not fetch health status. Analytics are best-effort only.")
except Exception:
    st.caption("⚠️ Could not fetch health status. Analytics are best-effort only.")

st.divider()

# Time window selector
since_hours = st.select_slider(
    "Time window (hours)",
    options=[6, 12, 24, 48, 72, 168],  # 168 = 7 days
    value=24,
)

# Fetch data
counts_data = get_event_counts(since_hours=since_hours)

# Guard for no data
if not counts_data.get("db_enabled", False):
    show_empty_state(
        title="Analytics not available",
        subtitle="Database persistence is disabled or analytics are not available.",
        action_label="Check system status",
        action_page_path="pages/99_🔧_System_Status.py"
    )
    st.stop()

counts = counts_data.get("counts", {})
if not counts:
    show_empty_state(
        title="No events in this time window",
        subtitle="Try selecting a longer time window or check back later.",
        action_label="Refresh",
        action_page_path=None
    )
    st.stop()

# A) Usage Overview - KPI cards
section("Usage overview")

total_events = sum(counts.values())
searches = counts.get("search_performed", 0)
cart_adds = counts.get("cart_item_added", 0)
exports = counts.get("export_list", 0)
swaps = counts.get("swap_clicked", 0)

# Calculate unique sessions and ads-ready metrics from recent events
try:
    events_data = get_recent_events(limit=500)
    if events_data.get("db_enabled", False):
        events = events_data.get("events", [])
        unique_sessions = len(set(e.get("session_id") for e in events if e.get("session_id"))) if events else 0
        
        # Calculate impressions and sponsored clicks from payload
        impressions = 0
        sponsored_impressions = 0
        sponsored_clicks = counts.get("sponsored_clicked", 0)
        
        for event in events:
            event_type = event.get("event_type") or event.get("event")
            if event_type == "impression_logged":
                impressions += 1
                payload = event.get("payload", {})
                if payload.get("placement") == "sponsored":
                    sponsored_impressions += 1
        
        # Calculate CTR (sponsored clicks / sponsored impressions)
        ctr = (sponsored_clicks / sponsored_impressions * 100) if sponsored_impressions > 0 else 0.0
    else:
        unique_sessions = 0
        impressions = 0
        sponsored_impressions = 0
        sponsored_clicks = 0
        ctr = 0.0
except Exception:
    unique_sessions = 0
    impressions = 0
    sponsored_impressions = 0
    sponsored_clicks = 0
    ctr = 0.0

# KPI row with ads metrics
kpi_row([
    {"label": "Total events", "value": total_events, "icon": "📊"},
    {"label": "Searches", "value": searches, "icon": "🔍"},
    {"label": "Cart adds", "value": cart_adds, "icon": "🛒"},
    {"label": "Impressions", "value": impressions, "icon": "👁️"},
])

# Ads metrics row (sponsored performance)
if impressions > 0 or sponsored_clicks > 0:
    st.markdown("#### Ads performance")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Sponsored impressions", sponsored_impressions)
    with col2:
        st.metric("Sponsored clicks", sponsored_clicks)
    with col3:
        st.metric("CTR", f"{ctr:.2f}%", delta=f"{sponsored_clicks}/{sponsored_impressions}" if sponsored_impressions > 0 else None)

# B) Funnel chart (Search → Add → Export)
section("User journey funnel")

col_funnel, col_ctr = st.columns([3, 1])
with col_funnel:
    with card():
        funnel_steps = [
            ("Search performed", searches),
            ("Item added to cart", cart_adds),
            ("List exported", exports),
        ]
        funnel_chart = build_funnel(funnel_steps)
        st.altair_chart(funnel_chart, use_container_width=True)

# Sponsored CTR mini-metric (optional, only if we have sponsored data)
with col_ctr:
    if sponsored_impressions > 0:
        with card():
            st.metric("Sponsored CTR", f"{ctr:.2f}%")
            st.caption(f"{sponsored_clicks} clicks / {sponsored_impressions} impressions")

# C) Activity over time
section("Activity over time")

# Get recent events and aggregate by hour/day
try:
    events_data = get_recent_events(limit=1000)
    if events_data.get("db_enabled", False) and events_data.get("events"):
        events = events_data.get("events", [])
        
        # Convert to DataFrame
        events_df = pd.json_normalize(events)
        
        if "ts" in events_df.columns:
            events_df["ts"] = pd.to_datetime(events_df["ts"], errors="coerce")
            events_df = events_df.dropna(subset=["ts"])
            
            # Determine time window and aggregate
            if since_hours <= 24:
                # Aggregate by hour
                events_df["time_bucket"] = events_df["ts"].dt.floor("H")
                time_col = "time_bucket"
                time_window = "hour"
            else:
                # Aggregate by day
                events_df["time_bucket"] = events_df["ts"].dt.floor("D")
                time_col = "time_bucket"
                time_window = "day"
            
            # Count events per time bucket
            time_series_df = events_df.groupby(time_col).size().reset_index(name="count")
            time_series_df = time_series_df.sort_values(time_col)
            
            if not time_series_df.empty:
                with card():
                    time_chart = build_time_series(time_series_df, time_col, "count", time_window)
                    st.altair_chart(time_chart, use_container_width=True)
            else:
                st.caption("No time series data available.")
        else:
            st.caption("Timestamp data not available for time series.")
    else:
        st.caption("Event data not available for time series.")
except Exception:
    st.caption("Could not generate time series chart.")

# D) Event mix (stacked bar)
section("Event mix")

with card():
    event_mix_chart = build_event_mix_stacked(counts)
    st.altair_chart(event_mix_chart, use_container_width=True)

# E) Recent events (collapsed, technical/debug) - clearly separated
st.divider()

with st.expander("🔧 Recent events (debug)", expanded=False):
    limit = st.select_slider(
        "Number of events",
        options=[50, 100, 200, 500],
        value=100,
    )
    
    events_data = get_recent_events(limit=limit)
    
    if not events_data.get("db_enabled", False):
        st.info("Database persistence is disabled. No recent events to show.")
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
                    return s if len(s) <= 200 else s[:200] + "..."
                
                if "payload" in events_df.columns:
                    events_df["payload"] = events_df["payload"].apply(_format_payload)
                
                # Select and display columns
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
                
                # Rename columns
                rename_map = {
                    "ts": "Timestamp",
                    "timestamp": "Timestamp",
                    "event_type": "Event Type",
                    "event": "Event Type",
                    "session_id": "Session ID",
                    "payload": "Payload",
                }
                
                display_df = events_df[display_columns].rename(columns=rename_map)
                
                st.dataframe(display_df, use_container_width=True)
                
                # CSV download
                try:
                    csv_data = display_df.to_csv(index=False).encode("utf-8")
                    st.download_button(
                        label="📥 Download as CSV",
                        data=csv_data,
                        file_name="recent_events.csv",
                        mime="text/csv",
                    )
                except Exception:
                    pass

# Last updated timestamp
st.caption(f"Last updated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
