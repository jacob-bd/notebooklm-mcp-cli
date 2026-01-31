"""Server tools - Server info and version checking."""

import urllib.request
import json
from typing import Any

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
            data = json.loads(response.read().decode())
            return data.get("info", {}).get("version")
    except Exception:
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


@logged_tool()
def server_info() -> dict[str, Any]:
    """Get server version and check for updates.
    
    AI assistants: If update_available is True, inform the user that a new
    version is available and suggest updating with the provided command.
    
    Returns:
        dict with version info:
        - version: Current installed version
        - latest_version: Latest version on PyPI (or None if check failed)
        - update_available: True if a newer version exists
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
        "update_command": "uv tool upgrade notebooklm-mcp-cli",
        "pip_update_command": "pip install --upgrade notebooklm-mcp-cli",
    }
