import typer
from typing import Optional
from pathlib import Path
from notebooklm_tools.core.client import NotebookLMClient, ArtifactNotReadyError, ArtifactError
from notebooklm_tools.cli.utils import get_client, handle_error

app = typer.Typer(help="Download artifacts from notebooks.")

@app.command("audio")
def download_audio(
    notebook_id: str = typer.Argument(..., help="Notebook ID"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output path (default: ./{notebook_id}_audio.mp4)"),
    artifact_id: Optional[str] = typer.Option(None, "--id", help="Specific artifact ID")
):
    """Download Audio Overview."""
    client = get_client()
    try:
        path = output or f"{notebook_id}_audio.mp4"
        saved = client.download_audio(notebook_id, path, artifact_id)
        typer.echo(f"Downloaded audio to: {saved}")
    except ArtifactNotReadyError:
        typer.echo("Error: Audio Overview is not ready or does not exist.", err=True)
        raise typer.Exit(1)
    except Exception as e:
        handle_error(e)

@app.command("video")
def download_video(
    notebook_id: str = typer.Argument(..., help="Notebook ID"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output path (default: ./{notebook_id}_video.mp4)"),
    artifact_id: Optional[str] = typer.Option(None, "--id", help="Specific artifact ID")
):
    """Download Video Overview."""
    client = get_client()
    try:
        path = output or f"{notebook_id}_video.mp4"
        saved = client.download_video(notebook_id, path, artifact_id)
        typer.echo(f"Downloaded video to: {saved}")
    except ArtifactNotReadyError:
        typer.echo("Error: Video Overview is not ready or does not exist.", err=True)
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
    client = get_client()
    try:
        path = output or f"{notebook_id}_report.md"
        saved = client.download_report(notebook_id, path, artifact_id)
        typer.echo(f"Downloaded report to: {saved}")
    except ArtifactNotReadyError:
        typer.echo("Error: Report is not ready or does not exist.", err=True)
        raise typer.Exit(1)
    except Exception as e:
        handle_error(e)

@app.command("mind-map")
def download_mind_map(
    notebook_id: str = typer.Argument(..., help="Notebook ID"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output path (default: ./{notebook_id}_mindmap.json)"),
    artifact_id: Optional[str] = typer.Option(None, "--id", help="Specific artifact ID (note ID)")
):
    """Download Mind Map (JSON)."""
    client = get_client()
    try:
        path = output or f"{notebook_id}_mindmap.json"
        saved = client.download_mind_map(notebook_id, path, artifact_id)
        typer.echo(f"Downloaded mind map to: {saved}")
    except ArtifactNotReadyError:
        typer.echo("Error: Mind map is not ready or does not exist.", err=True)
        raise typer.Exit(1)
    except Exception as e:
        handle_error(e)

@app.command("slide-deck")
def download_slide_deck(
    notebook_id: str = typer.Argument(..., help="Notebook ID"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output path (default: ./{notebook_id}_slides.pdf)"),
    artifact_id: Optional[str] = typer.Option(None, "--id", help="Specific artifact ID")
):
    """Download Slide Deck (PDF)."""
    client = get_client()
    try:
        path = output or f"{notebook_id}_slides.pdf"
        saved = client.download_slide_deck(notebook_id, path, artifact_id)
        typer.echo(f"Downloaded slide deck to: {saved}")
    except ArtifactNotReadyError:
        typer.echo("Error: Slide deck is not ready or does not exist.", err=True)
        raise typer.Exit(1)
    except Exception as e:
        handle_error(e)

@app.command("infographic")
def download_infographic(
    notebook_id: str = typer.Argument(..., help="Notebook ID"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output path (default: ./{notebook_id}_infographic.png)"),
    artifact_id: Optional[str] = typer.Option(None, "--id", help="Specific artifact ID")
):
    """Download Infographic (PNG)."""
    client = get_client()
    try:
        path = output or f"{notebook_id}_infographic.png"
        saved = client.download_infographic(notebook_id, path, artifact_id)
        typer.echo(f"Downloaded infographic to: {saved}")
    except ArtifactNotReadyError:
        typer.echo("Error: Infographic is not ready or does not exist.", err=True)
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
    client = get_client()
    try:
        path = output or f"{notebook_id}_table.csv"
        saved = client.download_data_table(notebook_id, path, artifact_id)
        typer.echo(f"Downloaded data table to: {saved}")
    except ArtifactNotReadyError:
        typer.echo("Error: Data table is not ready or does not exist.", err=True)
        raise typer.Exit(1)
    except Exception as e:
        handle_error(e)
