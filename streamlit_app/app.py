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

from utils.api_client import get_health_status
from utils.ui_components import render_backend_status
from utils.session import get_or_create_session_id
from utils.profile import HOUSEHOLD_PROFILES, DEFAULT_PROFILE_KEY, get_profile_by_key
from ui.style import inject_global_css, section_header, image_card, render_footer, get_random_asset_image

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
inject_global_css()

# Sidebar with app branding and global info
with st.sidebar:
    # App logo area
    st.markdown("### 🥕 **NL Grocery Aggregator**")
    st.caption("Compare prices & eat healthier")
    st.caption("Fresh, budget-friendly groceries for Dutch households.")
    
    st.divider()
    
    # System status card
    st.markdown('<div class="nlga-card nlga-card--sidebar">', unsafe_allow_html=True)
    backend_status = get_health_status()
    status_emoji = "🟢" if backend_status and backend_status.get("status") == "ok" else "🔴"
    st.markdown(f"#### {status_emoji} System status")
    st.caption("API health & supermarket connectors")
    render_backend_status(backend_status)
    st.markdown('</div>', unsafe_allow_html=True)
    
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
    
    # Retailers card
    st.markdown('<div class="nlga-card nlga-card--sidebar">', unsafe_allow_html=True)
    st.markdown("#### Retailers")
    st.caption("Currently supported supermarkets")
    st.markdown("✅ Albert Heijn")
    st.markdown("✅ Jumbo")
    st.markdown("✅ Picnic")
    st.markdown("✅ Dirk")
    st.caption("We compare products; we don't sell or endorse any retailer.")
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.divider()
    
    # Resources & Plus card
    st.markdown('<div class="nlga-card nlga-card--sidebar">', unsafe_allow_html=True)
    st.markdown("#### 📚 Resources")
    st.markdown("""
- [API documentation](https://nl-grocery-aggregator.onrender.com/docs)
- [GitHub repository](https://github.com/dk546/nl-grocery-aggregator)
""")
    st.markdown("---")
    st.markdown("#### ✨ Coming soon: NLGA Plus")
    st.caption("Save favorite baskets, track price history, and get smarter swap suggestions.")
    st.markdown('</div>', unsafe_allow_html=True)

# Main content area - Home Page
# For multi-page apps, Streamlit automatically shows the selected page content
# When no specific page is selected, show the home page content here

# 3-column hero: text, CTAs, image
col_text, col_cta, col_image = st.columns([2.2, 1.6, 1.4], gap="large")

with col_text:
    st.markdown("## Healthy, fresh groceries – at the best price")
    st.markdown(
        "Compare Albert Heijn, Jumbo, Picnic, and Dirk in one place. "
        "Build a basket that fits your household and your budget."
    )

with col_cta:
    # Primary navigation buttons
    st.markdown("#### Get started")
    btn_row1, btn_row2 = st.columns([1, 1], gap="small")
    with btn_row1:
        try:
            st.page_link(
                "pages/02_🛒_Search_and_Compare.py",
                label="🔍 Search & Compare",
                icon="🔍",
            )
        except (AttributeError, TypeError):
            st.info("Use the sidebar to open **Search & Compare**.")
    with btn_row2:
        try:
            st.page_link(
                "pages/03_🧺_My_Basket.py",
                label="🧺 My Basket",
                icon="🧺",
            )
        except (AttributeError, TypeError):
            st.info("Use the sidebar to open **My Basket**.")
    
    st.markdown("#### Why people use this")
    c1, c2, c3 = st.columns(3, gap="small")
    with c1:
        st.caption("🥦 **Fresh & balanced**")
    with c2:
        st.caption("💶 **Smart on budget**")
    with c3:
        st.caption("⏱️ **Less hassle**")

with col_image:
    image_path = get_random_asset_image("home_hero_side")
    if image_path:
        st.markdown('<div class="nlga-hero-side-image">', unsafe_allow_html=True)
        st.image(image_path, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

st.divider()

# "How it works" section
section_header(
    title="How it works",
    eyebrow="3 SIMPLE STEPS",
    help_text="Getting started is easy – just follow these steps to save money and eat healthier."
)

col1, col2, col3 = st.columns(3)

with col1:
    with st.container():
        st.markdown('<div class="nlga-card">', unsafe_allow_html=True)
        st.markdown("### 1️⃣ Pick your household & retailers")
        st.markdown("""
Choose your household profile in the sidebar (single, couple, family, or student).
We'll scale servings and weekly budgets, then search Albert Heijn, Jumbo, Picnic, and Dirk for you.
""")
        st.markdown('</div>', unsafe_allow_html=True)

with col2:
    with st.container():
        st.markdown('<div class="nlga-card">', unsafe_allow_html=True)
        st.markdown("### 2️⃣ Search, compare & add items")
        st.markdown("""
Search for any product and instantly see prices across all retailers.
Filter, sort by unit price, and add the best options straight to your basket.
""")
        st.markdown('</div>', unsafe_allow_html=True)

with col3:
    with st.container():
        st.markdown('<div class="nlga-card">', unsafe_allow_html=True)
        st.markdown("### 3️⃣ Check your savings & health insights")
        st.markdown("""
Open your basket to see totals per retailer, potential savings, and simple health tags.
Use this as a gentle guide – not medical advice – when planning weekly meals.
""")
        st.markdown('</div>', unsafe_allow_html=True)

st.divider()

# "Why this matters" / value props with side image
layout_main, layout_side = st.columns([2.2, 1], gap="large")

with layout_main:
    section_header(
        title="Why this matters",
        help_text="Small changes that add up to big benefits."
    )
    
    st.markdown("""
    - **💰 Save money** – Compare prices across Albert Heijn, Jumbo, Dirk, and Picnic and spot cheaper swaps before you check out.

    - **🥗 Eat a bit healthier** – Products are tagged as healthy, neutral, or less healthy based on simple rules. It's not perfect, but it nudges you toward more balanced baskets.

    - **📅 Plan weekly shops more easily** – Reuse favorite baskets as templates, explore recipes, and adjust everything automatically to your household size.
    """)

with layout_side:
    image_card("home_side", caption="Every week, build a fresh, balanced basket.")
    st.markdown('<div class="nlga-card nlga-card--sidebar">', unsafe_allow_html=True)
    st.markdown("#### This week at a glance")
    st.caption("Compare prices, plan your basket, and check simple health insights.")
    st.markdown("---")
    st.markdown("**✨ NLGA Plus (coming soon)**")
    st.caption("Price history, smart swaps, and personalized recipe ideas.")
    st.markdown('</div>', unsafe_allow_html=True)

st.divider()

# Footer note
st.caption("""
⚠️ **Important**: This app is experimental. Health tags are approximate and for information only.
Always double-check product information on the retailer's website before buying.
""")

# Footer
render_footer()

