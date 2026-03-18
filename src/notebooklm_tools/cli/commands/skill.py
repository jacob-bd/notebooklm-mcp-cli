"""Skill installer commands for NotebookLM CLI."""

import re
import shutil
from pathlib import Path
from typing import Literal, Optional

from notebooklm_tools import __version__

import typer
from rich.console import Console
from rich.table import Table

console = Console()
app = typer.Typer(
    name="skill",
    help="Install NotebookLM skills for AI tools",
    no_args_is_help=True,
)

# Tool configuration mapping
# "user"/"project" values are BASE skill directories — all skills from data/skills/
# are installed as subdirectories within these paths.
TOOL_CONFIGS = {
    "claude-code": {
        "user": Path.home() / ".claude/skills",
        "project": Path(".claude/skills"),
        "format": "skill.md",
        "description": "Claude Code CLI and Desktop",
    },
    "cursor": {
        "user": Path.home() / ".cursor/skills",
        "project": Path(".cursor/skills"),
        "format": "skill.md",
        "description": "Cursor AI editor",
    },
    "codex": {
        "user": Path.home() / ".agents/skills",
        "project": Path(".agents/skills"),
        "format": "skill.md",
        "description": "OpenAI Codex CLI",
    },
    "opencode": {
        "user": Path.home() / ".config/opencode/skills",
        "project": Path(".opencode/skills"),
        "format": "skill.md",
        "description": "OpenCode AI assistant",
    },
    "gemini-cli": {
        "user": Path.home() / ".gemini/skills",
        "project": Path(".gemini/skills"),
        "format": "skill.md",
        "description": "Google Gemini CLI",
    },
    "antigravity": {
        "user": Path.home() / ".gemini/antigravity/skills",
        "project": Path(".agent/skills"),
        "format": "skill.md",
        "description": "Antigravity agent framework",
    },
    "cline": {
        "user": Path.home() / ".cline/skills",
        "project": Path(".cline/skills"),
        "format": "skill.md",
        "description": "Cline CLI terminal agent",
    },
    "openclaw": {
        "user": Path.home() / ".openclaw/workspace/skills",
        "project": Path(".openclaw/workspace/skills"),
        "format": "skill.md",
        "description": "OpenClaw AI agent framework",
    },
    "gws": {
        "user": Path.home() / ".gws/skills",
        "project": Path(".gws/skills"),
        "format": "skill.md",
        "description": "Google Workspace CLI (gws)",
    },
    "other": {
        "project": Path("./nlm-skill-export"),
        "format": "all",
        "description": "Export all formats for manual installation",
    },
}


def complete_tool_name(ctx: "click.Context", param: "click.Parameter", incomplete: str) -> list[str]:
    """Shell completion callback for tool names."""
    return [name for name in TOOL_CONFIGS.keys() if name.startswith(incomplete)]


def get_data_dir() -> Path:
    """Get the package data directory containing skill files."""
    import notebooklm_tools

    package_dir = Path(notebooklm_tools.__file__).parent
    data_dir = package_dir / "data"

    if not data_dir.exists():
        console.print(f"[red]Error:[/red] Data directory not found: {data_dir}")
        raise typer.Exit(1)

    return data_dir


def check_install_status(tool: str, level: str = "user") -> tuple[bool, Optional[Path]]:
    """Check if skill is installed for a tool.

    Returns:
        (is_installed, install_path)
    """
    if tool not in TOOL_CONFIGS:
        return False, None

    config = TOOL_CONFIGS[tool]

    # Get install path
    if level == "user" and "user" in config:
        install_path = config["user"]
    elif level == "project" and "project" in config:
        install_path = config["project"]
    else:
        return False, None

    # Check format
    if config["format"] == "skill.md":
        # Check for nlm-skill/SKILL.md in the base skills directory
        skill_file = install_path / "nlm-skill" / "SKILL.md"
        return skill_file.exists(), install_path
    elif config["format"] == "agents.md":
        # Check for markers in AGENTS.md
        if not install_path.exists():
            return False, install_path
        content = install_path.read_text()
        return "<!-- nlm-skill-start -->" in content, install_path
    elif config["format"] == "all":
        # Check if export directory exists
        return install_path.exists(), install_path

    return False, None


def _inject_version_to_frontmatter(skill_path: Path) -> None:
    """Inject the current package version into the SKILL.md YAML frontmatter."""
    content = skill_path.read_text()
    if content.startswith("---"):
        # Find the closing --- of frontmatter
        end_idx = content.index("---", 3)
        frontmatter = content[3:end_idx]
        # Remove any existing version line
        frontmatter = re.sub(r"\nversion:.*", "", frontmatter)
        # Add version before closing ---
        frontmatter = frontmatter.rstrip() + f"\nversion: \"{__version__}\"\n"
        content = "---" + frontmatter + "---" + content[end_idx + 3:]
    else:
        # No frontmatter — prepend one with version
        content = f"---\nversion: \"{__version__}\"\n---\n\n" + content
    skill_path.write_text(content)


def _get_installed_version(tool: str, level: str) -> Optional[str]:
    """Read the version from an installed skill. Returns None if not found."""
    config = TOOL_CONFIGS[tool]
    install_path = config.get(level)
    if not install_path:
        return None

    format_type = config["format"]

    if format_type == "agents.md":
        if not install_path.exists():
            return None
        try:
            content = install_path.read_text()
            match = re.search(r'<!-- nlm-version: ([\d.]+) -->', content)
            return match.group(1) if match else None
        except Exception:
            return None
    elif format_type == "skill.md":
        # Primary skill is at nlm-skill/SKILL.md within the base directory
        skill_file = install_path / "nlm-skill" / "SKILL.md"
    elif format_type == "all":
        skill_file = install_path / "nlm-skill" / "SKILL.md"
    else:
        return None

    if not skill_file.exists():
        return None

    try:
        content = skill_file.read_text()
        match = re.search(r'version:\s*"([^"]*)"', content)
        return match.group(1) if match else None
    except Exception:
        return None


def _inject_version_to_agents_md(agents_path: Path) -> None:
    """Inject a version comment into the NLM section of AGENTS.md."""
    try:
        content = agents_path.read_text()
        version_comment = f"<!-- nlm-version: {__version__} -->"

        # Remove any existing version comment
        content = re.sub(r'<!-- nlm-version: [\d.]+ -->\n?', '', content)

        # Insert version comment right after the start marker
        start_marker = "<!-- nlm-skill-start -->"
        if start_marker in content:
            content = content.replace(
                start_marker,
                f"{start_marker}\n{version_comment}",
            )
            agents_path.write_text(content)
    except Exception:
        pass



def get_skill_names() -> list[str]:
    """Return sorted list of skill directory names from data/skills/."""
    data_dir = get_data_dir()
    skills_dir = data_dir / "skills"
    if not skills_dir.exists():
        return []
    return sorted(d.name for d in skills_dir.iterdir() if d.is_dir() and (d / "SKILL.md").exists())


def install_skill_md(base_path: Path) -> None:
    """Install all skills from data/skills/ to base_path/<skill-name>/."""
    data_dir = get_data_dir()
    skills_src = data_dir / "skills"

    # Create base directory
    base_path.mkdir(parents=True, exist_ok=True)

    if not skills_src.exists():
        # Fallback: legacy single-skill install from data/SKILL.md
        skill_dst = base_path / "nlm-skill"
        skill_dst.mkdir(parents=True, exist_ok=True)
        shutil.copy2(data_dir / "SKILL.md", skill_dst / "SKILL.md")
        _inject_version_to_frontmatter(skill_dst / "SKILL.md")
        ref_src = data_dir / "references"
        if ref_src.exists():
            shutil.copytree(ref_src, skill_dst / "references", dirs_exist_ok=True)
        console.print(f"[green]✓[/green] Installed nlm-skill (v{__version__}) to {base_path}")
        return

    installed: list[str] = []
    for skill_dir in sorted(skills_src.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue

        dst = base_path / skill_dir.name
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(skill_dir, dst)

        # Inject version into the SKILL.md
        _inject_version_to_frontmatter(dst / "SKILL.md")
        installed.append(skill_dir.name)

    console.print(f"[green]✓[/green] Installed {len(installed)} skills (v{__version__}) to {base_path}")
    for name in installed:
        console.print(f"  [dim]• {name}[/dim]")


def install_agents_md(install_path: Path) -> None:
    """Install/update AGENTS.md format (append with markers)."""
    data_dir = get_data_dir()
    section_src = data_dir / "AGENTS_SECTION.md"
    section_content = section_src.read_text()

    # Read existing AGENTS.md or create new
    if install_path.exists():
        content = install_path.read_text()

        # Check if already installed
        if "<!-- nlm-skill-start -->" in content:
            # Update existing section
            start_marker = "<!-- nlm-skill-start -->"
            end_marker = "<!-- nlm-skill-end -->"

            start_idx = content.find(start_marker)
            end_idx = content.find(end_marker)

            if start_idx != -1 and end_idx != -1:
                # Replace existing section
                before = content[:start_idx]
                after = content[end_idx + len(end_marker):]
                content = before + section_content + after
            else:
                # Malformed markers, append anyway
                content = content.rstrip() + "\n\n" + section_content + "\n"
        else:
            # Append new section
            content = content.rstrip() + "\n\n" + section_content + "\n"
    else:
        # Create new file with section
        install_path.parent.mkdir(parents=True, exist_ok=True)
        content = section_content + "\n"

    install_path.write_text(content)

    # Inject version marker into the NLM section
    _inject_version_to_agents_md(install_path)

    console.print(f"[green]✓[/green] Updated AGENTS.md at {install_path}")
    console.print(f"  [dim]• NLM section appended with markers")


def install_all_formats(install_path: Path) -> None:
    """Export all skill formats to a directory."""
    data_dir = get_data_dir()

    # Remove existing directory
    if install_path.exists():
        shutil.rmtree(install_path)

    # Create export directory
    install_path.mkdir(parents=True, exist_ok=True)

    # Copy all skills from data/skills/ into a "skills/" subdirectory
    skills_src = data_dir / "skills"
    skills_dst = install_path / "skills"
    if skills_src.exists():
        shutil.copytree(skills_src, skills_dst)
        # Inject version into each skill
        for skill_dir in skills_dst.iterdir():
            if skill_dir.is_dir():
                skill_md = skill_dir / "SKILL.md"
                if skill_md.exists():
                    _inject_version_to_frontmatter(skill_md)
    else:
        # Fallback: legacy single-skill
        skill_dir = install_path / "nlm-skill"
        skill_dir.mkdir()
        shutil.copy2(data_dir / "SKILL.md", skill_dir / "SKILL.md")
        shutil.copytree(data_dir / "references", skill_dir / "references")

    # Copy AGENTS.md section
    agents_file = install_path / "AGENTS_SECTION.md"
    shutil.copy2(data_dir / "AGENTS_SECTION.md", agents_file)

    # Create README
    skill_names = get_skill_names()
    skills_list = "\n".join(f"- `{n}/`" for n in skill_names) if skill_names else "- `nlm-skill/`"
    readme_content = f"""# NotebookLM Skill Export

This directory contains NotebookLM skill files in multiple formats.

## Skills Included ({len(skill_names)} total)

{skills_list}

Each skill directory contains a `SKILL.md` following the OpenClaw/gws skill format:
- **Atomic skills** (`nlm-*`): focused docs for individual command groups
- **Recipe skills** (`recipe-*`): step-by-step automation workflows
- **Persona skills** (`persona-*`): role-based behavioral configurations

### AGENTS_SECTION.md
Section format for Codex AGENTS.md (copy/paste into your AGENTS.md)

## Installation

Copy the `skills/` directory contents to your agent tool's skills folder:

### Claude Code
```bash
cp -r skills/* ~/.claude/skills/
```

### OpenCode
```bash
cp -r skills/* ~/.config/opencode/skills/
```

### Gemini CLI
```bash
cp -r skills/* ~/.gemini/skills/
```

### Antigravity / OpenClaw
```bash
cp -r skills/* ~/.openclaw/workspace/skills/
```

### Google Workspace CLI (gws)
```bash
cp -r skills/* ~/.gws/skills/
```

Or for project-level installation, copy to:
- Claude Code: `.claude/skills/`
- OpenCode: `.opencode/skills/`
- Gemini CLI: `.gemini/skills/`
- Antigravity / OpenClaw: `.agent/skills/` or `.openclaw/workspace/skills/`
- gws: `.gws/skills/`

### Codex
```bash
cp -r skills/* ~/.agents/skills/
```

## Automated Installation

Instead of manual copying, you can use:
```bash
nlm skill install <tool>
```

Where `<tool>` is: claude-code, cursor, codex, opencode, gemini-cli, antigravity, cline, openclaw, gws.
"""

    (install_path / "README.md").write_text(readme_content)

    n_skills = len(skill_names)
    console.print(f"[green]✓[/green] Exported {n_skills} skills to {install_path}")
    console.print(f"  [dim]• skills/ ({n_skills} skill directories)")
    console.print(f"  [dim]• AGENTS_SECTION.md (for Codex)")
    console.print(f"  [dim]• README.md (installation instructions)")


@app.command("install")
def install(
    tool: str = typer.Argument(
        ...,
        help="Tool to install skill for (claude-code, cursor, codex, opencode, gemini-cli, antigravity, other)",
        shell_complete=complete_tool_name,
    ),
    level: Literal["user", "project"] = typer.Option(
        "user",
        "--level",
        "-l",
        help="Install at user level (~/.config) or project level (./)",
    ),
) -> None:
    """
    Install NotebookLM skill for an AI tool.

    Examples:
        nlm skill install claude-code
        nlm skill install codex --level project
        nlm skill install other  # Export all formats
    """
    if tool not in TOOL_CONFIGS:
        valid_tools = ", ".join(TOOL_CONFIGS.keys())
        console.print(f"[red]Error:[/red] Unknown tool '{tool}'")
        console.print(f"Valid tools: {valid_tools}")
        raise typer.Exit(1)

    config = TOOL_CONFIGS[tool]

    # Check level support
    if level == "user" and "user" not in config:
        if tool == "other":
            # Auto-switch to project level for export
            level = "project"
            console.print("[dim]Note: 'other' exports to current directory (project level)[/dim]")
        else:
            console.print(f"[red]Error:[/red] Tool '{tool}' does not support user-level installation")
            console.print(f"Use --level project instead")
            raise typer.Exit(1)

    # Get install path
    install_path = config.get(level)
    if not install_path:
        install_path = config.get("project")  # Fallback

    # Validate parent directory exists for user-level installs
    if level == "user" and install_path:
        # For SKILL.md format, check the parent of the skill directory
        # For AGENTS.md format, check the parent of the file
        if config["format"] == "skill.md":
            parent_dir = install_path.parent
        elif config["format"] == "agents.md":
            parent_dir = install_path.parent
        else:
            parent_dir = None

        if parent_dir and not parent_dir.exists():
            console.print(f"[yellow]Warning:[/yellow] Parent directory does not exist: {parent_dir}")
            console.print(f"This suggests {tool} may not be installed on your system.")
            console.print()

            # Offer options
            console.print("Options:")
            console.print(f"  1. Create the directory and install anyway")
            console.print(f"  2. Use --level project to install in current directory")
            console.print(f"  3. Cancel and install {tool} first")
            console.print()

            choice = typer.prompt(
                "Choose an option",
                type=int,
                default=2,
            )

            if choice == 1:
                console.print(f"[dim]Creating {parent_dir}...[/dim]")
                parent_dir.mkdir(parents=True, exist_ok=True)
            elif choice == 2:
                console.print(f"[dim]Switching to project-level installation...[/dim]")
                level = "project"
                install_path = config.get("project")
                if not install_path:
                    console.print(f"[red]Error:[/red] Tool '{tool}' does not support project-level installation")
                    raise typer.Exit(1)
            else:
                console.print("Cancelled.")
                raise typer.Exit(0)

    # Check if already installed
    is_installed, _ = check_install_status(tool, level)
    if is_installed:
        console.print(f"[yellow]![/yellow] Skill already installed for {tool} at {level} level")
        if not typer.confirm("Overwrite existing installation?"):
            console.print("Cancelled.")
            raise typer.Exit(0)

    # Install based on format
    format_type = config["format"]

    try:
        if format_type == "skill.md":
            install_skill_md(install_path)
        elif format_type == "agents.md":
            install_agents_md(install_path)
        elif format_type == "all":
            install_all_formats(install_path)

        console.print(f"\n[green]✓[/green] Successfully installed skill for [cyan]{tool}[/cyan]")
        console.print(f"  Level: {level}")
        console.print(f"  Path: {install_path}")

    except Exception as e:
        console.print(f"\n[red]✗ Installation failed:[/red] {e}")
        raise typer.Exit(1)


@app.command("uninstall")
def uninstall(
    tool: str = typer.Argument(
        ...,
        help="Tool to uninstall skill from",
        shell_complete=complete_tool_name,
    ),
    level: Literal["user", "project"] = typer.Option(
        "user",
        "--level",
        "-l",
        help="Uninstall from user or project level",
    ),
) -> None:
    """
    Remove installed NotebookLM skill.

    Examples:
        nlm skill uninstall claude-code
        nlm skill uninstall codex --level project
    """
    if tool not in TOOL_CONFIGS:
        valid_tools = ", ".join(TOOL_CONFIGS.keys())
        console.print(f"[red]Error:[/red] Unknown tool '{tool}'")
        console.print(f"Valid tools: {valid_tools}")
        raise typer.Exit(1)

    is_installed, install_path = check_install_status(tool, level)

    if not is_installed:
        console.print(f"[yellow]![/yellow] Skill not installed for {tool} at {level} level")
        raise typer.Exit(0)

    # Confirm deletion
    if not typer.confirm(f"Remove skill from {install_path}?"):
        console.print("Cancelled.")
        raise typer.Exit(0)

    config = TOOL_CONFIGS[tool]
    format_type = config["format"]

    try:
        if format_type == "skill.md":
            # Remove all nlm/recipe/persona skill directories from the base path
            skill_names = get_skill_names()
            removed = []
            for name in skill_names:
                skill_path = install_path / name
                if skill_path.exists():
                    shutil.rmtree(skill_path)
                    removed.append(name)
            if removed:
                console.print(f"[green]✓[/green] Removed {len(removed)} skills from {install_path}")
                for name in removed:
                    console.print(f"  [dim]• {name}[/dim]")
            else:
                console.print(f"[yellow]![/yellow] No skill directories found in {install_path}")

        elif format_type == "agents.md":
            # Remove section from AGENTS.md
            if install_path.exists():
                content = install_path.read_text()
                start_marker = "<!-- nlm-skill-start -->"
                end_marker = "<!-- nlm-skill-end -->"

                start_idx = content.find(start_marker)
                end_idx = content.find(end_marker)

                if start_idx != -1 and end_idx != -1:
                    # Remove section
                    before = content[:start_idx].rstrip()
                    after = content[end_idx + len(end_marker):].lstrip()

                    if before and after:
                        content = before + "\n\n" + after
                    elif before:
                        content = before
                    elif after:
                        content = after
                    else:
                        content = ""

                    install_path.write_text(content)
                    console.print(f"[green]✓[/green] Removed NLM section from {install_path}")
                else:
                    console.print(f"[yellow]![/yellow] Markers not found in {install_path}")

        elif format_type == "all":
            # Remove export directory
            if install_path.exists():
                shutil.rmtree(install_path)
            console.print(f"[green]✓[/green] Removed {install_path}")

    except Exception as e:
        console.print(f"\n[red]✗ Uninstall failed:[/red] {e}")
        raise typer.Exit(1)


@app.command("list")
def list_tools() -> None:
    """
    Show available tools and installation status.
    """
    table = Table(title="NotebookLM Skill Installation Status")
    table.add_column("Tool", style="cyan")
    table.add_column("Description")
    table.add_column("User", justify="center")
    table.add_column("Project", justify="center")

    has_outdated = False

    for tool, config in TOOL_CONFIGS.items():
        # Skip "other" — it's an export format, not a real install target
        if tool == "other":
            continue

        # Check user level
        user_status = ""
        if "user" in config:
            is_installed, _ = check_install_status(tool, "user")
            if is_installed:
                installed_ver = _get_installed_version(tool, "user")
                if installed_ver is None:
                    user_status = "[yellow]✓ (unknown)[/yellow]"
                    has_outdated = True
                elif installed_ver != __version__:
                    user_status = f"[yellow]✓ (v{installed_ver})[/yellow]"
                    has_outdated = True
                else:
                    user_status = "[green]✓[/green]"
            else:
                user_status = "[dim]-[/dim]"
        else:
            user_status = "[dim]N/A[/dim]"

        # Check project level
        project_status = ""
        if "project" in config:
            is_installed, _ = check_install_status(tool, "project")
            if is_installed:
                installed_ver = _get_installed_version(tool, "project")
                if installed_ver is None:
                    project_status = "[yellow]✓ (unknown)[/yellow]"
                    has_outdated = True
                elif installed_ver != __version__:
                    project_status = f"[yellow]✓ (v{installed_ver})[/yellow]"
                    has_outdated = True
                else:
                    project_status = "[green]✓[/green]"
            else:
                project_status = "[dim]-[/dim]"
        else:
            project_status = "[dim]N/A[/dim]"

        table.add_row(
            tool,
            config["description"],
            user_status,
            project_status,
        )

    skill_names = get_skill_names()
    console.print(table)
    console.print(f"\n[dim]Legend: ✓ = installed, - = not installed, N/A = not applicable[/dim]")
    console.print(f"[dim]Installs {len(skill_names)} skills per tool: {', '.join(skill_names[:4])}{'...' if len(skill_names) > 4 else ''}[/dim]")
    if has_outdated:
        console.print(f"[yellow]⚠  Some skills are outdated (current: v{__version__}). Run 'nlm skill update' to update all.[/yellow]")


def _update_single_tool(tool: str, level: str) -> bool:
    """Update a single tool's skill at the given level. Returns True if updated."""
    config = TOOL_CONFIGS[tool]
    install_path = config.get(level)
    if not install_path:
        return False

    format_type = config["format"]

    try:
        if format_type == "skill.md":
            install_skill_md(install_path)
        elif format_type == "agents.md":
            install_agents_md(install_path)
        elif format_type == "all":
            install_all_formats(install_path)
        return True
    except Exception as e:
        console.print(f"[red]Error updating {tool} ({level}):[/red] {e}")
        return False


@app.command("update")
def update(
    tool: Optional[str] = typer.Argument(
        None,
        help="Tool to update (omit to update all outdated skills)",
        shell_complete=complete_tool_name,
    ),
) -> None:
    """
    Update outdated skills to the current version.

    Examples:
        nlm skill update              # Update all outdated skills
        nlm skill update claude-code  # Update just Claude Code
    """
    if tool and tool not in TOOL_CONFIGS:
        valid_tools = ", ".join(TOOL_CONFIGS.keys())
        console.print(f"[red]Error:[/red] Unknown tool '{tool}'")
        console.print(f"Valid tools: {valid_tools}")
        raise typer.Exit(1)

    tools_to_check = {tool: TOOL_CONFIGS[tool]} if tool else TOOL_CONFIGS
    updated = 0
    skipped = 0
    already_current = 0

    for t, config in tools_to_check.items():
        for level in ("user", "project"):
            if level not in config:
                continue

            is_installed, _ = check_install_status(t, level)
            if not is_installed:
                continue

            installed_ver = _get_installed_version(t, level)
            if installed_ver == __version__:
                already_current += 1
                if tool:
                    # Only show this message when updating a specific tool
                    console.print(f"[green]✓[/green] {t} ({level}) is already at v{__version__}")
                continue

            old_ver = installed_ver or "unknown"
            console.print(f"\n[bold]Updating {t} ({level}):[/bold] v{old_ver} → v{__version__}")
            if _update_single_tool(t, level):
                updated += 1
            else:
                skipped += 1

    # Summary
    console.print()
    if updated == 0 and already_current > 0 and skipped == 0:
        console.print(f"[green]All installed skills are already at v{__version__} ✓[/green]")
    elif updated > 0:
        console.print(f"[green]✓ Updated {updated} skill(s) to v{__version__}[/green]")
        if skipped > 0:
            console.print(f"[yellow]⚠ {skipped} skill(s) failed to update[/yellow]")
    elif skipped > 0:
        console.print(f"[red]✗ {skipped} skill(s) failed to update[/red]")
    else:
        if tool:
            console.print(f"[dim]{tool} is not installed. Use 'nlm skill install {tool}' first.[/dim]")
        else:
            console.print("[dim]No installed skills found to update.[/dim]")


@app.command("show")
def show(
    name: Optional[str] = typer.Argument(
        None,
        help="Skill name to show (e.g. nlm-skill, persona-researcher). Omit to list all.",
    ),
) -> None:
    """
    Display skill content. Shows all available skills if no name given.

    Examples:
        nlm skill show                   # List all skills
        nlm skill show nlm-skill         # Show main skill
        nlm skill show persona-researcher
    """
    data_dir = get_data_dir()
    skills_dir = data_dir / "skills"

    if name:
        # Show a specific skill
        skill_file = skills_dir / name / "SKILL.md" if skills_dir.exists() else data_dir / "SKILL.md"
        if not skill_file.exists():
            # Fallback to legacy location
            legacy = data_dir / "SKILL.md"
            if legacy.exists() and name in ("nlm-skill", "main"):
                console.print(legacy.read_text())
                return
            console.print(f"[red]Error:[/red] Skill '{name}' not found")
            skill_names = get_skill_names()
            if skill_names:
                console.print(f"Available: {', '.join(skill_names)}")
            raise typer.Exit(1)
        console.print(skill_file.read_text())
    else:
        # List all available skills
        skill_names = get_skill_names()
        if not skill_names:
            # Fallback to legacy
            legacy = data_dir / "SKILL.md"
            if legacy.exists():
                console.print(legacy.read_text())
            else:
                console.print("[red]Error:[/red] No skills found")
                raise typer.Exit(1)
            return

        table = Table(title=f"Available NotebookLM Skills ({len(skill_names)} total)")
        table.add_column("Skill", style="cyan")
        table.add_column("Category")
        table.add_column("Description")

        import re as _re
        for skill_name in skill_names:
            skill_md = skills_dir / skill_name / "SKILL.md"
            category = "atomic"
            description = ""
            if skill_name.startswith("recipe-"):
                category = "recipe"
            elif skill_name.startswith("persona-"):
                category = "persona"

            try:
                content = skill_md.read_text()
                m = _re.search(r'description:\s*"([^"]+)"', content)
                if m:
                    desc = m.group(1)
                    description = desc[:80] + "..." if len(desc) > 80 else desc
            except Exception:
                pass

            table.add_row(skill_name, category, description)

        console.print(table)
        console.print(f"\n[dim]Run 'nlm skill show <name>' to view a specific skill[/dim]")
