from typing import Any
import typer
from rich.console import Console
from notebooklm_tools.core.client import NotebookLMClient
from notebooklm_tools.core.auth import load_cached_tokens, AuthManager
from notebooklm_tools.utils.config import get_config

console = Console()

def get_client(profile: str | None = None) -> NotebookLMClient:
    """Get an authenticated NotebookLM client.

    Args:
        profile: Optional profile name. Uses config default_profile if not specified.

    Tries to load cached tokens first. If unavailable, guides the user to login.
    """
    # 1. Try environment variables first (most explicit)
    import os
    env_cookies = os.environ.get("NOTEBOOKLM_COOKIES")
    if env_cookies:
        return NotebookLMClient(cookies=extract_cookies_from_string(env_cookies))

    # 2. Try loading specified profile, or fall back to config default
    if not profile:
        profile = get_config().auth.default_profile
    manager = AuthManager(profile)
    if not manager.profile_exists():
        console.print(f"[red]Error:[/red] Profile '{manager.profile_name}' not found. Run 'nlm login' first.")
        raise typer.Exit(1)

    try:
        p = manager.load_profile()
        return NotebookLMClient(
            cookies=p.cookies,
            csrf_token=p.csrf_token or "",
            session_id=p.session_id or "",
        )
    except Exception:
        # No valid profile found
        console.print("[yellow]No authentication found.[/yellow]")
        console.print("Please run: [bold]nlm login[/bold]")
        raise typer.Exit(1)

def handle_error(e: Exception) -> None:
    """Standard error handler for CLI commands."""
    from notebooklm_tools.core.client import NotebookLMError
    
    if isinstance(e, typer.Exit):
        raise e
        
    if isinstance(e, NotebookLMError):
        console.print(f"[red]Error:[/red] {str(e)}")
    else:
        # Unexpected error
        console.print(f"[red]Unexpected Error:[/red] {str(e)}")
        # Only show traceback in debug mode? For now, keep it simple.
    
    raise typer.Exit(1)

def extract_cookies_from_string(cookie_str: str) -> dict[str, str]:
    """Helper to parse raw cookie string."""
    cookies = {}
    if not cookie_str:
        return cookies
    for item in cookie_str.split(";"):
        if "=" in item:
            key, value = item.split("=", 1)
            cookies[key.strip()] = value.strip()
    return cookies


# ========== Version Check Utilities ==========

import json
import os
import time
import urllib.request
from pathlib import Path

from notebooklm_tools import __version__


def _get_cache_path() -> Path:
    """Get path to version check cache file."""
    cache_dir = Path.home() / ".notebooklm-mcp-cli"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / "update_check.json"


def _get_cached_version_info() -> dict | None:
    """Load cached version info if still valid (within 24 hours)."""
    cache_path = _get_cache_path()
    if not cache_path.exists():
        return None
    
    try:
        with open(cache_path) as f:
            data = json.load(f)
        
        # Check if cache is still valid (24 hours = 86400 seconds)
        if time.time() - data.get("checked_at", 0) < 86400:
            return data
    except (json.JSONDecodeError, OSError):
        pass
    
    return None


def _save_version_cache(latest_version: str) -> None:
    """Save version info to cache."""
    cache_path = _get_cache_path()
    try:
        with open(cache_path, "w") as f:
            json.dump({
                "latest_version": latest_version,
                "checked_at": time.time(),
            }, f)
    except OSError:
        pass  # Silently ignore cache write failures


def _fetch_latest_version() -> str | None:
    """Fetch latest version from PyPI with 2 second timeout."""
    try:
        url = "https://pypi.org/pypi/notebooklm-mcp-cli/json"
        req = urllib.request.Request(url, headers={"User-Agent": "notebooklm-mcp-cli"})
        with urllib.request.urlopen(req, timeout=2) as response:
            data = json.loads(response.read().decode())
            return data.get("info", {}).get("version")
    except Exception:
        return None


def _compare_versions(current: str, latest: str) -> bool:
    """Compare version strings. Returns True if latest > current."""
    try:
        current_parts = [int(x) for x in current.split(".")]
        latest_parts = [int(x) for x in latest.split(".")]
        return latest_parts > current_parts
    except (ValueError, AttributeError):
        return False


def check_for_updates() -> tuple[bool, str | None]:
    """Check if a new version is available.
    
    Returns:
        Tuple of (update_available, latest_version).
        Uses cached result if available and fresh.
    """
    # Check cache first
    cached = _get_cached_version_info()
    if cached:
        latest = cached.get("latest_version")
        if latest:
            return _compare_versions(__version__, latest), latest
    
    # Fetch from PyPI
    latest = _fetch_latest_version()
    if latest:
        _save_version_cache(latest)
        return _compare_versions(__version__, latest), latest
    
    return False, None


def print_update_notification() -> None:
    """Print update notification if available. Call after command execution."""
    # Only show in TTY (not when piping output)
    import sys
    if not sys.stdout.isatty():
        return
    
    update_available, latest = check_for_updates()
    if update_available and latest:
        console.print()
        console.print(
            f"[dim]🔔 Update available:[/dim] [cyan]{__version__}[/cyan] → [green]{latest}[/green]. "
            f"[dim]Run[/dim] [bold]uv tool upgrade notebooklm-mcp-cli[/bold] [dim]to update.[/dim]"
        )
