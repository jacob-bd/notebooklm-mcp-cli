"""Cross-notebook CLI commands — query across multiple notebooks."""

import typer
from rich.panel import Panel

from notebooklm_tools.cli.utils import make_console
from notebooklm_tools.services.errors import ServiceError

console = make_console()
app = typer.Typer(
    help="Cross-notebook operations",
    rich_markup_mode="rich",
    no_args_is_help=True,
)


@app.command("query")
def cross_query(
    query: str = typer.Argument(..., help="Question to ask across notebooks"),
    notebooks: str | None = typer.Option(
        None,
        "--notebooks",
        "-n",
        help="Comma-separated notebook names or IDs",
    ),
    tags: str | None = typer.Option(
        None,
        "--tags",
        "-t",
        help="Comma-separated tags to select notebooks",
    ),
    all_notebooks: bool = typer.Option(
        False,
        "--all",
        "-a",
        help="Query ALL notebooks (rate limits apply)",
    ),
) -> None:
    """Query multiple notebooks and get aggregated answers."""
    from notebooklm_tools.cli.utils import get_client
    from notebooklm_tools.services import cross_notebook as cross_notebook_service

    try:
        client = get_client()

        names_list = None
        if notebooks:
            names_list = [n.strip() for n in notebooks.split(",") if n.strip()]

        tags_list = None
        if tags:
            tags_list = [t.strip() for t in tags.split(",") if t.strip()]

        with console.status("[dim]Querying notebooks...[/dim]"):
            result = cross_notebook_service.cross_notebook_query(
                client=client,
                query_text=query,
                notebook_names=names_list,
                tags=tags_list,
                all_notebooks=all_notebooks,
            )

        console.print(f"\n[bold]Cross-notebook query:[/bold] {query}")
        console.print(
            f"[dim]{result['notebooks_succeeded']}/{result['notebooks_queried']} "
            f"notebooks responded[/dim]\n"
        )

        for r in result["results"]:
            title = r.get("notebook_title") or r["notebook_id"][:12]
            if r["error"]:
                console.print(
                    Panel(
                        f"[red]Error:[/red] {r['error']}",
                        title=f"[red]{title}[/red]",
                        border_style="red",
                    )
                )
            else:
                sources = ""
                if r["sources_used"]:
                    source_names = []
                    for s in r["sources_used"]:
                        if isinstance(s, dict):
                            source_names.append(s.get("title", s.get("id", "?")))
                        else:
                            source_names.append(str(s))
                    sources = f"\n\n[dim]Sources: {', '.join(source_names)}[/dim]"
                console.print(
                    Panel(
                        f"{r['answer']}{sources}",
                        title=f"[cyan]{title}[/cyan]",
                        border_style="cyan",
                    )
                )

    except ServiceError as e:
        console.print(f"[red]Error:[/red] {e.user_message}")
        raise typer.Exit(1) from e
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from e
