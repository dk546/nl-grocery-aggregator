"""
Health Insights Page - Health Tracking and Analytics Dashboard.

This page provides insights into the healthiness of grocery choices and tracks
health-related metrics based on the current basket contents from the backend.
"""

import os
import sys
from pathlib import Path

# Ensure the streamlit_app directory is in the Python path
streamlit_app_dir = Path(__file__).parent.parent
if str(streamlit_app_dir) not in sys.path:
    sys.path.insert(0, str(streamlit_app_dir))

# Add project root to path to import api.config
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import pandas as pd
import streamlit as st

from utils.session import get_or_create_session_id
from utils.api_client import view_cart_backend
from utils.profile import HOUSEHOLD_PROFILES, get_profile_by_key
from ui.style import inject_global_css, section_header, pill_tag, image_card, render_footer

# Inject global CSS styling
inject_global_css()

# Get session ID (shared across pages)
session_id = get_or_create_session_id()

# Fetch basket from backend using shared session
try:
    cart_data = view_cart_backend(session_id)
    basket_items = cart_data.get("items", []) if cart_data else []
except Exception as e:
    st.error(f"Could not load your basket: {e}")
    basket_items = []

# Guard for "no basket / no health data"
if not basket_items:
    section_header(
        title="Health insights",
        eyebrow="GENTLE NUTRITION NUDGES",
        help_text="Add some items to your basket first to see a simple health breakdown."
    )
    st.info(
        "Once you've added items to your basket, we'll show how many are healthier, "
        "neutral or less healthy, plus a few gentle swap suggestions."
    )
    st.stop()

# Convert basket items to DataFrame for analysis
df = pd.DataFrame(basket_items)

# Ensure health_tag column exists (fill missing with "unknown")
if "health_tag" not in df.columns:
    df["health_tag"] = None
df["health_tag"] = df["health_tag"].fillna("unknown")

# Calculate total metrics
total_items = int(df["quantity"].sum()) if "quantity" in df.columns else len(df)
total_spend = float(cart_data.get("total_price", 0.0)) if cart_data else 0.0

# Health tag counts
healthy_count = len(df[df["health_tag"] == "healthy"])
unhealthy_count = len(df[df["health_tag"] == "unhealthy"])
neutral_count = len(df[df["health_tag"] == "neutral"])
unknown_count = len(df[df["health_tag"] == "unknown"])

# Calculate health percentages
# healthy_pct_all: percentage of all items that are healthy (including unknown in denominator)
healthy_pct_all = (healthy_count / len(df) * 100) if len(df) > 0 else 0
# healthy_pct_known: percentage of items with known health tags that are healthy (excluding unknown from denominator)
known_health_items = len(df) - unknown_count
healthy_pct_known = (healthy_count / known_health_items * 100) if known_health_items > 0 else 0

# Page header + household caption
section_header(
    title="Health insights for your basket",
    eyebrow="GENTLE NUTRITION NUDGES",
    help_text="A simple, visual breakdown of healthier, neutral and less healthy items."
)

profile_key = st.session_state.get("household_profile_key")
profile = HOUSEHOLD_PROFILES.get(profile_key) if profile_key else None
if profile:
    st.caption(
        f"For your **{profile.label.lower()}** household, use this as a rough guide when planning meals."
    )

# Metrics band (top row)
metrics_cols = st.columns(3, gap="large")
with metrics_cols[0]:
    st.metric("Healthy items", healthy_count)
with metrics_cols[1]:
    st.metric("Neutral items", neutral_count)
with metrics_cols[2]:
    st.metric("Less healthy", unhealthy_count)

st.divider()

# Main content with side column
main_col, side_col = st.columns([2.2, 1], gap="large")

with main_col:
    section_header(
        title="Basket health breakdown",
        eyebrow="OVERVIEW",
        help_text="How your current basket splits into healthier, neutral, and less healthy items."
    )
    
    # Chart card
    st.markdown('<div class="nlga-card">', unsafe_allow_html=True)
    
    # Create health breakdown DataFrame for chart
    tag_counts = df["health_tag"].value_counts()
    health_chart_data = pd.DataFrame({
        "Category": tag_counts.index,
        "Count": tag_counts.values
    })
    
    # Map health tags to friendly names for display
    health_chart_data["Category"] = health_chart_data["Category"].map({
        "healthy": "🥦 Healthy",
        "unhealthy": "⚠️ Less Healthy",
        "neutral": "⚪ Neutral",
        "unknown": "❔ Unknown"
    }).fillna(health_chart_data["Category"])
    
    st.bar_chart(health_chart_data.set_index("Category"), width='stretch')
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Items by health tag – optional detailed view
    st.markdown("### Items by health tag")
    st.caption("Use this to spot quick wins for swaps and rebalancing your basket.")
    
    # Detailed breakdown in expander to reduce scrolling
    with st.expander("Show detailed item list"):
        st.markdown('<div class="nlga-card">', unsafe_allow_html=True)
        
        # Create a readable item list with health tags
        if len(df) > 0:
            # Display items grouped by health tag
            for health_tag in ["healthy", "neutral", "unhealthy", "unknown"]:
                tag_items = df[df["health_tag"] == health_tag]
                if len(tag_items) > 0:
                    tag_display = {
                        "healthy": "🥦 Healthy",
                        "unhealthy": "⚠️ Less Healthy",
                        "neutral": "⚪ Neutral",
                        "unknown": "❔ Unknown"
                    }.get(health_tag, health_tag.capitalize())
                    
                    st.markdown(f"#### {tag_display}")
                    
                    for idx, row in tag_items.iterrows():
                        item_name = row.get("name", "Unknown")
                        quantity = row.get("quantity", 1)
                        health_tag_value = row.get("health_tag", "unknown")
                        
                        col_name, col_tag = st.columns([3, 1])
                        with col_name:
                            st.markdown(f"- {item_name} (Qty: {quantity})")
                        with col_tag:
                            if health_tag_value and health_tag_value != "unknown":
                                st.markdown(pill_tag(health_tag_value.capitalize()), unsafe_allow_html=True)
                    
                    st.markdown("---")
            
            # Also show aggregate summary table
            if "line_total" in df.columns:
                df["line_total"] = pd.to_numeric(df["line_total"], errors="coerce").fillna(0)
                health_summary = df.groupby("health_tag").agg({
                    "quantity": "sum",
                    "line_total": ["sum", "mean"]
                }).round(2)
                health_summary.columns = ["Total Quantity", "Total Spend (€)", "Avg. Item Price (€)"]
            else:
                health_summary = df.groupby("health_tag")["quantity"].sum().to_frame("Total Quantity") if "quantity" in df.columns else df.groupby("health_tag").size().to_frame("Count")
            
            # Rename index for better display
            health_summary.index = health_summary.index.map({
                "healthy": "🥦 Healthy",
                "unhealthy": "⚠️ Less Healthy",
                "neutral": "⚪ Neutral",
                "unknown": "❔ Unknown"
            })
            
            st.markdown("#### Summary Table")
            st.dataframe(health_summary, use_container_width=True)
        
        st.markdown('</div>', unsafe_allow_html=True)

with side_col:
    # Small image card
    image_card(
        "health_side",
        caption="Healthy, neutral, and less healthy items at a glance."
    )
    
    # Quick summary card
    section_header(
        title="Quick summary",
        eyebrow="SNAPSHOT",
        help_text="High-level view of your basket's balance."
    )
    st.markdown('<div class="nlga-card nlga-card--sidebar">', unsafe_allow_html=True)
    st.caption(f"Healthy items: {healthy_count}")
    st.caption(f"Neutral items: {neutral_count}")
    st.caption(f"Less healthy: {unhealthy_count}")
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Small swaps card – reuse existing suggestions logic
    if unhealthy_count > 0:
        unhealthy_items_df = df[df["health_tag"] == "unhealthy"].head(5)
        
        section_header(
            title="Small swaps, big impact",
            eyebrow="SUGGESTED CHANGES",
            help_text="Items where a slightly healthier alternative is available."
        )
        
        for idx, row in unhealthy_items_df.iterrows():
            item_name = row.get("name", "Unknown")
            retailer = row.get("retailer", "Unknown")
            retailer_display = retailer.title() if retailer else "Unknown"
            
            st.markdown('<div class="nlga-card nlga-card--sidebar">', unsafe_allow_html=True)
            st.markdown(f"**{item_name}** → explore alternatives")
            st.caption(f"From {retailer_display}. Consider healthier swaps in Search & Compare.")
            st.markdown('</div>', unsafe_allow_html=True)
        
        if unhealthy_count > 5:
            st.caption(f"... and {unhealthy_count - 5} more item(s) could be explored for alternatives.")
    
    # Plus teaser
    st.markdown("---")
    st.markdown('<div class="nlga-card nlga-card--sidebar">', unsafe_allow_html=True)
    st.markdown("#### ✨ NLGA Plus (concept)")
    st.caption(
        "Imagine seeing weekly trends, deeper nutrition scores, and meal ideas based on what you usually buy. "
        "That's where NLGA Plus could go."
    )
    st.markdown('</div>', unsafe_allow_html=True)

# Disclaimer at the bottom
st.caption("""
⚠️ These health insights are approximate and based on simple tagging rules.
They are not nutritional or medical advice. Always consider your own dietary needs.
""")

# Footer
render_footer()
