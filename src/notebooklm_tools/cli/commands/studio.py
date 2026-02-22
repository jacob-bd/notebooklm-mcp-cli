"""Studio CLI commands for generation (audio, report, quiz, etc.)."""

from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from notebooklm_tools.core.alias import get_alias_manager
from notebooklm_tools.core.exceptions import NLMError
from notebooklm_tools.cli.formatters import detect_output_format, get_formatter
from notebooklm_tools.cli.utils import get_client
from notebooklm_tools.services import studio as studio_service, ServiceError, ValidationError
from notebooklm_tools.utils.config import get_default_language

console = Console()

# Main studio app for status/delete
app = typer.Typer(
    help="Manage studio artifacts",
    rich_markup_mode="rich",
    no_args_is_help=True,
)

# Individual generation apps
audio_app = typer.Typer(
    help="Create audio overviews",
    rich_markup_mode="rich",
    no_args_is_help=True,
)
report_app = typer.Typer(
    help="Create reports",
    rich_markup_mode="rich",
    no_args_is_help=True,
)
quiz_app = typer.Typer(
    help="Create quizzes",
    rich_markup_mode="rich",
    no_args_is_help=True,
)
flashcards_app = typer.Typer(
    help="Create flashcards",
    rich_markup_mode="rich",
    no_args_is_help=True,
)
mindmap_app = typer.Typer(
    help="Create and manage mind maps",
    rich_markup_mode="rich",
    no_args_is_help=True,
)
slides_app = typer.Typer(
    help="Create slide decks",
    rich_markup_mode="rich",
    no_args_is_help=True,
)
infographic_app = typer.Typer(
    help="Create infographics",
    rich_markup_mode="rich",
    no_args_is_help=True,
)
video_app = typer.Typer(
    help="Create video overviews",
    rich_markup_mode="rich",
    no_args_is_help=True,
)
data_table_app = typer.Typer(
    help="Create data tables",
    rich_markup_mode="rich",
    no_args_is_help=True,
)


def parse_source_ids(source_ids: str | None) -> list[str] | None:
    """Parse comma-separated source IDs."""
    if source_ids:
        return [get_alias_manager().resolve(s.strip()) for s in source_ids.split(",")]
    return None


def _run_create(
    notebook_id: str,
    artifact_type: str,
    label: str,
    profile: Optional[str],
    **kwargs,
) -> None:
    """Shared CLI creation logic: spinner + service call + formatted output.

    CLI-specific concerns (confirmation, arg parsing) happen in each command.
    This helper handles the common pattern of spinner → create → print result.
    """
    if not kwargs.get("language"):
        kwargs["language"] = get_default_language()

    try:
        notebook_id = get_alias_manager().resolve(notebook_id)
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task(f"Creating {label}...", total=None)
            with get_client(profile) as client:
                result = studio_service.create_artifact(
                    client, notebook_id, artifact_type, **kwargs,
                )

        # Mind map has a different result shape
        if artifact_type == "mind_map":
            console.print(f"[green]✓[/green] Mind map created")
            console.print(f"  ID: {result.get('artifact_id', 'unknown')}")
            console.print(f"  Title: {result.get('title', 'Mind Map')}")
        else:
            console.print(f"[green]✓[/green] {label.title()} generation started")
            console.print(f"  Artifact ID: {result.get('artifact_id', 'unknown')}")
            console.print(f"\n[dim]Run 'nlm studio status {notebook_id}' to check progress.[/dim]")
    except (ValidationError, ServiceError) as e:
        msg = e.user_message if isinstance(e, ServiceError) else str(e)
        console.print(f"[red]Error:[/red] {msg}")
        if isinstance(e, ServiceError) and "rejected" in str(e):
            console.print("[dim]Try again later or create from NotebookLM UI for diagnosis.[/dim]")
        raise typer.Exit(1)
    except NLMError as e:
        console.print(f"[red]Error:[/red] {e.message}")
        if e.hint:
            console.print(f"\n[dim]Hint: {e.hint}[/dim]")
        raise typer.Exit(1)


# ========== Studio Status/Delete ==========

@app.command("status")
def studio_status(
    notebook_id: str = typer.Argument(..., help="Notebook ID"),
    full: bool = typer.Option(False, "--full", "-a", help="Show all details"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """List all studio artifacts and their status."""
    try:
        notebook_id = get_alias_manager().resolve(notebook_id)
        with get_client(profile) as client:
            artifacts = client.poll_studio_status(notebook_id)

        fmt = detect_output_format(json_output)
        formatter = get_formatter(fmt, console)
        formatter.format_artifacts(artifacts, full=full)
    except NLMError as e:
        console.print(f"[red]Error:[/red] {e.message}")
        if e.hint:
            console.print(f"\n[dim]Hint: {e.hint}[/dim]")
        raise typer.Exit(1)


@app.command("delete")
def studio_delete(
    notebook_id: str = typer.Argument(..., help="Notebook ID"),
    artifact_id: str = typer.Argument(..., help="Artifact ID to delete"),
    confirm: bool = typer.Option(False, "--confirm", "-y", help="Skip confirmation"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """Delete a studio artifact permanently."""
    notebook_id = get_alias_manager().resolve(notebook_id)
    artifact_id = get_alias_manager().resolve(artifact_id)

    if not confirm:
        typer.confirm(f"Are you sure you want to delete artifact {artifact_id}?", abort=True)

    try:
        with get_client(profile) as client:
            studio_service.delete_artifact(client, artifact_id, notebook_id)
        console.print(f"[green]✓[/green] Deleted artifact: {artifact_id}")
    except ServiceError as e:
        console.print(f"[red]Error:[/red] {e.user_message}")
        raise typer.Exit(1)
    except NLMError as e:
        console.print(f"[red]Error:[/red] {e.message}")
        if e.hint:
            console.print(f"\n[dim]Hint: {e.hint}[/dim]")
        raise typer.Exit(1)


@app.command("rename")
def studio_rename(
    artifact_id: str = typer.Argument(..., help="Artifact ID to rename"),
    new_title: str = typer.Argument(..., help="New title for the artifact"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """Rename a studio artifact."""
    artifact_id = get_alias_manager().resolve(artifact_id)

    try:
        with get_client(profile) as client:
            result = studio_service.rename_artifact(client, artifact_id, new_title)
        console.print(f"[green]✓[/green] Renamed artifact to: {result['new_title']}")
    except (ValidationError, ServiceError) as e:
        msg = e.user_message if isinstance(e, ServiceError) else str(e)
        console.print(f"[red]Error:[/red] {msg}")
        raise typer.Exit(1)
    except NLMError as e:
        console.print(f"[red]Error:[/red] {e.message}")
        if e.hint:
            console.print(f"\n[dim]Hint: {e.hint}[/dim]")
        raise typer.Exit(1)


# ========== Audio ==========

@audio_app.command("create")
def create_audio(
    notebook_id: str = typer.Argument(..., help="Notebook ID"),
    format: str = typer.Option(
        "deep_dive", "--format", "-f",
        help="Overview format (deep_dive, brief, critique, debate)",
    ),
    length: str = typer.Option(
        "default", "--length", "-l",
        help="Length (short, default, long)",
    ),
    language: str = typer.Option(
        "", "--language",
        help="BCP-47 language code (default: NOTEBOOKLM_HL or en)",
    ),
    focus: Optional[str] = typer.Option(
        None, "--focus",
        help="Optional focus topic",
    ),
    source_ids: Optional[str] = typer.Option(
        None, "--source-ids", "-s",
        help="Comma-separated source IDs",
    ),
    confirm: bool = typer.Option(False, "--confirm", "-y", help="Skip confirmation"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """Create an audio overview (podcast) from notebook sources."""
    if not confirm:
        typer.confirm(f"Create {format} audio overview?", abort=True)

    _run_create(
        notebook_id, "audio", "audio",
        profile=profile,
        source_ids=parse_source_ids(source_ids),
        audio_format=format, audio_length=length,
        language=language, focus_prompt=focus or "",
    )


# ========== Report ==========

@report_app.command("create")
def create_report(
    notebook_id: str = typer.Argument(..., help="Notebook ID"),
    format: str = typer.Option(
        "Briefing Doc", "--format", "-f",
        help="Format: 'Briefing Doc', 'Study Guide', 'Blog Post', 'Create Your Own'",
    ),
    prompt: str = typer.Option("", "--prompt", help="Custom prompt (required for 'Create Your Own')"),
    language: str = typer.Option("", "--language", help="BCP-47 language code (default: NOTEBOOKLM_HL or en)"),
    source_ids: Optional[str] = typer.Option(None, "--source-ids", "-s", help="Comma-separated source IDs"),
    confirm: bool = typer.Option(False, "--confirm", "-y", help="Skip confirmation"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """Create a report from notebook sources."""
    if format == "Create Your Own" and not prompt:
        console.print("[red]Error:[/red] --prompt is required when format is 'Create Your Own'")
        raise typer.Exit(1)

    if not confirm:
        typer.confirm(f"Create '{format}' report?", abort=True)

    _run_create(
        notebook_id, "report", "report",
        profile=profile,
        source_ids=parse_source_ids(source_ids),
        report_format=format, custom_prompt=prompt,
        language=language,
    )


# ========== Quiz ==========

@quiz_app.command("create")
def create_quiz(
    notebook_id: str = typer.Argument(..., help="Notebook ID"),
    count: int = typer.Option(2, "--count", "-c", help="Number of questions"),
    difficulty: int = typer.Option(2, "--difficulty", "-d", help="Difficulty 1-5 (1=easy, 5=hard)"),
    focus: Optional[str] = typer.Option(None, "--focus", "-f", help="Focus prompt to guide generation"),
    source_ids: Optional[str] = typer.Option(None, "--source-ids", "-s", help="Comma-separated source IDs"),
    confirm: bool = typer.Option(False, "--confirm", "-y", help="Skip confirmation"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """Create a quiz from notebook sources."""
    if not confirm:
        typer.confirm(f"Create quiz with {count} questions?", abort=True)

    # Quiz CLI sends raw int codes directly — bypass service string resolution
    try:
        notebook_id_resolved = get_alias_manager().resolve(notebook_id)
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task("Creating quiz...", total=None)
            with get_client(profile) as client:
                result = client.create_quiz(
                    notebook_id_resolved,
                    question_count=count,
                    difficulty=difficulty,
                    source_ids=parse_source_ids(source_ids),
                    focus_prompt=focus or "",
                )

        if not result or not result.get("artifact_id"):
            console.print("[red]Error:[/red] NotebookLM rejected quiz creation (no artifact returned).")
            console.print("[dim]Try again later or create from NotebookLM UI for diagnosis.[/dim]")
            raise typer.Exit(1)

        console.print("[green]✓[/green] Quiz generation started")
        console.print(f"  Artifact ID: {result.get('artifact_id', 'unknown')}")
        console.print(f"\n[dim]Run 'nlm studio status {notebook_id_resolved}' to check progress.[/dim]")
    except NLMError as e:
        console.print(f"[red]Error:[/red] {e.message}")
        if e.hint:
            console.print(f"\n[dim]Hint: {e.hint}[/dim]")
        raise typer.Exit(1)


# ========== Flashcards ==========

@flashcards_app.command("create")
def create_flashcards(
    notebook_id: str = typer.Argument(..., help="Notebook ID"),
    difficulty: str = typer.Option("medium", "--difficulty", "-d", help="Difficulty: easy, medium, hard"),
    focus: Optional[str] = typer.Option(None, "--focus", "-f", help="Focus prompt to guide generation"),
    source_ids: Optional[str] = typer.Option(None, "--source-ids", "-s", help="Comma-separated source IDs"),
    confirm: bool = typer.Option(False, "--confirm", "-y", help="Skip confirmation"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """Create flashcards from notebook sources."""
    if not confirm:
        typer.confirm("Create flashcards?", abort=True)

    _run_create(
        notebook_id, "flashcards", "flashcards",
        profile=profile,
        source_ids=parse_source_ids(source_ids),
        difficulty=difficulty,
        focus_prompt=focus or "",
    )


# ========== Mind Map ==========

@mindmap_app.command("create")
def create_mindmap(
    notebook_id: str = typer.Argument(..., help="Notebook ID"),
    title: str = typer.Option("Mind Map", "--title", "-t", help="Mind map title"),
    source_ids: Optional[str] = typer.Option(None, "--source-ids", "-s", help="Comma-separated source IDs"),
    confirm: bool = typer.Option(False, "--confirm", "-y", help="Skip confirmation"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """Create a mind map from notebook sources."""
    if not confirm:
        typer.confirm("Create mind map?", abort=True)

    _run_create(
        notebook_id, "mind_map", "mind map",
        profile=profile,
        source_ids=parse_source_ids(source_ids),
        title=title,
    )


# Note: mindmap list removed - use 'studio status' which now includes mindmaps


# ========== Slides ==========

@slides_app.command("create")
def create_slides(
    notebook_id: str = typer.Argument(..., help="Notebook ID"),
    format: str = typer.Option("detailed_deck", "--format", "-f", help="Format: detailed_deck, presenter_slides"),
    length: str = typer.Option("default", "--length", "-l", help="Length: short, default"),
    language: str = typer.Option("", "--language", help="BCP-47 language code (default: NOTEBOOKLM_HL or en)"),
    focus: str = typer.Option("", "--focus", help="Optional focus topic"),
    source_ids: Optional[str] = typer.Option(None, "--source-ids", "-s", help="Comma-separated source IDs"),
    confirm: bool = typer.Option(False, "--confirm", "-y", help="Skip confirmation"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """Create a slide deck from notebook sources."""
    if not confirm:
        typer.confirm("Create slide deck?", abort=True)

    _run_create(
        notebook_id, "slide_deck", "slide deck",
        profile=profile,
        source_ids=parse_source_ids(source_ids),
        slide_format=format, slide_length=length,
        language=language, focus_prompt=focus,
    )


@slides_app.command("revise")
def revise_slides(
    artifact_id: str = typer.Argument(..., help="Artifact ID of the slide deck to revise"),
    slide: list[str] = typer.Option(
        ..., "--slide",
        help='Slide revision in format: SLIDE_NUM "instruction" (e.g., --slide 1 "Make title larger")',
    ),
    confirm: bool = typer.Option(False, "--confirm", "-y", help="Skip confirmation"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """Revise individual slides in an existing slide deck.

    Creates a NEW slide deck with revisions applied. The original is not modified.

    Examples:
        nlm slides revise <artifact-id> --slide '1 Make the title larger' --confirm
        nlm slides revise <artifact-id> --slide '1 Make title larger' --slide '3 Remove the image' --confirm
    """
    artifact_id = get_alias_manager().resolve(artifact_id)

    # Parse --slide arguments: each is "NUMBER instruction text"
    instructions: list[dict] = []
    for s in slide:
        parts = s.strip().split(None, 1)
        if len(parts) < 2:
            console.print(f"[red]Error:[/red] Invalid --slide format: '{s}'. Expected: NUMBER \"instruction\"")
            raise typer.Exit(1)
        try:
            slide_num = int(parts[0])
        except ValueError:
            console.print(f"[red]Error:[/red] Invalid slide number: '{parts[0]}'. Must be an integer >= 1.")
            raise typer.Exit(1)
        instructions.append({"slide": slide_num, "instruction": parts[1]})

    if not confirm:
        console.print("[bold]Slides to revise:[/bold]")
        for inst in instructions:
            console.print(f"  Slide {inst['slide']}: {inst['instruction']}")
        console.print("\n[dim]This creates a NEW slide deck. The original is not modified.[/dim]")
        typer.confirm("Proceed with revision?", abort=True)

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task("Revising slide deck...", total=None)
            with get_client(profile) as client:
                result = studio_service.revise_artifact(
                    client, artifact_id, instructions,
                )

        console.print("[green]✓[/green] Slide deck revision started")
        console.print(f"  New Artifact ID: {result.get('artifact_id', 'unknown')}")
        console.print(f"  Original: {artifact_id}")
        console.print(f"\n[dim]Run 'nlm studio status <notebook-id>' to check progress.[/dim]")
    except (ValidationError, ServiceError) as e:
        msg = e.user_message if isinstance(e, ServiceError) else str(e)
        console.print(f"[red]Error:[/red] {msg}")
        raise typer.Exit(1)
    except NLMError as e:
        console.print(f"[red]Error:[/red] {e.message}")
        if e.hint:
            console.print(f"\n[dim]Hint: {e.hint}[/dim]")
        raise typer.Exit(1)


# ========== Infographic ==========

@infographic_app.command("create")
def create_infographic(
    notebook_id: str = typer.Argument(..., help="Notebook ID"),
    orientation: str = typer.Option("landscape", "--orientation", "-o", help="Orientation: landscape, portrait, square"),
    detail: str = typer.Option("standard", "--detail", "-d", help="Detail level: concise, standard, detailed"),
    language: str = typer.Option("", "--language", help="BCP-47 language code (default: NOTEBOOKLM_HL or en)"),
    focus: str = typer.Option("", "--focus", help="Optional focus topic"),
    source_ids: Optional[str] = typer.Option(None, "--source-ids", "-s", help="Comma-separated source IDs"),
    confirm: bool = typer.Option(False, "--confirm", "-y", help="Skip confirmation"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """Create an infographic from notebook sources."""
    if not confirm:
        typer.confirm("Create infographic?", abort=True)

    _run_create(
        notebook_id, "infographic", "infographic",
        profile=profile,
        source_ids=parse_source_ids(source_ids),
        orientation=orientation, detail_level=detail,
        language=language, focus_prompt=focus,
    )


# ========== Video ==========

@video_app.command("create")
def create_video(
    notebook_id: str = typer.Argument(..., help="Notebook ID"),
    format: str = typer.Option("explainer", "--format", "-f", help="Format: explainer, brief"),
    style: str = typer.Option(
        "auto_select", "--style", "-s",
        help="Visual style: auto_select, classic, whiteboard, kawaii, anime, watercolor, retro_print, heritage, paper_craft",
    ),
    language: str = typer.Option("", "--language", help="BCP-47 language code (default: NOTEBOOKLM_HL or en)"),
    focus: str = typer.Option("", "--focus", help="Optional focus topic"),
    source_ids: Optional[str] = typer.Option(None, "--source-ids", help="Comma-separated source IDs"),
    confirm: bool = typer.Option(False, "--confirm", "-y", help="Skip confirmation"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """Create a video overview from notebook sources."""
    if not confirm:
        typer.confirm("Create video overview?", abort=True)

    _run_create(
        notebook_id, "video", "video",
        profile=profile,
        source_ids=parse_source_ids(source_ids),
        video_format=format, visual_style=style,
        language=language, focus_prompt=focus,
    )


# ========== Data Table ==========

@data_table_app.command("create")
def create_data_table(
    notebook_id: str = typer.Argument(..., help="Notebook ID"),
    description: str = typer.Argument(..., help="Description of the data table to create"),
    language: str = typer.Option("", "--language", help="BCP-47 language code (default: NOTEBOOKLM_HL or en)"),
    source_ids: Optional[str] = typer.Option(None, "--source-ids", "-s", help="Comma-separated source IDs"),
    confirm: bool = typer.Option(False, "--confirm", "-y", help="Skip confirmation"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """Create a data table from notebook sources."""
    if not confirm:
        typer.confirm("Create data table?", abort=True)

    _run_create(
        notebook_id, "data_table", "data table",
        profile=profile,
        source_ids=parse_source_ids(source_ids),
        description=description, language=language,
    )
