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

from utils.api_client import get_health_status, get_backend_url
from utils.ui_components import render_header, render_backend_status

render_header("🔧 System Status", "Backend health and API documentation")

st.subheader("System Status")

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
        **API Documentation:**  
        [View API docs]({full_docs_url}) 📚
        """)
    
    with col2:
        st.caption("""
        The backend API powers product search and aggregation across
        Albert Heijn, Jumbo, and Picnic retailers.
        """)
    
    # Show raw status info in expander (optional, for debugging)
    with st.expander("📋 System Details"):
        if backend_status.get("raw"):
            st.json(backend_status["raw"])
else:
    st.caption("""
    The backend API is currently unreachable. Some features may not work properly.
    Please check your connection or try again later.
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
    
    - **Connector Uptime**: Real-time status for AH, Jumbo, and Picnic connectors
    - **Performance Metrics**: Average response times for search requests
    - **Error Tracking**: Recent API errors and error rates
    - **Request Volume**: Number of searches performed over time
    - **Service Health**: Overall system availability and reliability
    """)

