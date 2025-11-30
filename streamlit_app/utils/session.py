"""
Session management utilities for Streamlit pages.

This module provides functions for managing user sessions across Streamlit pages,
particularly for cart/basket operations that need to persist across navigation.
"""

import uuid
import streamlit as st

SESSION_ID_KEY = "session_id"


def get_or_create_session_id() -> str:
    """
    Get or create a persistent session ID stored in st.session_state.
    
    This function ensures that the same session ID is reused across all Streamlit pages
    within a single browser session. This allows the backend to associate cart/basket
    contents with a single logical user session.
    
    The session ID is stored in st.session_state which persists across page navigations
    within the same browser session. If the user refreshes the page or opens a new
    browser tab, a new session ID will be generated.
    
    Returns:
        Session ID string (UUID format)
        
    Example:
        >>> session_id = get_or_create_session_id()
        >>> # Use session_id for backend cart operations
        >>> cart = get_basket(session_id)
    """
    if SESSION_ID_KEY not in st.session_state:
        st.session_state[SESSION_ID_KEY] = str(uuid.uuid4())
    return st.session_state[SESSION_ID_KEY]

