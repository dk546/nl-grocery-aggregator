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
from ui.styles import load_global_styles
from ui.layout import page_header, section, card, kpi_row
from ui.style import render_footer
from ui.feedback import show_empty_state
from ui.feedback import show_empty_state  # Keep footer function
from ui.style import pill_tag  # Keep pill_tag helper

# Inject global CSS styling
load_global_styles()

# Get session ID (shared across pages)
session_id = get_or_create_session_id()

# Prepare basket button function for header
from ui.layout import get_basket_count

def _render_basket_button():
    basket_count = get_basket_count(session_id)
    basket_label = f"🧺 Basket ({basket_count})" if basket_count > 0 else "🧺 Basket"
    if st.button(basket_label, key="header_basket_btn_health", use_container_width=True):
        st.switch_page("pages/03_🧺_My_Basket.py")

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
        right=_render_basket_button
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
    right=_render_basket_button
)

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

# Calculate variety score (number of unique categories, if available)
variety_score = "—"
if "category" in df.columns:
    unique_categories = df["category"].nunique()
    variety_score = f"{unique_categories} categories"

# KPI row
kpi_row([
    {"label": "Health score", "value": f"{score}/100", "icon": "📊"},
    {"label": "% healthy", "value": f"{healthy_pct_all:.0f}%", "icon": "🥦"},
    {"label": "Items to improve", "value": items_to_improve, "icon": "⚠️"},
    {"label": "Variety", "value": variety_score, "icon": "📦"},
])

st.markdown("<br>", unsafe_allow_html=True)

# Navigation CTAs
nav_col1, nav_col2 = st.columns(2, gap="medium")
with nav_col1:
    if st.button("Open basket", use_container_width=True, type="secondary"):
        st.switch_page("pages/03_🧺_My_Basket.py")
with nav_col2:
    if st.button("Find savings", use_container_width=True):
        st.switch_page("pages/03_🧺_My_Basket.py")

st.divider()

# Main content - simplified layout
# Primary chart: Donut chart for basket composition
with card("Basket composition"):
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
                    legend=alt.Legend(title=None, orient="right")
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

st.markdown("<br>", unsafe_allow_html=True)

# Key Takeaways card
with card("Key takeaways"):
    # Calculate shares for insights
    total_count = df_donut["count"].sum() if not df_donut.empty else 0
    healthy_share = float(
        df_donut.loc[df_donut["segment"] == "🥦 Healthy", "percent"].sum()
    ) if not df_donut.empty and "🥦 Healthy" in df_donut["segment"].values else 0.0
    
    less_healthy_share = float(
        df_donut.loc[df_donut["segment"] == "⚠️ Less Healthy", "percent"].sum()
    ) if not df_donut.empty and "⚠️ Less Healthy" in df_donut["segment"].values else 0.0
    
    # Find main driver category
    if "category" in df.columns:
        category_counts = df["health_tag"].value_counts()
        main_category = category_counts.index[0] if len(category_counts) > 0 else "mixed"
    else:
        main_category = "mixed"
    
    # Generate 3 key takeaways
    takeaway1 = f"Your basket is **{score_category.lower()}** ({score}/100)."
    if healthy_share >= 0.5:
        takeaway2 = "Most items are healthy. Keep up the good choices."
    elif less_healthy_share >= 0.4:
        takeaway2 = f"**{int(less_healthy_share * 100)}%** of items are less healthy. Focus on swaps."
    else:
        takeaway2 = "Mix is balanced. Small swaps can improve your score."
    
    # Actionable insight
    if unhealthy_count > 0:
        takeaway3 = f"**{unhealthy_count} item(s)** could be swapped for healthier alternatives."
    elif healthy_share < 0.5:
        takeaway3 = "Add more vegetables, whole grains, or lean proteins."
    else:
        takeaway3 = "Your basket looks great! Maintain this balance."
    
    st.markdown(f"• {takeaway1}")
    st.markdown(f"• {takeaway2}")
    st.markdown(f"• {takeaway3}")

st.markdown("<br>", unsafe_allow_html=True)

# Secondary chart: Category breakdown (if categories available)
if "category" in df.columns and len(df["category"].dropna()) > 0:
    with card("Top categories"):
        # Group by category and health tag
        category_health = df.groupby(["category", "health_tag"]).size().reset_index(name="count")
        category_health = category_health[category_health["health_tag"] != "unknown"]
        
        if not category_health.empty:
            # Get top 5 categories by total count
            top_categories = df["category"].value_counts().head(5).index.tolist()
            category_health = category_health[category_health["category"].isin(top_categories)]
            
            # Create stacked bar chart
            chart = (
                alt.Chart(category_health)
                .mark_bar()
                .encode(
                    x=alt.X("category:N", title="Category", sort="-y"),
                    y=alt.Y("count:Q", title="Items"),
                    color=alt.Color(
                        "health_tag:N",
                        scale=alt.Scale(
                            domain=["healthy", "neutral", "unhealthy"],
                            range=["#22c55e", "#94a3b8", "#ef4444"]
                        ),
                        legend=alt.Legend(title=None)
                    ),
                    tooltip=["category:N", "health_tag:N", "count:Q"]
                )
                .properties(height=300)
            )
            st.altair_chart(chart, use_container_width=True)
        else:
            st.caption("No category data available.")

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
