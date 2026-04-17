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
import tomllib
from pathlib import Path

import typer
from rich.prompt import Confirm, Prompt
from rich.syntax import Syntax
from rich.table import Table

from notebooklm_tools.cli.utils import make_console

console = make_console()
app = typer.Typer(
    name="setup",
    help="Configure NotebookLM MCP server for AI tools",
    no_args_is_help=True,
)

# MCP server command - the binary that clients will execute
MCP_SERVER_CMD = "notebooklm-mcp"

# Default MCP tool call timeout in milliseconds (5 minutes).
# NotebookLM operations (query, source add, research, studio) can take 60-120+ seconds.
# OpenCode's default MCP SDK timeout is 60s, which is too short.
OPENCODE_MCP_TIMEOUT_MS = 300_000


def _find_mcp_server_path() -> str | None:
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


def _add_mcp_server(config: dict, key: str = "notebooklm-mcp", extra: dict | None = None) -> dict:
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


def _codex_config_path() -> Path:
    """Get Codex CLI config directory path."""
    return Path.home() / ".codex"


def _opencode_config_path() -> Path:
    """Get OpenCode global config path."""
    return Path.home() / ".config" / "opencode" / "opencode.json"


# =============================================================================
# Client definitions
# =============================================================================

CLIENT_REGISTRY = {
    "claude-code": {
        "name": "Claude Code",
        "description": "Anthropic CLI (claude command)",
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
        "has_auto_setup": True,
    },
    "opencode": {
        "name": "OpenCode",
        "description": "OpenCode terminal AI assistant",
        "has_auto_setup": True,
    },
}


def _complete_client(ctx, param, incomplete: str) -> list[str]:
    """Shell completion for client names."""
    all_clients = list(CLIENT_REGISTRY.keys()) + ["json", "all"]
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
            console.print("[green]✓[/green] Added to Claude Code (user scope)")
            return True
        elif "already exists" in result.stderr.lower():
            console.print("[green]✓[/green] Already configured in Claude Code")
            return True
        else:
            console.print(
                f"[yellow]Warning:[/yellow] claude mcp add returned: {result.stderr.strip()}"
            )
            return False
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
        console.print(f"[yellow]Warning:[/yellow] Could not run claude command: {e}")
        return False


def _setup_gemini() -> bool:
    """Add MCP to Gemini CLI config."""
    config_path = _gemini_config_path()
    config = _read_json_config(config_path)

    if _is_configured(config, "notebooklm"):
        console.print("[green]✓[/green] Already configured in Gemini CLI")
        return True

    console.print(
        "[yellow]Note:[/yellow] Gemini CLI requires [bold]trust: true[/bold] for this MCP "
        "server to function. This grants the server permission to run shell commands and "
        "access files without per-action prompts."
    )
    if not Confirm.ask("Grant elevated trust to notebooklm-mcp in Gemini CLI?", default=True):
        console.print("[yellow]Skipped.[/yellow] Re-run setup to add trust later.")
        return False

    _add_mcp_server(config, key="notebooklm", extra={"trust": True})
    _write_json_config(config_path, config)
    console.print("[green]✓[/green] Added to Gemini CLI")
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
        console.print("[green]✓[/green] Already configured in Windsurf")
        return True

    _add_mcp_server(config)
    _write_json_config(config_path, config)
    console.print("[green]✓[/green] Added to Windsurf")
    console.print(f"  [dim]{config_path}[/dim]")
    return True


def _setup_cline() -> bool:
    """Add MCP to Cline CLI config."""
    config_path = _cline_config_path()
    config = _read_json_config(config_path)

    if _is_configured(config):
        console.print("[green]✓[/green] Already configured in Cline CLI")
        return True

    _add_mcp_server(config)
    _write_json_config(config_path, config)
    console.print("[green]✓[/green] Added to Cline CLI")
    console.print(f"  [dim]{config_path}[/dim]")
    return True


def _setup_antigravity() -> bool:
    """Add MCP to Google Antigravity config."""
    config_path = _antigravity_config_path()
    config = _read_json_config(config_path)

    if _is_configured(config, "notebooklm"):
        console.print("[green]✓[/green] Already configured in Antigravity")
        return True

    _add_mcp_server(config, key="notebooklm")
    _write_json_config(config_path, config)
    console.print("[green]✓[/green] Added to Antigravity")
    console.print(f"  [dim]{config_path}[/dim]")
    return True


def _setup_codex() -> bool:
    """Add MCP to Codex CLI via `codex mcp add` (preferred) or config.toml fallback."""
    codex_cmd = shutil.which("codex")
    if codex_cmd:
        try:
            result = subprocess.run(
                [codex_cmd, "mcp", "add", "notebooklm-mcp", "--", MCP_SERVER_CMD],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                console.print("[green]✓[/green] Added to Codex CLI")
                return True
            elif "already exists" in result.stderr.lower():
                console.print("[green]✓[/green] Already configured in Codex CLI")
                return True
            else:
                console.print(
                    f"[yellow]Warning:[/yellow] codex mcp add returned: {result.stderr.strip()}"
                )
                return False
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
            console.print(f"[yellow]Warning:[/yellow] Could not run codex command: {e}")
            return False
    else:
        # Fallback: write config.toml directly
        config_path = _codex_config_path() / "config.toml"

        if config_path.exists():
            try:
                content = config_path.read_text()
                config = tomllib.loads(content)
                mcp_servers = config.get("mcp_servers", {})
                if "notebooklm" in mcp_servers or "notebooklm-mcp" in mcp_servers:
                    console.print("[green]✓[/green] Already configured in Codex CLI")
                    return True
            except Exception:
                content = config_path.read_text() if config_path.exists() else ""
        else:
            content = ""

        section = """
# NotebookLM MCP server
[mcp_servers.notebooklm]
command = "notebooklm-mcp"
args = []
enabled = true
"""
        new_content = content.rstrip() + "\n" + section if content.strip() else section.lstrip()

        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(new_content)
        console.print("[green]✓[/green] Added to Codex CLI (config.toml)")
        console.print(f"  [dim]{config_path}[/dim]")
        return True


def _setup_opencode() -> bool:
    """Add MCP to OpenCode config.

    Configures both the MCP server entry and a global ``experimental.mcp_timeout``
    so that long-running NotebookLM operations (query, source add, research, studio)
    don't hit OpenCode's default 60-second MCP request timeout.
    """
    config_path = _opencode_config_path()
    config = _read_json_config(config_path)

    mcp = config.get("mcp", {})
    if "notebooklm" in mcp or "notebooklm-mcp" in mcp:
        # Still ensure timeout is set even if server entry already exists
        _ensure_opencode_timeout(config)
        _write_json_config(config_path, config)
        console.print("[green]✓[/green] Already configured in OpenCode")
        return True

    mcp["notebooklm"] = {
        "type": "local",
        "command": [MCP_SERVER_CMD],
        "enabled": True,
        "timeout": OPENCODE_MCP_TIMEOUT_MS,
    }
    config["mcp"] = mcp

    # Set global experimental timeout (proven reliable across OpenCode versions)
    _ensure_opencode_timeout(config)

    _write_json_config(config_path, config)
    console.print("[green]✓[/green] Added to OpenCode")
    console.print(f"  [dim]{config_path}[/dim]")
    return True


def _ensure_opencode_timeout(config: dict) -> None:
    """Set ``experimental.mcp_timeout`` if not already present.

    The per-server ``timeout`` field is reportedly unreliable in some OpenCode
    versions, so we also set the global experimental timeout as a fallback.
    Only writes the value if the user hasn't already set a custom timeout.
    """
    experimental = config.setdefault("experimental", {})
    if "mcp_timeout" not in experimental:
        experimental["mcp_timeout"] = OPENCODE_MCP_TIMEOUT_MS


def _detect_tool(client_id: str) -> bool:
    """Check if an AI tool is installed/present on the system.

    Uses binary checks and config directory presence to determine
    if a tool is available.
    """
    checks = {
        "claude-code": lambda: shutil.which("claude") is not None,
        "gemini": lambda: (
            shutil.which("gemini") is not None or _gemini_config_path().parent.exists()
        ),
        "cursor": lambda: (Path.home() / ".cursor").exists(),
        "windsurf": lambda: _windsurf_config_path().parent.exists(),
        "cline": lambda: (Path.home() / ".cline").exists(),
        "antigravity": lambda: _antigravity_config_path().parent.exists(),
        "codex": lambda: shutil.which("codex") is not None or _codex_config_path().exists(),
        "opencode": lambda: (
            shutil.which("opencode") is not None or _opencode_config_path().exists()
        ),
    }
    check_fn = checks.get(client_id)
    if not check_fn:
        return False
    try:
        return check_fn()
    except Exception:
        return False


def _is_already_configured(client_id: str) -> bool:
    """Check if MCP is already configured for a client."""
    try:
        if client_id == "claude-code":
            claude_cmd = shutil.which("claude")
            if claude_cmd:
                result = subprocess.run(
                    [claude_cmd, "mcp", "list"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                return "notebooklm" in result.stdout.lower()
            return False

        elif client_id == "gemini":
            config = _read_json_config(_gemini_config_path())
            return _is_configured(config, "notebooklm")
        elif client_id == "cursor":
            config = _read_json_config(_cursor_config_path())
            return _is_configured(config)
        elif client_id == "windsurf":
            config = _read_json_config(_windsurf_config_path())
            return _is_configured(config)
        elif client_id == "cline":
            config = _read_json_config(_cline_config_path())
            return _is_configured(config)
        elif client_id == "antigravity":
            config = _read_json_config(_antigravity_config_path())
            return _is_configured(config, "notebooklm")
        elif client_id == "codex":
            codex_cmd = shutil.which("codex")
            if codex_cmd:
                result = subprocess.run(
                    [codex_cmd, "mcp", "list"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                return "notebooklm" in result.stdout.lower()
            else:
                # Check config.toml directly
                toml_path = _codex_config_path() / "config.toml"
                if toml_path.exists():
                    config = tomllib.loads(toml_path.read_text())
                    mcp = config.get("mcp_servers", {})
                    return "notebooklm" in mcp or "notebooklm-mcp" in mcp
        elif client_id == "opencode":
            config = _read_json_config(_opencode_config_path())
            mcp = config.get("mcp", {})
            return "notebooklm" in mcp or "notebooklm-mcp" in mcp
    except Exception:
        pass
    return False


def _setup_all() -> None:
    """Interactive multi-tool setup. Scans system for AI tools and lets user choose."""
    console.print("\n[bold]Scanning for AI tools...[/bold]\n")

    # Scan ALL tools (auto-setup and manual)
    detected = []  # (client_id, info, is_configured, has_auto)
    not_found = []

    for client_id, info in CLIENT_REGISTRY.items():
        is_present = _detect_tool(client_id)
        if is_present:
            has_auto = info["has_auto_setup"]
            already = _is_already_configured(client_id) if has_auto else False
            detected.append((client_id, info, already, has_auto))
        else:
            not_found.append((client_id, info))

    # Display results table
    table = Table(title="Detected AI Tools")
    table.add_column("#", justify="right", style="cyan", width=3)
    table.add_column("Tool", style="bold")
    table.add_column("Status", justify="center")

    configurable = []  # indices of tools that can be auto-configured
    for i, (client_id, info, already, has_auto) in enumerate(detected):  # noqa: B007
        num = str(i + 1)
        if not has_auto:
            table.add_row(num, info["name"], "[dim]use nlm skill install[/dim]")
        elif already:
            table.add_row(num, info["name"], "[green]✓ configured[/green]")
        else:
            table.add_row(num, info["name"], "[yellow]detected[/yellow]")
            configurable.append(i)

    console.print(table)

    if not_found:
        names = ", ".join(info["name"] for _, info in not_found)
        console.print(f"\n[dim]Not found: {names}[/dim]")

    if not configurable:
        if detected:
            console.print("\n[green]All detected tools are already configured! ✓[/green]")
        else:
            console.print("\n[yellow]No supported AI tools detected on your system.[/yellow]")
            console.print("[dim]Use 'nlm setup add <client>' to configure a specific tool.[/dim]")
        return

    # Interactive selection
    unconfigured_names = [f"{detected[i][1]['name']} ({detected[i][0]})" for i in configurable]
    console.print(f"\n[bold]Unconfigured tools:[/bold] {', '.join(unconfigured_names)}")
    console.print()

    choice = (
        Prompt.ask(
            "Configure which tools? [cyan]all/yes[/cyan] / comma-separated numbers / [cyan]none[/cyan]",
            default="all",
        )
        .strip()
        .lower()
    )

    if choice == "none" or choice == "n":
        console.print("Cancelled.")
        return

    # Determine which tools to configure
    if choice == "all" or choice == "a" or choice == "yes" or choice == "y":
        selected_indices = configurable
    else:
        try:
            nums = [int(n.strip()) for n in choice.split(",")]
            selected_indices = []
            for n in nums:
                idx = n - 1
                if idx in configurable:
                    selected_indices.append(idx)
                else:
                    console.print(f"[yellow]Skipping #{n} — already configured or invalid[/yellow]")
        except ValueError:
            console.print(
                "[red]Invalid input. Use 'all', 'none', or comma-separated numbers.[/red]"
            )
            return

    if not selected_indices:
        console.print("[dim]Nothing to configure.[/dim]")
        return

    # Execute setup for selected tools
    console.print()
    setup_fns = {
        "claude-code": _setup_claude_code,
        "gemini": _setup_gemini,
        "cursor": _setup_cursor,
        "windsurf": _setup_windsurf,
        "cline": _setup_cline,
        "antigravity": _setup_antigravity,
        "codex": _setup_codex,
        "opencode": _setup_opencode,
    }

    success_count = 0
    for idx in selected_indices:
        client_id, info, _, _has_auto = detected[idx]
        fn = setup_fns.get(client_id)
        if fn and fn():
            success_count += 1

    console.print(f"\n[green]✓ Configured {success_count} tool(s)[/green]")
    if success_count > 0:
        console.print("[dim]Restart the configured tools to activate the MCP server.[/dim]")


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

    config_type = _prompt_numbered(
        "Config type:",
        [
            ("uvx", "uvx (no install required)"),
            ("regular", "Regular (uses installed binary)"),
        ],
    )

    use_full_path = False
    if config_type == "regular":
        path_choice = _prompt_numbered(
            "Command format:",
            [
                ("name", "Command name (notebooklm-mcp)"),
                ("full", "Full path to binary"),
            ],
        )
        use_full_path = path_choice == "full"

    config_scope = _prompt_numbered(
        "Config scope:",
        [
            ("existing", "Add to existing config (server entry only)"),
            ("new", "New config file (includes mcpServers wrapper)"),
        ],
    )

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

    if platform.system() == "Darwin" and Confirm.ask("Copy to clipboard?", default=True):
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
        help="AI tool to configure, or 'all' to scan & configure interactively",
        shell_complete=_complete_client,
    ),
) -> None:
    """
    Add NotebookLM MCP server to an AI tool.

    Configures the MCP server transport so the AI tool can access
    NotebookLM features (notebooks, sources, audio, research, etc).

    Examples:
        nlm setup add claude-code
        nlm setup add gemini
        nlm setup add cursor
        nlm setup add windsurf
        nlm setup add cline
        nlm setup add antigravity
        nlm setup add opencode
        nlm setup add json
        nlm setup add all         # Interactive — detect and configure all
    """
    if client == "json":
        _setup_json()
        return

    if client == "all":
        _setup_all()
        return

    if client not in CLIENT_REGISTRY:
        valid = ", ".join(list(CLIENT_REGISTRY.keys()) + ["json", "all"])
        console.print(f"[red]Error:[/red] Unknown client '{client}'")
        console.print(f"Available clients: {valid}")
        raise typer.Exit(1)

    info = CLIENT_REGISTRY[client]
    console.print(f"\n[bold]{info['name']}[/bold] — Adding NotebookLM MCP\n")

    if not info["has_auto_setup"]:
        console.print(f"[yellow]Note:[/yellow] {info['name']} doesn't use MCP server config.")
        console.print(
            f"Use [cyan]nlm skill install {client}[/cyan] to install skill files instead."
        )
        raise typer.Exit(0)

    setup_fn = {
        "claude-code": _setup_claude_code,
        "gemini": _setup_gemini,
        "cursor": _setup_cursor,
        "windsurf": _setup_windsurf,
        "cline": _setup_cline,
        "antigravity": _setup_antigravity,
        "codex": _setup_codex,
        "opencode": _setup_opencode,
    }

    success = setup_fn[client]()
    if success:
        console.print(f"\n[dim]Restart {info['name']} to activate the MCP server.[/dim]")


@app.command("remove")
def setup_remove(
    client: str = typer.Argument(
        ...,
        help="AI tool to remove MCP from, or 'all' to remove from every configured tool",
        shell_complete=_complete_client,
    ),
) -> None:
    """
    Remove NotebookLM MCP server from an AI tool.

    Examples:
        nlm setup remove gemini
        nlm setup remove all
    """
    if client == "all":
        _remove_all()
        return

    if client not in CLIENT_REGISTRY:
        valid = ", ".join(list(CLIENT_REGISTRY.keys()) + ["all"])
        console.print(f"[red]Error:[/red] Unknown client '{client}'")
        console.print(f"Available clients: {valid}")
        raise typer.Exit(1)

    _remove_single(client)


def _remove_single(client: str) -> bool:
    """Remove MCP from a single client. Returns True if removed."""
    # Client-specific removal via CLI (preferred)
    if client == "claude-code":
        claude_cmd = shutil.which("claude")
        if claude_cmd:
            try:
                result = subprocess.run(
                    [claude_cmd, "mcp", "remove", "-s", "user", "notebooklm-mcp"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result.returncode == 0:
                    console.print("[green]✓[/green] Removed from Claude Code")
                    return True
                else:
                    console.print(f"[yellow]Note:[/yellow] {result.stderr.strip()}")
                    return False
            except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
                console.print(f"[yellow]Warning:[/yellow] Could not run claude command: {e}")
                return False
        else:
            console.print("[yellow]Warning:[/yellow] 'claude' command not found")
            return False

    # CLI-based removal for Codex
    if client == "codex":
        codex_cmd = shutil.which("codex")
        if codex_cmd:
            try:
                result = subprocess.run(
                    [codex_cmd, "mcp", "remove", "notebooklm-mcp"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result.returncode == 0:
                    console.print("[green]✓[/green] Removed from Codex CLI")
                    return True
                else:
                    console.print(f"[yellow]Note:[/yellow] {result.stderr.strip()}")
                    return False
            except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
                console.print(f"[yellow]Warning:[/yellow] Could not run codex command: {e}")
                return False
        else:
            console.print("[yellow]Warning:[/yellow] 'codex' command not found")
            return False

    # OpenCode uses "mcp" key, not "mcpServers"
    if client == "opencode":
        config_path = _opencode_config_path()
        if not config_path.exists():
            console.print("[dim]No config file found for OpenCode.[/dim]")
            return False
        config = _read_json_config(config_path)
        mcp = config.get("mcp", {})
        removed = False
        for key in ["notebooklm-mcp", "notebooklm"]:
            if key in mcp:
                del mcp[key]
                removed = True
        if removed:
            config["mcp"] = mcp
            # Clean up experimental.mcp_timeout if no other MCP servers remain
            if not mcp:
                experimental = config.get("experimental", {})
                experimental.pop("mcp_timeout", None)
                if not experimental:
                    config.pop("experimental", None)
                else:
                    config["experimental"] = experimental
            _write_json_config(config_path, config)
            console.print("[green]✓[/green] Removed from OpenCode")
            return True
        else:
            console.print("[dim]NotebookLM MCP was not configured in OpenCode.[/dim]")
            return False

    # JSON config-based clients
    config_paths = {
        "gemini": _gemini_config_path(),
        "cursor": _cursor_config_path(),
        "windsurf": _windsurf_config_path(),
        "cline": _cline_config_path(),
        "antigravity": _antigravity_config_path(),
    }

    config_path = config_paths.get(client)
    if not config_path or not config_path.exists():
        console.print(f"[dim]No config file found for {client}.[/dim]")
        return False

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
        return True
    else:
        console.print(
            f"[dim]NotebookLM MCP was not configured in {CLIENT_REGISTRY[client]['name']}.[/dim]"
        )
        return False


def _remove_all() -> None:
    """Remove MCP from all configured tools with explicit confirmation."""
    console.print("\n[bold]Scanning for configured tools...[/bold]\n")

    # Find all configured tools
    configured = []
    for client_id, info in CLIENT_REGISTRY.items():
        if not info["has_auto_setup"]:
            continue
        if _is_already_configured(client_id):
            configured.append((client_id, info))

    if not configured:
        console.print("[dim]No tools have NotebookLM MCP configured.[/dim]")
        return

    # Show what will be removed
    table = Table(title="Configured Tools")
    table.add_column("#", justify="right", style="cyan", width=3)
    table.add_column("Tool", style="bold")

    for i, (client_id, info) in enumerate(configured):  # noqa: B007
        table.add_row(str(i + 1), info["name"])

    console.print(table)

    # Strong warning and confirmation
    console.print()
    console.print("[bold red]⚠  WARNING:[/bold red] This will remove the NotebookLM MCP server")
    console.print(f"from [bold]{len(configured)}[/bold] tool(s) listed above.")
    console.print()

    if not Confirm.ask(
        "[bold]Are you sure you want to remove MCP from ALL configured tools?[/bold]",
        default=False,
    ):
        console.print("Cancelled.")
        return

    # Execute removal
    console.print()
    removed_count = 0
    for client_id, info in configured:  # noqa: B007
        if _remove_single(client_id):
            removed_count += 1

    console.print(f"\n[green]✓ Removed from {removed_count} tool(s)[/green]")
    if removed_count > 0:
        console.print("[dim]Restart the affected tools to apply changes.[/dim]")


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
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    if "notebooklm" in result.stdout.lower():
                        status = "[green]✓[/green]"
                except (subprocess.TimeoutExpired, OSError):
                    status = "[dim]?[/dim]"
                config_path = "claude mcp list"
            else:
                config_path = "not installed"

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
            codex_cmd = shutil.which("codex")
            if codex_cmd:
                try:
                    result = subprocess.run(
                        [codex_cmd, "mcp", "list"],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    if "notebooklm" in result.stdout.lower():
                        status = "[green]✓[/green]"
                except (subprocess.TimeoutExpired, OSError):
                    status = "[dim]?[/dim]"
                config_path = "codex mcp list"
            else:
                config_path = "not installed"

        elif client_id == "opencode":
            path = _opencode_config_path()
            config = _read_json_config(path)
            mcp = config.get("mcp", {})
            if "notebooklm" in mcp or "notebooklm-mcp" in mcp:
                status = "[green]✓[/green]"
            config_path = str(path).replace(str(Path.home()), "~")

        table.add_row(str(info["name"]), str(info["description"]), status, config_path)

    console.print(table)
    console.print("\n[dim]Add MCP server:  nlm setup add <client>[/dim]")
    console.print("[dim]Install skills:  nlm skill install <tool>[/dim]")
