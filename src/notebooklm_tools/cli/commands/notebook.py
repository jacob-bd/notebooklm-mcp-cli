"""Notebook CLI commands."""

from typing import Optional

import typer
from rich.console import Console

from notebooklm_tools.core.alias import get_alias_manager
from notebooklm_tools.core.client import NotebookLMClient
from notebooklm_tools.core.exceptions import NLMError
from notebooklm_tools.cli.formatters import detect_output_format, get_formatter

console = Console()
app = typer.Typer(
    help="Manage notebooks",
    rich_markup_mode="rich",
    no_args_is_help=True,
)


def get_client(profile: str | None = None) -> NotebookLMClient:
    """Get a client instance."""
    from notebooklm_tools.core.auth import AuthManager
    
    manager = AuthManager(profile if profile else "default")
    if not manager.profile_exists():
        console.print(f"[red]Error:[/red] Profile '{manager.profile_name}' not found. Run 'nlm login' first.")
        raise typer.Exit(1)
        
    p = manager.load_profile()
    return NotebookLMClient(
        cookies=p.cookies,
        csrf_token=p.csrf_token or "",
        session_id=p.session_id or "",
    )


@app.command("list")
def list_notebooks(
    full: bool = typer.Option(False, "--full", "-a", help="Show all columns"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Output IDs only"),
    title: bool = typer.Option(False, "--title", "-t", help="Show ID: Title format"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """List all notebooks."""
    try:
        with get_client(profile) as client:
            notebooks = client.list_notebooks()
        
        fmt = detect_output_format(json_output, quiet, title)
        formatter = get_formatter(fmt, console)
        formatter.format_notebooks(notebooks, full=full, title_only=title)
    except NLMError as e:
        console.print(f"[red]Error:[/red] {e.message}")
        if e.hint:
            console.print(f"\n[dim]Hint: {e.hint}[/dim]")
        raise typer.Exit(1)


@app.command("create")
def create_notebook(
    title: str = typer.Argument("", help="Notebook title"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """Create a new notebook."""
    try:
        with get_client(profile) as client:
            notebook = client.create_notebook(title)
        
        if not notebook:
            console.print("[red]Error:[/red] Failed to create notebook. The API returned an empty or invalid response.")
            raise typer.Exit(1)
            
        console.print(f"[green]✓[/green] Created notebook: {notebook.title}")
        console.print(f"  ID: {notebook.id}")
    except NLMError as e:
        console.print(f"[red]Error:[/red] {e.message}")
        if e.hint:
            console.print(f"\n[dim]Hint: {e.hint}[/dim]")
        raise typer.Exit(1)


@app.command("get")
def get_notebook(
    notebook_id: str = typer.Argument(..., help="Notebook ID"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """Get notebook details."""
    try:
        notebook_id = get_alias_manager().resolve(notebook_id)
        with get_client(profile) as client:
            notebook = client.get_notebook(notebook_id)
        
        fmt = detect_output_format(json_output)
        formatter = get_formatter(fmt, console)
        formatter.format_item(notebook, title="Notebook Details")
    except NLMError as e:
        console.print(f"[red]Error:[/red] {e.message}")
        if e.hint:
            console.print(f"\n[dim]Hint: {e.hint}[/dim]")
        raise typer.Exit(1)


@app.command("describe")
def describe_notebook(
    notebook_id: str = typer.Argument(..., help="Notebook ID"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """Get AI-generated notebook summary with suggested topics."""
    try:
        notebook_id = get_alias_manager().resolve(notebook_id)
        with get_client(profile) as client:
            result = client.get_notebook_summary(notebook_id)
        
        console.print("[bold]Summary:[/bold]")
        console.print(result.get("summary", "No summary available."))
        
        topics = result.get("suggested_topics", [])
        if topics:
            console.print("\n[bold]Suggested Topics:[/bold]")
            for topic in topics:
                if isinstance(topic, dict):
                    console.print(f"  • {topic.get('question', topic)}")
                else:
                    console.print(f"  • {topic}")
    except NLMError as e:
        console.print(f"[red]Error:[/red] {e.message}")
        if e.hint:
            console.print(f"\n[dim]Hint: {e.hint}[/dim]")
        raise typer.Exit(1)


@app.command("rename")
def rename_notebook(
    notebook_id: str = typer.Argument(..., help="Notebook ID"),
    new_title: str = typer.Argument(..., help="New title"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """Rename a notebook."""
    try:
        notebook_id = get_alias_manager().resolve(notebook_id)
        with get_client(profile) as client:
            success = client.rename_notebook(notebook_id, new_title)
        
        if success:
            console.print(f"[green]✓[/green] Renamed notebook to: {new_title}")
        else:
            console.print("[yellow]⚠[/yellow] Rename may have failed")
    except NLMError as e:
        console.print(f"[red]Error:[/red] {e.message}")
        if e.hint:
            console.print(f"\n[dim]Hint: {e.hint}[/dim]")
        raise typer.Exit(1)


@app.command("delete")
def delete_notebook(
    notebook_id: str = typer.Argument(..., help="Notebook ID"),
    confirm: bool = typer.Option(False, "--confirm", "-y", help="Skip confirmation"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """Delete a notebook permanently."""
    notebook_id = get_alias_manager().resolve(notebook_id)
    
    if not confirm:
        typer.confirm(
            f"Are you sure you want to delete notebook {notebook_id}?",
            abort=True,
        )
    
    try:
        with get_client(profile) as client:
            client.delete_notebook(notebook_id)
        
        console.print(f"[green]✓[/green] Deleted notebook: {notebook_id}")
    except NLMError as e:
        console.print(f"[red]Error:[/red] {e.message}")
        if e.hint:
            console.print(f"\n[dim]Hint: {e.hint}[/dim]")
        raise typer.Exit(1)


@app.command("query")
def query_notebook(
    notebook_id: str = typer.Argument(..., help="Notebook ID"),
    question: str = typer.Argument(..., help="Question to ask"),
    conversation_id: Optional[str] = typer.Option(
        None, "--conversation-id", "-c",
        help="Conversation ID for follow-up questions",
    ),
    source_ids: Optional[str] = typer.Option(
        None, "--source-ids", "-s",
        help="Comma-separated source IDs to query (default: all)",
    ),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """Chat with notebook sources."""
    try:
        sources = source_ids.split(",") if source_ids else None
        
        notebook_id = get_alias_manager().resolve(notebook_id)
        
        with get_client(profile) as client:
            response = client.query(
                notebook_id,
                question,
                source_ids=sources,
                conversation_id=conversation_id,
            )
        
        if response:
            console.print(response.get("answer", "No response"))
            
            # Print citations footer
            sources = response.get("sources", [])
            if sources:
                console.print("\n[bold]Sources:[/bold]")
                for i, src in enumerate(sources, 1):
                    title = src.get("title", "Untitled")
                    # Try to be smart about alignment if list is long, but simple is fine for now
                    console.print(f"  [dim][{i}] {title}[/dim]")
            
            conv_id = response.get("conversation_id")
            if conv_id:
                console.print(f"\n[dim]Conversation ID: {conv_id}[/dim]")
                console.print("[dim]Use --conversation-id for follow-up questions[/dim]")
        else:
            console.print("[yellow]No response received[/yellow]")
    except NLMError as e:
        console.print(f"[red]Error:[/red] {e.message}")
        if e.hint:
            console.print(f"\n[dim]Hint: {e.hint}[/dim]")
        raise typer.Exit(1)
