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
from utils.ui_components import render_header

render_header("📊 Health Insights", "High-level view of your grocery choices and health profile")

# Get session ID (shared across pages)
session_id = get_or_create_session_id()

st.subheader("🥦 Your Basket's Health Profile")

# Fetch basket from backend using shared session
try:
    cart_data = view_cart_backend(session_id)
    basket_items = cart_data.get("items", []) if cart_data else []
except Exception as e:
    st.error(f"Could not load your basket: {e}")
    basket_items = []

if not basket_items:
    # Empty basket state
    st.info("🛒 Your basket is empty. Add items from the Search & Compare page to see health insights.")
    
    if st.button("🔍 Go to Search & Compare", use_container_width=True):
        st.switch_page("pages/02_🛒_Search_and_Compare.py")
    
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

# Display key metrics
st.markdown("### 📊 Key Metrics")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Items", total_items)

with col2:
    st.metric(
        "% Healthy Items",
        f"{healthy_pct_all:.0f}%",
        delta=f"{healthy_count} items",
        help="Percentage of items tagged as healthy"
    )

with col3:
    st.metric("Total Spend", f"€{total_spend:.2f}")

with col4:
    unique_retailers = len(df["retailer"].unique()) if "retailer" in df.columns else 0
    st.metric("Retailers", unique_retailers)

st.divider()

# Health tag distribution
st.markdown("### 🥗 Health Tag Distribution")

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

st.bar_chart(health_chart_data.set_index("Category"), use_container_width=True)

# Display breakdown in columns
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown("#### 🥦 Healthy")
    st.markdown(f"**{healthy_count}** items ({healthy_pct_all:.0f}%)")
    st.progress(healthy_count / len(df) if len(df) > 0 else 0)

with col2:
    unhealthy_pct = (unhealthy_count / len(df) * 100) if len(df) > 0 else 0
    st.markdown("#### ⚠️ Less Healthy")
    st.markdown(f"**{unhealthy_count}** items ({unhealthy_pct:.0f}%)")
    st.progress(unhealthy_count / len(df) if len(df) > 0 else 0)

with col3:
    neutral_pct = (neutral_count / len(df) * 100) if len(df) > 0 else 0
    st.markdown("#### ⚪ Neutral")
    st.markdown(f"**{neutral_count}** items ({neutral_pct:.0f}%)")
    st.progress(neutral_count / len(df) if len(df) > 0 else 0)

with col4:
    unknown_pct = (unknown_count / len(df) * 100) if len(df) > 0 else 0
    st.markdown("#### ❔ Unknown")
    st.markdown(f"**{unknown_count}** items ({unknown_pct:.0f}%)")
    st.progress(unknown_count / len(df) if len(df) > 0 else 0)

st.divider()

# Price analysis by health category
st.markdown("### 💰 Spend by Health Category")

# Calculate spend by health tag (using line_total from cart items)
if "line_total" in df.columns:
    # Ensure line_total is numeric before aggregating
    df["line_total"] = pd.to_numeric(df["line_total"], errors="coerce").fillna(0)
    price_by_tag = df.groupby("health_tag")["line_total"].sum()
    
    # Create display DataFrame
    spend_chart_data = pd.DataFrame({
        "Category": price_by_tag.index,
        "Spend (€)": price_by_tag.values
    })
    
    # Map to friendly names
    spend_chart_data["Category"] = spend_chart_data["Category"].map({
        "healthy": "🥦 Healthy",
        "unhealthy": "⚠️ Less Healthy",
        "neutral": "⚪ Neutral",
        "unknown": "❔ Unknown"
    }).fillna(spend_chart_data["Category"])
    
    st.bar_chart(spend_chart_data.set_index("Category"), use_container_width=True)
    
    # Show metrics
    col1, col2, col3 = st.columns(3)
    
    if "healthy" in price_by_tag.index:
        with col1:
            st.metric(
                "Healthy Spend",
                f"€{price_by_tag['healthy']:.2f}",
                help="Total spend on items tagged as healthy"
            )
    
    if "unhealthy" in price_by_tag.index:
        with col2:
            healthy_spend = price_by_tag.get("healthy", 0)
            unhealthy_spend = price_by_tag["unhealthy"]
            delta = None
            if healthy_spend > 0:
                delta = f"{((unhealthy_spend / healthy_spend - 1) * 100):+.0f}%"
            st.metric(
                "Less Healthy Spend",
                f"€{unhealthy_spend:.2f}",
                delta=delta,
                help="Total spend on items tagged as less healthy"
            )
    
    if "neutral" in price_by_tag.index:
        with col3:
            st.metric(
                "Neutral Spend",
                f"€{price_by_tag['neutral']:.2f}",
                help="Total spend on items tagged as neutral"
            )
else:
    st.caption("Price information not available for comparison.")

st.divider()

# Health interpretation and recommendations
st.markdown("### 💡 Insights & Recommendations")

# Provide supportive, non-judgmental feedback (using healthy_pct_known for insights)
if healthy_pct_known >= 70:
    st.success("""
    🎉 **Nice!** Most of your basket is tagged as healthy 🥦
    
    You're making great choices for a balanced diet. Keep it up!
    """)
elif healthy_pct_known >= 40:
    st.info("""
    ⚖️ **Mixed basket** – you have a good variety of items!
    
    Consider swapping a few items for healthier alternatives to boost your health score.
    Try using the health filter in Search & Compare to discover healthier options.
    """)
else:
    st.warning("""
    💪 **There's room to add more healthy options!**
    
    Plenty of room for improvement – try filtering by 'Healthy' in Search & Compare
    to discover nutritious alternatives. Small changes add up over time!
    """)

# Show specific recommendations if there are unhealthy items
if unhealthy_count > 0:
    unhealthy_items_df = df[df["health_tag"] == "unhealthy"].head(5)
    
    st.markdown("**💡 Consider exploring alternatives for:**")
    for idx, row in unhealthy_items_df.iterrows():
        item_name = row.get("name", "Unknown")
        retailer = row.get("retailer", "Unknown")
        st.caption(f"- {item_name} ({retailer})")
    
    if unhealthy_count > 5:
        st.caption(f"... and {unhealthy_count - 5} more item(s)")
    
    st.caption("💡 Use the Search & Compare page with the '🥦 Healthy Only' filter to find alternatives.")

st.divider()

# Detailed breakdown table
st.markdown("### 📋 Detailed Breakdown")

if len(df) > 0:
    # Group by health tag and aggregate
    if "line_total" in df.columns:
        # Ensure line_total is numeric before aggregating
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
    
    st.dataframe(health_summary, use_container_width=True)

st.divider()

# Optional: AI Health Coach (only if OPENAI_API_KEY is set)
openai_api_key = os.getenv("OPENAI_API_KEY")
if openai_api_key:
    with st.expander("🤖 Experimental: AI Health Coach (beta)", expanded=False):
        st.write("Get a short, friendly reflection on your current basket based on the summary statistics above.")
        st.caption("⚠️ **Note:** This is not medical advice. This feature is experimental and for informational purposes only.")
        
        if st.button("Generate AI insight"):
            try:
                from openai import OpenAI
                
                client = OpenAI(api_key=openai_api_key)
                
                # Prepare context about the basket
                context = f"""
                Basket Summary:
                - Total items: {total_items}
                - Healthy items: {healthy_count} ({healthy_pct_all:.0f}% of all items, {healthy_pct_known:.0f}% of known tags)
                - Less healthy items: {unhealthy_count}
                - Neutral items: {neutral_count}
                - Unknown health tag: {unknown_count}
                - Total spend: €{total_spend:.2f}
                
                Health tag distribution:
                - Healthy: {healthy_count} items
                - Less Healthy: {unhealthy_count} items
                - Neutral: {neutral_count} items
                - Unknown: {unknown_count} items
                """
                
                if "line_total" in df.columns and "health_tag" in df.columns:
                    # Ensure line_total is numeric (already converted earlier, but ensure for safety)
                    df_temp = df.copy()
                    df_temp["line_total"] = pd.to_numeric(df_temp["line_total"], errors="coerce").fillna(0)
                    healthy_spend = df_temp[df_temp["health_tag"] == "healthy"]["line_total"].sum() if len(df_temp[df_temp["health_tag"] == "healthy"]) > 0 else 0
                    unhealthy_spend = df_temp[df_temp["health_tag"] == "unhealthy"]["line_total"].sum() if len(df_temp[df_temp["health_tag"] == "unhealthy"]) > 0 else 0
                    context += f"\n- Spend on healthy items: €{healthy_spend:.2f}"
                    context += f"\n- Spend on less healthy items: €{unhealthy_spend:.2f}"
                
                prompt = f"""You are a friendly, non-judgmental grocery shopping assistant. 
                
Based on this basket summary, provide a short, encouraging reflection (2-3 sentences) about the health profile.
Keep it:
- Positive and supportive
- Non-medical (no medical advice)
- Specific to the numbers provided
- Focused on small, achievable improvements if applicable

Basket context:
{context}

Response:"""
                
                with st.spinner("Generating insight..."):
                    response = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": "You are a friendly, supportive grocery shopping assistant. You provide non-medical, encouraging insights about food choices."},
                            {"role": "user", "content": prompt}
                        ],
                        max_tokens=150,
                        temperature=0.7
                    )
                    
                    ai_insight = response.choices[0].message.content
                    st.markdown(f"**💭 AI Insight:**\n\n{ai_insight}")
                    
            except ImportError:
                st.error("OpenAI Python client is not installed. Install it with: pip install openai")
            except Exception as e:
                st.error(f"Could not generate AI insight: {str(e)}")
                st.caption("Please check your OPENAI_API_KEY and try again.")

# Future enhancements placeholder
st.divider()
st.caption("""
**🔮 Planned Features:**
- Historical health score trends over time
- Personalized health recommendations based on past purchases
- Health score comparison with community averages
- Nutritional information aggregation and analysis
- Meal planning suggestions based on basket contents
""")
