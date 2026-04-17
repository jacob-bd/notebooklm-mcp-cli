"""Server tools - Server info and version checking."""

import json
import time
import urllib.request
from typing import Any, cast

from notebooklm_tools import __version__

from ._utils import logged_tool


def _get_latest_pypi_version() -> str | None:
    """Fetch the latest version from PyPI.

    Returns:
        Latest version string or None if fetch fails.
    """
    try:
        url = "https://pypi.org/pypi/notebooklm-mcp-cli/json"
        req = urllib.request.Request(url, headers={"User-Agent": "notebooklm-mcp-cli"})
        with urllib.request.urlopen(req, timeout=2) as response:
            data = cast(dict[str, Any], json.loads(response.read().decode()))
            info = data.get("info")
            if isinstance(info, dict):
                version = info.get("version")
                if isinstance(version, str):
                    return version
    except Exception:
        return None
    return None


def _compare_versions(current: str, latest: str) -> bool:
    """Compare version strings to determine if an update is available.

    Returns:
        True if latest is greater than current.
    """
    try:
        # Simple comparison: split by dots and compare numerically
        current_parts = [int(x) for x in current.split(".")]
        latest_parts = [int(x) for x in latest.split(".")]
        return latest_parts > current_parts
    except (ValueError, AttributeError):
        return False


def _check_auth_status() -> str:
    """Check local auth token state (no network call).

    Returns one of:
        configured  — tokens present and < 7 days old
        stale       — tokens present but > 7 days old
        not_configured — no tokens found
        error       — failed to check
    """
    try:
        from notebooklm_tools.core.auth import load_cached_tokens

        cached = load_cached_tokens()
        if not cached or not cached.cookies:
            return "not_configured"
        age_hours = (time.time() - cached.extracted_at) / 3600
        return "stale" if age_hours > 168 else "configured"
    except Exception:
        return "error"


@logged_tool()
def server_info() -> dict[str, Any]:
    """Get server version, check for updates, and report auth status.

    AI assistants: If update_available is True, inform the user that a new
    version is available and suggest updating with the provided command.

    Note: auth_status is a LOCAL check (token presence and age on disk).
    It does NOT make a live Google API call. A "configured" status means
    tokens exist and are recent — not that they are guaranteed valid.

    Returns:
        dict with version info:
        - version: Current installed version
        - latest_version: Latest version on PyPI (or None if check failed)
        - update_available: True if a newer version exists
        - auth_status: configured | stale | not_configured | error
        - update_command: Command to run to update
    """
    latest = _get_latest_pypi_version()
    update_available = False

    if latest:
        update_available = _compare_versions(__version__, latest)

    return {
        "status": "success",
        "version": __version__,
        "latest_version": latest,
        "update_available": update_available,
        "auth_status": _check_auth_status(),
        "update_command": "uv tool upgrade notebooklm-mcp-cli",
        "pip_update_command": "pip install --upgrade notebooklm-mcp-cli",
    }
