"""Interactive REPL for notebook chat."""

import re

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from notebooklm_tools.core.alias import get_alias_manager
from notebooklm_tools.core.exceptions import NLMError
from notebooklm_tools.cli.utils import get_client

console = Console()

HELP_TEXT = """
[bold]Available Commands:[/bold]
  /exit, /quit  Exit the chat
  /clear        Start new conversation
  /sources      List notebook sources
  /help         Show this help
"""


def _parse_citations(text: str) -> set[int]:
    """Extract citation numbers from response text.
    
    Handles formats: [1], [1, 2], [11-13], [1, 2, 5-7]
    """
    citations = set()
    
    # Find all bracketed citation groups
    pattern = r'\[(\d+(?:\s*[-,]\s*\d+)*)\]'
    matches = re.findall(pattern, text)
    
    for match in matches:
        # Split by comma first
        parts = match.split(',')
        for part in parts:
            part = part.strip()
            if '-' in part:
                # Handle ranges like "11-13"
                try:
                    start, end = part.split('-')
                    for num in range(int(start.strip()), int(end.strip()) + 1):
                        citations.add(num)
                except ValueError:
                    pass
            else:
                # Single number
                try:
                    citations.add(int(part))
                except ValueError:
                    pass
    
    return citations


def run_chat_repl(notebook_id: str, profile: str | None = None) -> None:
    """Run interactive chat session with a notebook."""
    notebook_id = get_alias_manager().resolve(notebook_id)
    
    try:
        with get_client(profile) as client:
            # Get notebook info for welcome banner
            notebook = client.get_notebook(notebook_id)
            if not notebook:
                console.print("[red]Error:[/red] Notebook not found.")
                raise typer.Exit(1)

            # Handle dict, list, or Notebook object returns
            if isinstance(notebook, dict):
                notebook_title = notebook.get("title", "Notebook")
                sources_list = notebook.get("sources", [])
            elif isinstance(notebook, list):
                notebook_title = f"Notebook {notebook_id[:8]}"
                sources_list = []
            else:
                notebook_title = notebook.title or "Notebook"
                sources_list = notebook.sources or []
            source_count = len(sources_list)
            
            # Welcome banner
            console.print(Panel(
                f"[bold]{notebook_title}[/bold]\n"
                f"[dim]{source_count} source(s) loaded[/dim]\n\n"
                f"Type your question and press Enter.\n"
                f"Use [bold]/help[/bold] for commands, [bold]/exit[/bold] to quit.",
                title="NotebookLM Chat",
                border_style="blue",
            ))
            console.print()
            
            conversation_id: str | None = None
            turn_number = 0
            
            while True:
                try:
                    # Get user input
                    user_input = console.input("[bold cyan]You:[/bold cyan] ").strip()
                    
                    # Handle empty input
                    if not user_input:
                        continue
                    
                    # Handle slash commands
                    if user_input.startswith("/"):
                        cmd = user_input.lower()
                        
                        if cmd in ("/exit", "/quit"):
                            console.print("\n[dim]Goodbye![/dim]")
                            break
                        
                        elif cmd == "/clear":
                            conversation_id = None
                            turn_number = 0
                            console.print("[green]✓[/green] Conversation cleared.\n")
                            continue
                        
                        elif cmd == "/sources":
                            if sources_list:
                                console.print("\n[bold]Sources:[/bold]")
                                for i, src in enumerate(sources_list, 1):
                                    title = src.get("title", "Untitled")
                                    stype = src.get("type", "unknown")
                                    console.print(f"  [{i}] {title} [dim]({stype})[/dim]")
                                console.print()
                            else:
                                console.print("[dim]No sources in this notebook.[/dim]\n")
                            continue
                        
                        elif cmd == "/help":
                            console.print(HELP_TEXT)
                            continue
                        
                        else:
                            console.print(f"[yellow]Unknown command:[/yellow] {user_input}")
                            console.print("[dim]Type /help for available commands.[/dim]\n")
                            continue
                    
                    # Query the notebook
                    turn_number += 1
                    
                    with console.status("[dim]Thinking...[/dim]", spinner="dots"):
                        result = client.query(
                            notebook_id,
                            query_text=user_input,
                            conversation_id=conversation_id,
                        )
                    
                    if result:
                        conversation_id = result.get("conversation_id")
                        answer = result.get("answer", "No response.")
                        
                        # Render response with notebook title as label
                        console.print()
                        console.print(f"[bold green]{notebook_title}:[/bold green]")
                        console.print(Markdown(answer))
                        
                        # Parse and display citation legend
                        cited_nums = _parse_citations(answer)
                        citations_map = result.get("citations", {})
                        
                        if cited_nums and sources_list:
                            # Build UUID -> title lookup
                            uuid_to_title = {
                                src.get("id"): src.get("title", "Untitled")
                                for src in sources_list
                            }
                            
                            # Collect unique sources cited
                            cited_sources: dict[str, list[int]] = {}
                            for num in sorted(cited_nums):
                                source_uuid = citations_map.get(num)
                                if source_uuid:
                                    if source_uuid not in cited_sources:
                                        cited_sources[source_uuid] = []
                                    cited_sources[source_uuid].append(num)
                            
                            if cited_sources:
                                console.print()
                                console.print("[dim]" + "─" * 40 + "[/dim]")
                                console.print("[dim]Sources cited:[/dim]")
                                for uuid, nums in cited_sources.items():
                                    title = uuid_to_title.get(uuid, uuid[:8] + "...")
                                    nums_str = ", ".join(f"[{n}]" for n in nums)
                                    console.print(f"[dim]  {nums_str} {title}[/dim]")
                        
                        console.print()
                    else:
                        console.print("[red]No response from AI.[/red]\n")
                
                except KeyboardInterrupt:
                    console.print("\n\n[dim]Interrupted. Type /exit to quit.[/dim]\n")
                    continue
                
                except NLMError as e:
                    console.print(f"\n[red]Error:[/red] {e.message}")
                    if e.hint:
                        console.print(f"[dim]{e.hint}[/dim]")
                    console.print()
                    continue
    
    except NLMError as e:
        console.print(f"[red]Error:[/red] {e.message}")
        if e.hint:
            console.print(f"[dim]{e.hint}[/dim]")
        raise typer.Exit(1)
    
    except KeyboardInterrupt:
        console.print("\n[dim]Goodbye![/dim]")

