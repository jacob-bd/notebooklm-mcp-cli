"""Shared test configuration and fixtures."""

import os

import pytest


def pytest_collection_modifyitems(config, items):
    """Auto-skip e2e tests unless NOTEBOOKLM_E2E=1 is set."""
    if os.environ.get('NOTEBOOKLM_E2E') == '1':
        return

    skip_e2e = pytest.mark.skip(reason='Set NOTEBOOKLM_E2E=1 to run e2e tests')
    for item in items:
        if 'e2e' in item.keywords:
            item.add_marker(skip_e2e)
