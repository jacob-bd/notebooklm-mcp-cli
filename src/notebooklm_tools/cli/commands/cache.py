"""Cache management CLI commands."""

from typing import Optional
import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(
    help="Manage the API response cache",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

console = Console()


@app.command("list")
def cache_list() -> None:
    """List all cached entries with TTL remaining."""
    from notebooklm_tools.utils.cache import get_cache

    entries = get_cache().list_entries()

    if not entries:
        console.print("[dim]No cached entries found.[/dim]")
        return

    table = Table(title=f"Cache Entries ({len(entries)} total)", show_header=True, header_style="bold cyan")
    table.add_column("Key", style="cyan", no_wrap=True)
    table.add_column("TTL (s)", justify="right")
    table.add_column("Size (bytes)", justify="right")
    table.add_column("Compressed", justify="center")

    for entry in entries:
        ttl = entry.get("ttl_remaining", 0)
        ttl_str = f"[green]{ttl:.0f}[/green]" if ttl > 60 else f"[yellow]{ttl:.0f}[/yellow]"
        table.add_row(
            entry.get("key", ""),
            ttl_str,
            str(entry.get("size_bytes", 0)),
            "✓" if entry.get("compressed") else "",
        )

    console.print(table)


@app.command("clear")
def cache_clear(
    key: Optional[str] = typer.Argument(None, help="Cache key prefix to clear (e.g. 'notebook:abc123'). Leave empty to clear all."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation for clearing all."),
) -> None:
    """Clear cache entries by prefix, or all entries."""
    from notebooklm_tools.utils.cache import get_cache

    cache = get_cache()

    if key:
        cache.invalidate(key)
        console.print(f"[green]✓[/green] Cleared cache entries matching: [cyan]{key}[/cyan]")
    else:
        if not yes:
            typer.confirm("Clear ALL cache entries?", abort=True)
        cache.clear_all()
        console.print("[green]✓[/green] All cache entries cleared.")
