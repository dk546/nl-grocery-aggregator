"""
In-process TTL cache for search queries.

This module provides a simple, lightweight cache for aggregated search results
to reduce redundant API calls to external retailers while keeping results fresh.

The cache is process-local and in-memory, with automatic expiration based on TTL.
"""

import time
from typing import Any, Dict, Hashable, Optional, Tuple

# Cache storage: Dict[Hashable, Tuple[float, Dict[str, Any]]]
# Key -> (timestamp, cached_value)
_SEARCH_CACHE: Dict[Hashable, Tuple[float, Dict[str, Any]]] = {}

# TTL in seconds - 60 seconds balances freshness with API call reduction
SEARCH_CACHE_TTL_SECONDS = 60


def make_search_cache_key(
    query: str,
    retailers: list[str],
    size: int,
    page: int,
    sort_by: Optional[str],
    health_filter: Optional[str],
) -> Hashable:
    """
    Create a deterministic cache key for a search request.
    
    Args:
        query: Search query string
        retailers: List of retailer identifiers
        size: Results per retailer
        page: Page number
        sort_by: Sort criterion
        health_filter: Health filter option
        
    Returns:
        Hashable cache key (tuple)
    """
    # Normalize query: lowercase and strip whitespace
    query_norm = query.strip().lower() if query else ""
    
    # Normalize retailers: sorted tuple for deterministic ordering
    retailers_key = tuple(sorted(retailers)) if retailers else ()
    
    # Normalize sort_by: use empty string for None
    sort_by_norm = sort_by or ""
    
    # Normalize health_filter: use "all" for None
    health_filter_norm = health_filter or "all"
    
    return (query_norm, retailers_key, size, page, sort_by_norm, health_filter_norm)


def get_cached_search(key: Hashable) -> Optional[Dict[str, Any]]:
    """
    Retrieve a cached search result if it exists and hasn't expired.
    
    Args:
        key: Cache key from make_search_cache_key()
        
    Returns:
        Cached result dictionary, or None if not found or expired
    """
    now = time.time()
    entry = _SEARCH_CACHE.get(key)
    
    if not entry:
        return None
    
    timestamp, value = entry
    
    # Check if expired
    if now - timestamp > SEARCH_CACHE_TTL_SECONDS:
        # Expired - remove from cache
        _SEARCH_CACHE.pop(key, None)
        return None
    
    # Cache hit - return cached value
    return value


def set_cached_search(key: Hashable, value: Dict[str, Any]) -> None:
    """
    Store a search result in the cache.
    
    Args:
        key: Cache key from make_search_cache_key()
        value: Result dictionary to cache (must be {"results": [...], "connectors_status": {...}})
    """
    _SEARCH_CACHE[key] = (time.time(), value)


def clear_cache() -> None:
    """Clear all cached search results (useful for testing)."""
    _SEARCH_CACHE.clear()


def get_cache_size() -> int:
    """Get the current number of cached entries (useful for monitoring)."""
    return len(_SEARCH_CACHE)

