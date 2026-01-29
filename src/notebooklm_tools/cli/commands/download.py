import asyncio
import typer
from typing import Optional, Callable, Any
from rich.console import Console
from rich.progress import (
    Progress,
    TextColumn,
    BarColumn,
    DownloadColumn,
    TransferSpeedColumn,
    TimeRemainingColumn,
)
from notebooklm_tools.core.client import NotebookLMClient, ArtifactNotReadyError, ArtifactError
from notebooklm_tools.cli.utils import get_client, handle_error
from notebooklm_tools.core.alias import get_alias_manager

app = typer.Typer(help="Download artifacts from notebooks.")
console = Console()
err_console = Console(stderr=True)


def download_with_progress(
    download_func: Callable[[Callable[[int, int], None]], Any],
    description: str,
    show_progress: bool = True,
):
    """Wrapper to show progress bar for downloads.

    Args:
        download_func: Function that takes a progress callback and returns result
        description: Description to show
        show_progress: Whether to show progress bar

    Returns:
        Result of download_func
    """
    if not show_progress:
        return download_func(lambda current, total: None)

    with Progress(
        TextColumn("[bold blue]{task.description}"),
        BarColumn(bar_width=None),
        "[progress.percentage]{task.percentage:>3.0f}%",
        DownloadColumn(),
        TransferSpeedColumn(),
        TimeRemainingColumn(),
        console=console,
        transient=True,
    ) as progress:
        task_id = progress.add_task(description, total=None)

        def update_progress(current: int, total: int | None):
            if total:
                progress.update(task_id, completed=current, total=total)
            else:
                progress.update(task_id, completed=current)

        return download_func(update_progress)


def simple_download(
    download_func: Callable[[NotebookLMClient], str],
    artifact_name: str,
) -> None:
    """Common pattern for simple (non-streaming) downloads.

    Args:
        download_func: Function that takes client and returns saved path
        artifact_name: Human-readable name for error messages
    """
    client = get_client()
    try:
        saved = download_func(client)
        console.print(f"[green]✓[/green] Downloaded {artifact_name} to: {saved}")
    except ArtifactNotReadyError:
        err_console.print(f"[red]Error:[/red] {artifact_name} is not ready or does not exist.")
        raise typer.Exit(1)
    except Exception as e:
        handle_error(e)

@app.command("audio")
def download_audio(
    notebook_id: str = typer.Argument(..., help="Notebook ID"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output path (default: ./{notebook_id}_audio.m4a)"),
    artifact_id: Optional[str] = typer.Option(None, "--id", help="Specific artifact ID"),
    no_progress: bool = typer.Option(False, "--no-progress", help="Disable download progress bar")
):
    """Download Audio Overview."""
    notebook_id = get_alias_manager().resolve(notebook_id)
    client = get_client()
    try:
        path = output or f"{notebook_id}_audio.m4a"
        saved = download_with_progress(
            lambda cb: asyncio.run(client.download_audio(notebook_id, path, artifact_id, progress_callback=cb)),
            "Downloading audio",
            show_progress=not no_progress
        )
        console.print(f"[green]✓[/green] Downloaded audio to: {saved}")
    except ArtifactNotReadyError:
        err_console.print("[red]Error:[/red] Audio Overview is not ready or does not exist.")
        raise typer.Exit(1)
    except Exception as e:
        handle_error(e)

@app.command("video")
def download_video(
    notebook_id: str = typer.Argument(..., help="Notebook ID"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output path (default: ./{notebook_id}_video.mp4)"),
    artifact_id: Optional[str] = typer.Option(None, "--id", help="Specific artifact ID"),
    no_progress: bool = typer.Option(False, "--no-progress", help="Disable download progress bar")
):
    """Download Video Overview."""
    notebook_id = get_alias_manager().resolve(notebook_id)
    client = get_client()
    try:
        path = output or f"{notebook_id}_video.mp4"
        saved = download_with_progress(
            lambda cb: asyncio.run(client.download_video(notebook_id, path, artifact_id, progress_callback=cb)),
            "Downloading video",
            show_progress=not no_progress
        )
        console.print(f"[green]✓[/green] Downloaded video to: {saved}")
    except ArtifactNotReadyError:
        err_console.print("[red]Error:[/red] Video Overview is not ready or does not exist.")
        raise typer.Exit(1)
    except Exception as e:
        handle_error(e)

@app.command("report")
def download_report(
    notebook_id: str = typer.Argument(..., help="Notebook ID"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output path (default: ./{notebook_id}_report.md)"),
    artifact_id: Optional[str] = typer.Option(None, "--id", help="Specific artifact ID")
):
    """Download Report (Markdown)."""
    notebook_id = get_alias_manager().resolve(notebook_id)
    path = output or f"{notebook_id}_report.md"
    simple_download(
        lambda client: client.download_report(notebook_id, path, artifact_id),
        "report"
    )

@app.command("mind-map")
def download_mind_map(
    notebook_id: str = typer.Argument(..., help="Notebook ID"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output path (default: ./{notebook_id}_mindmap.json)"),
    artifact_id: Optional[str] = typer.Option(None, "--id", help="Specific artifact ID (note ID)")
):
    """Download Mind Map (JSON)."""
    notebook_id = get_alias_manager().resolve(notebook_id)
    path = output or f"{notebook_id}_mindmap.json"
    simple_download(
        lambda client: client.download_mind_map(notebook_id, path, artifact_id),
        "mind map"
    )

@app.command("slide-deck")
def download_slide_deck(
    notebook_id: str = typer.Argument(..., help="Notebook ID"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output path (default: ./{notebook_id}_slides.pdf)"),
    artifact_id: Optional[str] = typer.Option(None, "--id", help="Specific artifact ID"),
    no_progress: bool = typer.Option(False, "--no-progress", help="Disable download progress bar")
):
    """Download Slide Deck (PDF)."""
    notebook_id = get_alias_manager().resolve(notebook_id)
    client = get_client()
    try:
        path = output or f"{notebook_id}_slides.pdf"
        saved = download_with_progress(
            lambda cb: asyncio.run(client.download_slide_deck(notebook_id, path, artifact_id, progress_callback=cb)),
            "Downloading slide deck",
            show_progress=not no_progress
        )
        console.print(f"[green]✓[/green] Downloaded slide deck to: {saved}")
    except ArtifactNotReadyError:
        err_console.print("[red]Error:[/red] Slide deck is not ready or does not exist.")
        raise typer.Exit(1)
    except Exception as e:
        handle_error(e)

@app.command("infographic")
def download_infographic(
    notebook_id: str = typer.Argument(..., help="Notebook ID"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output path (default: ./{notebook_id}_infographic.png)"),
    artifact_id: Optional[str] = typer.Option(None, "--id", help="Specific artifact ID"),
    no_progress: bool = typer.Option(False, "--no-progress", help="Disable download progress bar")
):
    """Download Infographic (PNG)."""
    notebook_id = get_alias_manager().resolve(notebook_id)
    client = get_client()
    try:
        path = output or f"{notebook_id}_infographic.png"
        saved = download_with_progress(
            lambda cb: asyncio.run(client.download_infographic(notebook_id, path, artifact_id, progress_callback=cb)),
            "Downloading infographic",
            show_progress=not no_progress
        )
        console.print(f"[green]✓[/green] Downloaded infographic to: {saved}")
    except ArtifactNotReadyError:
        err_console.print("[red]Error:[/red] Infographic is not ready or does not exist.")
        raise typer.Exit(1)
    except Exception as e:
        handle_error(e)

@app.command("data-table")
def download_data_table(
    notebook_id: str = typer.Argument(..., help="Notebook ID"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output path (default: ./{notebook_id}_table.csv)"),
    artifact_id: Optional[str] = typer.Option(None, "--id", help="Specific artifact ID")
):
    """Download Data Table (CSV)."""
    notebook_id = get_alias_manager().resolve(notebook_id)
    path = output or f"{notebook_id}_table.csv"
    simple_download(
        lambda client: client.download_data_table(notebook_id, path, artifact_id),
        "data table"
    )


@app.command("quiz")
def download_quiz_cmd(
    notebook_id: str = typer.Argument(..., help="Notebook ID"),
    output: Optional[str] = typer.Option(
        None, "--output", "-o",
        help="Output path (default: ./{notebook_id}_quiz.{ext})"
    ),
    artifact_id: Optional[str] = typer.Option(None, "--id", help="Specific artifact ID"),
    format: str = typer.Option(
        "json", "--format", "-f",
        help="Output format: json, markdown, or html"
    ),
):
    """Download Quiz."""
    notebook_id = get_alias_manager().resolve(notebook_id)
    client = get_client()

    # Validate format
    if format not in ("json", "markdown", "html"):
        err_console.print(
            f"[red]Error:[/red] Invalid format '{format}'. "
            "Use: json, markdown, or html"
        )
        raise typer.Exit(1)

    # Determine extension
    ext_map = {"json": "json", "markdown": "md", "html": "html"}
    ext = ext_map[format]

    try:
        path = output or f"{notebook_id}_quiz.{ext}"
        saved = asyncio.run(
            client.download_quiz(notebook_id, path, artifact_id, format)
        )
        console.print(f"[green]✓[/green] Downloaded quiz to: {saved}")
    except ArtifactNotReadyError:
        err_console.print(
            "[red]Error:[/red] Quiz is not ready or does not exist."
        )
        raise typer.Exit(1)
    except ValueError as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        handle_error(e)


@app.command("flashcards")
def download_flashcards_cmd(
    notebook_id: str = typer.Argument(..., help="Notebook ID"),
    output: Optional[str] = typer.Option(
        None, "--output", "-o",
        help="Output path (default: ./{notebook_id}_flashcards.{ext})"
    ),
    artifact_id: Optional[str] = typer.Option(None, "--id", help="Specific artifact ID"),
    format: str = typer.Option(
        "json", "--format", "-f",
        help="Output format: json, markdown, or html"
    ),
):
    """Download Flashcards."""
    notebook_id = get_alias_manager().resolve(notebook_id)
    client = get_client()

    # Validate format
    if format not in ("json", "markdown", "html"):
        err_console.print(
            f"[red]Error:[/red] Invalid format '{format}'. "
            "Use: json, markdown, or html"
        )
        raise typer.Exit(1)

    # Determine extension
    ext_map = {"json": "json", "markdown": "md", "html": "html"}
    ext = ext_map[format]

    try:
        path = output or f"{notebook_id}_flashcards.{ext}"
        saved = asyncio.run(
            client.download_flashcards(notebook_id, path, artifact_id, format)
        )
        console.print(f"[green]✓[/green] Downloaded flashcards to: {saved}")
    except ArtifactNotReadyError:
        err_console.print(
            "[red]Error:[/red] Flashcards are not ready or do not exist."
        )
        raise typer.Exit(1)
    except ValueError as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        handle_error(e)
