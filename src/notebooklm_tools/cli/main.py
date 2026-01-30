"""Main CLI application for NotebookLM Tools."""

from typing import Optional

import typer
from rich.console import Console

from notebooklm_tools import __version__
from notebooklm_tools.cli.commands.chat import app as chat_app
from notebooklm_tools.cli.commands.notebook import app as notebook_app
from notebooklm_tools.cli.commands.note import app as note_app
from notebooklm_tools.cli.commands.research import app as research_app
from notebooklm_tools.cli.commands.source import app as source_app
from notebooklm_tools.cli.commands.alias import app as alias_app
from notebooklm_tools.cli.commands.config import app as config_app
from notebooklm_tools.cli.commands.skill import app as skill_app
from notebooklm_tools.cli.commands.studio import (
    app as studio_app,
    audio_app,
    data_table_app,
    flashcards_app,
    infographic_app,
    mindmap_app,
    quiz_app,
    report_app,
    slides_app,
    video_app,
)
from notebooklm_tools.cli.commands.download import app as download_app
from notebooklm_tools.cli.commands.share import app as share_app
from notebooklm_tools.cli.commands.export import app as export_app
from notebooklm_tools.cli.commands.verbs import (
    create_app,
    list_app,
    get_app,
    delete_app,
    add_app,
    rename_app,
    status_app,
    describe_app,
    query_app,
    sync_app,
    content_app,
    stale_app,
    configure_app,
    set_app,
    show_app,
    install_app,
    uninstall_app,
)

console = Console()

# Main application
app = typer.Typer(
    name="nlm",
    help="NotebookLM Tools - Unified CLI for Google NotebookLM",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

# =============================================================================
# LOGIN app with nested profile commands
# =============================================================================

login_app = typer.Typer(
    help="Authentication and profile management",
    rich_markup_mode="rich",
    no_args_is_help=True,
)

# Profile management subcommands
profile_app = typer.Typer(
    help="Manage authentication profiles",
    rich_markup_mode="rich",
    no_args_is_help=True,
)


@login_app.callback(invoke_without_command=True)
def login_callback(
    ctx: typer.Context,
    manual: bool = typer.Option(
        False, "--manual", "-m",
        help="Manually provide cookies from a file",
    ),
    check: bool = typer.Option(
        False, "--check",
        help="Only check if current auth is valid",
    ),
    profile: str = typer.Option(
        "default", "--profile", "-p",
        help="Profile name to save credentials to",
    ),
    cookie_file: Optional[str] = typer.Option(
        None, "--file", "-f",
        help="Path to file containing cookies (for manual mode)",
    ),
) -> None:
    """
    Authenticate with NotebookLM.

    Default: Uses Chrome DevTools Protocol to extract cookies automatically.
    Use --manual to import cookies from a file.
    Use --check to validate existing credentials.
    """
    from notebooklm_tools.core.auth import AuthManager
    from notebooklm_tools.core.exceptions import NLMError

    # If a subcommand is invoked, don't run login logic
    if ctx.invoked_subcommand is not None:
        return

    auth = AuthManager(profile)

    if check:
        # Check existing auth by making a real API call
        try:
            from notebooklm_tools.core.client import NotebookLMClient

            p = auth.load_profile()
            console.print(f"[dim]Checking credentials for profile: {p.name}...[/dim]")

            # Actually test the API using profile's credentials
            with NotebookLMClient(
                cookies=p.cookies,
                csrf_token=p.csrf_token or "",
                session_id=p.session_id or "",
            ) as client:
                notebooks = client.list_notebooks()

            # Success! Update last validated
            auth.save_profile(
                cookies=p.cookies,
                csrf_token=p.csrf_token,
                session_id=p.session_id,
                email=p.email,
            )

            console.print(f"[green]✓[/green] Authentication valid!")
            console.print(f"  Profile: {p.name}")
            console.print(f"  Notebooks found: {len(notebooks)}")
            if p.email:
                console.print(f"  Account: {p.email}")
        except NLMError as e:
            console.print(f"[red]✗[/red] Authentication failed: {e.message}")
            if e.hint:
                console.print(f"[dim]{e.hint}[/dim]")
            raise typer.Exit(2)
        return

    if manual:
        # Manual mode - read from file
        if not cookie_file:
            cookie_file = typer.prompt(
                "Enter path to file containing cookies",
                default="~/.nlm/cookies.txt",
            )
        try:
            profile_obj = auth.login_with_file(cookie_file)
            console.print(f"[green]✓[/green] Successfully authenticated!")
            console.print(f"  Profile saved: {profile}")
            console.print(f"  Credentials saved to: {auth.profile_dir}")
        except NLMError as e:
            console.print(f"[red]Error:[/red] {e.message}")
            if e.hint:
                console.print(f"\n[dim]Hint: {e.hint}[/dim]")
            raise typer.Exit(1)
        return

    # Default: CDP mode - Chrome DevTools Protocol
    console.print("[bold]Launching Chrome for authentication...[/bold]")
    console.print("[dim]Using Chrome DevTools Protocol[/dim]\n")

    try:
        from notebooklm_tools.utils.cdp import extract_cookies_via_cdp, terminate_chrome
        from notebooklm_tools.utils.config import check_migration_sources, run_migration, get_storage_dir

        # Check if we need to migrate from legacy packages
        # IMPORTANT: Don't use get_chrome_profile_dir() here as it creates the directory,
        # which would prevent migration from running
        chrome_profile = get_storage_dir() / "chrome-profile"
        profile_exists = chrome_profile.exists() and (
            (chrome_profile / "Default").exists() or (chrome_profile / "Local State").exists()
        )

        if not profile_exists:
            sources = check_migration_sources()
            if sources["chrome_profiles"]:
                console.print("[yellow]Found Chrome profile from legacy installation![/yellow]")
                for src in sources["chrome_profiles"]:
                    console.print(f"  [dim]{src}[/dim]")
                console.print("[dim]Migrating to new location...[/dim]")

                actions = run_migration(dry_run=False)
                for action in actions:
                    console.print(f"  [green]✓[/green] {action}")
                console.print()

        console.print("Starting Chrome...")
        result = extract_cookies_via_cdp(
            auto_launch=True,
            wait_for_login=True,
            login_timeout=300,
            profile_name=profile,
        )

        cookies = result["cookies"]
        csrf_token = result.get("csrf_token", "")
        session_id = result.get("session_id", "")
        email = result.get("email", "")

        # Save to profile
        auth.save_profile(
            cookies=cookies,
            csrf_token=csrf_token,
            session_id=session_id,
            email=email,
        )

        # Close Chrome to release profile lock (enables headless auth later)
        console.print("[dim]Closing Chrome...[/dim]")
        terminate_chrome()

        console.print(f"\n[green]✓[/green] Successfully authenticated!")
        console.print(f"  Profile: {profile}")
        console.print(f"  Cookies: {len(cookies)} extracted")
        console.print(f"  CSRF Token: {'Yes' if csrf_token else 'No (will be auto-extracted)'}")
        if email:
            console.print(f"  Account: {email}")
        console.print(f"  Credentials saved to: {auth.profile_dir}")

    except NLMError as e:
        console.print(f"\n[red]Error:[/red] {e.message}")
        if e.hint:
            console.print(f"\n[dim]Hint: {e.hint}[/dim]")
        raise typer.Exit(1)


@profile_app.command("list")
def profile_list() -> None:
    """List all authentication profiles."""
    from notebooklm_tools.core.auth import AuthManager

    profiles = AuthManager.list_profiles()

    if not profiles:
        console.print("[dim]No profiles found.[/dim]")
        console.print("\nRun 'nlm login' to create a profile.")
        return

    console.print("[bold]Available profiles:[/bold]")
    for name in profiles:
        try:
            auth = AuthManager(name)
            p = auth.load_profile()
            email = p.email or "Unknown"
            console.print(f"  [cyan]{name}[/cyan]: {email}")
        except Exception:
            console.print(f"  [cyan]{name}[/cyan]: [dim](invalid)[/dim]")


@profile_app.command("delete")
def profile_delete(
    profile: str = typer.Argument(..., help="Profile name to delete"),
    confirm: bool = typer.Option(
        False, "--confirm", "-y",
        help="Skip confirmation prompt",
    ),
) -> None:
    """Delete a profile and its credentials."""
    from notebooklm_tools.core.auth import AuthManager

    auth = AuthManager(profile)

    if not auth.profile_exists():
        console.print(f"[red]Error:[/red] Profile '{profile}' not found")
        raise typer.Exit(1)

    if not confirm:
        typer.confirm(
            f"Are you sure you want to delete profile '{profile}'?",
            abort=True,
        )

    auth.delete_profile()
    console.print(f"[green]✓[/green] Deleted profile: {profile}")


@profile_app.command("rename")
def profile_rename(
    old_name: str = typer.Argument(..., help="Current profile name"),
    new_name: str = typer.Argument(..., help="New profile name"),
) -> None:
    """Rename an authentication profile."""
    from notebooklm_tools.core.auth import AuthManager
    from notebooklm_tools.core.exceptions import NLMError

    # Check if old profile exists
    old_auth = AuthManager(old_name)
    if not old_auth.profile_exists():
        console.print(f"[red]Error:[/red] Profile '{old_name}' not found")
        raise typer.Exit(1)

    # Check if new profile name already exists
    new_auth = AuthManager(new_name)
    if new_auth.profile_exists():
        console.print(f"[red]Error:[/red] Profile '{new_name}' already exists")
        raise typer.Exit(1)

    try:
        # Load old profile data
        profile_data = old_auth.load_profile()

        # Save with new name
        new_auth.save_profile(
            cookies=profile_data.cookies,
            csrf_token=profile_data.csrf_token,
            session_id=profile_data.session_id,
            email=profile_data.email,
        )

        # Delete old profile
        old_auth.delete_profile()

        console.print(f"[green]✓[/green] Renamed profile from '{old_name}' to '{new_name}'")
    except NLMError as e:
        console.print(f"[red]Error:[/red] {e.message}")
        if e.hint:
            console.print(f"\n[dim]Hint: {e.hint}[/dim]")
        raise typer.Exit(1)


@login_app.command("switch")
def login_switch(
    profile: str = typer.Argument(..., help="Profile name to switch to"),
) -> None:
    """Switch the default profile for all commands."""
    from notebooklm_tools.core.auth import AuthManager
    from notebooklm_tools.utils.config import get_config, save_config

    # Check if profile exists
    auth = AuthManager(profile)
    if not auth.profile_exists():
        console.print(f"[red]Error:[/red] Profile '{profile}' not found")
        console.print("\nAvailable profiles:")
        for name in AuthManager.list_profiles():
            console.print(f"  [cyan]{name}[/cyan]")
        raise typer.Exit(1)

    # Update config
    config = get_config()
    old_profile = config.auth.default_profile
    config.auth.default_profile = profile
    save_config(config)

    # Show confirmation with account info
    try:
        p = auth.load_profile()
        email = p.email or "Unknown"
        console.print(f"[green]✓[/green] Switched default profile to [cyan]{profile}[/cyan]")
        console.print(f"  Account: {email}")
        if old_profile != profile:
            console.print(f"  [dim]Previous: {old_profile}[/dim]")
    except Exception:
        console.print(f"[green]✓[/green] Switched default profile to [cyan]{profile}[/cyan]")


# Register profile commands under login
login_app.add_typer(profile_app, name="profile")

# Register login app with nested profile commands
app.add_typer(login_app, name="login")

# Register noun-first subcommands (existing structure)
app.add_typer(notebook_app, name="notebook", help="Manage notebooks")
app.add_typer(note_app, name="note", help="Manage notes")
app.add_typer(source_app, name="source", help="Manage sources")
app.add_typer(chat_app, name="chat", help="Configure chat settings")
app.add_typer(studio_app, name="studio", help="Manage studio artifacts")
app.add_typer(research_app, name="research", help="Research and discover sources")
app.add_typer(alias_app, name="alias", help="Manage ID aliases")
app.add_typer(config_app, name="config", help="Manage configuration")
app.add_typer(download_app, name="download", help="Download artifacts (audio, video, etc)")
app.add_typer(share_app, name="share", help="Manage notebook sharing")
app.add_typer(export_app, name="export", help="Export artifacts to Google Docs/Sheets")
app.add_typer(skill_app, name="skill", help="Install skills for AI tools")

# Generation commands as top-level
app.add_typer(audio_app, name="audio", help="Create audio overviews")
app.add_typer(report_app, name="report", help="Create reports")
app.add_typer(quiz_app, name="quiz", help="Create quizzes")
app.add_typer(flashcards_app, name="flashcards", help="Create flashcards")
app.add_typer(mindmap_app, name="mindmap", help="Create and manage mind maps")
app.add_typer(slides_app, name="slides", help="Create slide decks")
app.add_typer(infographic_app, name="infographic", help="Create infographics")
app.add_typer(video_app, name="video", help="Create video overviews")
app.add_typer(data_table_app, name="data-table", help="Create data tables")

# Auth is now under login (removed auth_app registration)

# Register verb-first subcommands (alternative structure)
app.add_typer(create_app, name="create", help="Create resources (notebooks, audio, video, etc)")
app.add_typer(list_app, name="list", help="List resources (notebooks, sources, artifacts)")
app.add_typer(get_app, name="get", help="Get details about resources")
app.add_typer(delete_app, name="delete", help="Delete resources (notebooks, sources, artifacts)")
app.add_typer(add_app, name="add", help="Add resources (sources to notebooks)")
app.add_typer(rename_app, name="rename", help="Rename resources")
app.add_typer(status_app, name="status", help="Check status of resources")
app.add_typer(describe_app, name="describe", help="Get AI-generated descriptions and summaries")
app.add_typer(query_app, name="query", help="Chat with notebook sources")
app.add_typer(sync_app, name="sync", help="Sync resources (Drive sources)")
app.add_typer(content_app, name="content", help="Get raw content from sources")
app.add_typer(stale_app, name="stale", help="List stale resources that need syncing")
app.add_typer(configure_app, name="configure", help="Configure settings")
app.add_typer(set_app, name="set", help="Set values (aliases, config)")
app.add_typer(show_app, name="show", help="Show information")
app.add_typer(install_app, name="install", help="Install resources (skills)")
app.add_typer(uninstall_app, name="uninstall", help="Uninstall resources (skills)")


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        False, "--version", "-v",
        help="Show version and exit",
    ),
    ai: bool = typer.Option(
        False, "--ai",
        help="Output AI-friendly documentation for this CLI",
    ),
) -> None:
    """
    NLM - Command-line interface for Google NotebookLM.
    
    Use 'nlm <command> --help' for help on specific commands.
    """
    if version:
        console.print(f"nlm version {__version__}")
        raise typer.Exit()
    
    if ai:
        from notebooklm_tools.cli.ai_docs import print_ai_docs
        print_ai_docs()
        raise typer.Exit()
    
    # Show help if no command provided
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())


def cli_main():
    """Main CLI entry point with error handling."""
    try:
        app()
    except Exception as e:
        # Import here to avoid circular dependencies
        from notebooklm_tools.core.exceptions import (
            AuthenticationError,
            NLMError,
        )
        from notebooklm_tools.core.errors import ClientAuthenticationError


        # Handle authentication errors cleanly
        if isinstance(e, (AuthenticationError, ClientAuthenticationError)):
            console.print(f"\n[red]✗ Authentication Error[/red]")
            console.print(f"  {str(e)}")
            console.print(f"\n[yellow]→[/yellow] Run [cyan]nlm login[/cyan] or [cyan]notebooklm-mcp-auth[/cyan] to re-authenticate\n")
            raise typer.Exit(1)

        # Handle other NLM errors cleanly
        elif isinstance(e, NLMError):
            console.print(f"\n[red]✗ Error:[/red] {e.message}")
            if e.hint:
                console.print(f"[dim]{e.hint}[/dim]\n")
            raise typer.Exit(1)

        # For unexpected errors, show the traceback
        else:
            raise


if __name__ == "__main__":
    cli_main()
