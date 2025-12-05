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
from utils.profile import get_profile_by_key
from ui.style import inject_global_css, section_header, pill_tag, image_card, render_footer

# Inject global CSS styling
inject_global_css()

# Page header
section_header(
    title="Health insights for your basket",
    eyebrow="GENTLE NUTRITION NUDGES",
    help_text="See a simple breakdown of healthier, neutral and less healthy items in your basket."
)

# Household profile context
profile_key = st.session_state.get("household_profile_key")
profile = get_profile_by_key(profile_key)
if profile:
    st.caption(f"For your **{profile.label.lower()}** household, these insights are a rough guide for weekly planning.")

# Get session ID (shared across pages)
session_id = get_or_create_session_id()

# Fetch basket from backend using shared session
try:
    cart_data = view_cart_backend(session_id)
    basket_items = cart_data.get("items", []) if cart_data else []
except Exception as e:
    st.error(f"Could not load your basket: {e}")
    basket_items = []

# Handle empty basket / no data state
if not basket_items:
    st.info(
        "Add a few items to your basket first.\n\n"
        "Once you have a basket, we'll show a simple breakdown of healthier, neutral and less healthy choices."
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

# Top metrics band
metric_cols = st.columns(3, gap="large")

with metric_cols[0]:
    st.metric("Healthy items", healthy_count)

with metric_cols[1]:
    st.metric("Neutral items", neutral_count)

with metric_cols[2]:
    st.metric("Less healthy items", unhealthy_count)

st.divider()

# Main content with side column
main_col, side_col = st.columns([2.2, 1], gap="large")

with main_col:
    # Visual breakdown section
    section_header(
        title="Basket health breakdown",
        eyebrow="OVERVIEW",
        help_text="A quick glance at how many items fall into each health category."
    )
    
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
        
        st.bar_chart(spend_chart_data.set_index("Category"), width='stretch')
        
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
        
        st.dataframe(health_summary, width='stretch')
    
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
    
    # Disclaimer at bottom
    st.divider()
    st.caption("""
    ⚠️ These health insights are approximate and based on simple tagging rules.
    They are not nutritional or medical advice. Always consider your own dietary needs.
    """)

with side_col:
    image_card("health_side", caption="Use these insights as a gentle guide, not strict rules.")
    
    # Quick summary
    section_header(
        title="Quick summary",
        eyebrow="SNAPSHOT",
        help_text="High-level view of your basket's balance."
    )
    
    st.markdown('<div class="nlga-card nlga-card--sidebar">', unsafe_allow_html=True)
    st.caption(f"🥦 Healthy items: {healthy_count}")
    st.caption(f"⚪ Neutral items: {neutral_count}")
    st.caption(f"⚠️ Less healthy: {unhealthy_count}")
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Show specific recommendations if there are unhealthy items
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
            st.markdown(f"**{item_name}**")
            st.caption(f"From {retailer_display}")
            st.caption("💡 Consider exploring healthier alternatives in Search & Compare.")
            st.markdown('</div>', unsafe_allow_html=True)
        
        if unhealthy_count > 5:
            st.caption(f"... and {unhealthy_count - 5} more item(s) could be explored for alternatives.")

# Footer
render_footer()
