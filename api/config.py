"""
Configuration management for NL Grocery Aggregator.

This module centralizes environment variable loading from .env file at project root.
It should be imported early in both backend (api/main.py) and frontend (streamlit_app/app.py)
to ensure .env is loaded before any other code accesses environment variables.

On Render/production, .env will not exist, but load_dotenv() is safe to call and will no-op.
Environment variables from Render dashboard will be used instead.

Environment Variables:
- APIFY_TOKEN: Required for AH and Jumbo connectors (Apify API token)
- APIFY_AH_ACTOR_ID: Optional, defaults to "harvestedge/my-actor"
- APIFY_JUMBO_ACTOR_ID: Optional, defaults to "harvestedge/jumbo-supermarket-scraper"
- PICNIC_USERNAME: Required for Picnic connector
- PICNIC_PASSWORD: Required for Picnic connector
- PICNIC_COUNTRY_CODE: Optional, defaults to "NL"
- BACKEND_URL: Optional, backend URL (defaults to http://localhost:8000 for local dev)
"""

import os
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv
    _DOTENV_AVAILABLE = True
except ImportError:
    _DOTENV_AVAILABLE = False
    load_dotenv = None


def load_env_file() -> None:
    """
    Load environment variables from .env file at project root.
    
    This function locates the project root by going up from this file's location
    (api/config.py -> project root) and loads .env if it exists.
    
    Safe to call multiple times. On Render/production where .env doesn't exist,
    this is a no-op and platform environment variables will be used.
    """
    if _DOTENV_AVAILABLE and load_dotenv:
        # Get project root: api/config.py -> api/ -> project root
        this_file = Path(__file__).resolve()
        project_root = this_file.parent.parent
        env_path = project_root / ".env"
        
        # Load .env if it exists (override=False means existing env vars take precedence)
        load_dotenv(env_path, override=False)


# Load .env file on module import (if available)
# This happens when api.config or config.env is imported
load_env_file()


class ApifyConfig:
    """Configuration for Apify-based connectors (AH and Jumbo)."""
    
    @staticmethod
    def get_token() -> Optional[str]:
        """
        Get Apify API token from environment.
        
        Returns:
            Apify token string or None if not set
            
        Note:
            This does not raise an error - let connectors handle validation.
        """
        return os.getenv("APIFY_TOKEN")
    
    @staticmethod
    def get_ah_actor_id() -> str:
        """
        Get Albert Heijn Apify actor ID.
        
        Returns:
            Actor ID string (default: "harvestedge/my-actor")
        """
        return os.getenv("APIFY_AH_ACTOR_ID", "harvestedge/my-actor")
    
    @staticmethod
    def get_jumbo_actor_id() -> str:
        """
        Get Jumbo Apify actor ID.
        
        Returns:
            Actor ID string (default: "harvestedge/jumbo-supermarket-scraper")
        """
        return os.getenv("APIFY_JUMBO_ACTOR_ID", "harvestedge/jumbo-supermarket-scraper")


class PicnicConfig:
    """Configuration for Picnic connector."""
    
    @staticmethod
    def get_username() -> Optional[str]:
        """
        Get Picnic username from environment.
        
        Returns:
            Picnic username string or None if not set
        """
        return os.getenv("PICNIC_USERNAME")
    
    @staticmethod
    def get_password() -> Optional[str]:
        """
        Get Picnic password from environment.
        
        Returns:
            Picnic password string or None if not set
        """
        return os.getenv("PICNIC_PASSWORD")
    
    @staticmethod
    def get_country_code() -> str:
        """
        Get Picnic country code.
        
        Returns:
            Country code string (default: "NL")
        """
        return os.getenv("PICNIC_COUNTRY_CODE", "NL")


def get_required_env_vars() -> dict:
    """
    Get a dictionary of all required environment variables and their status.
    
    Returns:
        Dictionary with keys:
        - apify_token: bool (True if set)
        - picnic_username: bool (True if set)
        - picnic_password: bool (True if set)
    """
    return {
        "apify_token": ApifyConfig.get_token() is not None,
        "picnic_username": PicnicConfig.get_username() is not None,
        "picnic_password": PicnicConfig.get_password() is not None,
    }


def validate_required_config() -> None:
    """
    Validate that all required environment variables are set.
    
    Raises:
        RuntimeError: If any required configuration is missing
        
    Note:
        This is a convenience function. Connectors will also validate their
        own required configuration and raise RuntimeError if missing.
    """
    missing = []
    
    if not ApifyConfig.get_token():
        missing.append("APIFY_TOKEN (required for AH and Jumbo)")
    
    if not PicnicConfig.get_username():
        missing.append("PICNIC_USERNAME (required for Picnic)")
    
    if not PicnicConfig.get_password():
        missing.append("PICNIC_PASSWORD (required for Picnic)")
    
    if missing:
        raise RuntimeError(
            f"Missing required environment variables:\n" +
            "\n".join(f"  - {var}" for var in missing) +
            "\n\nPlease create a .env file at the project root with these variables."
        )

