"""
NL Grocery Aggregator - Streamlit Frontend Main Entry Point.

This is the main Streamlit application entry point. It sets up the page configuration
and provides the global layout with sidebar navigation and backend status.

Note: Multi-page routing is handled automatically by Streamlit via the `pages/` folder.
Files in `pages/` starting with numbered prefixes will appear as pages in the sidebar navigation.
The main Home page content is rendered directly in this file (app.py) when no specific page is selected.
"""

import sys
from pathlib import Path

# Ensure the streamlit_app directory is in the Python path
# This allows imports to work regardless of how the app is run
streamlit_app_dir = Path(__file__).parent
if str(streamlit_app_dir) not in sys.path:
    sys.path.insert(0, str(streamlit_app_dir))

# Add project root to path so we can import api.config
project_root = streamlit_app_dir.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import config early to load .env file before any other code accesses environment variables
# This ensures local development uses .env file, while Render uses platform env vars
import api.config  # noqa: F401

import streamlit as st

from utils.api_client import get_health_status, get_cart_summary, view_cart_backend
from utils.session import get_or_create_session_id
from utils.profile import DEFAULT_PROFILE_KEY
from ui.styles import load_global_styles
from ui.layout import page_header, section, card, kpi_row, preferences_bar
from ui.style import render_footer  # Keep footer function

# Initialize session ID early for cart operations
get_or_create_session_id()

# Initialize household profile in session state
if "household_profile_key" not in st.session_state:
    st.session_state["household_profile_key"] = DEFAULT_PROFILE_KEY

# Page configuration - must be called before any other Streamlit commands
st.set_page_config(
    page_title="NL Grocery Aggregator",
    page_icon="🥕",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inject global CSS styling
load_global_styles()

# Sidebar with app branding and global info
with st.sidebar:
    # App logo area - minimal
    st.markdown("### 🥕 **NL Grocery Aggregator**")
    
    st.divider()
    
    # Compact basket mini-summary
    session_id = get_or_create_session_id()
    cart_summary = get_cart_summary(session_id)
    if cart_summary:
        st.markdown(f"**Basket:** {cart_summary.get('total_items', 0)} items")
        st.markdown(f"**Total:** €{cart_summary.get('total_cost_eur', 0.0):.2f}")
        if st.button("Open Basket", use_container_width=True, type="primary"):
            st.switch_page("pages/03_🧺_My_Basket.py")
    else:
        st.caption("Basket is empty")
        if st.button("Open Basket", use_container_width=True):
            st.switch_page("pages/03_🧺_My_Basket.py")
    
    st.divider()

# Main content area - Home Page
# For multi-page apps, Streamlit automatically shows the selected page content
# When no specific page is selected, show the home page content here

# Page header - minimal
page_header(
    "NL Grocery Aggregator",
    subtitle="Compare prices across Albert Heijn, Jumbo, Picnic, and Dirk."
)

# Get cart data for KPIs
session_id = get_or_create_session_id()
cart_data = view_cart_backend(session_id)  # Returns None on error, {} or {items: []} if empty

# Calculate KPI values safely
if cart_data and cart_data.get("items"):
    basket_items_count = len(cart_data["items"])
    basket_total = cart_data.get("total_price", 0.0)
    retailers_count = len(set(item.get("retailer", "") for item in cart_data["items"]))
else:
    basket_items_count = 0
    basket_total = 0.0
    retailers_count = 0

# Backend status (compact inline badge)
backend_status = get_health_status()
mode_text = "online" if backend_status and backend_status.get("status") == "ok" else "offline (limited mode)"
status_dot = "●"
status_color_class = "online" if mode_text == "online" else "offline"

status_col1, status_col2 = st.columns([5, 1])
with status_col1:
    st.markdown(f'<span class="status-badge status-{status_color_class}">{status_dot} {mode_text.capitalize()}</span>', unsafe_allow_html=True)
with status_col2:
    if st.button("System Status", use_container_width=True, type="secondary"):
        st.switch_page("pages/99_🔧_System_Status.py")

# KPI row
kpi_row([
    {"label": "Basket items", "value": basket_items_count if basket_items_count > 0 else "—", "icon": "🧺"},
    {"label": "Basket total", "value": f"€{basket_total:.2f}" if basket_total > 0 else "—", "icon": "💶"},
    {"label": "Retailers", "value": retailers_count if retailers_count > 0 else "—", "icon": "🏪"},
    {"label": "Mode", "value": mode_text.split()[0] if mode_text != "online" else mode_text, "icon": "⚡"},
])

# Prominent CTA buttons
st.markdown("#### Get started")
cta_col1, cta_col2, cta_col3 = st.columns([2, 1, 1], gap="medium")

with cta_col1:
    if st.button("Start Search", use_container_width=True, type="primary"):
        st.switch_page("pages/02_🛒_Search_and_Compare.py")

with cta_col2:
    if st.button("Open Basket", use_container_width=True):
        st.switch_page("pages/03_🧺_My_Basket.py")

with cta_col3:
    if st.button("Health Insights", use_container_width=True, type="secondary"):
        st.switch_page("pages/04_📊_Health_Insights.py")

# Preferences bar (expanded on home)
preferences_bar(mode="expanded", location_key="home")

# How it works - in expander to keep page minimal
with st.expander("How it works", expanded=False):
    st.markdown("""
    1. **Search & Compare** – Search for products across all retailers and compare prices instantly.
    2. **Build Your Basket** – Add items and see totals per retailer, potential savings, and health tags.
    3. **Get Insights** – Review your basket's health breakdown and explore healthier alternatives.
    """)

# What you can do - collapsed expander with key features
with st.expander("What you can do", expanded=False):
    feature_col1, feature_col2, feature_col3 = st.columns(3, gap="medium")
    
    with feature_col1:
        st.markdown("**🔍 Search & Compare**")
        st.caption("Search across retailers, compare prices, find best deals.")
    
    with feature_col2:
        st.markdown("**🧺 My Basket**")
        st.caption("Build shopping lists, track totals, manage weekly planning.")
    
    with feature_col3:
        st.markdown("**📊 Health Insights**")
        st.caption("Review health breakdown, get swap suggestions.")

# Health tagging disclaimer - collapsed expander
with st.expander("Health tagging (disclaimer)", expanded=False):
    st.info("Products are automatically tagged as **healthy**, **unhealthy**, or **neutral** based on nutritional information. These tags are approximations and should not be considered medical advice.")
    st.caption("⚠️ **Important**: Health tags are approximate. Always verify product information on the retailer's website before making purchase decisions.")

# Sponsored spotlight (demo) - collapsed expander
with st.expander("Sponsored (demo)", expanded=False):
    try:
        from utils.sponsored_data import get_sponsored_deals_for_search
        from utils.retailers import get_retailer_display_name
        
        home_sponsored = get_sponsored_deals_for_search(query=None, retailer_codes=None, max_deals=2)
        
        if home_sponsored:
            cols = st.columns(len(home_sponsored))
            for col, deal in zip(cols, home_sponsored):
                with col:
                    with card():
                        st.markdown("**⭐ Sponsored**")
                        st.markdown(f"**{deal.title}**")
                        st.markdown(f"**€{deal.price_eur:.2f}**")
                        st.caption(deal.promo_text)
                        
                        retailer_label = get_retailer_display_name(deal.retailer)
                        st.caption(f"🛒 {retailer_label}")
                        
                        if deal.product_url:
                            st.link_button(
                                "View product",
                                url=deal.product_url,
                                use_container_width=True
                            )
                        else:
                            st.button(
                                "View product",
                                disabled=True,
                                use_container_width=True,
                                key=f"home_sponsored_{deal.id}",
                            )
        else:
            st.caption("Sponsored slots appear here when configured.")
    except Exception:
        st.caption("Sponsored content unavailable.")

# Footer
render_footer()

