"""Server tools - Server info and version checking."""

import json
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
    """Return the classic string status used by server_info.

    This is now a trivial, elegant wrapper around the single source of truth
    (`check_auth` in services/auth.py). All the real logic + tests live there.

    Maps the underlying AuthCheckResult.reason to a small set of stable
    statuses that are easier for agents to act on:

    - "configured"    — live check passed; credentials work.
    - "not_configured"— no credentials stored at all.
    - "stale"         — credentials are known-bad (expired, past the 7-day
                        heuristic, or the saved profile failed to load).
                        Operations against NotebookLM will fail until the
                        user runs `nlm login`.
    - "unverified"    — we could not confirm either way (network error,
                        non-200 HTTP, timeout). Cached credentials may
                        still work for actual API calls, so the previous
                        blanket "stale" label was misleading.
    - "error"         — unexpected exception inside the check itself.
    """
    try:
        from notebooklm_tools.services.auth import check_auth

        res = check_auth(live=True)

        if res.valid:
            return "configured"
        if res.reason == "no_tokens":
            return "not_configured"
        if res.reason in ("expired", "stale_heuristic") or (res.reason or "").startswith(
            "load_error"
        ):
            return "stale"
        if (res.reason or "").startswith("network_error") or (res.reason or "").startswith("http_"):
            return "unverified"
        # Unknown reason — be conservative.
        return "stale"
    except Exception:
        return "error"


@logged_tool()
def server_info() -> dict[str, Any]:
    """Get server version, check for updates, and report auth status.

    AI assistants: If update_available is True, inform the user that a new
    version is available and suggest updating with the provided command.

    auth_status now performs a best-effort *live* validation against
    NotebookLM (same mechanism as `nlm login --check`) when tokens exist.
    This makes the reported status consistent with actual usability instead
    of relying only on a local age heuristic.

    auth_status meanings:
    - "configured"     — live check passed; credentials are good.
    - "not_configured" — no credentials are stored (first-time setup).
    - "stale"          — credentials are known-bad (expired or past the
                         7-day heuristic). Operations will fail; ask the
                         user to run `nlm login` to refresh.
    - "unverified"     — the live check could not be completed (network
                         error, timeout, non-200 response). Cached
                         credentials may still work for actual API calls,
                         so do not assume the user needs to re-auth.
    - "error"          — unexpected exception inside the check itself.

    Returns:
        dict with version info:
        - version: Current installed version
        - latest_version: Latest version on PyPI (or None if check failed)
        - update_available: True if a newer version is available
        - auth_status: configured | stale | unverified | not_configured | error
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
