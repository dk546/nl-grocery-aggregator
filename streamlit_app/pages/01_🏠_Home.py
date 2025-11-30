"""
Home Page - Welcome and Overview.

This page provides an introduction to the NL Grocery Aggregator application,
explaining its features and purpose.
"""

import sys
from pathlib import Path

# Ensure the streamlit_app directory is in the Python path
streamlit_app_dir = Path(__file__).parent.parent
if str(streamlit_app_dir) not in sys.path:
    sys.path.insert(0, str(streamlit_app_dir))

import streamlit as st

from utils.api_client import get_health_status
from utils.ui_components import render_header, render_backend_status, render_feature_card

render_header("🏠 Home", "Welcome to the NL Grocery Health Companion")

# Introduction
st.markdown("""
This application helps you compare grocery prices across **Albert Heijn**, **Jumbo**, and **Picnic**
while nudging you towards healthier choices through automatic health tagging.
""")

# Backend status
st.subheader("System Status")
backend_status = get_health_status()
render_backend_status(backend_status)

st.divider()

# Feature cards
st.subheader("✨ Key Features")

col1, col2, col3 = st.columns(3)

with col1:
    render_feature_card(
        title="Search & Compare",
        description="""
        Search for products across all retailers in one place. Compare prices
        and see which retailer offers the best deal. Products are automatically
        marked as cheapest when multiple retailers sell the same item.
        """,
        emoji="🔍"
    )

with col2:
    render_feature_card(
        title="My Basket",
        description="""
        Build your shopping list and track what you plan to buy. See totals
        across retailers and manage your weekly grocery planning. (Coming soon:
        weekly planner mode with meal suggestions.)
        """,
        emoji="🧺"
    )

with col3:
    render_feature_card(
        title="Recipes & Ideas",
        description="""
        Get inspiration for healthy meals. Find recipes and automatically
        search for ingredients across retailers. (Coming soon: recipe-based
        shopping lists.)
        """,
        emoji="🍳"
    )

st.divider()

# Health tagging info
st.subheader("🥦 Health Tagging")
st.info("""
Products are automatically tagged as **healthy**, **unhealthy**, or **neutral** based on
their nutritional information. These tags are approximations and should not be considered
medical advice. Always check product labels for detailed nutritional information.
""")

# Important disclaimer
st.divider()
st.caption("""
⚠️ **Important**: This application uses an experimental API that aggregates data from retailer websites.
Health tags are approximate and for informational purposes only. Always verify product information
on the retailer's website before making purchase decisions.
""")

