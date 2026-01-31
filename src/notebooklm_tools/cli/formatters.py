"""Output formatting utilities for NLM CLI."""

import json
import sys
from enum import Enum
from typing import Any

from rich.console import Console
from rich.table import Table


class OutputFormat(str, Enum):
    """Output format options."""

    TABLE = "table"
    JSON = "json"
    COMPACT = "compact"


def detect_output_format(
    json_flag: bool = False,
    quiet_flag: bool = False,
    title_flag: bool = False,
    url_flag: bool = False,
) -> OutputFormat:
    """
    Detect the appropriate output format based on flags and TTY.
    
    Args:
        json_flag: User explicitly requested JSON output.
        quiet_flag: User requested quiet/compact output.
        title_flag: User requested title output (for notebooks).
        url_flag: User requested URL output (for sources).
    
    Returns:
        The output format to use.
    """
    if json_flag:
        return OutputFormat.JSON
    if quiet_flag or title_flag or url_flag:
        return OutputFormat.COMPACT
    
    # Auto-detect based on TTY
    if not sys.stdout.isatty():
        return OutputFormat.JSON
    
    return OutputFormat.TABLE


class Formatter:
    """Base class for output formatters."""

    def __init__(self, console: Console | None = None) -> None:
        self.console = console or Console()

    def format_notebooks(
        self,
        notebooks: list[Any],
        full: bool = False,
        title_only: bool = False,
    ) -> None:
        """Format notebook list output."""
        raise NotImplementedError

    def format_sources(
        self,
        sources: list[Any],
        full: bool = False,
        url_only: bool = False,
    ) -> None:
        """Format source list output."""
        raise NotImplementedError

    def format_artifacts(
        self,
        artifacts: list[Any],
        full: bool = False,
    ) -> None:
        """Format studio artifacts output."""
        raise NotImplementedError

    def format_item(self, item: Any, title: str = "") -> None:
        """Format a single item."""
        raise NotImplementedError

    def format_message(self, message: str, style: str = "") -> None:
        """Format a simple message."""
        self.console.print(message, style=style)

    def format_error(self, message: str, hint: str | None = None) -> None:
        """Format an error message."""
        self.console.print(f"[red]Error:[/red] {message}")
        if hint:
            self.console.print(f"\n[dim]Hint: {hint}[/dim]")

    def format_success(self, message: str) -> None:
        """Format a success message."""
        self.console.print(f"[green]✓[/green] {message}")


class TableFormatter(Formatter):
    """Format output as rich tables."""

    def format_notebooks(
        self,
        notebooks: list[Any],
        full: bool = False,
        title_only: bool = False,
    ) -> None:
        if not notebooks:
            self.console.print("[dim]No notebooks found.[/dim]")
            return

        table = Table(show_header=True, header_style="bold")
        table.add_column("ID", style="cyan", min_width=36, no_wrap=True)
        table.add_column("Title", overflow="ellipsis", max_width=50)
        table.add_column("Src", justify="right", width=4)
        table.add_column("Updated", no_wrap=True, width=10)
        
        if full:
            table.add_column("Created", no_wrap=True, width=10)

        for nb in notebooks:
            # Handle both source_count and sources_count for compatibility
            src_count = getattr(nb, 'source_count', None) or getattr(nb, 'sources_count', 0)
            # Handle both modified_at and updated_at - format as short date
            updated = getattr(nb, 'modified_at', None) or getattr(nb, 'updated_at', None)
            if updated:
                if isinstance(updated, str):
                    updated_str = updated[:10]  # Just the date part
                else:
                    updated_str = updated.strftime("%Y-%m-%d")
            else:
                updated_str = "-"
            
            row = [
                str(nb.id),  # Full ID for copy/paste
                nb.title,
                str(src_count),
                updated_str,
            ]
            if full:
                created = getattr(nb, 'created_at', None)
                if created:
                    created_str = created[:10] if isinstance(created, str) else created.strftime("%Y-%m-%d")
                else:
                    created_str = "-"
                row.append(created_str)
            table.add_row(*row)

        self.console.print(table)

    def format_sources(
        self,
        sources: list[Any],
        full: bool = False,
        url_only: bool = False,
    ) -> None:
        if not sources:
            self.console.print("[dim]No sources found.[/dim]")
            return

        table = Table(show_header=True, header_style="bold")
        table.add_column("ID", style="cyan", min_width=36, no_wrap=True)
        table.add_column("Title", max_width=30, overflow="ellipsis")
        table.add_column("Type")
        
        if full:
            table.add_column("URL", overflow="fold", max_width=80)
            table.add_column("Stale", justify="center")

        for src in sources:
            # Handle both dict and object
            if isinstance(src, dict):
                src_id = src.get('id', '')
                src_title = src.get('title', 'Untitled')
                src_type = src.get('source_type_name') or src.get('type', 'unknown')
                src_url = src.get('url', '')
                is_stale = src.get('is_stale', False)
            else:
                src_id = str(src.id)
                src_title = src.title
                src_type = src.type
                src_url = getattr(src, 'url', '') or ''
                is_stale = getattr(src, 'is_stale', False)
            
            row = [
                src_id,
                src_title,
                src_type,
            ]
            if full:
                row.extend([src_url or '-', '⚠️' if is_stale else ''])
            table.add_row(*row)

        self.console.print(table)

    def format_artifacts(
        self,
        artifacts: list[Any],
        full: bool = False,
    ) -> None:
        if not artifacts:
            self.console.print("[dim]No artifacts found.[/dim]")
            return

        table = Table(show_header=True, header_style="bold")
        table.add_column("ID", style="cyan", min_width=36, no_wrap=True)
        table.add_column("Title", max_width=40)
        table.add_column("Type")
        table.add_column("Status")
        
        if full:
            table.add_column("URL")

        for art in artifacts:
            # Handle both dict and object
            if isinstance(art, dict):
                art_id = art.get('artifact_id', art.get('id', ''))
                art_type = art.get('type', 'unknown')
                art_status = art.get('status', 'unknown')
                art_title = art.get('title', '')
                art_url = art.get('url', '')
            else:
                art_id = str(art.id)
                art_type = art.type
                art_status = art.status
                art_title = getattr(art, 'title', '')
                art_url = getattr(art, 'url', '')
            
            # Status with color and Unicode symbol for quick scanning
            status_config = {
                'completed': ('green', '✓'),
                'pending': ('yellow', '●'),
                'in_progress': ('yellow', '●'),
                'failed': ('red', '✗'),
            }
            
            if art_status in status_config:
                style, symbol = status_config[art_status]
                status_display = f'[{style}]{symbol} {art_status}[/{style}]'
            else:
                status_display = art_status
            
            row = [
                art_id,
                art_title or '-',
                art_type,
                status_display,
            ]
            if full:
                row.append(art_url or '-')
            table.add_row(*row)

        self.console.print(table)

    def format_item(self, item: Any, title: str = "") -> None:
        if title:
            self.console.print(f"[bold]{title}[/bold]")
        
        if hasattr(item, "model_dump"):
            data = item.model_dump(exclude_none=True)
        elif hasattr(item, "__dict__"):
            data = {k: v for k, v in item.__dict__.items() if not k.startswith("_")}
        else:
            data = {"value": item}
        
        for key, value in data.items():
            # Special handling for sources list
            if key == "sources" and isinstance(value, list):
                self.console.print(f"  [cyan]{key}:[/cyan]")
                for src in value:
                    if isinstance(src, dict):
                        self.console.print(f"    • {src.get('title', 'Untitled')} [dim]({src.get('id', '')})[/dim]")
                    else:
                        self.console.print(f"    • {src}")
            else:
                self.console.print(f"  [cyan]{key}:[/cyan] {value}")


class JsonFormatter(Formatter):
    """Format output as JSON."""

    def format_notebooks(
        self,
        notebooks: list[Any],
        full: bool = False,
        title_only: bool = False,
    ) -> None:
        data = []
        for nb in notebooks:
            src_count = getattr(nb, 'source_count', None) or getattr(nb, 'sources_count', 0)
            item = {"id": nb.id, "title": nb.title, "source_count": src_count}
            updated = getattr(nb, 'modified_at', None) or getattr(nb, 'updated_at', None)
            if updated:
                item["updated_at"] = updated if isinstance(updated, str) else updated.isoformat()
            created = getattr(nb, 'created_at', None)
            if full and created:
                item["created_at"] = created if isinstance(created, str) else created.isoformat()
            data.append(item)
        print(json.dumps(data, indent=2))

    def format_sources(
        self,
        sources: list[Any],
        full: bool = False,
        url_only: bool = False,
    ) -> None:
        data = []
        for src in sources:
            if isinstance(src, dict):
                item = {
                    'id': src.get('id', ''),
                    'title': src.get('title', ''),
                    'type': src.get('source_type_name') or src.get('type', ''),
                    'url': src.get('url', ''),
                }
                if full:
                    item['is_stale'] = src.get('is_stale', False)
            else:
                item = {
                    'id': src.id,
                    'title': src.title,
                    'type': src.type,
                    'url': getattr(src, 'url', '') or '',
                }
                if full:
                    item['is_stale'] = getattr(src, 'is_stale', False)
            data.append(item)
        print(json.dumps(data, indent=2))

    def format_artifacts(
        self,
        artifacts: list[Any],
        full: bool = False,
    ) -> None:
        data = []
        for art in artifacts:
            if isinstance(art, dict):
                item = {'id': art.get('artifact_id', art.get('id', '')), 'type': art.get('type', ''), 'status': art.get('status', '')}
                if full:
                    item['title'] = art.get('title', '')
                    item['url'] = art.get('url', '')
                    item['custom_instructions'] = art.get('custom_instructions', None)
            else:
                item = {'id': art.id, 'type': art.type, 'status': art.status}
                if full:
                    item['title'] = getattr(art, 'title', '')
                    item['url'] = getattr(art, 'url', '')
                    item['custom_instructions'] = getattr(art, 'custom_instructions', None)
            data.append(item)
        print(json.dumps(data, indent=2))

    def format_item(self, item: Any, title: str = "") -> None:
        if hasattr(item, "model_dump"):
            data = item.model_dump(exclude_none=True)
        elif hasattr(item, "__dict__"):
            data = {k: v for k, v in item.__dict__.items() if not k.startswith("_")}
        else:
            data = {"value": item}
        print(json.dumps(data, indent=2))


class CompactFormatter(Formatter):
    """Format output as compact text (for piping)."""

    def format_notebooks(
        self,
        notebooks: list[Any],
        full: bool = False,
        title_only: bool = False,
    ) -> None:
        for nb in notebooks:
            if title_only:
                print(f"{nb.id}: {nb.title}")
            else:
                print(nb.id)

    def format_sources(
        self,
        sources: list[Any],
        full: bool = False,
        url_only: bool = False,
    ) -> None:
        for src in sources:
            if isinstance(src, dict):
                src_id = src.get('id', '')
                src_url = src.get('url', '')
            else:
                src_id = str(src.id)
                src_url = getattr(src, 'url', '') or ''
            
            if url_only:
                if src_url:
                    print(f"{src_id}: {src_url}")
            else:
                print(src_id)

    def format_artifacts(
        self,
        artifacts: list[Any],
        full: bool = False,
    ) -> None:
        for art in artifacts:
            if isinstance(art, dict):
                print(art.get('artifact_id', art.get('id', '')))
            else:
                print(art.id)

    def format_item(self, item: Any, title: str = "") -> None:
        if hasattr(item, "id"):
            print(item.id)
        else:
            print(str(item))


def get_formatter(format: OutputFormat, console: Console | None = None) -> Formatter:
    """Get the appropriate formatter for the output format."""
    formatters = {
        OutputFormat.TABLE: TableFormatter,
        OutputFormat.JSON: JsonFormatter,
        OutputFormat.COMPACT: CompactFormatter,
    }
    return formatters[format](console)
