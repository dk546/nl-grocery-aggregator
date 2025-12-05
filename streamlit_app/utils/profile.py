"""
Household Profile Module.

This module defines household profile types and provides helpers for accessing
the current user's profile. Profiles are used to customize messaging and
servings estimates throughout the app.
"""

from dataclasses import dataclass
from typing import Dict


@dataclass
class HouseholdProfile:
    """
    Represents a household profile type.
    
    Attributes:
        key: Unique identifier for the profile (e.g., "single", "couple")
        label: Human-readable label (e.g., "1-person household")
        description: Short description of the profile
        serving_multiplier: Multiplier for recipe servings (e.g., 2.0 for couple)
        typical_weekly_budget_hint: Optional hint for typical weekly budget (in EUR)
    """
    key: str
    label: str
    description: str
    serving_multiplier: float  # how many 'base servings' this profile typically needs
    typical_weekly_budget_hint: float | None = None  # optional, for messaging


HOUSEHOLD_PROFILES: Dict[str, HouseholdProfile] = {
    "single": HouseholdProfile(
        key="single",
        label="1-person household",
        description="You mainly shop just for yourself.",
        serving_multiplier=1.0,
        typical_weekly_budget_hint=40.0,
    ),
    "couple": HouseholdProfile(
        key="couple",
        label="2-person household",
        description="You shop for you and one other person.",
        serving_multiplier=2.0,
        typical_weekly_budget_hint=70.0,
    ),
    "family": HouseholdProfile(
        key="family",
        label="Family household",
        description="You shop for a family (e.g. 2 adults + kids).",
        serving_multiplier=4.0,
        typical_weekly_budget_hint=110.0,
    ),
    "student": HouseholdProfile(
        key="student",
        label="Student / shared flat",
        description="You're in a student or shared flat situation.",
        serving_multiplier=1.5,
        typical_weekly_budget_hint=50.0,
    ),
}


DEFAULT_PROFILE_KEY = "single"


def get_profile_by_key(key: str | None) -> HouseholdProfile:
    """
    Get a HouseholdProfile by its key.
    
    Args:
        key: Profile key (e.g., "single", "couple"). If None or invalid, returns default.
    
    Returns:
        HouseholdProfile instance (defaults to "single" if key is invalid)
    """
    if not key:
        return HOUSEHOLD_PROFILES[DEFAULT_PROFILE_KEY]
    return HOUSEHOLD_PROFILES.get(key, HOUSEHOLD_PROFILES[DEFAULT_PROFILE_KEY])

