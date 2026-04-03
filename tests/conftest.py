"""Test configuration — ensure tests always run in personal mode."""

import os

import pytest


@pytest.fixture(autouse=True)
def personal_mode_for_tests(monkeypatch):
    """Force personal mode during tests to avoid config.toml interference."""
    monkeypatch.setenv("NOTEBOOKLM_MODE", "personal")
    # Reset cached config so it picks up the env var
    from notebooklm_tools.utils.config import reset_config
    reset_config()
    yield
    reset_config()
