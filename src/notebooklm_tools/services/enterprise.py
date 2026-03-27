"""Enterprise service layer — bridges EnterpriseClient to MCP tool interface.

This module provides the same function signatures that MCP tools expect,
but routes through the Enterprise REST API (Discovery Engine) instead of
the personal batchexecute client.
"""

import os

from ..core.enterprise_client import EnterpriseClient

# Singleton client
_enterprise_client: EnterpriseClient | None = None


def get_enterprise_client() -> EnterpriseClient:
    """Get or create the enterprise API client."""
    global _enterprise_client
    if _enterprise_client is None:
        _enterprise_client = EnterpriseClient()
    return _enterprise_client


def reset_enterprise_client() -> None:
    """Reset the enterprise client (e.g. after token refresh)."""
    global _enterprise_client
    if _enterprise_client:
        _enterprise_client.close()
    _enterprise_client = None


def is_enterprise_mode() -> bool:
    """Check if we're in enterprise mode."""
    return os.environ.get("NOTEBOOKLM_MODE", "personal").lower() == "enterprise"
