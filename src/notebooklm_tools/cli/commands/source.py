"""Source CLI commands."""

from typing import Optional

import typer
from rich.console import Console

from notebooklm_tools.core.alias import get_alias_manager
from notebooklm_tools.core.exceptions import NLMError
from notebooklm_tools.cli.formatters import detect_output_format, get_formatter
from notebooklm_tools.cli.utils import get_client
from notebooklm_tools.services import sources as sources_service, ServiceError

console = Console()
app = typer.Typer(
    help="Manage sources",
    rich_markup_mode="rich",
    no_args_is_help=True,
)


@app.command("list")
def list_sources(
    notebook_id: str = typer.Argument(..., help="Notebook ID"),
    full: bool = typer.Option(False, "--full", "-a", help="Show all columns"),
    drive: bool = typer.Option(False, "--drive", "-d", help="Show Drive sources with freshness status"),
    skip_freshness: bool = typer.Option(False, "--skip-freshness", "-S", help="Skip freshness checks (faster, use with --drive)"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Output IDs only"),
    url: bool = typer.Option(False, "--url", "-u", help="Output as ID: URL"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """List sources in a notebook."""
    try:
        notebook_id = get_alias_manager().resolve(notebook_id)
        with get_client(profile) as client:
            if drive:
                sources = client.get_notebook_sources_with_types(notebook_id)
                if not skip_freshness:
                    for src in sources:
                        src['is_fresh'] = client.check_source_freshness(src['id'])
            else:
                sources = client.get_notebook_sources_with_types(notebook_id)

        fmt = detect_output_format(json_output, quiet, url_flag=url)
        formatter = get_formatter(fmt, console)
        formatter.format_sources(sources, full=full or drive, url_only=url)
    except NLMError as e:
        console.print(f"[red]Error:[/red] {e.message}")
        if e.hint:
            console.print(f"\n[dim]Hint: {e.hint}[/dim]")
        raise typer.Exit(1)


@app.command("add")
def add_source(
    notebook_id: str = typer.Argument(..., help="Notebook ID"),
    url: Optional[str] = typer.Option(None, "--url", "-u", help="URL to add (website or YouTube)"),
    text: Optional[str] = typer.Option(None, "--text", "-t", help="Text content to add"),
    drive: Optional[str] = typer.Option(None, "--drive", "-d", help="Google Drive document ID"),
    youtube: Optional[str] = typer.Option(None, "--youtube", "-y", help="YouTube URL"),
    file: Optional[str] = typer.Option(None, "--file", "-f", help="Local file to upload (PDF, etc.)"),
    title: str = typer.Option("", "--title", help="Title for the source"),
    doc_type: str = typer.Option("doc", "--type", help="Drive doc type: doc, slides, sheets, pdf"),
    wait: bool = typer.Option(False, "--wait", "-w", help="Wait for source processing to complete"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """Add a source to a notebook.

    Examples:
        nlm source add <notebook-id> --url https://example.com
        nlm source add <notebook-id> --url https://example.com --wait
        nlm source add <notebook-id> --file document.pdf --wait
    """
    notebook_id = get_alias_manager().resolve(notebook_id)

    # Validate that exactly one source type is provided (CLI-specific UX)
    source_count = sum(1 for x in [url, text, drive, youtube, file] if x)
    if source_count == 0:
        console.print("[red]Error:[/red] Please specify a source: --url, --text, --file, --drive, or --youtube")
        raise typer.Exit(1)
    if source_count > 1:
        console.print("[red]Error:[/red] Please specify only one source type at a time")
        raise typer.Exit(1)

    # Map CLI flags to service source_type + params
    if youtube:
        # YouTube is just a URL source type
        source_type, source_url = "url", youtube
    elif url:
        source_type, source_url = "url", url
    else:
        source_type, source_url = None, None

    try:
        with get_client(profile) as client:
            if source_type == "url":
                if wait:
                    console.print(f"[blue]Adding {source_url} and waiting for processing...[/blue]")
                result = sources_service.add_source(
                    client, notebook_id, "url",
                    url=source_url, wait=wait,
                )
            elif text:
                if wait:
                    console.print("[blue]Adding text and waiting for processing...[/blue]")
                result = sources_service.add_source(
                    client, notebook_id, "text",
                    text=text, title=title or None, wait=wait,
                )
            elif drive:
                if wait:
                    console.print("[blue]Adding Drive document and waiting for processing...[/blue]")
                result = sources_service.add_source(
                    client, notebook_id, "drive",
                    document_id=drive, title=title or None,
                    doc_type=doc_type, wait=wait,
                )
            elif file:
                from pathlib import Path
                file_path = Path(file).expanduser().resolve()
                if not file_path.exists():
                    console.print(f"[red]Error:[/red] File not found: {file}")
                    raise typer.Exit(1)
                console.print(f"[blue]Uploading {file_path.name}{'...' if not wait else ' and waiting for processing...'}[/blue]")
                result = sources_service.add_source(
                    client, notebook_id, "file",
                    file_path=str(file_path), wait=wait,
                )
            else:
                raise typer.Exit(1)

        # Show result
        ready_msg = " (ready)" if wait else ""
        console.print(f"[green]✓[/green] Added source: {result['title']}{ready_msg}")
        console.print(f"[dim]Source ID: {result['source_id']}[/dim]")
    except ServiceError as e:
        console.print(f"[red]Error:[/red] {e.user_message}")
        raise typer.Exit(1)
    except NLMError as e:
        console.print(f"[red]Error:[/red] {e.message}")
        if e.hint:
            console.print(f"\n[dim]Hint: {e.hint}[/dim]")
        raise typer.Exit(1)


@app.command("get")
def get_source(
    source_id: str = typer.Argument(..., help="Source ID"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """Get source details."""
    try:
        source_id = get_alias_manager().resolve(source_id)
        with get_client(profile) as client:
            source = client.get_source_fulltext(source_id)

        fmt = detect_output_format(json_output)
        formatter = get_formatter(fmt, console)
        formatter.format_item(source, title="Source Details")
    except NLMError as e:
        console.print(f"[red]Error:[/red] {e.message}")
        if e.hint:
            console.print(f"\n[dim]Hint: {e.hint}[/dim]")
        raise typer.Exit(1)


@app.command("describe")
def describe_source(
    source_id: str = typer.Argument(..., help="Source ID"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """Get AI-generated source summary with keywords."""
    try:
        source_id = get_alias_manager().resolve(source_id)
        with get_client(profile) as client:
            summary = client.get_source_guide(source_id)

        fmt = detect_output_format(json_output)
        formatter = get_formatter(fmt, console)
        formatter.format_item(summary, title="Source Summary")
    except NLMError as e:
        console.print(f"[red]Error:[/red] {e.message}")
        if e.hint:
            console.print(f"\n[dim]Hint: {e.hint}[/dim]")
        raise typer.Exit(1)


@app.command("content")
def get_source_content(
    source_id: str = typer.Argument(..., help="Source ID"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Write content to file"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """Get raw source content (no AI processing)."""
    try:
        source_id = get_alias_manager().resolve(source_id)
        with get_client(profile) as client:
            content = client.get_source_fulltext(source_id)

        if output:
            from pathlib import Path
            Path(output).write_text(content["content"])
            console.print(f"[green]✓[/green] Wrote {content['char_count']:,} characters to {output}")
        else:
            fmt = detect_output_format(json_output)
            formatter = get_formatter(fmt, console)
            formatter.format_item(content, title="Source Content")
    except NLMError as e:
        console.print(f"[red]Error:[/red] {e.message}")
        if e.hint:
            console.print(f"\n[dim]Hint: {e.hint}[/dim]")
        raise typer.Exit(1)


@app.command("rename")
def rename_source(
    source_id: str = typer.Argument(..., help="Source ID"),
    title: str = typer.Argument(..., help="New title"),
    notebook_id: str = typer.Option(..., "--notebook", "-n", help="Notebook ID containing the source"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """Rename a source."""
    source_id = get_alias_manager().resolve(source_id)
    notebook_id = get_alias_manager().resolve(notebook_id)

    try:
        with get_client(profile) as client:
            result = sources_service.rename_source(client, notebook_id, source_id, title)
        console.print(f"[green]✓[/green] Renamed source to: {result['title']}")
        console.print(f"[dim]Source ID: {result['source_id']}[/dim]")
    except ServiceError as e:
        console.print(f"[red]Error:[/red] {e.user_message}")
        raise typer.Exit(1)
    except NLMError as e:
        console.print(f"[red]Error:[/red] {e.message}")
        if e.hint:
            console.print(f"\n[dim]Hint: {e.hint}[/dim]")
        raise typer.Exit(1)


@app.command("delete")
def delete_source(
    source_id: str = typer.Argument(..., help="Source ID"),
    confirm: bool = typer.Option(False, "--confirm", "-y", help="Skip confirmation"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """Delete a source permanently."""
    source_id = get_alias_manager().resolve(source_id)

    if not confirm:
        typer.confirm(
            f"Are you sure you want to delete source {source_id}?",
            abort=True,
        )

    try:
        with get_client(profile) as client:
            sources_service.delete_source(client, source_id)
        console.print(f"[green]✓[/green] Deleted source: {source_id}")
    except ServiceError as e:
        console.print(f"[red]Error:[/red] {e.user_message}")
        raise typer.Exit(1)
    except NLMError as e:
        console.print(f"[red]Error:[/red] {e.message}")
        if e.hint:
            console.print(f"\n[dim]Hint: {e.hint}[/dim]")
        raise typer.Exit(1)


@app.command("stale")
def list_stale_sources(
    notebook_id: str = typer.Argument(..., help="Notebook ID"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """List Drive sources that need syncing."""
    try:
        notebook_id = get_alias_manager().resolve(notebook_id)
        with get_client(profile) as client:
            sources = client.get_notebook_sources_with_types(notebook_id)

        stale_sources = [s for s in sources if not s.get('is_fresh', True)]

        if not stale_sources:
            console.print("[green]✓[/green] All Drive sources are up to date.")
            return

        console.print(f"[yellow]⚠[/yellow] {len(stale_sources)} source(s) need syncing:")

        fmt = detect_output_format(json_output)
        formatter = get_formatter(fmt, console)
        formatter.format_sources(stale_sources, full=True)

        console.print("\n[dim]Run 'nlm source sync <notebook-id>' to sync all stale sources.[/dim]")
    except NLMError as e:
        console.print(f"[red]Error:[/red] {e.message}")
        if e.hint:
            console.print(f"\n[dim]Hint: {e.hint}[/dim]")
        raise typer.Exit(1)


@app.command("sync")
def sync_sources(
    notebook_id: str = typer.Argument(..., help="Notebook ID"),
    source_ids: Optional[str] = typer.Option(
        None, "--source-ids", "-s",
        help="Comma-separated source IDs to sync (default: all stale)",
    ),
    confirm: bool = typer.Option(False, "--confirm", "-y", help="Skip confirmation"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """Sync Drive sources with latest content."""
    try:
        notebook_id = get_alias_manager().resolve(notebook_id)

        with get_client(profile) as client:
            if source_ids:
                ids_to_sync = [get_alias_manager().resolve(sid.strip()) for sid in source_ids.split(",")]
            else:
                sources = client.get_notebook_sources_with_types(notebook_id)
                ids_to_sync = [s['id'] for s in sources if not s.get('is_fresh', True)]

        if not ids_to_sync:
            console.print("[green]✓[/green] No sources need syncing.")
            return

        if not confirm:
            typer.confirm(
                f"Sync {len(ids_to_sync)} source(s)?",
                abort=True,
            )

        with get_client(profile) as client:
            results = sources_service.sync_drive_sources(client, ids_to_sync)

        synced = sum(1 for r in results if r.get("synced"))
        console.print(f"[green]✓[/green] Synced {synced} source(s)")
    except ServiceError as e:
        console.print(f"[red]Error:[/red] {e.user_message}")
        raise typer.Exit(1)
    except NLMError as e:
        console.print(f"[red]Error:[/red] {e.message}")
        if e.hint:
            console.print(f"\n[dim]Hint: {e.hint}[/dim]")
        raise typer.Exit(1)
