"""Studio CLI commands for generation (audio, report, quiz, etc.)."""

from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from notebooklm_tools.core import constants
from notebooklm_tools.core.alias import get_alias_manager
from notebooklm_tools.core.exceptions import NLMError
from notebooklm_tools.cli.formatters import detect_output_format, get_formatter
from notebooklm_tools.cli.utils import get_client

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
            # Use poll_studio_status to get the latest status
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
            # Note: delete_studio_artifact takes (artifact_id, notebook_id) - REVERSED kwargs in client
            client.delete_studio_artifact(artifact_id, notebook_id=notebook_id)
        
        console.print(f"[green]✓[/green] Deleted artifact: {artifact_id}")
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
        "en", "--language",
        help="BCP-47 language code (en, es, fr, de, ja)",
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
    
    try:
        notebook_id = get_alias_manager().resolve(notebook_id)

        # Convert string parameters to integer codes
        try:
            format_code = constants.AUDIO_FORMATS.get_code(format)
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)
        try:
            length_code = constants.AUDIO_LENGTHS.get_code(length)
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task("Creating audio...", total=None)
            with get_client(profile) as client:
                result = client.create_audio_overview(
                    notebook_id,
                    format_code=format_code,
                    length_code=length_code,
                    language=language,
                    focus_prompt=focus,
                    source_ids=parse_source_ids(source_ids),
                )
        
        console.print(f"[green]✓[/green] Audio generation started")
        if result:
            console.print(f"  Artifact ID: {result.get('artifact_id', 'unknown')}")
        console.print(f"  Format: {format}")
        console.print(f"\n[dim]Run 'nlm studio status {notebook_id}' to check progress.[/dim]")
    except NLMError as e:
        console.print(f"[red]Error:[/red] {e.message}")
        if e.hint:
            console.print(f"\n[dim]Hint: {e.hint}[/dim]")
        raise typer.Exit(1)


# ========== Report ==========

@report_app.command("create")
def create_report(
    notebook_id: str = typer.Argument(..., help="Notebook ID"),
    format: str = typer.Option(
        "Briefing Doc", "--format", "-f",
        help="Format: 'Briefing Doc', 'Study Guide', 'Blog Post', 'Create Your Own'",
    ),
    prompt: str = typer.Option("", "--prompt", help="Custom prompt (required for 'Create Your Own')"),
    language: str = typer.Option("en", "--language", help="BCP-47 language code"),
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
    
    try:
        notebook_id = get_alias_manager().resolve(notebook_id)
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task("Creating report...", total=None)
            with get_client(profile) as client:
                result = client.create_report(
                    notebook_id,
                    report_format=format,
                    custom_prompt=prompt,
                    language=language,
                    source_ids=parse_source_ids(source_ids),
                )
        
        console.print(f"[green]✓[/green] Report generation started")
        if result:
            console.print(f"  Artifact ID: {result.get('artifact_id', 'unknown')}")
        console.print(f"\n[dim]Run 'nlm studio status {notebook_id}' to check progress.[/dim]")
    except NLMError as e:
        console.print(f"[red]Error:[/red] {e.message}")
        if e.hint:
            console.print(f"\n[dim]Hint: {e.hint}[/dim]")
        raise typer.Exit(1)


# ========== Quiz ==========

@quiz_app.command("create")
def create_quiz(
    notebook_id: str = typer.Argument(..., help="Notebook ID"),
    count: int = typer.Option(2, "--count", "-c", help="Number of questions"),
    difficulty: int = typer.Option(2, "--difficulty", "-d", help="Difficulty 1-5 (1=easy, 5=hard)"),
    source_ids: Optional[str] = typer.Option(None, "--source-ids", "-s", help="Comma-separated source IDs"),
    confirm: bool = typer.Option(False, "--confirm", "-y", help="Skip confirmation"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """Create a quiz from notebook sources."""
    if not confirm:
        typer.confirm(f"Create quiz with {count} questions?", abort=True)
    
    try:
        notebook_id = get_alias_manager().resolve(notebook_id)
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task("Creating quiz...", total=None)
            with get_client(profile) as client:
                result = client.create_quiz(
                    notebook_id,
                    question_count=count,
                    difficulty=difficulty,
                    source_ids=parse_source_ids(source_ids),
                )
        
        console.print(f"[green]✓[/green] Quiz generation started")
        if result:
            console.print(f"  Artifact ID: {result.get('artifact_id', 'unknown')}")
        console.print(f"\n[dim]Run 'nlm studio status {notebook_id}' to check progress.[/dim]")
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
    source_ids: Optional[str] = typer.Option(None, "--source-ids", "-s", help="Comma-separated source IDs"),
    confirm: bool = typer.Option(False, "--confirm", "-y", help="Skip confirmation"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """Create flashcards from notebook sources."""
    if not confirm:
        typer.confirm("Create flashcards?", abort=True)
    
    try:
        notebook_id = get_alias_manager().resolve(notebook_id)

        # Convert string parameters to integer codes
        try:
            difficulty_code = constants.FLASHCARD_DIFFICULTIES.get_code(difficulty)
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task("Creating flashcards...", total=None)
            with get_client(profile) as client:
                result = client.create_flashcards(
                    notebook_id,
                    difficulty_code=difficulty_code,
                    source_ids=parse_source_ids(source_ids),
                )
        
        console.print(f"[green]✓[/green] Flashcards generation started")
        if result:
            console.print(f"  Artifact ID: {result.get('artifact_id', 'unknown')}")
        console.print(f"\n[dim]Run 'nlm studio status {notebook_id}' to check progress.[/dim]")
    except NLMError as e:
        console.print(f"[red]Error:[/red] {e.message}")
        if e.hint:
            console.print(f"\n[dim]Hint: {e.hint}[/dim]")
        raise typer.Exit(1)


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
    
    try:
        notebook_id = get_alias_manager().resolve(notebook_id)
        parsed_source_ids = parse_source_ids(source_ids)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task("Creating mind map...", total=None)
            with get_client(profile) as client:
                # Two-step process: generate then save
                gen_result = client.generate_mind_map(
                    notebook_id=notebook_id,
                    source_ids=parsed_source_ids,
                )

                # Check if generation was successful and we have mind_map_json to save
                if gen_result and 'mind_map_json' in gen_result:
                    result = client.save_mind_map(
                        notebook_id,
                        gen_result['mind_map_json'],
                        source_ids=parsed_source_ids,
                        title=title if title else "Mind Map",
                    )
                else:
                    raise NLMError("Failed to generate mind map")
        
        console.print(f"[green]✓[/green] Mind map created")
        if result:
            console.print(f"  ID: {result.get('mind_map_id', result.get('artifact_id', 'unknown'))}")
            console.print(f"  Title: {title}")
    except NLMError as e:
        console.print(f"[red]Error:[/red] {e.message}")
        if e.hint:
            console.print(f"\n[dim]Hint: {e.hint}[/dim]")
        raise typer.Exit(1)


# Note: mindmap list removed - use 'studio status' which now includes mindmaps


# ========== Slides ==========

@slides_app.command("create")
def create_slides(
    notebook_id: str = typer.Argument(..., help="Notebook ID"),
    format: str = typer.Option("detailed_deck", "--format", "-f", help="Format: detailed_deck, presenter_slides"),
    length: str = typer.Option("default", "--length", "-l", help="Length: short, default"),
    language: str = typer.Option("en", "--language", help="BCP-47 language code"),
    focus: str = typer.Option("", "--focus", help="Optional focus topic"),
    source_ids: Optional[str] = typer.Option(None, "--source-ids", "-s", help="Comma-separated source IDs"),
    confirm: bool = typer.Option(False, "--confirm", "-y", help="Skip confirmation"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """Create a slide deck from notebook sources."""
    if not confirm:
        typer.confirm("Create slide deck?", abort=True)
    
    try:
        notebook_id = get_alias_manager().resolve(notebook_id)

        # Convert string parameters to integer codes
        try:
            format_code = constants.SLIDE_DECK_FORMATS.get_code(format)
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)
        try:
            length_code = constants.SLIDE_DECK_LENGTHS.get_code(length)
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task("Creating slides...", total=None)
            with get_client(profile) as client:
                result = client.create_slide_deck(
                    notebook_id,
                    format_code=format_code,
                    length_code=length_code,
                    language=language,
                    focus_prompt=focus,
                    source_ids=parse_source_ids(source_ids),
                )
        
        console.print(f"[green]✓[/green] Slide deck generation started")
        if result:
            console.print(f"  Artifact ID: {result.get('artifact_id', 'unknown')}")
        console.print(f"\n[dim]Run 'nlm studio status {notebook_id}' to check progress.[/dim]")
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
    language: str = typer.Option("en", "--language", help="BCP-47 language code"),
    focus: str = typer.Option("", "--focus", help="Optional focus topic"),
    source_ids: Optional[str] = typer.Option(None, "--source-ids", "-s", help="Comma-separated source IDs"),
    confirm: bool = typer.Option(False, "--confirm", "-y", help="Skip confirmation"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """Create an infographic from notebook sources."""
    if not confirm:
        typer.confirm("Create infographic?", abort=True)
    
    try:
        notebook_id = get_alias_manager().resolve(notebook_id)

        # Convert string parameters to integer codes
        try:
            orientation_code = constants.INFOGRAPHIC_ORIENTATIONS.get_code(orientation)
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)
        try:
            detail_code = constants.INFOGRAPHIC_DETAILS.get_code(detail)
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task("Creating infographic...", total=None)
            with get_client(profile) as client:
                result = client.create_infographic(
                    notebook_id,
                    orientation_code=orientation_code,
                    detail_level_code=detail_code,
                    language=language,
                    focus_prompt=focus,
                    source_ids=parse_source_ids(source_ids),
                )
        
        console.print(f"[green]✓[/green] Infographic generation started")
        if result:
            console.print(f"  Artifact ID: {result.get('artifact_id', 'unknown')}")
        console.print(f"\n[dim]Run 'nlm studio status {notebook_id}' to check progress.[/dim]")
    except NLMError as e:
        console.print(f"[red]Error:[/red] {e.message}")
        if e.hint:
            console.print(f"\n[dim]Hint: {e.hint}[/dim]")
        raise typer.Exit(1)


# ========== Video ==========

@video_app.command("create")
def create_video(
    notebook_id: str = typer.Argument(..., help="Notebook ID"),
    format: str = typer.Option("explainer", "--format", "-f", help="Format: explainer, brief"),
    style: str = typer.Option(
        "auto_select", "--style", "-s",
        help="Visual style: auto_select, classic, whiteboard, kawaii, anime, watercolor, retro_print, heritage, paper_craft",
    ),
    language: str = typer.Option("en", "--language", help="BCP-47 language code"),
    focus: str = typer.Option("", "--focus", help="Optional focus topic"),
    source_ids: Optional[str] = typer.Option(None, "--source-ids", help="Comma-separated source IDs"),
    confirm: bool = typer.Option(False, "--confirm", "-y", help="Skip confirmation"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """Create a video overview from notebook sources."""
    if not confirm:
        typer.confirm("Create video overview?", abort=True)
    
    try:
        notebook_id = get_alias_manager().resolve(notebook_id)

        # Convert string parameters to integer codes
        try:
            format_code = constants.VIDEO_FORMATS.get_code(format)
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)
        try:
            style_code = constants.VIDEO_STYLES.get_code(style)
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task("Creating video...", total=None)
            with get_client(profile) as client:
                result = client.create_video_overview(
                    notebook_id,
                    format_code=format_code,
                    visual_style_code=style_code,
                    language=language,
                    focus_prompt=focus,
                    source_ids=parse_source_ids(source_ids),
                )
        
        console.print(f"[green]✓[/green] Video generation started")
        if result:
            console.print(f"  Artifact ID: {result.get('artifact_id', 'unknown')}")
        console.print(f"\n[dim]Run 'nlm studio status {notebook_id}' to check progress.[/dim]")
    except NLMError as e:
        console.print(f"[red]Error:[/red] {e.message}")
        if e.hint:
            console.print(f"\n[dim]Hint: {e.hint}[/dim]")
        raise typer.Exit(1)


# ========== Data Table ==========

@data_table_app.command("create")
def create_data_table(
    notebook_id: str = typer.Argument(..., help="Notebook ID"),
    description: str = typer.Argument(..., help="Description of the data table to create"),
    language: str = typer.Option("en", "--language", help="BCP-47 language code"),
    source_ids: Optional[str] = typer.Option(None, "--source-ids", "-s", help="Comma-separated source IDs"),
    confirm: bool = typer.Option(False, "--confirm", "-y", help="Skip confirmation"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """Create a data table from notebook sources."""
    if not confirm:
        typer.confirm("Create data table?", abort=True)
    
    try:
        notebook_id = get_alias_manager().resolve(notebook_id)
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task("Creating data table...", total=None)
            with get_client(profile) as client:
                result = client.create_data_table(
                    notebook_id,
                    description=description,
                    language=language,
                    source_ids=parse_source_ids(source_ids),
                )
        
        console.print(f"[green]✓[/green] Data table generation started")
        if result:
            console.print(f"  Artifact ID: {result.get('artifact_id', 'unknown')}")
        console.print(f"\n[dim]Run 'nlm studio status {notebook_id}' to check progress.[/dim]")
    except NLMError as e:
        console.print(f"[red]Error:[/red] {e.message}")
        if e.hint:
            console.print(f"\n[dim]Hint: {e.hint}[/dim]")
        raise typer.Exit(1)
