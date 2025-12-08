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
import altair as alt

from utils.session import get_or_create_session_id
from utils.api_client import view_cart_backend
from utils.profile import HOUSEHOLD_PROFILES, get_profile_by_key
from utils.preferences import (
    get_user_preferences_from_session,
    PREFERENCE_HEALTH_FIRST,
    PREFERENCE_BUDGET_FIRST,
)
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

# Calculate Basket Health Score (0-100)
# Note: "less healthy" is the unhealthy_count in the scoring model
score_raw = (
    healthy_count * 20 +
    neutral_count * 5 -
    unhealthy_count * 15
)
# Normalize to 0-100 range
score = max(0, min(100, int(score_raw)))

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

# Basket Health Score display
st.subheader("Basket Health Score")

if score >= 80:
    color = "🟢"
    label = "Excellent"
elif score >= 60:
    color = "🟡"
    label = "Good"
elif score >= 40:
    color = "🟠"
    label = "Needs improvement"
else:
    color = "🔴"
    label = "Unhealthy"

st.markdown(f"### {color} {score}/100 — **{label}**")

# Optional tip based on score
if score < 60:
    st.info("Try swapping a few neutral items for healthier ones to improve your score.")
elif score == 100:
    st.success("Perfect score! Your basket is very healthy.")

st.divider()

profile_key = st.session_state.get("household_profile_key")
profile = HOUSEHOLD_PROFILES.get(profile_key) if profile_key else None
if profile:
    st.caption(
        f"For your **{profile.label.lower()}** household, use this as a rough guide when planning meals."
    )

# Get user preferences for personalized messaging
prefs = get_user_preferences_from_session()

# Preference-aware narrative box
with st.container():
    if prefs.health_focus == PREFERENCE_HEALTH_FIRST:
        st.info(
            "You've told us you care most about **healthier choices**. "
            "Use this page to reduce the number of less healthy items in your basket and increase healthy ones over time."
        )
    elif prefs.health_focus == PREFERENCE_BUDGET_FIRST:
        st.info(
            "You've told us you care most about **staying on budget**. "
            "We'll still highlight health patterns, but focus on small, realistic improvements rather than strict rules."
        )
    else:
        st.info(
            "You've chosen a **balanced focus** between health and price. "
            "Try swapping a few less healthy items for healthier alternatives without increasing your total spend too much."
        )

# Show dietary preferences if set
if prefs.dietary_tags:
    st.caption(
        "Dietary preferences noted: "
        + ", ".join(prefs.dietary_tags)
        + ". We'll gradually use this to refine suggestions and recipes."
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
    
    # Charts: Bar chart and donut chart side by side
    col_bar, col_donut = st.columns(2)
    
    with col_bar:
        # Bar chart card
        st.markdown('<div class="nlga-card">', unsafe_allow_html=True)
        
        # Create health breakdown DataFrame for bar chart
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
    
    with col_donut:
        # Donut chart card
        st.markdown('<div class="nlga-card">', unsafe_allow_html=True)
        
        # Create DataFrame for donut chart (exclude "unknown" and zero counts)
        donut_data = [
            {"segment": "🥦 Healthy", "count": healthy_count},
            {"segment": "⚪ Neutral", "count": neutral_count},
            {"segment": "⚠️ Less Healthy", "count": unhealthy_count},
        ]
        df_donut = pd.DataFrame(donut_data)
        df_donut = df_donut[df_donut["count"] > 0]
        
        if df_donut.empty:
            st.info("No items in basket yet. Add items to see health breakdown.")
        else:
            # Calculate percentages
            total_count = df_donut["count"].sum()
            if total_count > 0:
                df_donut["percent"] = df_donut["count"] / total_count
            else:
                df_donut["percent"] = 0.0
            
            # Create donut chart with Altair
            chart = (
                alt.Chart(df_donut)
                .mark_arc(innerRadius=60)  # donut effect
                .encode(
                    theta=alt.Theta("count:Q", stack=True),
                    color=alt.Color(
                        "segment:N",
                        scale=alt.Scale(
                            domain=["🥦 Healthy", "⚪ Neutral", "⚠️ Less Healthy"],
                            range=["#22c55e", "#94a3b8", "#ef4444"]  # green, gray, red
                        ),
                        legend=alt.Legend(title="Category", orient="right")
                    ),
                    tooltip=[
                        "segment:N",
                        "count:Q",
                        alt.Tooltip("percent:Q", format=".0%", title="Share"),
                    ],
                )
                .properties(
                    width=400,
                    height=400
                )
            )
            
            # Add percentage labels text layer
            text = (
                alt.Chart(df_donut)
                .mark_text(radius=110, size=14, align="center", baseline="middle")
                .encode(
                    theta=alt.Theta("count:Q", stack=True),
                    text=alt.Text("percent:Q", format=".0%"),
                    color=alt.value("white"),  # ensures contrast on colored slices
                )
            )
            
            # Combine chart and text
            donut_chart = chart + text
            st.altair_chart(donut_chart, use_container_width=True)
            
            # Basket health insights panel
            st.markdown("### Basket health insights")
            
            # Calculate shares for insights
            healthy_share = float(
                df_donut.loc[df_donut["segment"] == "🥦 Healthy", "percent"].sum()
            ) if not df_donut.empty and "🥦 Healthy" in df_donut["segment"].values else 0.0
            
            neutral_share = float(
                df_donut.loc[df_donut["segment"] == "⚪ Neutral", "percent"].sum()
            ) if not df_donut.empty and "⚪ Neutral" in df_donut["segment"].values else 0.0
            
            less_healthy_share = float(
                df_donut.loc[df_donut["segment"] == "⚠️ Less Healthy", "percent"].sum()
            ) if not df_donut.empty and "⚠️ Less Healthy" in df_donut["segment"].values else 0.0
            
            # Generate insights based on proportions
            if total_count == 0:
                st.info("Add items to your basket to see personalized health insights.")
            elif healthy_share >= 0.7:
                st.success(
                    "Your basket is **mostly healthy** 🌱. Great job! "
                    "You could maintain this by keeping an eye on treats and ultra-processed items."
                )
            elif less_healthy_share >= 0.4:
                st.warning(
                    "A big share of your basket is **less healthy** ⚠️. "
                    "Try swapping a few items for healthier alternatives to improve your overall score."
                )
            elif neutral_share >= 0.5 and healthy_share < 0.4:
                st.info(
                    "Your basket is **quite neutral**. You're not doing badly, but there's room to add "
                    "more vegetables, whole grains, or lean proteins for a healthier mix."
                )
            else:
                st.info(
                    "Your basket is fairly **balanced**. A couple of targeted swaps could make it even healthier."
                )
        
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
    
    # Health-based swap suggestions section
    st.divider()
    st.subheader("Health-based swap suggestions")
    st.caption(
        "Quick ideas for improving your basket health score by swapping some items for healthier alternatives."
    )
    
    # Calculate health-based swap suggestions
    health_swap_suggestions = []
    try:
        from aggregator.savings import find_basket_savings
        from aggregator.search import aggregated_search
        
        # Prepare basket items in the format expected by the savings helper
        basket_items_for_swaps = []
        for idx, row in df.iterrows():
            item_dict = {
                "retailer": row.get("retailer", ""),
                "product_id": row.get("product_id", ""),
                "name": row.get("name", ""),
                "price_eur": float(row.get("price_eur", row.get("price", 0.0))),
                "quantity": int(row.get("quantity", 1)),
                "line_total": float(row.get("line_total", row.get("price_eur", row.get("price", 0.0)) * row.get("quantity", 1))),
                "image_url": row.get("image_url"),
                "health_tag": row.get("health_tag", "neutral"),
                "category": row.get("category"),
                "price_per_unit": row.get("price_per_unit"),
            }
            basket_items_for_swaps.append(item_dict)
        
        # Get detailed savings suggestions (includes full alternative item info)
        savings_result = find_basket_savings(basket_items_for_swaps, aggregated_search)
        suggestions_raw = savings_result.get("suggestions", [])
        
        # Filter to only health-improving suggestions and calculate health score impact
        for s in suggestions_raw:
            suggestion_type = s.get("type", "")
            
            # Only include suggestions that improve health
            if suggestion_type in ("healthier", "cheaper_and_healthier"):
                current = s.get("current", {})
                alternative = s.get("alternative", {})
                
                current_health = current.get("health_tag", "neutral")
                alt_health = alternative.get("health_tag", "neutral")
                
                # Skip if alternative is not healthier
                health_order = {"unhealthy": 0, "neutral": 1, "healthy": 2}
                if health_order.get(alt_health, 1) <= health_order.get(current_health, 1):
                    continue
                
                # Calculate health score improvement using the same formula as the page score
                # Current item contribution
                current_score = 0
                if current_health == "healthy":
                    current_score = 20
                elif current_health == "neutral":
                    current_score = 5
                elif current_health == "unhealthy":
                    current_score = -15
                
                # Alternative item contribution
                alt_score = 0
                if alt_health == "healthy":
                    alt_score = 20
                elif alt_health == "neutral":
                    alt_score = 5
                elif alt_health == "unhealthy":
                    alt_score = -15
                
                # Health improvement = alt_score - current_score
                delta_health_score = alt_score - current_score
                
                # Get price impact (savings is positive when alternative is cheaper)
                savings_amount = s.get("estimated_savings", 0.0)
                delta_price = -savings_amount  # Negative savings = price increase, positive = savings
                
                health_swap_suggestions.append({
                    "from_item": {
                        "name": current.get("name", "Current item"),
                        "health_tag": current_health,
                    },
                    "to_item": {
                        "name": alternative.get("name", "Alternative item"),
                        "health_tag": alt_health,
                    },
                    "delta_price": delta_price,
                    "delta_health": delta_health_score,
                    "savings_amount": savings_amount,
                })
        
        # Sort by health improvement (descending), then by price impact (ascending = cheaper first)
        health_swap_suggestions.sort(key=lambda x: (-x["delta_health"], x["delta_price"]))
        
        # Limit to top 5 suggestions
        health_swap_suggestions = health_swap_suggestions[:5]
        
    except Exception as e:
        # Fail gracefully - suggestions are a nice-to-have
        health_swap_suggestions = []
    
    # Display suggestions
    if not health_swap_suggestions:
        st.info("Your basket already looks very healthy. No obvious swaps to suggest right now.")
    else:
        for suggestion in health_swap_suggestions:
            from_item = suggestion.get("from_item", {})
            to_item = suggestion.get("to_item", {})
            delta_price = suggestion.get("delta_price", 0.0)
            delta_health = suggestion.get("delta_health", 0)
            
            st.markdown('<div class="nlga-card">', unsafe_allow_html=True)
            
            st.markdown(
                f"**Swap:** {from_item.get('name', 'Current item')} → {to_item.get('name', 'Alternative item')}"
            )
            
            # Health impact
            if delta_health > 0:
                st.markdown(f"- 🥦 Health impact: `+{delta_health}` points to basket score")
            elif delta_health < 0:
                st.markdown(f"- Health impact: `{delta_health}` points (not recommended)")
            else:
                st.markdown("- Health impact: neutral")
            
            # Price impact
            if delta_price is not None:
                if delta_price < 0:
                    st.markdown(f"- 💶 Price impact: saves €{abs(delta_price):.2f}")
                elif delta_price > 0:
                    st.markdown(f"- 💶 Price impact: +€{delta_price:.2f}")
                else:
                    st.markdown("- 💶 Price impact: no change")
            
            st.markdown('</div>', unsafe_allow_html=True)
            st.markdown("")  # Add spacing between suggestions

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
