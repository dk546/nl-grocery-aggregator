"""
User Preferences Module.

This module defines user preferences for health focus and dietary restrictions.
Preferences are stored in st.session_state and persist across page navigations.

Preferences are used to:
- Re-rank Smart Swaps suggestions (health-first vs budget-first vs balanced)
- Adjust Health Insights page messaging
- Guide future recipe suggestions and filtering (when implemented)
"""

from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional

import streamlit as st

# Health focus preference constants
PREFERENCE_HEALTH_BALANCED = "balanced"
PREFERENCE_HEALTH_FIRST = "health_first"
PREFERENCE_BUDGET_FIRST = "budget_first"

ALLOWED_HEALTH_FOCUS = [
    PREFERENCE_HEALTH_BALANCED,
    PREFERENCE_HEALTH_FIRST,
    PREFERENCE_BUDGET_FIRST,
]

# Dietary preference tags
ALLOWED_DIETARY_TAGS = [
    "vegetarian",
    "vegan",
    "halal",
    "no_pork",
    "lactose_free",
    "gluten_free",
    "low_sugar",
]

# Session state key for user preferences
SESSION_KEY_USER_PREFS = "user_preferences"


@dataclass
class UserPreferences:
    """
    User preferences for health focus and dietary restrictions.
    
    Attributes:
        health_focus: One of "balanced", "health_first", or "budget_first"
        dietary_tags: List of dietary preference tags (e.g., ["vegetarian", "halal"])
    """
    health_focus: str = PREFERENCE_HEALTH_BALANCED
    dietary_tags: List[str] = None

    def __post_init__(self):
        """Ensure dietary_tags is a list."""
        if self.dietary_tags is None:
            self.dietary_tags = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert preferences to a dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserPreferences":
        """
        Create UserPreferences from a dictionary.
        
        Args:
            data: Dictionary with 'health_focus' and/or 'dietary_tags' keys
            
        Returns:
            UserPreferences instance with validated values
        """
        if not data:
            return cls()

        health_focus = data.get("health_focus", PREFERENCE_HEALTH_BALANCED)
        dietary_tags = data.get("dietary_tags") or []

        # Validate health_focus
        if health_focus not in ALLOWED_HEALTH_FOCUS:
            health_focus = PREFERENCE_HEALTH_BALANCED

        # Filter dietary_tags to only allowed values
        dietary_tags = [t for t in dietary_tags if t in ALLOWED_DIETARY_TAGS]

        return cls(health_focus=health_focus, dietary_tags=dietary_tags)


def get_user_preferences_from_session() -> UserPreferences:
    """
    Get user preferences from session state.
    
    Returns:
        UserPreferences instance (defaults if not set)
        
    This function ensures preferences are initialized in session state.
    """
    raw = st.session_state.get(SESSION_KEY_USER_PREFS)

    if isinstance(raw, UserPreferences):
        return raw

    if isinstance(raw, dict):
        prefs = UserPreferences.from_dict(raw)
    else:
        prefs = UserPreferences()

    # Store in session state for persistence
    st.session_state[SESSION_KEY_USER_PREFS] = prefs

    return prefs


def save_user_preferences_to_session(prefs: UserPreferences) -> None:
    """
    Save user preferences to session state.
    
    Args:
        prefs: UserPreferences instance to save
    """
    st.session_state[SESSION_KEY_USER_PREFS] = prefs

