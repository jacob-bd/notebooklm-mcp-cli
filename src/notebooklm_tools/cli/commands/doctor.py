"""Diagnostic command for troubleshooting NotebookLM MCP setup."""

import shutil
import platform
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

console = Console()
app = typer.Typer(
    name="doctor",
    help="Diagnose NotebookLM MCP installation and configuration",
    invoke_without_command=True,
)


@app.callback(invoke_without_command=True)
def doctor(
    ctx: typer.Context,
    verbose: bool = typer.Option(
        False, "--verbose", "-v",
        help="Show additional diagnostic details",
    ),
) -> None:
    """
    Run diagnostics on your NotebookLM MCP installation.

    Checks installation, authentication, Chrome profile, and AI tool
    configurations. Suggests fixes for common issues.

    Examples:
        nlm doctor
        nlm doctor --verbose
    """
    if ctx.invoked_subcommand is not None:
        return

    console.print("[bold]NotebookLM MCP Doctor[/bold]\n")

    all_ok = True
    all_ok &= _check_installation(verbose)
    console.print()
    all_ok &= _check_authentication(verbose)
    console.print()
    all_ok &= _check_chrome(verbose)
    console.print()
    all_ok &= _check_clients(verbose)
    console.print()

    if all_ok:
        console.print("[green]✓ All checks passed![/green]")
    else:
        console.print("[yellow]Some issues found.[/yellow] See suggestions above.")


def _check_installation(verbose: bool) -> bool:
    """Check that the package and binaries are properly installed."""
    console.print("[bold]Installation[/bold]")
    ok = True

    # Package version
    try:
        from notebooklm_tools import __version__
        console.print(f"  notebooklm-mcp-cli: [green]{__version__}[/green]")
    except ImportError:
        console.print(f"  notebooklm-mcp-cli: [red]not importable[/red]")
        ok = False

    # Binary paths
    for cmd in ["nlm", "notebooklm-mcp"]:
        path = shutil.which(cmd)
        if path:
            console.print(f"  {cmd}: [green]{path}[/green]")
        else:
            console.print(f"  {cmd}: [red]not found in PATH[/red]")
            ok = False

    # Python version
    if verbose:
        import sys
        console.print(f"  python: [dim]{sys.executable} ({platform.python_version()})[/dim]")
        console.print(f"  platform: [dim]{platform.system()} {platform.machine()}[/dim]")

    return ok


def _check_authentication(verbose: bool) -> bool:
    """Check authentication status."""
    console.print("[bold]Authentication[/bold]")
    ok = True

    from notebooklm_tools.core.auth import AuthManager
    from notebooklm_tools.utils.config import get_config

    config = get_config()
    default_profile = config.auth.default_profile
    profiles = AuthManager.list_profiles()

    if not profiles:
        console.print(f"  Profiles: [red]none[/red]")
        console.print(f"  [yellow]→[/yellow] Run [cyan]nlm login[/cyan] to authenticate")
        return False

    console.print(f"  Default profile: [cyan]{default_profile}[/cyan]")
    console.print(f"  Profiles found: {len(profiles)}")

    # Check default profile
    try:
        auth = AuthManager(default_profile)
        if auth.profile_exists():
            profile = auth.load_profile()

            has_cookies = bool(profile.cookies)
            has_csrf = bool(profile.csrf_token)
            email = profile.email or "unknown"

            if has_cookies:
                console.print(f"  Cookies: [green]present[/green] ({len(profile.cookies)} cookies)")
            else:
                console.print(f"  Cookies: [red]missing[/red]")
                ok = False

            console.print(f"  CSRF token: {'[green]yes[/green]' if has_csrf else '[yellow]no[/yellow] (will auto-extract)'}")
            console.print(f"  Account: {email}")

            if verbose:
                # Show last validated time
                last_validated = getattr(profile, "last_validated", None)
                if last_validated:
                    console.print(f"  Last validated: [dim]{last_validated}[/dim]")
        else:
            console.print(f"  Profile '{default_profile}': [red]not found[/red]")
            console.print(f"  [yellow]→[/yellow] Run [cyan]nlm login[/cyan] to create it")
            ok = False
    except Exception as e:
        console.print(f"  Profile '{default_profile}': [red]error loading[/red] ({e})")
        ok = False

    # Show other profiles
    if verbose and len(profiles) > 1:
        console.print(f"  Other profiles: {', '.join(p for p in profiles if p != default_profile)}")

    return ok


def _check_chrome(verbose: bool) -> bool:
    """Check Chrome installation and saved profile."""
    console.print("[bold]Chrome[/bold]")
    ok = True

    # Chrome binary
    system = platform.system()
    if system == "Darwin":
        chrome_path = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
    elif system == "Windows":
        chrome_path = Path("C:/Program Files/Google/Chrome/Application/chrome.exe")
        if not chrome_path.exists():
            chrome_path = Path("C:/Program Files (x86)/Google/Chrome/Application/chrome.exe")
    else:
        chrome_path = Path(shutil.which("google-chrome") or shutil.which("chromium") or "")

    if chrome_path.exists():
        console.print(f"  Chrome: [green]installed[/green]")
        if verbose:
            console.print(f"  [dim]{chrome_path}[/dim]")
    else:
        console.print(f"  Chrome: [red]not found[/red]")
        console.print(f"  [yellow]→[/yellow] Chrome is required for authentication")
        ok = False

    # Saved Chrome profile
    from notebooklm_tools.utils.config import get_storage_dir

    chrome_profiles_dir = get_storage_dir() / "chrome-profiles"
    has_profile = False

    if chrome_profiles_dir.exists():
        for profile_dir in chrome_profiles_dir.iterdir():
            if profile_dir.is_dir() and (profile_dir / "Default").exists():
                has_profile = True
                console.print(f"  Saved profile: [green]{profile_dir.name}[/green]")
                if verbose:
                    console.print(f"  [dim]{profile_dir}[/dim]")

    # Also check legacy location
    legacy_chrome = get_storage_dir() / "chrome-profile"
    if legacy_chrome.exists() and (legacy_chrome / "Default").exists():
        has_profile = True
        if verbose:
            console.print(f"  Legacy profile: [dim]{legacy_chrome}[/dim]")

    if has_profile:
        console.print(f"  Headless auth: [green]available[/green] (saved Google login)")
    else:
        console.print(f"  Headless auth: [yellow]not available[/yellow] (no saved profile)")
        console.print(f"  [dim]Run nlm login once to save Chrome profile for headless refresh[/dim]")

    return ok


def _check_clients(verbose: bool) -> bool:
    """Check AI tool MCP configurations."""
    console.print("[bold]AI Tool Configurations[/bold]")

    # Import setup module for config detection
    from notebooklm_tools.cli.commands.setup import (
        CLIENT_REGISTRY,
        _claude_desktop_config_path,
        _gemini_config_path,
        _cursor_config_path,
        _windsurf_config_path,
        _read_json_config,
        _is_configured,
    )

    import subprocess

    configured_count = 0
    total_count = 0

    for client_id, info in CLIENT_REGISTRY.items():
        if not info["has_auto_setup"]:
            continue
        total_count += 1

        status = None

        if client_id == "claude-code":
            claude_cmd = shutil.which("claude")
            if claude_cmd:
                try:
                    result = subprocess.run(
                        [claude_cmd, "mcp", "list"],
                        capture_output=True, text=True, timeout=5,
                    )
                    if "notebooklm" in result.stdout.lower():
                        status = True
                except (subprocess.TimeoutExpired, OSError):
                    pass
            elif not claude_cmd:
                if verbose:
                    console.print(f"  {info['name']}: [dim]not installed[/dim]")
                continue

        elif client_id == "claude-desktop":
            path = _claude_desktop_config_path()
            config = _read_json_config(path)
            status = _is_configured(config)

        elif client_id == "gemini":
            path = _gemini_config_path()
            config = _read_json_config(path)
            status = _is_configured(config, "notebooklm")

        elif client_id == "cursor":
            path = _cursor_config_path()
            config = _read_json_config(path)
            status = _is_configured(config)

        elif client_id == "windsurf":
            path = _windsurf_config_path()
            config = _read_json_config(path)
            status = _is_configured(config)

        if status is True:
            console.print(f"  {info['name']}: [green]configured[/green]")
            configured_count += 1
        elif status is False:
            console.print(f"  {info['name']}: [yellow]not configured[/yellow]  → [cyan]nlm setup add {client_id}[/cyan]")
        # None means we couldn't determine (already printed)

    if configured_count == 0:
        console.print(f"\n  [yellow]No AI tools configured.[/yellow]")
        console.print(f"  Run [cyan]nlm setup add <client>[/cyan] to configure one.")
        return False

    return True
