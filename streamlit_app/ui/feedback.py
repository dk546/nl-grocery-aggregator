"""
Standardized feedback utilities for consistent error, empty, and loading states.

Provides reusable components for displaying errors, empty states, and loading indicators
across all pages in a consistent manner.
"""

from contextlib import contextmanager
from typing import Optional
import streamlit as st


def show_error(message: str, hint: Optional[str] = None) -> None:
    """
    Display a standardized error message with optional hint.
    
    Args:
        message: Main error message to display
        hint: Optional hint text to help users resolve the issue
    """
    st.error(f"⚠️ {message}")
    if hint:
        st.caption(f"💡 {hint}")


def show_empty_state(
    title: str,
    subtitle: Optional[str] = None,
    action_label: str = "Get started",
    action_page_path: Optional[str] = None
) -> None:
    """
    Display a standardized empty state with optional action button.
    
    Args:
        title: Main empty state title
        subtitle: Optional subtitle/description text
        action_label: Label for the action button
        action_page_path: Optional page path to navigate to when button is clicked
    """
    st.info(f"📭 **{title}**")
    if subtitle:
        st.caption(subtitle)
    
    if action_page_path:
        if st.button(action_label, use_container_width=True, type="primary"):
            st.switch_page(action_page_path)


@contextmanager
def working_spinner(label: str = "Working…"):
    """
    Context manager wrapper for standardized loading spinners.
    
    Usage:
        with working_spinner("Preparing…"):
            # Do work here
            pass
    
    Args:
        label: Spinner label text (default: "Working…")
    """
    with st.spinner(label):
        yield

