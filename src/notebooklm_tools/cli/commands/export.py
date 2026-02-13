"""Export CLI commands - Export artifacts to Google Docs/Sheets."""

from typing import Optional

import typer
from rich.console import Console

from notebooklm_tools.core.alias import get_alias_manager
from notebooklm_tools.core.exceptions import NLMError
from notebooklm_tools.cli.utils import get_client
from notebooklm_tools.services import exports as export_service, ServiceError

console = Console()
app = typer.Typer(
    help="Export artifacts to Google Docs/Sheets",
    rich_markup_mode="rich",
    no_args_is_help=True,
)


@app.command("artifact")
def export_artifact(
    notebook: str = typer.Argument(..., help="Notebook ID or alias"),
    artifact_id: str = typer.Argument(..., help="Artifact ID to export"),
    export_type: str = typer.Option(
        ..., "--type", "-t",
        help="Export type: 'docs' or 'sheets'",
    ),
    title: Optional[str] = typer.Option(
        None, "--title",
        help="Title for the exported document",
    ),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """Export an artifact to Google Docs or Sheets.
    
    Examples:
        nlm export artifact NOTEBOOK_ID ARTIFACT_ID --type docs
        nlm export artifact NOTEBOOK_ID ARTIFACT_ID --type sheets --title "My Data"
    """
    try:
        notebook_id = get_alias_manager().resolve(notebook)
        with get_client(profile) as client:
            result = export_service.export_artifact(
                client=client,
                notebook_id=notebook_id,
                artifact_id=artifact_id,
                export_type=export_type,
                title=title,
            )
        
        if json_output:
            import json
            console.print(json.dumps(result, indent=2))
            return
        
        console.print(f"[green]✓[/green] {result['message']}")
        console.print(f"[bold]URL:[/bold] {result['url']}")

    except ServiceError as e:
        console.print(f"[red]Error:[/red] {e.user_message}")
        raise typer.Exit(1)
    except NLMError as e:
        console.print(f"[red]Error:[/red] {e.message}")
        if e.hint:
            console.print(f"\n[dim]Hint: {e.hint}[/dim]")
        raise typer.Exit(1)


@app.command("to-docs")
def export_to_docs(
    notebook: str = typer.Argument(..., help="Notebook ID or alias"),
    artifact_id: str = typer.Argument(..., help="Artifact ID to export (Report)"),
    title: Optional[str] = typer.Option(
        None, "--title",
        help="Title for the Google Doc",
    ),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """Export a Report artifact to Google Docs.
    
    Works with: Briefing Doc, Study Guide, Blog Post, etc.
    
    Example:
        nlm export to-docs NOTEBOOK_ID ARTIFACT_ID --title "My Report"
    """
    try:
        notebook_id = get_alias_manager().resolve(notebook)
        with get_client(profile) as client:
            result = export_service.export_artifact(
                client=client,
                notebook_id=notebook_id,
                artifact_id=artifact_id,
                export_type="docs",
                title=title,
            )
        
        console.print(f"[green]✓[/green] {result['message']}")
        console.print(f"[bold]URL:[/bold] {result['url']}")

    except ServiceError as e:
        console.print(f"[red]Error:[/red] {e.user_message}")
        raise typer.Exit(1)
    except NLMError as e:
        console.print(f"[red]Error:[/red] {e.message}")
        if e.hint:
            console.print(f"\n[dim]Hint: {e.hint}[/dim]")
        raise typer.Exit(1)


@app.command("to-sheets")
def export_to_sheets(
    notebook: str = typer.Argument(..., help="Notebook ID or alias"),
    artifact_id: str = typer.Argument(..., help="Artifact ID to export (Data Table)"),
    title: Optional[str] = typer.Option(
        None, "--title",
        help="Title for the Google Sheet",
    ),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """Export a Data Table artifact to Google Sheets.
    
    Example:
        nlm export to-sheets NOTEBOOK_ID ARTIFACT_ID --title "My Data Table"
    """
    try:
        notebook_id = get_alias_manager().resolve(notebook)
        with get_client(profile) as client:
            result = export_service.export_artifact(
                client=client,
                notebook_id=notebook_id,
                artifact_id=artifact_id,
                export_type="sheets",
                title=title,
            )
        
        console.print(f"[green]✓[/green] {result['message']}")
        console.print(f"[bold]URL:[/bold] {result['url']}")

    except ServiceError as e:
        console.print(f"[red]Error:[/red] {e.user_message}")
        raise typer.Exit(1)
    except NLMError as e:
        console.print(f"[red]Error:[/red] {e.message}")
        if e.hint:
            console.print(f"\n[dim]Hint: {e.hint}[/dim]")
        raise typer.Exit(1)
