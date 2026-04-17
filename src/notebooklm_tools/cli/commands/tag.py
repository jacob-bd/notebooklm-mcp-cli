"""Tag CLI commands — manage notebook tags for smart selection."""

import typer
from rich.table import Table

from notebooklm_tools.cli.utils import make_console
from notebooklm_tools.services import smart_select as smart_select_service
from notebooklm_tools.services.errors import ServiceError

console = make_console()
app = typer.Typer(
    help="Manage notebook tags for smart selection",
    rich_markup_mode="rich",
    no_args_is_help=True,
)


@app.command("add")
def tag_add(
    notebook_id: str = typer.Argument(..., help="Notebook UUID or alias"),
    tags: str = typer.Option(
        ..., "--tags", "-t", help="Comma-separated tags (e.g. 'ai,research,llm')"
    ),
    title: str = typer.Option("", "--title", help="Notebook title for display"),
) -> None:
    """Add tags to a notebook."""
    try:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        result = smart_select_service.tag_add(notebook_id, tag_list, title)
        console.print(
            f"[green]\u2713[/green] Tags updated for [bold]{result.get('notebook_title') or notebook_id}[/bold]"
        )
        console.print(f"  Tags: {', '.join(result['tags'])}")
    except ServiceError as e:
        console.print(f"[red]Error:[/red] {e.user_message}")
        raise typer.Exit(1) from e


@app.command("remove")
def tag_remove(
    notebook_id: str = typer.Argument(..., help="Notebook UUID or alias"),
    tags: str = typer.Option(..., "--tags", "-t", help="Comma-separated tags to remove"),
) -> None:
    """Remove tags from a notebook."""
    try:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        result = smart_select_service.tag_remove(notebook_id, tag_list)
        if result["tags"]:
            console.print(f"[green]\u2713[/green] Tags updated: {', '.join(result['tags'])}")
        else:
            console.print(f"[green]\u2713[/green] All tags removed from notebook {notebook_id}")
    except ServiceError as e:
        console.print(f"[red]Error:[/red] {e.user_message}")
        raise typer.Exit(1) from e


@app.command("list")
def tag_list() -> None:
    """List all tagged notebooks."""
    result = smart_select_service.tag_list()

    if result["count"] == 0:
        console.print("[dim]No tagged notebooks.[/dim]")
        console.print(
            "\nUse [cyan]nlm tag add <notebook-id> --tags 'ai,research'[/cyan] to add tags."
        )
        return

    table = Table(title=f"Tagged Notebooks ({result['count']})")
    table.add_column("Notebook", style="cyan")
    table.add_column("ID", style="dim")
    table.add_column("Tags", style="green")

    for entry in result["entries"]:
        title = entry.get("notebook_title") or "(untitled)"
        nb_id = entry["notebook_id"][:12] + "..."
        tags = ", ".join(entry["tags"])
        table.add_row(title, nb_id, tags)

    console.print(table)


@app.command("select")
def tag_select(
    query: str = typer.Argument(..., help="Query to match against tags"),
) -> None:
    """Find notebooks relevant to a query using tags."""
    try:
        result = smart_select_service.smart_select(query)

        if result["count"] == 0:
            console.print(f"[dim]No notebooks match query: '{query}'[/dim]")
            return

        console.print(f"[bold]Matching notebooks for:[/bold] {query}")
        for i, entry in enumerate(result["matched_notebooks"], 1):
            title = entry.get("notebook_title") or entry["notebook_id"][:12]
            tags = ", ".join(entry["tags"])
            console.print(f"  {i}. [cyan]{title}[/cyan] — {tags}")
    except ServiceError as e:
        console.print(f"[red]Error:[/red] {e.user_message}")
        raise typer.Exit(1) from e
