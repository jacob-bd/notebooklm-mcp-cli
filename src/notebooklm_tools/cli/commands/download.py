"""Download CLI commands."""

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
from notebooklm_tools.core.client import ArtifactNotReadyError
from notebooklm_tools.cli.utils import get_client, handle_error
from notebooklm_tools.core.alias import get_alias_manager
from notebooklm_tools.services import downloads as downloads_service, ServiceError

app = typer.Typer(help="Download artifacts from notebooks.")
console = Console()
err_console = Console(stderr=True)


def _download_with_progress(
    download_func: Callable[[Callable[[int, int], None]], Any],
    description: str,
    show_progress: bool = True,
):
    """Wrapper to show progress bar for downloads (CLI-only presentation concern)."""
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


def _streaming_download(
    notebook_id: str,
    artifact_type: str,
    output: Optional[str],
    artifact_id: Optional[str],
    no_progress: bool,
    default_suffix: str,
    description: str,
    slide_deck_format: str = "pdf",
) -> None:
    """Common pattern for streaming (async with progress) downloads."""
    notebook_id = get_alias_manager().resolve(notebook_id)
    downloads_service.validate_artifact_type(artifact_type)

    client = get_client()
    path = output or f"{notebook_id}_{default_suffix}"

    try:
        saved = _download_with_progress(
            lambda cb: asyncio.run(
                downloads_service.download_async(
                    client, notebook_id, artifact_type, path,
                    artifact_id=artifact_id,
                    progress_callback=cb,
                    slide_deck_format=slide_deck_format,
                )
            )["path"],
            description,
            show_progress=not no_progress,
        )
        console.print(f"[green]✓[/green] Downloaded {artifact_type.replace('_', ' ')} to: {saved}")
    except ArtifactNotReadyError:
        err_console.print(f"[red]Error:[/red] {description.replace('Downloading ', '').title()} is not ready or does not exist.")
        raise typer.Exit(1)
    except ServiceError as e:
        err_console.print(f"[red]Error:[/red] {e.user_message}")
        raise typer.Exit(1)
    except Exception as e:
        handle_error(e)


def _simple_download(
    notebook_id: str,
    artifact_type: str,
    output: Optional[str],
    artifact_id: Optional[str],
    default_suffix: str,
) -> None:
    """Common pattern for simple (synchronous) downloads."""
    notebook_id = get_alias_manager().resolve(notebook_id)
    downloads_service.validate_artifact_type(artifact_type)

    path = output or f"{notebook_id}_{default_suffix}"
    client = get_client()

    try:
        result = downloads_service.download_sync(
            client, notebook_id, artifact_type, path,
            artifact_id=artifact_id,
        )
        console.print(f"[green]✓[/green] Downloaded {artifact_type.replace('_', ' ')} to: {result['path']}")
    except ArtifactNotReadyError:
        err_console.print(f"[red]Error:[/red] {artifact_type.replace('_', ' ').title()} is not ready or does not exist.")
        raise typer.Exit(1)
    except ServiceError as e:
        err_console.print(f"[red]Error:[/red] {e.user_message}")
        raise typer.Exit(1)
    except Exception as e:
        handle_error(e)


def _interactive_download(
    notebook_id: str,
    artifact_type: str,
    output: Optional[str],
    artifact_id: Optional[str],
    output_format: str,
) -> None:
    """Common pattern for interactive artifact downloads (quiz/flashcards)."""
    notebook_id = get_alias_manager().resolve(notebook_id)
    downloads_service.validate_artifact_type(artifact_type)
    downloads_service.validate_output_format(output_format)

    ext = downloads_service.get_default_extension(artifact_type, output_format)
    path = output or f"{notebook_id}_{artifact_type}.{ext}"
    client = get_client()

    try:
        result_dict = asyncio.run(
            downloads_service.download_async(
                client, notebook_id, artifact_type, path,
                artifact_id=artifact_id,
                output_format=output_format,
            )
        )
        console.print(f"[green]✓[/green] Downloaded {artifact_type.replace('_', ' ')} to: {result_dict['path']}")
    except ArtifactNotReadyError:
        err_console.print(f"[red]Error:[/red] {artifact_type.replace('_', ' ').title()} is not ready or does not exist.")
        raise typer.Exit(1)
    except ServiceError as e:
        err_console.print(f"[red]Error:[/red] {e.user_message}")
        raise typer.Exit(1)
    except ValueError as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        handle_error(e)


# --- Streaming downloads (with progress bars) ---

@app.command("audio")
def download_audio(
    notebook_id: str = typer.Argument(..., help="Notebook ID"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output path (default: ./{notebook_id}_audio.m4a)"),
    artifact_id: Optional[str] = typer.Option(None, "--id", help="Specific artifact ID"),
    no_progress: bool = typer.Option(False, "--no-progress", help="Disable download progress bar"),
):
    """Download Audio Overview."""
    _streaming_download(notebook_id, "audio", output, artifact_id, no_progress, "audio.m4a", "Downloading audio")


@app.command("video")
def download_video(
    notebook_id: str = typer.Argument(..., help="Notebook ID"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output path (default: ./{notebook_id}_video.mp4)"),
    artifact_id: Optional[str] = typer.Option(None, "--id", help="Specific artifact ID"),
    no_progress: bool = typer.Option(False, "--no-progress", help="Disable download progress bar"),
):
    """Download Video Overview."""
    _streaming_download(notebook_id, "video", output, artifact_id, no_progress, "video.mp4", "Downloading video")


@app.command("slide-deck")
def download_slide_deck(
    notebook_id: str = typer.Argument(..., help="Notebook ID"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output path (default: ./{notebook_id}_slides.{ext})"),
    artifact_id: Optional[str] = typer.Option(None, "--id", help="Specific artifact ID"),
    no_progress: bool = typer.Option(False, "--no-progress", help="Disable download progress bar"),
    format: str = typer.Option("pdf", "--format", "-f", help="File format: pdf (default) or pptx"),
):
    """Download Slide Deck (PDF or PPTX)."""
    fmt = format.lower()
    if fmt not in ("pdf", "pptx"):
        err_console.print("[red]Error:[/red] --format must be 'pdf' or 'pptx'")
        raise typer.Exit(1)
    default_suffix = f"slides.{fmt}"
    _streaming_download(
        notebook_id, "slide_deck", output, artifact_id, no_progress,
        default_suffix, "Downloading slide deck",
        slide_deck_format=fmt,
    )


@app.command("infographic")
def download_infographic(
    notebook_id: str = typer.Argument(..., help="Notebook ID"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output path (default: ./{notebook_id}_infographic.png)"),
    artifact_id: Optional[str] = typer.Option(None, "--id", help="Specific artifact ID"),
    no_progress: bool = typer.Option(False, "--no-progress", help="Disable download progress bar"),
):
    """Download Infographic (PNG)."""
    _streaming_download(notebook_id, "infographic", output, artifact_id, no_progress, "infographic.png", "Downloading infographic")


# --- Simple (synchronous) downloads ---

@app.command("report")
def download_report(
    notebook_id: str = typer.Argument(..., help="Notebook ID"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output path (default: ./{notebook_id}_report.md)"),
    artifact_id: Optional[str] = typer.Option(None, "--id", help="Specific artifact ID"),
):
    """Download Report (Markdown)."""
    _simple_download(notebook_id, "report", output, artifact_id, "report.md")


@app.command("mind-map")
def download_mind_map(
    notebook_id: str = typer.Argument(..., help="Notebook ID"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output path (default: ./{notebook_id}_mindmap.json)"),
    artifact_id: Optional[str] = typer.Option(None, "--id", help="Specific artifact ID (note ID)"),
):
    """Download Mind Map (JSON)."""
    _simple_download(notebook_id, "mind_map", output, artifact_id, "mindmap.json")


@app.command("data-table")
def download_data_table(
    notebook_id: str = typer.Argument(..., help="Notebook ID"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output path (default: ./{notebook_id}_table.csv)"),
    artifact_id: Optional[str] = typer.Option(None, "--id", help="Specific artifact ID"),
):
    """Download Data Table (CSV)."""
    _simple_download(notebook_id, "data_table", output, artifact_id, "table.csv")


# --- Interactive format downloads (quiz/flashcards) ---

@app.command("quiz")
def download_quiz_cmd(
    notebook_id: str = typer.Argument(..., help="Notebook ID"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output path (default: ./{notebook_id}_quiz.{ext})"),
    artifact_id: Optional[str] = typer.Option(None, "--id", help="Specific artifact ID"),
    format: str = typer.Option("json", "--format", "-f", help="Output format: json, markdown, or html"),
):
    """Download Quiz."""
    _interactive_download(notebook_id, "quiz", output, artifact_id, format)


@app.command("flashcards")
def download_flashcards_cmd(
    notebook_id: str = typer.Argument(..., help="Notebook ID"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output path (default: ./{notebook_id}_flashcards.{ext})"),
    artifact_id: Optional[str] = typer.Option(None, "--id", help="Specific artifact ID"),
    format: str = typer.Option("json", "--format", "-f", help="Output format: json, markdown, or html"),
):
    """Download Flashcards."""
    _interactive_download(notebook_id, "flashcards", output, artifact_id, format)
