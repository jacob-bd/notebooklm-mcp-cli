"""MCP server setup commands for AI tool clients.

Configures the notebooklm-mcp server in various AI tool config files,
so the tools can use NotebookLM via MCP protocol.

This is different from `nlm skill` which installs skill/reference docs.
`nlm setup` configures the actual MCP server transport.
"""

import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.syntax import Syntax
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


def _claude_desktop_app_support_dir() -> Path:
    """Get the Claude Desktop Application Support directory (platform-specific)."""
    system = platform.system()
    if system == "Darwin":
        return Path.home() / "Library" / "Application Support" / "Claude"
    elif system == "Windows":
        appdata = Path(os.environ.get("APPDATA", ""))
        return appdata / "Claude"
    else:  # Linux
        return Path.home() / ".config" / "claude"


def _check_claude_desktop_extension() -> tuple[bool, bool, Optional[str]]:
    """Check if notebooklm-mcp is installed as a Claude Desktop Extension (.mcpb).

    Returns:
        (installed, enabled, version):
            installed: True if the extension is registered in extensions-installations.json
            enabled: True if the extension is enabled in its settings file
            version: The installed extension version string, or None
    """
    app_dir = _claude_desktop_app_support_dir()
    installations_path = app_dir / "extensions-installations.json"

    installations = _read_json_config(installations_path)
    extensions = installations.get("extensions", {})

    # Search for any extension whose manifest name contains 'notebooklm'
    for ext_id, ext_data in extensions.items():
        manifest = ext_data.get("manifest", {})
        name = manifest.get("name", "")
        if "notebooklm" in name.lower():
            version = manifest.get("version")

            # Check if the extension is enabled
            settings_path = app_dir / "Claude Extensions Settings" / f"{ext_id}.json"
            settings = _read_json_config(settings_path)
            enabled = settings.get("isEnabled", False)

            return True, enabled, version

    return False, False, None


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


def _cline_config_path() -> Path:
    """Get Cline CLI MCP settings path.

    This is the standalone CLI path, NOT the VS Code extension path.
    """
    return Path.home() / ".cline" / "data" / "settings" / "cline_mcp_settings.json"


def _antigravity_config_path() -> Path:
    """Get Google Antigravity MCP config path."""
    return Path.home() / ".gemini" / "antigravity" / "mcp_config.json"


# =============================================================================
# Client definitions
# =============================================================================

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
    "cline": {
        "name": "Cline CLI",
        "description": "Cline CLI terminal agent",
        "has_auto_setup": True,
    },
    "antigravity": {
        "name": "Antigravity",
        "description": "Google Antigravity AI IDE",
        "has_auto_setup": True,
    },
    "codex": {
        "name": "Codex CLI",
        "description": "OpenAI Codex CLI",
        "has_auto_setup": False,
    },
}


def _complete_client(ctx, param, incomplete: str) -> list[str]:
    """Shell completion for client names."""
    all_clients = list(CLIENT_REGISTRY.keys()) + ["json"]
    return [name for name in all_clients if name.startswith(incomplete)]


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


def _setup_cline() -> bool:
    """Add MCP to Cline CLI config."""
    config_path = _cline_config_path()
    config = _read_json_config(config_path)

    if _is_configured(config):
        console.print(f"[green]✓[/green] Already configured in Cline CLI")
        return True

    _add_mcp_server(config)
    _write_json_config(config_path, config)
    console.print(f"[green]✓[/green] Added to Cline CLI")
    console.print(f"  [dim]{config_path}[/dim]")
    return True


def _setup_antigravity() -> bool:
    """Add MCP to Google Antigravity config."""
    config_path = _antigravity_config_path()
    config = _read_json_config(config_path)

    if _is_configured(config, "notebooklm"):
        console.print(f"[green]✓[/green] Already configured in Antigravity")
        return True

    _add_mcp_server(config, key="notebooklm")
    _write_json_config(config_path, config)
    console.print(f"[green]✓[/green] Added to Antigravity")
    console.print(f"  [dim]{config_path}[/dim]")
    return True


def _prompt_numbered(prompt_text: str, options: list[tuple[str, str]], default: int = 1) -> str:
    """Show a numbered prompt and return the chosen option value.

    Args:
        prompt_text: Header text for the prompt.
        options: List of (value, label) tuples.
        default: 1-based default choice number.

    Returns:
        The value string of the chosen option.
    """
    console.print(f"{prompt_text}")
    for i, (_value, label) in enumerate(options, 1):
        marker = " [dim](default)[/dim]" if i == default else ""
        console.print(f"  [cyan]{i}[/cyan]) {label}{marker}")

    valid = [str(i) for i in range(1, len(options) + 1)]
    choice = Prompt.ask("Choose", choices=valid, default=str(default), show_choices=False)
    return options[int(choice) - 1][0]


def _setup_json() -> None:
    """Interactive flow to generate MCP JSON config for any tool."""
    console.print("[bold]Generate MCP JSON config[/bold]\n")
    console.print("This generates a JSON snippet you can paste into any tool's MCP config.\n")

    config_type = _prompt_numbered("Config type:", [
        ("uvx", "uvx (no install required)"),
        ("regular", "Regular (uses installed binary)"),
    ])

    use_full_path = False
    if config_type == "regular":
        path_choice = _prompt_numbered("Command format:", [
            ("name", "Command name (notebooklm-mcp)"),
            ("full", "Full path to binary"),
        ])
        use_full_path = path_choice == "full"

    config_scope = _prompt_numbered("Config scope:", [
        ("existing", "Add to existing config (server entry only)"),
        ("new", "New config file (includes mcpServers wrapper)"),
    ])

    # Build the server entry
    if config_type == "uvx":
        server_entry = {
            "command": "uvx",
            "args": ["--from", "notebooklm-mcp-cli", "notebooklm-mcp"],
        }
    else:
        if use_full_path:
            binary_path = _find_mcp_server_path()
            if not binary_path:
                console.print(
                    "[yellow]Warning:[/yellow] notebooklm-mcp not found in PATH, "
                    "using command name instead"
                )
                binary_path = MCP_SERVER_CMD
            server_entry = {"command": binary_path}
        else:
            server_entry = {"command": MCP_SERVER_CMD}

    if config_scope == "new":
        output = {"mcpServers": {"notebooklm-mcp": server_entry}}
    else:
        output = {"notebooklm-mcp": server_entry}

    json_str = json.dumps(output, indent=2)

    console.print()
    console.print(Syntax(json_str, "json", theme="monokai", padding=1))
    console.print()

    if platform.system() == "Darwin":
        if Confirm.ask("Copy to clipboard?", default=True):
            try:
                subprocess.run(
                    ["pbcopy"],
                    input=json_str.encode(),
                    check=True,
                    timeout=5,
                )
                console.print("[green]✓[/green] Copied to clipboard")
            except (subprocess.SubprocessError, OSError):
                console.print("[yellow]Warning:[/yellow] Could not copy to clipboard")


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
        nlm setup add cline
        nlm setup add antigravity
        nlm setup add json
    """
    if client == "json":
        _setup_json()
        return

    if client not in CLIENT_REGISTRY:
        valid = ", ".join(list(CLIENT_REGISTRY.keys()) + ["json"])
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
        "cline": _setup_cline,
        "antigravity": _setup_antigravity,
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
        "cline": _cline_config_path(),
        "antigravity": _antigravity_config_path(),
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
            else:
                # Check for .mcpb extension installation
                ext_installed, ext_enabled, ext_version = _check_claude_desktop_extension()
                if ext_installed:
                    ver_label = f" v{ext_version}" if ext_version else ""
                    if ext_enabled:
                        status = f"[green]✓[/green] [dim](extension{ver_label})[/dim]"
                    else:
                        status = f"[yellow]✓[/yellow] [dim](extension{ver_label}, disabled)[/dim]"
                    config_path = "Settings > Extensions"
                else:
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

        elif client_id == "cline":
            path = _cline_config_path()
            config = _read_json_config(path)
            if _is_configured(config):
                status = "[green]✓[/green]"
            config_path = str(path).replace(str(Path.home()), "~")

        elif client_id == "antigravity":
            path = _antigravity_config_path()
            config = _read_json_config(path)
            if _is_configured(config, "notebooklm"):
                status = "[green]✓[/green]"
            config_path = str(path).replace(str(Path.home()), "~")

        elif client_id == "codex":
            config_path = "uses nlm skill install codex"

        table.add_row(info["name"], info["description"], status, config_path)

    console.print(table)
    console.print("\n[dim]Add MCP server:  nlm setup add <client>[/dim]")
    console.print("[dim]Install skills:  nlm skill install <tool>[/dim]")
