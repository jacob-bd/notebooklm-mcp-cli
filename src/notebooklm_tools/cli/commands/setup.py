"""MCP server setup commands for AI tool clients.

Configures the notebooklm-mcp server in various AI tool config files,
so the tools can use NotebookLM via MCP protocol.

This is different from `nlm skill` which installs skill/reference docs.
`nlm setup` configures the actual MCP server transport.
"""

import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

console = Console()
app = typer.Typer(
    name="setup",
    help="Configure NotebookLM MCP server for AI tools",
    no_args_is_help=True,
)

# MCP server command - the binary that clients will execute
MCP_SERVER_CMD = "notebooklm-mcp"


def _find_mcp_server_path() -> Optional[str]:
    """Find the full path to the notebooklm-mcp binary."""
    return shutil.which(MCP_SERVER_CMD)


def _read_json_config(path: Path) -> dict:
    """Read a JSON config file, returning empty dict if missing or invalid."""
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def _write_json_config(path: Path, config: dict) -> None:
    """Write a JSON config file, creating parent dirs as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, indent=2) + "\n")


def _is_configured(config: dict, key: str = "notebooklm-mcp") -> bool:
    """Check if notebooklm-mcp is already in an mcpServers config."""
    servers = config.get("mcpServers", {})
    return key in servers or "notebooklm" in servers


def _add_mcp_server(config: dict, key: str = "notebooklm-mcp", extra: Optional[dict] = None) -> dict:
    """Add notebooklm-mcp to an mcpServers config dict."""
    config.setdefault("mcpServers", {})
    entry = {"command": MCP_SERVER_CMD, "args": []}
    if extra:
        entry.update(extra)
    config["mcpServers"][key] = entry
    return config


# =============================================================================
# Client-specific config paths
# =============================================================================

def _claude_desktop_config_path() -> Path:
    """Get Claude Desktop config path (platform-specific)."""
    system = platform.system()
    if system == "Darwin":
        return Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    elif system == "Windows":
        appdata = Path(os.environ.get("APPDATA", ""))
        return appdata / "Claude" / "claude_desktop_config.json"
    else:  # Linux
        return Path.home() / ".config" / "claude" / "claude_desktop_config.json"


def _gemini_config_path() -> Path:
    """Get Gemini CLI config path."""
    return Path.home() / ".gemini" / "settings.json"


def _cursor_config_path(level: str = "user") -> Path:
    """Get Cursor MCP config path."""
    if level == "project":
        return Path(".cursor") / "mcp.json"
    # User-level
    system = platform.system()
    if system == "Darwin":
        return Path.home() / ".cursor" / "mcp.json"
    elif system == "Windows":
        appdata = Path(os.environ.get("APPDATA", ""))
        return appdata / "Cursor" / "User" / "mcp.json"
    else:
        return Path.home() / ".config" / "cursor" / "mcp.json"


def _windsurf_config_path() -> Path:
    """Get Windsurf MCP config path."""
    system = platform.system()
    if system == "Darwin":
        return Path.home() / ".codeium" / "windsurf" / "mcp_config.json"
    elif system == "Windows":
        appdata = Path(os.environ.get("APPDATA", ""))
        return appdata / "Codeium" / "windsurf" / "mcp_config.json"
    else:
        return Path.home() / ".config" / "codeium" / "windsurf" / "mcp_config.json"


# =============================================================================
# Client definitions
# =============================================================================

import os

CLIENT_REGISTRY = {
    "claude-code": {
        "name": "Claude Code",
        "description": "Anthropic CLI (claude command)",
        "has_auto_setup": True,
    },
    "claude-desktop": {
        "name": "Claude Desktop",
        "description": "Claude desktop application",
        "has_auto_setup": True,
    },
    "gemini": {
        "name": "Gemini CLI",
        "description": "Google Gemini CLI",
        "has_auto_setup": True,
    },
    "cursor": {
        "name": "Cursor",
        "description": "Cursor AI editor",
        "has_auto_setup": True,
    },
    "windsurf": {
        "name": "Windsurf",
        "description": "Codeium Windsurf editor",
        "has_auto_setup": True,
    },
    "codex": {
        "name": "Codex CLI",
        "description": "OpenAI Codex CLI",
        "has_auto_setup": False,
    },
}


def _complete_client(incomplete: str) -> list[str]:
    """Shell completion for client names."""
    return [name for name in CLIENT_REGISTRY if name.startswith(incomplete)]


# =============================================================================
# Setup implementations
# =============================================================================

def _setup_claude_code() -> bool:
    """Add MCP to Claude Code via `claude mcp add`."""
    claude_cmd = shutil.which("claude")
    if not claude_cmd:
        console.print("[yellow]Warning:[/yellow] 'claude' command not found in PATH")
        console.print("  Install Claude Code: https://docs.anthropic.com/en/docs/claude-code")
        console.print()
        console.print("  Manual setup — add to [dim]~/.claude/settings.json[/dim]:")
        console.print('    "mcpServers": { "notebooklm-mcp": { "command": "notebooklm-mcp" } }')
        return False

    try:
        result = subprocess.run(
            [claude_cmd, "mcp", "add", "-s", "user", "notebooklm-mcp", "--", MCP_SERVER_CMD],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            console.print(f"[green]✓[/green] Added to Claude Code (user scope)")
            return True
        elif "already exists" in result.stderr.lower():
            console.print(f"[green]✓[/green] Already configured in Claude Code")
            return True
        else:
            console.print(f"[yellow]Warning:[/yellow] claude mcp add returned: {result.stderr.strip()}")
            return False
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
        console.print(f"[yellow]Warning:[/yellow] Could not run claude command: {e}")
        return False


def _setup_claude_desktop() -> bool:
    """Add MCP to Claude Desktop config file."""
    config_path = _claude_desktop_config_path()
    config = _read_json_config(config_path)

    if _is_configured(config):
        console.print(f"[green]✓[/green] Already configured in Claude Desktop")
        return True

    _add_mcp_server(config)
    _write_json_config(config_path, config)
    console.print(f"[green]✓[/green] Added to Claude Desktop")
    console.print(f"  [dim]{config_path}[/dim]")
    return True


def _setup_gemini() -> bool:
    """Add MCP to Gemini CLI config."""
    config_path = _gemini_config_path()
    config = _read_json_config(config_path)

    if _is_configured(config, "notebooklm"):
        console.print(f"[green]✓[/green] Already configured in Gemini CLI")
        return True

    _add_mcp_server(config, key="notebooklm", extra={"trust": True})
    _write_json_config(config_path, config)
    console.print(f"[green]✓[/green] Added to Gemini CLI")
    console.print(f"  [dim]{config_path}[/dim]")
    return True


def _setup_cursor(level: str = "user") -> bool:
    """Add MCP to Cursor config."""
    config_path = _cursor_config_path(level)
    config = _read_json_config(config_path)

    if _is_configured(config):
        console.print(f"[green]✓[/green] Already configured in Cursor ({level})")
        return True

    _add_mcp_server(config)
    _write_json_config(config_path, config)
    console.print(f"[green]✓[/green] Added to Cursor ({level})")
    console.print(f"  [dim]{config_path}[/dim]")
    return True


def _setup_windsurf() -> bool:
    """Add MCP to Windsurf config."""
    config_path = _windsurf_config_path()
    config = _read_json_config(config_path)

    if _is_configured(config):
        console.print(f"[green]✓[/green] Already configured in Windsurf")
        return True

    _add_mcp_server(config)
    _write_json_config(config_path, config)
    console.print(f"[green]✓[/green] Added to Windsurf")
    console.print(f"  [dim]{config_path}[/dim]")
    return True


# =============================================================================
# Commands
# =============================================================================

@app.command("add")
def setup_add(
    client: str = typer.Argument(
        ...,
        help="AI tool to configure (claude-code, claude-desktop, gemini, cursor, windsurf)",
        shell_complete=_complete_client,
    ),
) -> None:
    """
    Add NotebookLM MCP server to an AI tool.

    Configures the MCP server transport so the AI tool can access
    NotebookLM features (notebooks, sources, audio, research, etc).

    Examples:
        nlm setup add claude-code
        nlm setup add claude-desktop
        nlm setup add gemini
        nlm setup add cursor
        nlm setup add windsurf
    """
    if client not in CLIENT_REGISTRY:
        valid = ", ".join(CLIENT_REGISTRY.keys())
        console.print(f"[red]Error:[/red] Unknown client '{client}'")
        console.print(f"Available clients: {valid}")
        raise typer.Exit(1)

    info = CLIENT_REGISTRY[client]
    console.print(f"\n[bold]{info['name']}[/bold] — Adding NotebookLM MCP\n")

    if not info["has_auto_setup"]:
        console.print(f"[yellow]Note:[/yellow] {info['name']} doesn't use MCP server config.")
        console.print(f"Use [cyan]nlm skill install {client}[/cyan] to install skill files instead.")
        raise typer.Exit(0)

    setup_fn = {
        "claude-code": _setup_claude_code,
        "claude-desktop": _setup_claude_desktop,
        "gemini": _setup_gemini,
        "cursor": _setup_cursor,
        "windsurf": _setup_windsurf,
    }

    success = setup_fn[client]()
    if success:
        console.print(f"\n[dim]Restart {info['name']} to activate the MCP server.[/dim]")


@app.command("remove")
def setup_remove(
    client: str = typer.Argument(
        ...,
        help="AI tool to remove MCP from",
        shell_complete=_complete_client,
    ),
) -> None:
    """
    Remove NotebookLM MCP server from an AI tool.

    Examples:
        nlm setup remove claude-desktop
        nlm setup remove gemini
    """
    if client not in CLIENT_REGISTRY:
        valid = ", ".join(CLIENT_REGISTRY.keys())
        console.print(f"[red]Error:[/red] Unknown client '{client}'")
        console.print(f"Available clients: {valid}")
        raise typer.Exit(1)

    # Client-specific removal
    if client == "claude-code":
        claude_cmd = shutil.which("claude")
        if claude_cmd:
            result = subprocess.run(
                [claude_cmd, "mcp", "remove", "-s", "user", "notebooklm-mcp"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                console.print(f"[green]✓[/green] Removed from Claude Code")
            else:
                console.print(f"[yellow]Note:[/yellow] {result.stderr.strip()}")
        else:
            console.print("[yellow]Warning:[/yellow] 'claude' command not found")
        return

    # JSON config-based clients
    config_paths = {
        "claude-desktop": _claude_desktop_config_path(),
        "gemini": _gemini_config_path(),
        "cursor": _cursor_config_path(),
        "windsurf": _windsurf_config_path(),
    }

    config_path = config_paths.get(client)
    if not config_path or not config_path.exists():
        console.print(f"[dim]No config file found for {client}.[/dim]")
        return

    config = _read_json_config(config_path)
    servers = config.get("mcpServers", {})

    removed = False
    for key in ["notebooklm-mcp", "notebooklm"]:
        if key in servers:
            del servers[key]
            removed = True

    if removed:
        _write_json_config(config_path, config)
        console.print(f"[green]✓[/green] Removed from {CLIENT_REGISTRY[client]['name']}")
    else:
        console.print(f"[dim]NotebookLM MCP was not configured in {CLIENT_REGISTRY[client]['name']}.[/dim]")


@app.command("list")
def setup_list() -> None:
    """
    Show supported AI tools and their MCP configuration status.
    """
    table = Table(title="NotebookLM MCP Server Configuration")
    table.add_column("Client", style="cyan")
    table.add_column("Description")
    table.add_column("MCP Status", justify="center")
    table.add_column("Config Path", style="dim")

    for client_id, info in CLIENT_REGISTRY.items():
        status = "[dim]-[/dim]"
        config_path = ""

        if client_id == "claude-code":
            # Check via claude command
            claude_cmd = shutil.which("claude")
            if claude_cmd:
                try:
                    result = subprocess.run(
                        [claude_cmd, "mcp", "list"],
                        capture_output=True, text=True, timeout=5,
                    )
                    if "notebooklm" in result.stdout.lower():
                        status = "[green]✓[/green]"
                except (subprocess.TimeoutExpired, OSError):
                    status = "[dim]?[/dim]"
                config_path = "claude mcp list"
            else:
                config_path = "not installed"

        elif client_id == "claude-desktop":
            path = _claude_desktop_config_path()
            config = _read_json_config(path)
            if _is_configured(config):
                status = "[green]✓[/green]"
            config_path = str(path).replace(str(Path.home()), "~")

        elif client_id == "gemini":
            path = _gemini_config_path()
            config = _read_json_config(path)
            if _is_configured(config, "notebooklm"):
                status = "[green]✓[/green]"
            config_path = str(path).replace(str(Path.home()), "~")

        elif client_id == "cursor":
            path = _cursor_config_path()
            config = _read_json_config(path)
            if _is_configured(config):
                status = "[green]✓[/green]"
            config_path = str(path).replace(str(Path.home()), "~")

        elif client_id == "windsurf":
            path = _windsurf_config_path()
            config = _read_json_config(path)
            if _is_configured(config):
                status = "[green]✓[/green]"
            config_path = str(path).replace(str(Path.home()), "~")

        elif client_id == "codex":
            config_path = "uses nlm skill install codex"

        table.add_row(info["name"], info["description"], status, config_path)

    console.print(table)
    console.print("\n[dim]Add MCP server:  nlm setup add <client>[/dim]")
    console.print("[dim]Install skills:  nlm skill install <tool>[/dim]")
