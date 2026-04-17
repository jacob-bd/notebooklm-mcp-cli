"""Pipeline CLI commands — define and execute multi-step workflows."""

import typer
from rich.table import Table

from notebooklm_tools.cli.utils import make_console
from notebooklm_tools.services import pipeline as pipeline_service
from notebooklm_tools.services.errors import ServiceError

console = make_console()
app = typer.Typer(
    help="Pipeline automation for multi-step workflows",
    rich_markup_mode="rich",
    no_args_is_help=True,
)


@app.command("run")
def pipeline_run(
    pipeline_name: str = typer.Argument(..., help="Pipeline name"),
    notebook_id: str = typer.Option(..., "--notebook", "-n", help="Target notebook UUID"),
    input_url: str = typer.Option("", "--input-url", "-u", help="URL variable ($INPUT_URL)"),
) -> None:
    """Execute a pipeline on a notebook."""
    from notebooklm_tools.cli.utils import get_client

    try:
        client = get_client()
        variables = {}
        if input_url:
            variables["INPUT_URL"] = input_url

        with console.status(f"[dim]Running pipeline '{pipeline_name}'...[/dim]"):
            result = pipeline_service.pipeline_run(client, notebook_id, pipeline_name, variables)

        console.print(f"\n[bold]Pipeline:[/bold] {result['pipeline_name']}")
        console.print(
            f"[dim]{result['succeeded']}/{result['total_steps']} steps succeeded "
            f"({result['total_duration_ms']}ms)[/dim]\n"
        )

        for step in result["steps"]:
            if step["success"]:
                console.print(
                    f"  [green]\u2713[/green] Step {step['step']}: {step['action']} ({step['duration_ms']}ms)"
                )
            else:
                console.print(
                    f"  [red]\u2717[/red] Step {step['step']}: {step['action']} — {step['error']}"
                )

    except ServiceError as e:
        console.print(f"[red]Error:[/red] {e.user_message}")
        raise typer.Exit(1) from e


@app.command("list")
def pipeline_list() -> None:
    """List all available pipelines."""
    pipelines = pipeline_service.pipeline_list()

    if not pipelines:
        console.print("[dim]No pipelines available.[/dim]")
        return

    table = Table(title=f"Pipelines ({len(pipelines)})")
    table.add_column("Name", style="cyan")
    table.add_column("Steps", justify="center")
    table.add_column("Source", style="dim")
    table.add_column("Description")

    for p in pipelines:
        source_badge = (
            "[green]builtin[/green]" if p["source"] == "builtin" else "[yellow]user[/yellow]"
        )
        table.add_row(p["name"], str(p["steps_count"]), source_badge, p["description"])

    console.print(table)


@app.command("create")
def pipeline_create(
    name: str = typer.Argument(..., help="Pipeline name"),
    description: str = typer.Option("", "--description", "-d", help="Pipeline description"),
    file: str | None = typer.Option(
        None, "--file", "-f", help="YAML file with pipeline definition"
    ),
) -> None:
    """Create a user-defined pipeline from a YAML file."""
    import yaml

    if not file:
        console.print("[red]Error:[/red] --file is required with a YAML pipeline definition")
        console.print("\nExample YAML:")
        console.print("[dim]steps:")
        console.print("  - action: source_add")
        console.print('    params: { type: url, url: "$INPUT_URL" }')
        console.print("  - action: notebook_query")
        console.print('    params: { query: "Summarize the content" }[/dim]')
        raise typer.Exit(1)

    try:
        from pathlib import Path

        data = yaml.safe_load(Path(file).read_text(encoding="utf-8"))
        steps = data.get("steps", []) if isinstance(data, dict) else []
        desc = description or data.get("description", "")

        result = pipeline_service.pipeline_create(name, desc, steps)
        console.print(
            f"[green]\u2713[/green] Pipeline '{result['name']}' created ({result['steps_count']} steps)"
        )
    except ServiceError as e:
        console.print(f"[red]Error:[/red] {e.user_message}")
        raise typer.Exit(1) from e
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from e
