"""
Layout primitives for consistent page structure.

Provides reusable components for page headers, sections, cards, and KPI rows.
"""

from contextlib import contextmanager
from typing import Optional
import streamlit as st

# Import preferences utilities for preferences bar
try:
    from utils.profile import HOUSEHOLD_PROFILES, DEFAULT_PROFILE_KEY, get_profile_by_key
    from utils.preferences import (
        get_user_preferences_from_session,
        save_user_preferences_to_session,
        ALLOWED_DIETARY_TAGS,
        PREFERENCE_HEALTH_BALANCED,
        PREFERENCE_HEALTH_FIRST,
        PREFERENCE_BUDGET_FIRST,
    )
except ImportError:
    # Fallback if imports fail (shouldn't happen in normal usage)
    HOUSEHOLD_PROFILES = {}
    DEFAULT_PROFILE_KEY = "single"
    ALLOWED_DIETARY_TAGS = []
    PREFERENCE_HEALTH_BALANCED = "balanced"
    PREFERENCE_HEALTH_FIRST = "health_first"
    PREFERENCE_BUDGET_FIRST = "budget_first"


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


def render_basket_button(session_id: str, page_key: str) -> None:
    """
    Render a basket button for page headers with item count.
    
    Args:
        session_id: Session ID for getting cart data
        page_key: Unique key suffix for the button (e.g., "search", "health", "recipes")
                  Used to ensure unique button keys across pages
    """
    basket_count = get_basket_count(session_id)
    basket_label = f"🧺 Basket ({basket_count})" if basket_count > 0 else "🧺 Basket"
    if st.button(basket_label, key=f"header_basket_btn_{page_key}", use_container_width=True):
        st.switch_page("pages/03_🧺_My_Basket.py")


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


def preferences_summary_text() -> str:
    """
    Build a compact summary string of current preferences from session state.
    
    Returns:
        Compact summary like "1-person household · A bit of both · No dietary restrictions"
    """
    # Get household profile
    profile_key = st.session_state.get("household_profile_key", DEFAULT_PROFILE_KEY)
    profile = get_profile_by_key(profile_key)
    household_text = profile.label
    
    # Get health focus
    prefs = get_user_preferences_from_session()
    health_focus_map = {
        PREFERENCE_HEALTH_BALANCED: "A bit of both",
        PREFERENCE_HEALTH_FIRST: "Healthier choices first",
        PREFERENCE_BUDGET_FIRST: "Lowest prices first",
    }
    health_text = health_focus_map.get(prefs.health_focus, "A bit of both")
    
    # Get dietary preferences
    dietary_tags = prefs.dietary_tags or []
    if not dietary_tags:
        dietary_text = "No dietary restrictions"
    elif len(dietary_tags) == 1:
        # Map to friendly name
        dietary_map = {
            "vegetarian": "Vegetarian",
            "vegan": "Vegan",
            "halal": "Halal",
            "no_pork": "No pork",
            "lactose_free": "Lactose-free",
            "gluten_free": "Gluten-free",
            "low_sugar": "Low sugar",
        }
        dietary_text = dietary_map.get(dietary_tags[0], dietary_tags[0])
    else:
        dietary_text = f"{len(dietary_tags)} dietary preferences"
    
    return f"{household_text} · {health_text} · {dietary_text}"


def render_preferences_controls(mode: str, location_key: str) -> None:
    """
    Render household and food preferences controls.
    
    Args:
        mode: "expanded" (full controls) or "collapsed" (summary + expander)
        location_key: Unique key prefix for widget keys to avoid collisions
    """
    if mode == "expanded":
        # Full controls visible
        st.markdown("### Preferences")
        st.caption("Customize your shopping experience")
        
        # Household profile selector
        profile_keys = list(HOUSEHOLD_PROFILES.keys())
        profile_labels = [HOUSEHOLD_PROFILES[k].label for k in profile_keys]
        
        try:
            current_index = profile_keys.index(st.session_state.get("household_profile_key", DEFAULT_PROFILE_KEY))
        except ValueError:
            current_index = profile_keys.index(DEFAULT_PROFILE_KEY)
        
        selected_label = st.selectbox(
            "Household",
            options=profile_labels,
            index=current_index,
            help="We'll tailor servings and insights based on your household type.",
            key=f"{location_key}_household"
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
        
        st.markdown("---")
        
        # Health focus radio
        prefs = get_user_preferences_from_session()
        
        health_focus_label = st.radio(
            "Priority",
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
            key=f"{location_key}_priority"
        )
        
        # Dietary preferences multiselect
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
            help="We'll use this in your insights and recipe suggestions.",
            key=f"{location_key}_dietary"
        )
        
        # Save back to session
        prefs.health_focus = health_focus_label
        prefs.dietary_tags = dietary_selection
        save_user_preferences_to_session(prefs)
        
    elif mode == "collapsed":
        # Summary row + expander
        summary = preferences_summary_text()
        
        summary_col, edit_col = st.columns([4, 1])
        with summary_col:
            st.markdown(f"**{summary}**")
        with edit_col:
            with st.expander("Edit", expanded=False):
                render_preferences_controls("expanded", f"{location_key}_edit")


def preferences_bar(mode: str, location_key: str) -> None:
    """
    Render a preferences bar component (wrapped in card).
    
    Args:
        mode: "expanded" (full controls) or "collapsed" (summary + expander)
        location_key: Unique key prefix for widget keys
    """
    with card():
        render_preferences_controls(mode, location_key)

