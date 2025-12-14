"""
System Status Page - Backend health and API documentation.

This page displays the status of the backend API, provides links to API documentation,
and shows system diagnostics information.
"""

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

import streamlit as st

from utils.api_client import get_health_status, get_backend_url, add_to_cart_backend, view_cart_backend, remove_from_cart_backend
from utils.ui_components import render_backend_status, render_db_status
from utils.session import get_or_create_session_id
from ui.styles import load_global_styles
from ui.layout import page_header
from ui.style import render_footer

# Inject global CSS styling
load_global_styles()

page_header(
    title="🔧 System Status",
    subtitle="Backend health, diagnostics, and API documentation."
)

st.caption("This page shows the current status of the backend API and connectors that power search, basket, and insights.")

st.subheader("Backend API Health")

# Get backend health status
backend_status = get_health_status()

# Display backend connection status
render_backend_status(backend_status)

# Show additional system info if available
if backend_status and backend_status.get("status") == "ok":
    col1, col2 = st.columns(2)
    
    with col1:
        # Show API documentation link if available
        docs_url = backend_status.get("docs_url", "/docs")
        backend_url = get_backend_url()
        full_docs_url = f"{backend_url}{docs_url}" if docs_url.startswith("/") else docs_url
        
        st.markdown(f"""
        **📚 API Documentation**  
        [View API docs]({full_docs_url})  
        Interactive API documentation with Swagger UI.
        """)
    
    with col2:
        st.markdown("""
        **ℹ️ About the Backend**  
        The backend API powers product search and aggregation across
        Albert Heijn, Jumbo, Picnic, and Dirk retailers.
        """)
    
    # Show raw status info in expander (optional, for debugging)
    with st.expander("📋 System Details (Raw Status Response)"):
        if backend_status.get("raw"):
            st.json(backend_status["raw"])
        else:
            st.info("No detailed status information available.")
else:
    st.warning("""
    ⚠️ The backend API is currently unreachable. Some features may not work properly.
    Please check your connection or try again later.
    """)

st.divider()

# Database Status Section
st.subheader("Database Status")

# Get database status from health response
db_enabled = False
cart_sessions_count = 0
price_history_count = 0

if backend_status:
    raw_status = backend_status.get("raw", {})
    db_enabled = raw_status.get("db_enabled", False)

# Display database status
render_db_status(db_enabled)

if db_enabled:
    # Try to get database statistics
    try:
        # Import here to avoid issues if DB module has import errors
        import sys
        from pathlib import Path
        project_root = Path(__file__).parent.parent.parent
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))
        
        from aggregator.db import get_cart_sessions_count, get_price_history_count
        
        cart_sessions_count = get_cart_sessions_count()
        price_history_count = get_price_history_count()
        
        # Display statistics
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Cart Sessions", cart_sessions_count)
        
        with col2:
            st.metric("Price History Records", price_history_count)
            
    except Exception as e:
        st.warning(f"⚠️ Could not retrieve database statistics: {e}")
else:
    st.info("""
    **Fallback Storage Mode**
    
    Database persistence is not enabled. The app is using:
    - **In-memory storage** for shopping carts (data lost on server restart)
    - **JSONL file** for price history (data persists until server restart)
    
    To enable Postgres persistence, set the `DATABASE_URL` environment variable
    and install SQLAlchemy: `pip install sqlalchemy psycopg2-binary`
    """)

st.divider()

# TODO: When the backend exposes a dedicated /health endpoint, extend this section
# to include per-connector status, latency metrics, and error rates.
#
# Example structure for future /health endpoint:
# {
#     "status": "ok",
#     "connectors": {
#         "ah": {"status": "up", "uptime": 99.9, "avg_latency_ms": 250},
#         "jumbo": {"status": "up", "uptime": 99.8, "avg_latency_ms": 180},
#         "picnic": {"status": "up", "uptime": 99.9, "avg_latency_ms": 320}
#     },
#     "metrics": {
#         "total_requests": 1234,
#         "error_rate": 0.01,
#         "avg_response_time_ms": 250
#     }
# }
#
# This data can be visualized here as:
# - Connector uptime dashboard (percentage gauges)
# - Latency charts (line chart over time)
# - Error rate indicators
# - Request volume statistics

with st.expander("🔮 Planned System Diagnostics", expanded=False):
    st.markdown("""
    In future versions, this section will show:
    
    - **Connector Uptime**: Real-time status for AH, Jumbo, Picnic, and Dirk connectors
    - **Performance Metrics**: Average response times for search requests
    - **Error Tracking**: Recent API errors and error rates
    - **Request Volume**: Number of searches performed over time
    - **Service Health**: Overall system availability and reliability
    """)

st.divider()

# Demo Controls Section
with st.expander("Demo controls", expanded=False):
    st.caption("Use these controls to reset the demo state or load sample data.")
    
    demo_col1, demo_col2, demo_col3 = st.columns(3, gap="small")
    
    with demo_col1:
        if st.button("Reset session", use_container_width=True, type="secondary"):
            # Clear search-related state
            keys_to_clear = [
                "search_query", "search_retailers", "search_results",
                "search_connectors_status", "search_sort_by",
                "basket_savings", "savings_data", "export_ready",
                "export_shopping_list_text", "selected_items_for_basket",
                "planned_recipes", "recipe_search", "selected_category_tag"
            ]
            for key in keys_to_clear:
                if key in st.session_state:
                    del st.session_state[key]
            
            # Clear cart via backend
            try:
                session_id = get_or_create_session_id()
                cart_data = view_cart_backend(session_id)
                if cart_data and cart_data.get("items"):
                    # Remove all items from cart
                    for item in cart_data["items"]:
                        try:
                            remove_from_cart_backend(
                                session_id=session_id,
                                retailer=item.get("retailer", ""),
                                product_id=item.get("product_id", ""),
                                qty=item.get("quantity", 1)
                            )
                        except Exception:
                            pass  # Non-blocking: continue clearing other items
            except Exception:
                pass  # Non-blocking
            
            st.toast("✅ Done", icon="✅")
            st.rerun()
    
    with demo_col2:
        if st.button("Load demo basket", use_container_width=True, type="secondary"):
            # Load a small fixed set of example items
            demo_items = [
                {"retailer": "ah", "product_id": "demo-milk", "name": "Demo: Milk 1L", "price_eur": 1.25, "quantity": 1},
                {"retailer": "ah", "product_id": "demo-bread", "name": "Demo: Bread (wholegrain)", "price_eur": 1.80, "quantity": 1},
                {"retailer": "jumbo", "product_id": "demo-eggs", "name": "Demo: Eggs (10-pack)", "price_eur": 2.50, "quantity": 1},
                {"retailer": "ah", "product_id": "demo-fruit", "name": "Demo: Seasonal fruit", "price_eur": 3.00, "quantity": 1},
            ]
            
            try:
                session_id = get_or_create_session_id()
                added_count = 0
                for item in demo_items:
                    result = add_to_cart_backend(
                        session_id=session_id,
                        retailer=item["retailer"],
                        product_id=item["product_id"],
                        name=item["name"],
                        price_eur=item["price_eur"],
                        quantity=item["quantity"]
                    )
                    if result is not None:
                        added_count += 1
                
                if added_count > 0:
                    st.toast("✅ Done", icon="✅")
                else:
                    st.toast("⚠️ Error", icon="⚠️")
            except Exception as e:
                st.toast("⚠️ Error", icon="⚠️")
    
    with demo_col3:
        if st.button("Clear cache", use_container_width=True, type="secondary"):
            # Clear Streamlit cache
            st.cache_data.clear()
            st.toast("✅ Done", icon="✅")

st.markdown("---")
# Removed decorative image

# Footer
render_footer()

