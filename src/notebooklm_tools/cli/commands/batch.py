"""Batch CLI commands — perform operations across multiple notebooks."""

import typer
from rich.table import Table

from notebooklm_tools.cli.utils import make_console
from notebooklm_tools.services.errors import ServiceError

console = make_console()
app = typer.Typer(
    help="Batch operations across multiple notebooks",
    rich_markup_mode="rich",
    no_args_is_help=True,
)


def _print_batch_result(result: dict) -> None:
    """Print a formatted batch result table."""
    table = Table(
        title=f"{result['operation']} ({result['succeeded']}/{result['total']} succeeded)"
    )
    table.add_column("Notebook", style="cyan")
    table.add_column("Status")
    table.add_column("Details", style="dim")

    for item in result["items"]:
        title = item.get("notebook_title") or item["notebook_id"][:12]
        if item["success"]:
            status = "[green]\u2713[/green]"
            details = str(item["result"])[:80] if item["result"] else ""
        else:
            status = "[red]\u2717[/red]"
            details = item.get("error", "Unknown error")[:80]
        table.add_row(title, status, details)

    console.print(table)


@app.command("query")
def batch_query(
    query: str = typer.Argument(..., help="Question to ask across notebooks"),
    notebooks: str | None = typer.Option(
        None, "--notebooks", "-n", help="Comma-separated notebook names"
    ),
    tags: str | None = typer.Option(None, "--tags", "-t", help="Comma-separated tags"),
    all_notebooks: bool = typer.Option(False, "--all", "-a", help="Query ALL notebooks"),
) -> None:
    """Query multiple notebooks with the same question."""
    from notebooklm_tools.cli.utils import get_client
    from notebooklm_tools.services import batch as batch_service

    try:
        client = get_client()
        names = [n.strip() for n in notebooks.split(",") if n.strip()] if notebooks else None
        tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None

        with console.status("[dim]Querying notebooks...[/dim]"):
            result = batch_service.batch_query(client, query, names, tag_list, all_notebooks)
        _print_batch_result(result)
    except ServiceError as e:
        console.print(f"[red]Error:[/red] {e.user_message}")
        raise typer.Exit(1) from e


@app.command("add-source")
def batch_add_source(
    url: str = typer.Argument(..., help="URL to add as source"),
    notebooks: str | None = typer.Option(
        None, "--notebooks", "-n", help="Comma-separated notebook names"
    ),
    tags: str | None = typer.Option(None, "--tags", "-t", help="Comma-separated tags"),
    all_notebooks: bool = typer.Option(False, "--all", "-a", help="Add to ALL notebooks"),
) -> None:
    """Add the same source URL to multiple notebooks."""
    from notebooklm_tools.cli.utils import get_client
    from notebooklm_tools.services import batch as batch_service

    try:
        client = get_client()
        names = [n.strip() for n in notebooks.split(",") if n.strip()] if notebooks else None
        tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None

        with console.status("[dim]Adding source to notebooks...[/dim]"):
            result = batch_service.batch_add_source(client, url, names, tag_list, all_notebooks)
        _print_batch_result(result)
    except ServiceError as e:
        console.print(f"[red]Error:[/red] {e.user_message}")
        raise typer.Exit(1) from e


@app.command("create")
def batch_create(
    titles: str = typer.Argument(..., help="Comma-separated notebook titles"),
) -> None:
    """Create multiple notebooks at once."""
    from notebooklm_tools.cli.utils import get_client
    from notebooklm_tools.services import batch as batch_service

    try:
        client = get_client()
        title_list = [t.strip() for t in titles.split(",") if t.strip()]

        with console.status("[dim]Creating notebooks...[/dim]"):
            result = batch_service.batch_create(client, title_list)
        _print_batch_result(result)
    except ServiceError as e:
        console.print(f"[red]Error:[/red] {e.user_message}")
        raise typer.Exit(1) from e


@app.command("delete")
def batch_delete(
    notebooks: str | None = typer.Option(
        None, "--notebooks", "-n", help="Comma-separated notebook names"
    ),
    tags: str | None = typer.Option(None, "--tags", "-t", help="Comma-separated tags"),
    confirm: bool = typer.Option(False, "--confirm", "-y", help="Confirm deletion"),
) -> None:
    """Delete multiple notebooks. IRREVERSIBLE."""
    from notebooklm_tools.cli.utils import get_client
    from notebooklm_tools.services import batch as batch_service

    if not confirm:
        typer.confirm("This will PERMANENTLY delete multiple notebooks. Continue?", abort=True)
        confirm = True

    try:
        client = get_client()
        names = [n.strip() for n in notebooks.split(",") if n.strip()] if notebooks else None
        tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None

        with console.status("[dim]Deleting notebooks...[/dim]"):
            result = batch_service.batch_delete(client, names, tag_list, confirm=True)
        _print_batch_result(result)
    except ServiceError as e:
        console.print(f"[red]Error:[/red] {e.user_message}")
        raise typer.Exit(1) from e


@app.command("studio")
def batch_studio(
    artifact_type: str = typer.Argument(
        "audio", help="Type: audio, video, report, flashcards, etc."
    ),
    notebooks: str | None = typer.Option(
        None, "--notebooks", "-n", help="Comma-separated notebook names"
    ),
    tags: str | None = typer.Option(None, "--tags", "-t", help="Comma-separated tags"),
    all_notebooks: bool = typer.Option(False, "--all", "-a", help="Generate for ALL notebooks"),
) -> None:
    """Generate studio artifacts across multiple notebooks."""
    from notebooklm_tools.cli.utils import get_client
    from notebooklm_tools.services import batch as batch_service

    try:
        client = get_client()
        names = [n.strip() for n in notebooks.split(",") if n.strip()] if notebooks else None
        tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None

        with console.status(f"[dim]Generating {artifact_type} artifacts...[/dim]"):
            result = batch_service.batch_studio(
                client, artifact_type, names, tag_list, all_notebooks
            )
        _print_batch_result(result)
    except ServiceError as e:
        console.print(f"[red]Error:[/red] {e.user_message}")
        raise typer.Exit(1) from e
