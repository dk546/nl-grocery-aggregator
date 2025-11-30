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

import uuid

import streamlit as st

from utils.api_client import get_health_status
from utils.ui_components import render_backend_status
from utils.session import get_or_create_session_id

# Initialize session ID early for cart operations
get_or_create_session_id()

# Page configuration - must be called before any other Streamlit commands
st.set_page_config(
    page_title="NL Grocery Aggregator",
    page_icon="🥦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Sidebar with app branding and global info
with st.sidebar:
    st.title("🥦 NL Grocery Aggregator")
    st.caption("Compare Dutch groceries, shop smarter, eat better.")
    
    st.divider()
    
    # Backend status check (cached in api_client.get_health_status)
    st.subheader("System Status")
    backend_status = get_health_status()
    render_backend_status(backend_status)
    
    st.divider()
    
    # Links and info
    st.markdown("### 📚 Resources")
    st.markdown("""
    - [API Documentation](https://nl-grocery-aggregator.onrender.com/docs)
    - [GitHub Repository](https://github.com/dk546/nl-grocery-aggregator)
    """)
    
    st.divider()
    
    st.markdown("### ℹ️ About")
    st.caption("""
    This is an experimental application for comparing grocery prices and health
    information across Dutch supermarkets. Data is provided for educational
    purposes only.
    """)

# Main content area
# For multi-page apps, Streamlit automatically shows the selected page content
# The Home page (01_🏠_Home.py) will be shown by default
st.markdown("# 🥦 Welcome to NL Grocery Aggregator")
st.markdown("""
Use the sidebar to navigate between pages:
- **Home**: Overview and getting started
- **Search & Compare**: Find and compare products across retailers
- **My Basket**: Manage your shopping list
- **Health Insights**: Track your healthy choices
- **Recipes**: Get recipe inspiration
""")

