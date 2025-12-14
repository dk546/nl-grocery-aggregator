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
from utils.preferences import (
    get_user_preferences_from_session,
    PREFERENCE_HEALTH_FIRST,
    PREFERENCE_BUDGET_FIRST,
)
from ui.styles import load_global_styles
from ui.layout import page_header, section, card, kpi_row, render_basket_button, preferences_summary_text
from ui.style import render_footer
from ui.feedback import show_empty_state
from ui.charts import (
    build_radial_score,
    build_donut_composition,
    build_diverging_category_bars
)

# Inject global CSS styling
load_global_styles()

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
    page_header(
        title="Health insights",
        subtitle="Add some items to your basket first to see a simple health breakdown.",
        right=lambda: render_basket_button(session_id, "health")
    )
    show_empty_state(
        title="Your basket is empty",
        subtitle="Add items to your basket to see health insights and improvement suggestions.",
        action_label="Open basket",
        action_page_path="pages/03_🧺_My_Basket.py"
    )
    st.stop()

# Cache health aggregates computation
@st.cache_data(ttl=60)  # Cache for 60 seconds
def compute_health_aggregates(basket_items_list: list, total_price: float) -> dict:
    """Compute health aggregates from basket items."""
    df_temp = pd.DataFrame(basket_items_list)
    if "health_tag" not in df_temp.columns:
        df_temp["health_tag"] = None
    df_temp["health_tag"] = df_temp["health_tag"].fillna("unknown")
    
    total_items = int(df_temp["quantity"].sum()) if "quantity" in df_temp.columns else len(df_temp)
    
    healthy_count = len(df_temp[df_temp["health_tag"] == "healthy"])
    unhealthy_count = len(df_temp[df_temp["health_tag"] == "unhealthy"])
    neutral_count = len(df_temp[df_temp["health_tag"] == "neutral"])
    unknown_count = len(df_temp[df_temp["health_tag"] == "unknown"])
    
    # Calculate Basket Health Score (0-100)
    score_raw = (
        healthy_count * 20 +
        neutral_count * 5 -
        unhealthy_count * 15
    )
    score = max(0, min(100, int(score_raw)))
    
    healthy_pct_all = (healthy_count / len(df_temp) * 100) if len(df_temp) > 0 else 0
    known_health_items = len(df_temp) - unknown_count
    healthy_pct_known = (healthy_count / known_health_items * 100) if known_health_items > 0 else 0
    
    return {
        "total_items": total_items,
        "total_spend": total_price,
        "healthy_count": healthy_count,
        "unhealthy_count": unhealthy_count,
        "neutral_count": neutral_count,
        "unknown_count": unknown_count,
        "score": score,
        "healthy_pct_all": healthy_pct_all,
        "healthy_pct_known": healthy_pct_known,
        "df": df_temp
    }

# Calculate health aggregates (cached)
health_data = compute_health_aggregates(basket_items, float(cart_data.get("total_price", 0.0)) if cart_data else 0.0)
df = health_data["df"]
total_items = health_data["total_items"]
total_spend = health_data["total_spend"]
healthy_count = health_data["healthy_count"]
unhealthy_count = health_data["unhealthy_count"]
neutral_count = health_data["neutral_count"]
unknown_count = health_data["unknown_count"]
score = health_data["score"]
healthy_pct_all = health_data["healthy_pct_all"]
healthy_pct_known = health_data["healthy_pct_known"]

# Page header with basket button
page_header(
    title="Health Insights",
    subtitle="Quick overview of your basket's health balance and improvement opportunities.",
    right=lambda: render_basket_button(session_id, "health")
)

# Context caption (1-line, subtle)
prefs_summary = preferences_summary_text()
st.caption(f"Based on: {prefs_summary}")

# Calculate health score category
if score >= 80:
    score_category = "Excellent"
elif score >= 60:
    score_category = "Good"
elif score >= 40:
    score_category = "Needs improvement"
else:
    score_category = "Unhealthy"

# Calculate items to improve (unhealthy items)
items_to_improve = unhealthy_count

# TOP ROW: Hero charts (2 columns) - aligned grid
hero_col1, hero_col2 = st.columns(2, gap="medium")

with hero_col1:
    with card():
        section("Health score", caption=None)
        score_chart = build_radial_score(score, score_category)
        st.altair_chart(score_chart, use_container_width=True)

with hero_col2:
    with card():
        section("Basket composition", caption=None)
        donut_data = {
            "Healthy": healthy_count,
            "Neutral": neutral_count,
            "Less Healthy": unhealthy_count,
        }
        donut_chart = build_donut_composition(donut_data)
        st.altair_chart(donut_chart, use_container_width=True)

# SECOND ROW: Key takeaways as insight cards
section("Key takeaways")

# Calculate shares for insights
total_count = healthy_count + neutral_count + unhealthy_count
healthy_share = (healthy_count / total_count) if total_count > 0 else 0.0
less_healthy_share = (unhealthy_count / total_count) if total_count > 0 else 0.0

# Find main driver category (most common health tag)
if "category" in df.columns and len(df["category"].dropna()) > 0:
    category_counts = df["category"].value_counts()
    main_category = category_counts.index[0] if len(category_counts) > 0 else None
else:
    main_category = None

# Generate 3 key takeaways with icons - equal height cards
insight_col1, insight_col2, insight_col3 = st.columns(3, gap="medium")

with insight_col1:
    st.markdown('<div class="nlga-card nlga-insight-card">', unsafe_allow_html=True)
    st.markdown("### 📊 Overall score")
    st.markdown(f"Your basket is **{score_category.lower()}** ({score}/100).")
    st.markdown('</div>', unsafe_allow_html=True)

with insight_col2:
    st.markdown('<div class="nlga-card nlga-insight-card">', unsafe_allow_html=True)
    st.markdown("### 🎯 Main driver")
    if main_category:
        st.markdown(f"**{main_category}** is your largest category.")
    elif healthy_share >= 0.5:
        st.markdown("Most items are healthy. Keep it up!")
    elif less_healthy_share >= 0.4:
        st.markdown(f"**{int(less_healthy_share * 100)}%** less healthy items need attention.")
    else:
        st.markdown("Mix is balanced. Small swaps can help.")
    st.markdown('</div>', unsafe_allow_html=True)

with insight_col3:
    st.markdown('<div class="nlga-card nlga-insight-card">', unsafe_allow_html=True)
    st.markdown("### 💡 Next step")
    if unhealthy_count > 0:
        st.markdown(f"Swap **{unhealthy_count} item(s)** for healthier alternatives.")
    elif healthy_share < 0.5:
        st.markdown("Add more vegetables, whole grains, or lean proteins.")
    else:
        st.markdown("Your basket looks great! Maintain this balance.")
    st.markdown('</div>', unsafe_allow_html=True)

# THIRD ROW: Diverging bars by category
if "category" in df.columns and len(df["category"].dropna()) > 0:
    section("What drives your score")
    
    # Calculate healthy vs less healthy percentages by category
    category_data = []
    for category in df["category"].dropna().unique():
        cat_df = df[df["category"] == category]
        cat_total = len(cat_df)
        if cat_total > 0:
            healthy_items = len(cat_df[cat_df["health_tag"] == "healthy"])
            less_healthy_items = len(cat_df[cat_df["health_tag"] == "unhealthy"])
            
            category_data.append({
                "category": category,
                "healthy_pct": healthy_items / cat_total,
                "less_healthy_pct": less_healthy_items / cat_total,
            })
    
    # Sort by total items and take top 8
    category_data_df = pd.DataFrame(category_data)
    if not category_data_df.empty:
        # Add total count for sorting
        category_totals = df["category"].value_counts()
        category_data_df["total_items"] = category_data_df["category"].map(category_totals)
        category_data_df = category_data_df.sort_values("total_items", ascending=False).head(8)
        category_data_df = category_data_df.drop("total_items", axis=1)
        
        with card():
            diverging_chart = build_diverging_category_bars(category_data_df)
            st.altair_chart(diverging_chart, use_container_width=True)
    else:
        st.caption("No category breakdown available.")

# Navigation CTAs (compact, consistent sizing)
nav_col1, nav_col2 = st.columns(2, gap="medium")
with nav_col1:
    if st.button("Open basket", use_container_width=True, type="secondary"):
        st.switch_page("pages/03_🧺_My_Basket.py")
with nav_col2:
    if st.button("Find savings", use_container_width=True, type="secondary"):
        st.switch_page("pages/03_🧺_My_Basket.py")

st.divider()

# Actionable suggestions in expander
with st.expander("Improve this basket", expanded=False):
    # Health-based swap suggestions
    
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

# Compact disclaimer
st.caption("⚠️ Health insights are approximate and for information only. Not medical advice.")

# Footer
render_footer()
