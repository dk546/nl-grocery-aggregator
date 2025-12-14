"""
Layout primitives for consistent page structure.

Provides reusable components for page headers, sections, cards, and KPI rows.
"""

from contextlib import contextmanager
from typing import Optional
import streamlit as st


def get_basket_count(session_id: str) -> int:
    """
    Get current basket item count for display.
    
    Args:
        session_id: Session ID for getting cart data
        
    Returns:
        Number of items in basket, or 0 if empty/error
    """
    try:
        from streamlit_app.utils.api_client import view_cart_backend
        
        cart_data = view_cart_backend(session_id)
        if cart_data and cart_data.get("items"):
            return len(cart_data["items"])
        return 0
    except Exception:
        return 0


def page_header(title: str, subtitle: Optional[str] = None, right: Optional[callable] = None) -> None:
    """
    Render a consistent page header with title and optional subtitle.
    
    Args:
        title: Main page title
        subtitle: Optional subtitle/description text
        right: Optional callable that renders right-side content (e.g., buttons, badges)
    """
    if right is not None:
        col_title, col_right = st.columns([3, 1])
        with col_title:
            st.markdown(f'<div class="nlga-page-header">', unsafe_allow_html=True)
            st.markdown(f"# {title}")
            if subtitle:
                st.markdown(f'<div class="subtitle">{subtitle}</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        with col_right:
            right()  # Call the function to render content
    else:
        st.markdown(f'<div class="nlga-page-header">', unsafe_allow_html=True)
        st.markdown(f"# {title}")
        if subtitle:
            st.markdown(f'<div class="subtitle">{subtitle}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)


def kpi_row(kpis: list[dict]) -> None:
    """
    Render a row of KPI metrics.
    
    Args:
        kpis: List of dicts with keys:
            - label: KPI label text
            - value: KPI value (number or string)
            - delta: Optional delta/change indicator
            - icon: Optional emoji or icon prefix
    """
    cols = st.columns(len(kpis))
    for col, kpi in zip(cols, kpis):
        with col:
            label = kpi.get("label", "")
            value = kpi.get("value", "")
            delta = kpi.get("delta", None)
            icon = kpi.get("icon", "")
            
            display_label = f"{icon} {label}" if icon else label
            st.metric(
                label=display_label,
                value=value,
                delta=delta
            )


def section(title: str, caption: Optional[str] = None) -> None:
    """
    Render a section header with optional caption.
    
    Args:
        title: Section title
        caption: Optional caption/help text below title
    """
    st.markdown(f'<div class="nlga-section">', unsafe_allow_html=True)
    st.markdown(f'<div class="nlga-section-title">', unsafe_allow_html=True)
    st.markdown(f"## {title}")
    st.markdown('</div>', unsafe_allow_html=True)
    if caption:
        st.markdown(f'<div class="nlga-section-caption">{caption}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


@contextmanager
def card(title: Optional[str] = None):
    """
    Context manager for a card container.
    
    Usage:
        with card("Card Title"):
            st.write("Card content")
    
    Args:
        title: Optional card title
    """
    st.markdown('<div class="nlga-card">', unsafe_allow_html=True)
    if title:
        st.markdown(f"### {title}")
    yield
    st.markdown('</div>', unsafe_allow_html=True)

