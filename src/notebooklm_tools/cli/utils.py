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
