"""Cache tools - Inspect and manage the API response cache."""

from typing import Any
from ._utils import logged_tool
from ...utils.cache import get_cache


@logged_tool()
def cache_list() -> dict[str, Any]:
    """List all cached entries with key, type, TTL remaining, and size.

    Returns a list of all active (non-expired) cache entries showing
    the cache key, value size, and seconds until expiry.
    """
    entries = get_cache().list_entries()
    return {
        "status": "success",
        "entries": entries,
        "count": len(entries),
    }


@logged_tool()
def cache_clear(key: str = "") -> dict[str, Any]:
    """Clear cache entries.

    Args:
        key: Cache key prefix to clear (e.g. 'notebook:abc123', 'notebook_list').
             Leave empty to clear ALL cached entries.

    Returns:
        Confirmation of what was cleared.
    """
    cache = get_cache()
    if key:
        cache.invalidate(key)
        return {"status": "success", "cleared": key, "message": f"Cleared cache entries matching prefix: {key}"}
    cache.clear_all()
    return {"status": "success", "cleared": "all", "message": "All cache entries cleared."}
