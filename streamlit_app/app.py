"""
NL Grocery Aggregator - Streamlit Frontend Main Entry Point.

This is the main Streamlit application entry point. It sets up the page configuration
and provides the global layout with sidebar navigation and backend status.

Note: Multi-page routing is handled automatically by Streamlit via the `pages/` folder.
Files in `pages/` starting with numbered prefixes (e.g., `01_🏠_Home.py`) will appear
as pages in the sidebar navigation.
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
from utils.ui_components import render_backend_status, render_db_status
from utils.session import get_or_create_session_id
from utils.profile import HOUSEHOLD_PROFILES, DEFAULT_PROFILE_KEY, get_profile_by_key
from utils.preferences import (
    get_user_preferences_from_session,
    save_user_preferences_to_session,
    ALLOWED_DIETARY_TAGS,
    PREFERENCE_HEALTH_BALANCED,
    PREFERENCE_HEALTH_FIRST,
    PREFERENCE_BUDGET_FIRST,
)
from ui.styles import load_global_styles
from ui.layout import page_header, section, card, kpi_row
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
    
    # Household Profile card
    st.markdown('<div class="nlga-card nlga-card--sidebar">', unsafe_allow_html=True)
    st.markdown("#### Household")
    st.caption("We'll tailor servings & insights to this profile.")
    
    profile_keys = list(HOUSEHOLD_PROFILES.keys())
    profile_labels = [HOUSEHOLD_PROFILES[k].label for k in profile_keys]
    
    try:
        current_index = profile_keys.index(st.session_state["household_profile_key"])
    except ValueError:
        current_index = profile_keys.index(DEFAULT_PROFILE_KEY)
    
    selected_label = st.selectbox(
        "Who are we shopping for?",
        options=profile_labels,
        index=current_index,
        help="We'll lightly tailor servings and insights based on your household type.",
        label_visibility="collapsed",
    )
    
    # Map label back to key
    selected_key = profile_keys[profile_labels.index(selected_label)]
    st.session_state["household_profile_key"] = selected_key
    
    current_profile = get_profile_by_key(selected_key)
    
    # Show one-line hint with profile info
    budget_hint = f"~€{current_profile.typical_weekly_budget_hint:.0f}/week" if current_profile.typical_weekly_budget_hint else ""
    servings_info = f"{int(current_profile.serving_multiplier)} servings"
    hint_parts = []
    if budget_hint:
        hint_parts.append(budget_hint)
    hint_parts.append(servings_info)
    if hint_parts:
        st.caption(" • ".join(hint_parts))
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.divider()
    
    # Food Preferences card
    st.markdown('<div class="nlga-card nlga-card--sidebar">', unsafe_allow_html=True)
    st.markdown("#### Food preferences")
    
    prefs = get_user_preferences_from_session()
    
    health_focus_label = st.radio(
        "What should we prioritize?",
        options=[
            PREFERENCE_HEALTH_BALANCED,
            PREFERENCE_HEALTH_FIRST,
            PREFERENCE_BUDGET_FIRST,
        ],
        format_func=lambda v: {
            PREFERENCE_HEALTH_BALANCED: "A bit of both",
            PREFERENCE_HEALTH_FIRST: "Healthier choices first",
            PREFERENCE_BUDGET_FIRST: "Lowest prices first",
        }.get(v, v),
        index=[
            PREFERENCE_HEALTH_BALANCED,
            PREFERENCE_HEALTH_FIRST,
            PREFERENCE_BUDGET_FIRST,
        ].index(prefs.health_focus),
        help="We'll use this to sort smart suggestions and interpret your health insights.",
    )
    
    dietary_selection = st.multiselect(
        "Dietary preferences (optional)",
        options=ALLOWED_DIETARY_TAGS,
        default=prefs.dietary_tags,
        format_func=lambda v: {
            "vegetarian": "Vegetarian",
            "vegan": "Vegan",
            "halal": "Halal",
            "no_pork": "No pork",
            "lactose_free": "Lactose-free",
            "gluten_free": "Gluten-free",
            "low_sugar": "Low sugar",
        }.get(v, v),
        help="We don't filter products yet, but we'll use this in your insights and future recipe suggestions.",
    )
    
    # Save back to session
    prefs.health_focus = health_focus_label
    prefs.dietary_tags = dietary_selection
    save_user_preferences_to_session(prefs)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.divider()
    
    # System status - compact
    with st.expander("System status", expanded=False):
        backend_status = get_health_status()
        status_emoji = "🟢" if backend_status and backend_status.get("status") == "ok" else "🔴"
        st.markdown(f"**Backend:** {status_emoji}")
        render_backend_status(backend_status)
        
        # Database status
        db_enabled = False
        if backend_status:
            raw_status = backend_status.get("raw", {})
            db_enabled = raw_status.get("db_enabled", False)
        render_db_status(db_enabled)

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

backend_status = get_health_status()
mode_text = "Live" if backend_status and backend_status.get("status") == "ok" else "Offline"

# KPI row
kpi_row([
    {"label": "Basket items", "value": basket_items_count if basket_items_count > 0 else "—", "icon": "🧺"},
    {"label": "Basket total", "value": f"€{basket_total:.2f}" if basket_total > 0 else "—", "icon": "💶"},
    {"label": "Retailers", "value": retailers_count if retailers_count > 0 else "—", "icon": "🏪"},
    {"label": "Mode", "value": mode_text, "icon": "⚡"},
])

st.markdown("<br>", unsafe_allow_html=True)

# Prominent CTA buttons
st.markdown("#### Get started")
cta_col1, cta_col2, cta_col3 = st.columns(3, gap="medium")

with cta_col1:
    if st.button("Start Search", use_container_width=True, type="primary"):
        st.switch_page("pages/02_🛒_Search_and_Compare.py")

with cta_col2:
    if st.button("Open Basket", use_container_width=True):
        st.switch_page("pages/03_🧺_My_Basket.py")

with cta_col3:
    if st.button("Health Insights", use_container_width=True):
        st.switch_page("pages/04_📊_Health_Insights.py")

st.divider()

# How it works - in expander to keep page minimal
with st.expander("How it works", expanded=False):
    st.markdown("""
    1. **Search & Compare** – Search for products across all retailers and compare prices instantly.
    2. **Build Your Basket** – Add items and see totals per retailer, potential savings, and health tags.
    3. **Get Insights** – Review your basket's health breakdown and explore healthier alternatives.
    """)

st.markdown("<br>", unsafe_allow_html=True)

# Footer
render_footer()

