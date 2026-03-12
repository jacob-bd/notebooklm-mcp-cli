"""Tests for utils.cache module."""

import time
import pytest
from notebooklm_tools.utils.cache import NotebookCache, get_cache, reset_cache, TTL


class TestNotebookCache:
    """Test SQLite cache with TTL."""

    def test_set_and_get(self):
        cache = get_cache()
        cache.set("test:key", {"value": 42}, ttl=60)
        result = cache.get("test:key")
        assert result == {"value": 42}

    def test_miss_returns_none(self):
        cache = get_cache()
        assert cache.get("nonexistent:key") is None

    def test_expired_returns_none(self):
        cache = get_cache()
        cache.set("test:expired", "data", ttl=0)
        # TTL=0 means already expired
        time.sleep(0.01)
        assert cache.get("test:expired") is None

    def test_invalidate_prefix(self):
        cache = get_cache()
        cache.set("notebook:abc", {"id": "abc"}, ttl=60)
        cache.set("notebook:xyz", {"id": "xyz"}, ttl=60)
        cache.set("notebook_list", [1, 2, 3], ttl=60)

        cache.invalidate("notebook:abc")
        assert cache.get("notebook:abc") is None
        assert cache.get("notebook:xyz") is not None
        assert cache.get("notebook_list") is not None

    def test_clear_all(self):
        cache = get_cache()
        cache.set("key1", "val1", ttl=60)
        cache.set("key2", "val2", ttl=60)
        cache.clear_all()
        assert cache.get("key1") is None
        assert cache.get("key2") is None

    def test_list_entries(self):
        cache = get_cache()
        cache.set("test:a", {"x": 1}, ttl=300)
        cache.set("test:b", {"y": 2}, ttl=300)
        entries = cache.list_entries()
        keys = [e["key"] for e in entries]
        assert "test:a" in keys
        assert "test:b" in keys

    def test_list_entries_shows_ttl(self):
        cache = get_cache()
        cache.set("test:ttl", "data", ttl=300)
        entries = cache.list_entries()
        entry = next(e for e in entries if e["key"] == "test:ttl")
        assert entry["ttl_remaining_seconds"] > 0
        assert entry["ttl_remaining_seconds"] <= 300

    def test_large_value_compressed(self):
        cache = get_cache()
        large_value = {"data": "x" * 5000}
        cache.set("test:large", large_value, ttl=60)
        result = cache.get("test:large")
        assert result == large_value

    def test_overwrite_existing(self):
        cache = get_cache()
        cache.set("test:overwrite", "first", ttl=60)
        cache.set("test:overwrite", "second", ttl=60)
        assert cache.get("test:overwrite") == "second"

    def test_ttl_constants_exist(self):
        assert "notebook_list" in TTL
        assert "notebook" in TTL
        assert "notebook_summary" in TTL
        assert "source_guide" in TTL
        assert "source_content" in TTL
        assert "source_freshness" in TTL
        assert TTL["notebook_summary"] >= 86400  # at least 24hr for AI calls

    def test_singleton(self):
        c1 = get_cache()
        c2 = get_cache()
        assert c1 is c2

    def test_reset_creates_new_instance(self):
        c1 = get_cache()
        reset_cache()
        c2 = get_cache()
        assert c1 is not c2
