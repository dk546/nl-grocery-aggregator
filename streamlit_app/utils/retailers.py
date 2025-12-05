"""
Retailer configuration and mappings for the Streamlit UI.

This module provides central configuration for supported retailers,
display names, and mappings used throughout the UI.
"""

# Mapping from display labels (shown to users) to retailer codes (used in API)
RETAILER_OPTIONS = {
    "Albert Heijn": "ah",
    "Jumbo": "jumbo",
    "Picnic": "picnic",
    "Dirk": "dirk",
}

# Reverse mapping: retailer code -> display name
RETAILER_DISPLAY_NAMES = {
    "ah": "Albert Heijn",
    "jumbo": "Jumbo",
    "picnic": "Picnic",
    "dirk": "Dirk",
}

# Default list of retailers (all enabled by default)
DEFAULT_RETAILERS = ["Albert Heijn", "Jumbo", "Picnic", "Dirk"]

# List of all retailer codes (for backend API calls)
ALL_RETAILER_CODES = list(RETAILER_DISPLAY_NAMES.keys())


def get_retailer_display_name(retailer_code: str) -> str:
    """
    Get the human-readable display name for a retailer code.
    
    Args:
        retailer_code: Retailer identifier (e.g., "ah", "dirk")
    
    Returns:
        Display name (e.g., "Albert Heijn", "Dirk") or the code itself if not found
    """
    return RETAILER_DISPLAY_NAMES.get(retailer_code.lower(), retailer_code.title())

