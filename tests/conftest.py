"""Shared test fixtures."""

import pytest
from notebooklm_tools.utils.cache import get_cache, reset_cache


@pytest.fixture(autouse=True)
def clear_cache():
    """Reset the SQLite cache and clear all entries between tests."""
    try:
        get_cache().clear_all()
    except Exception:
        pass
    reset_cache()
    yield
    try:
        get_cache().clear_all()
    except Exception:
        pass
    reset_cache()
