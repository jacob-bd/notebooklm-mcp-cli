"""Verb-first CLI commands for NotebookLM Tools.

This module provides alternative command structure:
- nlm create notebook "Title"  (vs nlm notebook create "Title")
- nlm list notebooks           (vs nlm notebook list)
- nlm delete notebook <id>     (vs nlm notebook delete <id>)

Both command structures coexist for user flexibility.
"""

from typing import Optional

import typer

# Import existing command implementations
from notebooklm_tools.cli.commands.notebook import (
    create_notebook,
    list_notebooks,
    get_notebook,
    describe_notebook,
    rename_notebook,
    delete_notebook,
    query_notebook,
)
from notebooklm_tools.cli.commands.source import (
    list_sources,
    add_source,
    get_source,
    describe_source,
    get_source_content,
    delete_source,
    list_stale_sources,
    sync_sources,
)
from notebooklm_tools.cli.commands.studio import (
    studio_status,
    studio_delete,
    create_audio,
    create_video,
    create_report,
    create_infographic,
    create_slides,
    create_quiz,
    create_flashcards,
    create_data_table,
    create_mindmap,
)
from notebooklm_tools.cli.commands.research import (
    start_research,
    research_status,
    import_research,
)
from notebooklm_tools.cli.commands.chat import (
    configure_chat,
)
from notebooklm_tools.cli.commands.download import (
    download_audio,
    download_video,
    download_report,
    download_mind_map,
    download_slide_deck,
    download_infographic,
    download_data_table,
)
from notebooklm_tools.cli.commands.alias import (
    set_alias,
    get_alias,
    list_aliases,
    delete_alias,
)
from notebooklm_tools.cli.commands.config import (
    show_config,
    get_config_value,
    set_config_value,
)
from notebooklm_tools.cli.commands.skill import (
    install as skill_install,
    uninstall as skill_uninstall,
    list_tools as skill_list,
    show as skill_show,
)

# =============================================================================
# CREATE verb
# =============================================================================

create_app = typer.Typer(help="Create resources (notebooks, audio, video, etc)")


@create_app.command("notebook")
def create_notebook_verb(
    title: str = typer.Argument(..., help="Notebook title"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """Create a new notebook."""
    create_notebook(title=title, profile=profile)


@create_app.command("audio")
def create_audio_verb(
    notebook: str = typer.Argument(..., help="Notebook ID or alias"),
    format_opt: Optional[str] = typer.Option(None, "--format", "-f", help="Audio format (deep_dive/brief/critique/debate)"),
    length: Optional[str] = typer.Option(None, "--length", "-l", help="Audio length (short/default/long)"),
    language: Optional[str] = typer.Option(None, "--language", help="BCP-47 language code (en, es, fr, de, ja)"),
    focus: Optional[str] = typer.Option(None, "--focus", help="Optional focus topic"),
    source_ids: Optional[str] = typer.Option(None, "--source-ids", "-s", help="Comma-separated source IDs"),
    confirm: bool = typer.Option(False, "--confirm", "-y", help="Skip confirmation prompt"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """Create an audio overview."""
    create_audio(
        notebook_id=notebook,
        format=format_opt or "deep_dive",
        length=length or "default",
        language=language or "en",
        focus=focus,
        source_ids=source_ids,
        confirm=confirm,
        profile=profile
    )


@create_app.command("video")
def create_video_verb(
    notebook: str = typer.Argument(..., help="Notebook ID or alias"),
    format_opt: Optional[str] = typer.Option(None, "--format", "-f", help="Format: explainer, brief"),
    style: Optional[str] = typer.Option(None, "--style", "-s", help="Visual style: auto_select, classic, whiteboard, kawaii, anime, watercolor, retro_print, heritage, paper_craft"),
    language: Optional[str] = typer.Option(None, "--language", help="BCP-47 language code"),
    focus: Optional[str] = typer.Option(None, "--focus", help="Optional focus topic"),
    source_ids: Optional[str] = typer.Option(None, "--source-ids", help="Comma-separated source IDs"),
    confirm: bool = typer.Option(False, "--confirm", "-y", help="Skip confirmation prompt"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """Create a video overview."""
    create_video(
        notebook_id=notebook,
        format=format_opt or "explainer",
        style=style or "auto_select",
        language=language or "en",
        focus=focus or "",
        source_ids=source_ids,
        confirm=confirm,
        profile=profile
    )


@create_app.command("report")
def create_report_verb(
    notebook: str = typer.Argument(..., help="Notebook ID or alias"),
    format_opt: Optional[str] = typer.Option(None, "--format", "-f", help="Format: 'Briefing Doc', 'Study Guide', 'Blog Post', 'Create Your Own'"),
    prompt: Optional[str] = typer.Option(None, "--prompt", help="Custom prompt (required for 'Create Your Own')"),
    language: Optional[str] = typer.Option(None, "--language", help="BCP-47 language code"),
    source_ids: Optional[str] = typer.Option(None, "--source-ids", "-s", help="Comma-separated source IDs"),
    confirm: bool = typer.Option(False, "--confirm", "-y", help="Skip confirmation prompt"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """Create a report."""
    create_report(
        notebook_id=notebook,
        format=format_opt or "Briefing Doc",
        prompt=prompt or "",
        language=language or "en",
        source_ids=source_ids,
        confirm=confirm,
        profile=profile
    )


@create_app.command("infographic")
def create_infographic_verb(
    notebook: str = typer.Argument(..., help="Notebook ID or alias"),
    orientation: Optional[str] = typer.Option(None, "--orientation", "-o", help="Orientation: landscape, portrait, square"),
    detail: Optional[str] = typer.Option(None, "--detail", "-d", help="Detail level: concise, standard, detailed"),
    language: Optional[str] = typer.Option(None, "--language", help="BCP-47 language code"),
    focus: Optional[str] = typer.Option(None, "--focus", help="Optional focus topic"),
    source_ids: Optional[str] = typer.Option(None, "--source-ids", "-s", help="Comma-separated source IDs"),
    confirm: bool = typer.Option(False, "--confirm", "-y", help="Skip confirmation prompt"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """Create an infographic."""
    create_infographic(
        notebook_id=notebook,
        orientation=orientation or "landscape",
        detail=detail or "standard",
        language=language or "en",
        focus=focus or "",
        source_ids=source_ids,
        confirm=confirm,
        profile=profile
    )


@create_app.command("slides")
def create_slides_verb(
    notebook: str = typer.Argument(..., help="Notebook ID or alias"),
    format_opt: Optional[str] = typer.Option(None, "--format", "-f", help="Format: detailed, presenter"),
    length: Optional[str] = typer.Option(None, "--length", "-l", help="Length: short, default"),
    language: Optional[str] = typer.Option(None, "--language", help="BCP-47 language code"),
    focus: Optional[str] = typer.Option(None, "--focus", help="Optional focus topic"),
    source_ids: Optional[str] = typer.Option(None, "--source-ids", "-s", help="Comma-separated source IDs"),
    confirm: bool = typer.Option(False, "--confirm", "-y", help="Skip confirmation prompt"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """Create a slide deck."""
    create_slides(
        notebook_id=notebook,
        format=format_opt or "detailed",
        length=length or "default",
        language=language or "en",
        focus=focus or "",
        source_ids=source_ids,
        confirm=confirm,
        profile=profile
    )


@create_app.command("quiz")
def create_quiz_verb(
    notebook: str = typer.Argument(..., help="Notebook ID or alias"),
    count: Optional[int] = typer.Option(None, "--count", "-c", help="Number of questions"),
    difficulty: Optional[int] = typer.Option(None, "--difficulty", "-d", help="Difficulty 1-5 (1=easy, 5=hard)"),
    source_ids: Optional[str] = typer.Option(None, "--source-ids", "-s", help="Comma-separated source IDs"),
    confirm: bool = typer.Option(False, "--confirm", "-y", help="Skip confirmation prompt"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """Create a quiz."""
    create_quiz(
        notebook_id=notebook,
        count=count or 2,
        difficulty=difficulty or 2,
        source_ids=source_ids,
        confirm=confirm,
        profile=profile
    )


@create_app.command("flashcards")
def create_flashcards_verb(
    notebook: str = typer.Argument(..., help="Notebook ID or alias"),
    difficulty: Optional[str] = typer.Option(None, "--difficulty", "-d", help="Difficulty: easy, medium, hard"),
    source_ids: Optional[str] = typer.Option(None, "--source-ids", "-s", help="Comma-separated source IDs"),
    confirm: bool = typer.Option(False, "--confirm", "-y", help="Skip confirmation prompt"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """Create flashcards."""
    create_flashcards(
        notebook_id=notebook,
        difficulty=difficulty or "medium",
        source_ids=source_ids,
        confirm=confirm,
        profile=profile
    )


@create_app.command("data-table")
def create_data_table_verb(
    notebook: str = typer.Argument(..., help="Notebook ID or alias"),
    description: str = typer.Argument(..., help="Description of the data table to create"),
    language: Optional[str] = typer.Option(None, "--language", help="BCP-47 language code"),
    source_ids: Optional[str] = typer.Option(None, "--source-ids", "-s", help="Comma-separated source IDs"),
    confirm: bool = typer.Option(False, "--confirm", "-y", help="Skip confirmation prompt"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """Create a data table."""
    create_data_table(
        notebook_id=notebook,
        description=description,
        language=language or "en",
        source_ids=source_ids,
        confirm=confirm,
        profile=profile
    )


@create_app.command("mindmap")
def create_mindmap_verb(
    notebook: str = typer.Argument(..., help="Notebook ID or alias"),
    title: Optional[str] = typer.Option(None, "--title", "-t", help="Mind map title"),
    source_ids: Optional[str] = typer.Option(None, "--source-ids", "-s", help="Comma-separated source IDs"),
    confirm: bool = typer.Option(False, "--confirm", "-y", help="Skip confirmation prompt"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """Create a mind map."""
    create_mindmap(
        notebook_id=notebook,
        title=title or "Mind Map",
        source_ids=source_ids,
        confirm=confirm,
        profile=profile
    )


# =============================================================================
# LIST verb
# =============================================================================

list_app = typer.Typer(help="List resources (notebooks, sources, artifacts)")


@list_app.command("notebooks")
def list_notebooks_verb(
    full: bool = typer.Option(False, "--full", "-a", help="Show all columns"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Output IDs only"),
    title: bool = typer.Option(False, "--title", "-t", help="Show ID: Title format"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """List all notebooks."""
    list_notebooks(full=full, json_output=json_output, quiet=quiet, title=title, profile=profile)


@list_app.command("sources")
def list_sources_verb(
    notebook: str = typer.Argument(..., help="Notebook ID or alias"),
    full: bool = typer.Option(False, "--full", "-a", help="Show all columns"),
    drive: bool = typer.Option(False, "--drive", "-d", help="Show Drive sources with freshness status"),
    skip_freshness: bool = typer.Option(False, "--skip-freshness", "-S", help="Skip freshness checks (faster, use with --drive)"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Output IDs only"),
    url: bool = typer.Option(False, "--url", "-u", help="Output as ID: URL"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """List sources in a notebook."""
    list_sources(notebook_id=notebook, full=full, drive=drive, skip_freshness=skip_freshness, json_output=json_output, quiet=quiet, url=url, profile=profile)


@list_app.command("artifacts")
def list_artifacts_verb(
    notebook: str = typer.Argument(..., help="Notebook ID or alias"),
    full: bool = typer.Option(False, "--full", "-a", help="Show all details"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """List all studio artifacts."""
    studio_status(notebook_id=notebook, full=full, json_output=json_output, profile=profile)


@list_app.command("aliases")
def list_aliases_verb() -> None:
    """List all aliases."""
    list_aliases()


@list_app.command("stale-sources")
def list_stale_sources_verb(
    notebook: str = typer.Argument(..., help="Notebook ID or alias"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """List Drive sources that need syncing."""
    list_stale_sources(notebook_id=notebook, json_output=json_output, profile=profile)


@list_app.command("skills")
def list_skills_verb() -> None:
    """List available skills and installation status."""
    skill_list()


# =============================================================================
# GET verb
# =============================================================================

get_app = typer.Typer(help="Get details about resources")


@get_app.command("notebook")
def get_notebook_verb(
    notebook: str = typer.Argument(..., help="Notebook ID or alias"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """Get notebook details."""
    get_notebook(notebook_id=notebook, json_output=json_output, profile=profile)


@get_app.command("source")
def get_source_verb(
    source: str = typer.Argument(..., help="Source ID"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """Get source details."""
    get_source(source_id=source, json_output=json_output, profile=profile)


@get_app.command("config")
def get_config_verb(
    key: str = typer.Argument(..., help="Configuration key (e.g. output.format)"),
) -> None:
    """Get configuration value."""
    get_config_value(key=key)


@get_app.command("alias")
def get_alias_verb(
    name: str = typer.Argument(..., help="Alias name"),
) -> None:
    """Get alias value."""
    get_alias(name=name)


# =============================================================================
# DELETE verb
# =============================================================================

delete_app = typer.Typer(help="Delete resources (notebooks, sources, artifacts)")


@delete_app.command("notebook")
def delete_notebook_verb(
    notebook: str = typer.Argument(..., help="Notebook ID or alias"),
    confirm: bool = typer.Option(False, "--confirm", "-y", help="Skip confirmation prompt"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """Delete a notebook permanently."""
    delete_notebook(notebook_id=notebook, confirm=confirm, profile=profile)


@delete_app.command("source")
def delete_source_verb(
    source: str = typer.Argument(..., help="Source ID"),
    confirm: bool = typer.Option(False, "--confirm", "-y", help="Skip confirmation prompt"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """Delete a source from notebook."""
    delete_source(source_id=source, confirm=confirm, profile=profile)


@delete_app.command("artifact")
def delete_artifact_verb(
    notebook: str = typer.Argument(..., help="Notebook ID or alias"),
    artifact: str = typer.Argument(..., help="Artifact ID"),
    confirm: bool = typer.Option(False, "--confirm", "-y", help="Skip confirmation prompt"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """Delete a studio artifact permanently."""
    studio_delete(notebook_id=notebook, artifact_id=artifact, confirm=confirm, profile=profile)


@delete_app.command("alias")
def delete_alias_verb(
    name: str = typer.Argument(..., help="Alias name"),
) -> None:
    """Delete an alias."""
    delete_alias(name=name)


# =============================================================================
# ADD verb (for sources)
# =============================================================================

add_app = typer.Typer(help="Add resources (sources to notebooks)")


@add_app.command("url")
def add_url_verb(
    notebook: str = typer.Argument(..., help="Notebook ID or alias"),
    url_arg: str = typer.Argument(..., help="URL to add"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """Add a URL source to notebook."""
    # Explicitly pass None for unused source types to avoid typer.Option resolution issues
    add_source(notebook, url=url_arg, text=None, drive=None, youtube=None, file=None, profile=profile)


@add_app.command("text")
def add_text_verb(
    notebook: str = typer.Argument(..., help="Notebook ID or alias"),
    text_arg: str = typer.Argument(..., help="Text content to add"),
    title: Optional[str] = typer.Option(None, "--title", help="Source title"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """Add text source to notebook."""
    # Explicitly pass None for unused source types to avoid typer.Option resolution issues
    add_source(notebook, url=None, text=text_arg, drive=None, youtube=None, file=None, title=title or "Pasted Text", profile=profile)


@add_app.command("drive")
def add_drive_verb(
    notebook: str = typer.Argument(..., help="Notebook ID or alias"),
    document_id: str = typer.Argument(..., help="Google Drive document ID"),
    title: Optional[str] = typer.Option(None, "--title", help="Source title"),
    doc_type: str = typer.Option("doc", "--type", help="Drive doc type: doc, slides, sheets, pdf"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """Add a Google Drive source to notebook."""
    # Explicitly pass None for unused source types to avoid typer.Option resolution issues
    add_source(notebook, url=None, text=None, drive=document_id, youtube=None, file=None, title=title or f"Drive Document ({document_id[:8]}...)", doc_type=doc_type, profile=profile)


# =============================================================================
# RENAME verb
# =============================================================================

rename_app = typer.Typer(help="Rename resources")


@rename_app.command("notebook")
def rename_notebook_verb(
    notebook: str = typer.Argument(..., help="Notebook ID or alias"),
    title: str = typer.Argument(..., help="New title"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """Rename a notebook."""
    rename_notebook(notebook_id=notebook, new_title=title, profile=profile)


# =============================================================================
# STATUS verb
# =============================================================================

status_app = typer.Typer(help="Check status of resources")


@status_app.command("artifacts")
def status_artifacts_verb(
    notebook: str = typer.Argument(..., help="Notebook ID or alias"),
    full: bool = typer.Option(False, "--full", "-a", help="Show all details"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """Check status of studio artifacts."""
    studio_status(notebook_id=notebook, full=full, json_output=json_output, profile=profile)


@status_app.command("research")
def status_research_verb(
    notebook: str = typer.Argument(..., help="Notebook ID or alias"),
    task_id: Optional[str] = typer.Option(None, "--task-id", "-t", help="Specific task ID to check"),
    compact: bool = typer.Option(True, "--compact/--full", help="Show compact or full details"),
    poll_interval: int = typer.Option(30, "--poll-interval", help="Seconds between status checks"),
    max_wait: int = typer.Option(300, "--max-wait", help="Maximum seconds to wait (0 for single check)"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """Check status of research task."""
    research_status(
        notebook_id=notebook,
        task_id=task_id,
        compact=compact,
        poll_interval=poll_interval,
        max_wait=max_wait,
        profile=profile
    )


# =============================================================================
# DESCRIBE verb
# =============================================================================

describe_app = typer.Typer(help="Get AI-generated descriptions and summaries")


@describe_app.command("notebook")
def describe_notebook_verb(
    notebook: str = typer.Argument(..., help="Notebook ID or alias"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """Get AI-generated notebook summary with suggested topics."""
    describe_notebook(notebook_id=notebook, profile=profile)


@describe_app.command("source")
def describe_source_verb(
    source: str = typer.Argument(..., help="Source ID"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """Get AI-generated source summary with keywords."""
    describe_source(source_id=source, profile=profile)


# =============================================================================
# QUERY verb (for chatting with notebooks)
# =============================================================================

query_app = typer.Typer(help="Chat with notebook sources")


@query_app.command("notebook")
def query_notebook_verb(
    notebook: str = typer.Argument(..., help="Notebook ID or alias"),
    question: str = typer.Argument(..., help="Question to ask"),
    conversation_id: Optional[str] = typer.Option(None, "--conversation-id", "-c", help="Conversation ID for follow-up questions"),
    source_ids: Optional[str] = typer.Option(None, "--source-ids", "-s", help="Comma-separated source IDs to query (default: all)"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """Chat with notebook sources."""
    query_notebook(
        notebook_id=notebook,
        question=question,
        conversation_id=conversation_id,
        source_ids=source_ids,
        profile=profile
    )


# =============================================================================
# SYNC verb (for Drive sources)
# =============================================================================

sync_app = typer.Typer(help="Sync resources (Drive sources)")


@sync_app.command("sources")
def sync_sources_verb(
    notebook: str = typer.Argument(..., help="Notebook ID or alias"),
    source_ids: Optional[str] = typer.Option(None, "--source-ids", "-s", help="Comma-separated source IDs to sync (default: all stale)"),
    confirm: bool = typer.Option(False, "--confirm", "-y", help="Skip confirmation"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """Sync Drive sources with latest content."""
    sync_sources(
        notebook_id=notebook,
        source_ids=source_ids,
        confirm=confirm,
        profile=profile
    )


# =============================================================================
# CONTENT verb (for getting raw source content)
# =============================================================================

content_app = typer.Typer(help="Get raw content from sources")


@content_app.command("source")
def content_source_verb(
    source: str = typer.Argument(..., help="Source ID"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Write content to file"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """Get raw source content (no AI processing)."""
    get_source_content(source_id=source, output=output, profile=profile)


# =============================================================================
# STALE verb (for listing stale Drive sources)
# =============================================================================

stale_app = typer.Typer(help="List stale resources that need syncing")


@stale_app.command("sources")
def stale_sources_verb(
    notebook: str = typer.Argument(..., help="Notebook ID or alias"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """List Drive sources that need syncing."""
    list_stale_sources(notebook_id=notebook, json_output=json_output, profile=profile)


# =============================================================================
# RESEARCH verb
# =============================================================================

research_app = typer.Typer(help="Research and discover sources")


@research_app.command("start")
def research_start_verb(
    query: str = typer.Argument(..., help="What to search for"),
    source: str = typer.Option("web", "--source", "-s", help="Where to search: web or drive"),
    mode: str = typer.Option("fast", "--mode", "-m", help="Research mode: fast (~30s, ~10 sources) or deep (~5min, ~40 sources, web only)"),
    notebook_id: Optional[str] = typer.Option(None, "--notebook-id", "-n", help="Add to existing notebook"),
    title: Optional[str] = typer.Option(None, "--title", "-t", help="Title for new notebook"),
    force: bool = typer.Option(False, "--force", "-f", help="Start new research even if one is already pending"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """Start a research task to find new sources."""
    start_research(
        query=query,
        source=source,
        mode=mode,
        notebook_id=notebook_id,
        title=title,
        force=force,
        profile=profile
    )


@research_app.command("import")
def research_import_verb(
    notebook: str = typer.Argument(..., help="Notebook ID or alias"),
    task_id: Optional[str] = typer.Argument(None, help="Research task ID (auto-detects if not provided)"),
    indices: Optional[str] = typer.Option(None, "--indices", "-i", help="Comma-separated indices of sources to import (default: all)"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """Import discovered sources into notebook."""
    import_research(
        notebook_id=notebook,
        task_id=task_id,
        indices=indices,
        profile=profile
    )


# =============================================================================
# CONFIGURE verb (for chat settings)
# =============================================================================

configure_app = typer.Typer(help="Configure settings")


@configure_app.command("chat")
def configure_chat_verb(
    notebook: str = typer.Argument(..., help="Notebook ID or alias"),
    goal: Optional[str] = typer.Option(None, "--goal", "-g", help="Chat goal: default, learning_guide, or custom"),
    prompt: Optional[str] = typer.Option(None, "--prompt", help="Custom prompt (required when goal=custom, max 10000 chars)"),
    response_length: Optional[str] = typer.Option(None, "--response-length", "-r", help="Response length: default, longer, or shorter"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """Configure chat settings for a notebook."""
    configure_chat(
        notebook_id=notebook,
        goal=goal or "default",
        prompt=prompt,
        response_length=response_length or "default",
        profile=profile
    )


# =============================================================================
# DOWNLOAD verb
# =============================================================================

download_app = typer.Typer(help="Download studio artifacts")


@download_app.command("audio")
def download_audio_verb(
    notebook: str = typer.Argument(..., help="Notebook ID or alias"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output filename"),
    artifact_id: Optional[str] = typer.Option(None, "--id", help="Specific artifact ID"),
    no_progress: bool = typer.Option(False, "--no-progress", help="Disable download progress bar"),
) -> None:
    """Download audio overview."""
    download_audio(
        notebook_id=notebook,
        output=output,
        artifact_id=artifact_id,
        no_progress=no_progress
    )


@download_app.command("video")
def download_video_verb(
    notebook: str = typer.Argument(..., help="Notebook ID or alias"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output filename"),
    artifact_id: Optional[str] = typer.Option(None, "--id", help="Specific artifact ID"),
    no_progress: bool = typer.Option(False, "--no-progress", help="Disable download progress bar"),
) -> None:
    """Download video overview."""
    download_video(
        notebook_id=notebook,
        output=output,
        artifact_id=artifact_id,
        no_progress=no_progress
    )


@download_app.command("report")
def download_report_verb(
    notebook: str = typer.Argument(..., help="Notebook ID or alias"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output filename"),
    artifact_id: Optional[str] = typer.Option(None, "--id", help="Specific artifact ID"),
) -> None:
    """Download report."""
    download_report(
        notebook_id=notebook,
        output=output,
        artifact_id=artifact_id
    )


@download_app.command("mind-map")
def download_mindmap_verb(
    notebook: str = typer.Argument(..., help="Notebook ID or alias"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output filename"),
    artifact_id: Optional[str] = typer.Option(None, "--id", help="Specific artifact ID (note ID)"),
) -> None:
    """Download mind map."""
    download_mind_map(
        notebook_id=notebook,
        output=output,
        artifact_id=artifact_id
    )


@download_app.command("slides")
def download_slides_verb(
    notebook: str = typer.Argument(..., help="Notebook ID or alias"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output filename"),
    artifact_id: Optional[str] = typer.Option(None, "--id", help="Specific artifact ID"),
    no_progress: bool = typer.Option(False, "--no-progress", help="Disable download progress bar"),
) -> None:
    """Download slide deck."""
    download_slide_deck(
        notebook_id=notebook,
        output=output,
        artifact_id=artifact_id,
        no_progress=no_progress
    )


@download_app.command("infographic")
def download_infographic_verb(
    notebook: str = typer.Argument(..., help="Notebook ID or alias"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output filename"),
    artifact_id: Optional[str] = typer.Option(None, "--id", help="Specific artifact ID"),
    no_progress: bool = typer.Option(False, "--no-progress", help="Disable download progress bar"),
) -> None:
    """Download infographic."""
    download_infographic(
        notebook_id=notebook,
        output=output,
        artifact_id=artifact_id,
        no_progress=no_progress
    )


@download_app.command("data-table")
def download_data_table_verb(
    notebook: str = typer.Argument(..., help="Notebook ID or alias"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output filename"),
    artifact_id: Optional[str] = typer.Option(None, "--id", help="Specific artifact ID"),
) -> None:
    """Download data table."""
    download_data_table(
        notebook_id=notebook,
        output=output,
        artifact_id=artifact_id
    )


# =============================================================================
# SET verb (for aliases and config)
# =============================================================================

set_app = typer.Typer(help="Set values (aliases, config)")


@set_app.command("alias")
def set_alias_verb(
    name: str = typer.Argument(..., help="Alias name (e.g. 'my-notebook')"),
    value: str = typer.Argument(..., help="ID to alias"),
) -> None:
    """Set an alias for an ID."""
    set_alias(name=name, value=value)


@set_app.command("config")
def set_config_verb(
    key: str = typer.Argument(..., help="Configuration key (e.g. output.format)"),
    value: str = typer.Argument(..., help="Configuration value"),
) -> None:
    """Set configuration value."""
    set_config_value(key=key, value=value)


# =============================================================================
# SHOW verb (for displaying info)
# =============================================================================

show_app = typer.Typer(help="Show information")


@show_app.command("config")
def show_config_verb(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Show all configuration."""
    show_config(json_output=json_output)


@show_app.command("aliases")
def show_aliases_verb() -> None:
    """Show all aliases."""
    list_aliases()


@show_app.command("skill")
def show_skill_verb() -> None:
    """Show NotebookLM skill content."""
    skill_show()


# =============================================================================
# INSTALL verb (for skills)
# =============================================================================

install_app = typer.Typer(help="Install resources (skills)")


@install_app.command("skill")
def install_skill_verb(
    tool: str = typer.Argument(..., help="Tool to install skill for (claude-code, opencode, gemini-cli, antigravity, codex, other)"),
    level: str = typer.Option("user", "--level", "-l", help="Install at user level (~/.config) or project level (./)"),
) -> None:
    """Install NotebookLM skill for an AI tool."""
    skill_install(tool=tool, level=level)


# =============================================================================
# UNINSTALL verb (for skills)
# =============================================================================

uninstall_app = typer.Typer(help="Uninstall resources (skills)")


@uninstall_app.command("skill")
def uninstall_skill_verb(
    tool: str = typer.Argument(..., help="Tool to uninstall skill from"),
    level: str = typer.Option("user", "--level", "-l", help="Uninstall from user or project level"),
) -> None:
    """Remove installed NotebookLM skill."""
    skill_uninstall(tool=tool, level=level)

