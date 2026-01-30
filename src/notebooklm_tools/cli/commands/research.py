"""Research CLI commands."""

from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from notebooklm_tools.core.alias import get_alias_manager
from notebooklm_tools.core.exceptions import NLMError
from notebooklm_tools.cli.utils import get_client

console = Console()
app = typer.Typer(
    help="Research and discover sources",
    rich_markup_mode="rich",
    no_args_is_help=True,
)


@app.command("start")
def start_research(
    query: str = typer.Argument(..., help="What to search for"),
    source: str = typer.Option(
        "web", "--source", "-s",
        help="Where to search: web or drive",
    ),
    mode: str = typer.Option(
        "fast", "--mode", "-m",
        help="Research mode: fast (~30s, ~10 sources) or deep (~5min, ~40 sources, web only)",
    ),
    notebook_id: Optional[str] = typer.Option(
        None, "--notebook-id", "-n",
        help="Add to existing notebook",
    ),
    title: Optional[str] = typer.Option(
        None, "--title", "-t",
        help="Title for new notebook",
    ),
    force: bool = typer.Option(
        False, "--force", "-f",
        help="Start new research even if one is already pending",
    ),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """
    Start a research task to find new sources.
    
    This searches the web or Google Drive to discover relevant sources
    for your research topic. Use 'nlm research status' to check progress
    and 'nlm research import' to add discovered sources to your notebook.
    """
    # Validate source
    if source not in ["web", "drive"]:
        console.print("[red]Error:[/red] Source must be 'web' or 'drive'")
        raise typer.Exit(1)
    
    # Validate mode
    if mode not in ["fast", "deep"]:
        console.print("[red]Error:[/red] Mode must be 'fast' or 'deep'")
        raise typer.Exit(1)
    
    # Validate deep mode restriction
    if mode == "deep" and source != "web":
        console.print("[red]Error:[/red] Deep research mode is only available for web sources")
        console.print("[dim]Use --mode fast for Drive search, or --source web for deep research.[/dim]")
        raise typer.Exit(1)
    
    try:
        # notebook_id is required for research
        if not notebook_id:
            console.print("[red]Error:[/red] --notebook-id is required for research")
            raise typer.Exit(1)
            
        notebook_id = get_alias_manager().resolve(notebook_id)
        
        with get_client(profile) as client:
            # Check for existing research before starting new one
            if not force:
                existing = client.poll_research(notebook_id)
                if existing and existing.get("status") == "in_progress":
                    console.print("[yellow]Warning:[/yellow] Research already in progress for this notebook.")
                    console.print(f"  Task ID: {existing.get('task_id', 'unknown')}")
                    console.print(f"  Sources found so far: {existing.get('source_count', 0)}")
                    console.print("\n[dim]Use --force to start a new research anyway (will overwrite pending results).[/dim]")
                    console.print("[dim]Or run 'nlm research status' to check progress / 'nlm research import' to save results.[/dim]")
                    raise typer.Exit(1)
                elif existing and existing.get("status") == "completed" and existing.get("source_count", 0) > 0:
                    console.print("[yellow]Warning:[/yellow] Previous research completed with sources not yet imported.")
                    console.print(f"  Task ID: {existing.get('task_id', 'unknown')}")
                    console.print(f"  Sources available: {existing.get('source_count', 0)}")
                    console.print("\n[dim]Use --force to start a new research (will discard existing results).[/dim]")
                    console.print("[dim]Or run 'nlm research import' to save the existing results first.[/dim]")
                    raise typer.Exit(1)
            
            task = client.start_research(
                notebook_id=notebook_id,
                query=query,
                source=source,
                mode=mode,
            )
        
        if not task:
            console.print("[red]Error:[/red] Failed to start research")
            raise typer.Exit(1)
        
        console.print("[green]✓[/green] Research started")
        console.print(f"  Query: {query}")
        console.print(f"  Source: {source}")
        console.print(f"  Mode: {mode}")
        console.print(f"  Notebook ID: {notebook_id}")
        console.print(f"  Task ID: {task.get('task_id', 'unknown')}")
        
        estimate = "~30 seconds" if mode == "fast" else "~5 minutes"
        console.print(f"\n[dim]Estimated time: {estimate}[/dim]")
        console.print(f"[dim]Run 'nlm research status {notebook_id}' to check progress.[/dim]")
    except NLMError as e:
        console.print(f"[red]Error:[/red] {e.message}")
        if e.hint:
            console.print(f"\n[dim]Hint: {e.hint}[/dim]")
        raise typer.Exit(1)


@app.command("status")
def research_status(
    notebook_id: str = typer.Argument(..., help="Notebook ID"),
    task_id: Optional[str] = typer.Option(None, "--task-id", "-t", help="Specific task ID to check"),
    compact: bool = typer.Option(
        True, "--compact/--full",
        help="Show compact or full details",
    ),
    poll_interval: int = typer.Option(
        30, "--poll-interval",
        help="Seconds between status checks",
    ),
    max_wait: int = typer.Option(
        300, "--max-wait",
        help="Maximum seconds to wait (0 for single check)",
    ),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """
    Check research task progress.
    
    By default, polls until the task completes or times out.
    Use --max-wait 0 for a single status check.
    """
    try:
        notebook_id = get_alias_manager().resolve(notebook_id)
        if task_id:
            task_id = get_alias_manager().resolve(task_id)

        if max_wait > 0:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                progress.add_task("Waiting for research to complete...", total=None)
                
                # Simple polling loop
                import time
                elapsed = 0
                with get_client(profile) as client:
                    while elapsed < max_wait:
                        task = client.poll_research(notebook_id, target_task_id=task_id)
                        if task and task.get('status') == 'completed':
                            break
                        time.sleep(poll_interval)
                        elapsed += poll_interval
        else:
            with get_client(profile) as client:
                task = client.poll_research(notebook_id, target_task_id=task_id)
        
        # Handle None task (no research found)
        if task is None:
            console.print(f"\n[bold]Research Status:[/bold]")
            console.print(f"  Status: [dim]no research found[/dim]")
            if task_id:
                console.print(f"  Task ID: [cyan]{task_id}[/cyan] [dim](not found)[/dim]")
            console.print(f"\n[dim]Start a research task with 'nlm research start'.[/dim]")
            raise typer.Exit(0)
        
        # Handle dict response from client
        if isinstance(task, dict):
            status = task.get('status', 'unknown')
            sources_found = task.get('sources_found', task.get('source_count', 0))
            report = task.get('report', '')
            sources = task.get('sources', [])
            all_tasks = task.get('tasks', [])
        else:
            status = getattr(task, 'status', 'unknown')
            sources_found = getattr(task, 'sources_found', 0)
            report = getattr(task, 'report', '')
            sources = getattr(task, 'sources', [])
            all_tasks = []
        
        status_style = {
            "completed": "green",
            "pending": "yellow",
            "running": "yellow",
            "in_progress": "yellow",
            "no_research": "dim",
            "failed": "red",
        }.get(status, "")
        
        console.print(f"\n[bold]Research Status:[/bold]")
        
        # Display all tasks if multiple exist
        if len(all_tasks) > 1:
            console.print(f"  Tasks found: {len(all_tasks)}")
            console.print(f"  Overall status: [{status_style}]{status}[/{status_style}]" if status_style else f"  Overall status: {status}")
            console.print()
            for i, t in enumerate(all_tasks):
                t_status = t.get("status", "unknown")
                t_style = {"completed": "green", "in_progress": "yellow"}.get(t_status, "")
                task_id_str = t.get('task_id', 'unknown')
                console.print(f"  [{i+1}] Task ID: [cyan]{task_id_str}[/cyan]")
                console.print(f"      Status: [{t_style}]{t_status}[/{t_style}]" if t_style else f"      Status: {t_status}")
                console.print(f"      Sources: {t.get('source_count', 0)}")
        else:
            # Show task ID for single task too
            task_id_val = task.get('task_id', '')
            if status_style:
                console.print(f"  Status: [{status_style}]{status}[/{status_style}]")
            if task_id_val:
                console.print(f"  Task ID: [cyan]{task_id_val}[/cyan]")
            else:
                console.print(f"  Status: {status}")
                if task_id_val:
                    console.print(f"  Task ID: [cyan]{task_id_val}[/cyan]")
            console.print(f"  Sources found: {sources_found}")
        
        if report and not compact:
            console.print(f"\n[bold]Report:[/bold]")
            console.print(report)
        
        if sources and not compact:
            console.print(f"\n[bold]Discovered Sources:[/bold]")
            for i, src in enumerate(sources):
                if isinstance(src, dict):
                    title = src.get("title", "Untitled")
                    url = src.get("url", "")
                else:
                    title = getattr(src, 'title', 'Untitled')
                    url = getattr(src, 'url', '')
                console.print(f"  [{i}] {title}")
                if url:
                    console.print(f"      [dim]{url}[/dim]")
        
        if status == "completed":
            console.print(f"\n[dim]Run 'nlm research import {notebook_id} <task-id>' to import sources.[/dim]")
    except NLMError as e:
        console.print(f"[red]Error:[/red] {e.message}")
        if e.hint:
            console.print(f"\n[dim]Hint: {e.hint}[/dim]")
        raise typer.Exit(1)


@app.command("import")
def import_research(
    notebook_id: str = typer.Argument(..., help="Notebook ID"),
    task_id: Optional[str] = typer.Argument(None, help="Research task ID (auto-detects if not provided)"),
    indices: Optional[str] = typer.Option(
        None, "--indices", "-i",
        help="Comma-separated indices of sources to import (default: all)",
    ),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """
    Import discovered sources from a completed research task.
    
    If TASK_ID is not provided, automatically imports from the first
    available completed or in-progress research task.
    """
    try:
        source_indices = None
        if indices:
            source_indices = [int(i.strip()) for i in indices.split(",")]
        
        notebook_id = get_alias_manager().resolve(notebook_id)
        
        with get_client(profile) as client:
            # Auto-detect task ID if not provided
            if not task_id:
                research = client.poll_research(notebook_id)
                if not research or research.get("status") == "no_research":
                    console.print("[red]Error:[/red] No research tasks found for this notebook.")
                    console.print("[dim]Start a research task first with 'nlm research start'.[/dim]")
                    raise typer.Exit(1)
                
                # Get task ID from first task
                task_id = research.get("task_id")
                if not task_id:
                    tasks = research.get("tasks", [])
                    if tasks:
                        task_id = tasks[0].get("task_id")
                
                if not task_id:
                    console.print("[red]Error:[/red] Could not determine task ID.")
                    raise typer.Exit(1)
                
                console.print(f"[dim]Using task: {task_id}[/dim]")
            else:
                task_id = get_alias_manager().resolve(task_id)
            
            # Get sources from the latest research poll
            research_result = client.poll_research(notebook_id, target_task_id=task_id)
            if not research_result or 'sources' not in research_result:
                console.print("[red]Error:[/red] No research sources found.")
                raise typer.Exit(1)
            
            # Filter sources by indices if provided
            all_sources = research_result.get('sources', [])
            if source_indices:
                sources_to_import = [all_sources[i] for i in source_indices if i < len(all_sources)]
            else:
                sources_to_import = all_sources
            
            sources = client.import_research_sources(notebook_id, task_id, sources_to_import)
        
        console.print(f"[green]✓[/green] Imported {len(sources) if sources else 0} source(s)")
        if sources:
            for src in sources:
                if isinstance(src, dict):
                    console.print(f"  • {src.get('title', 'Unknown')}")
                else:
                    console.print(f"  • {getattr(src, 'title', 'Unknown')}")
    except ValueError as e:
        console.print(f"[red]Error:[/red] Invalid indices. Use comma-separated numbers like: 0,2,5")
        raise typer.Exit(1)
    except NLMError as e:
        console.print(f"[red]Error:[/red] {e.message}")
        if e.hint:
            console.print(f"\n[dim]Hint: {e.hint}[/dim]")
        raise typer.Exit(1)
