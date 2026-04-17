"""Configuration CLI commands."""

import typer
from rich.syntax import Syntax

from notebooklm_tools.cli.formatters import print_json
from notebooklm_tools.cli.utils import make_console
from notebooklm_tools.utils.config import _config_to_toml, get_config, save_config

console = make_console()
app = typer.Typer(
    help="Manage configuration settings",
    rich_markup_mode="rich",
    no_args_is_help=True,
)


@app.command("show")
def show_config(
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
) -> None:
    """Show current configuration."""
    config = get_config()

    if json_output:
        print_json(config.model_dump())
    else:
        # Print as TOML syntax highlighted
        toml_str = _config_to_toml(config)
        syntax = Syntax(toml_str, "toml", theme="monokai", line_numbers=False)
        console.print(syntax)


@app.command("get")
def get_config_value(
    key: str = typer.Argument(..., help="Configuration key (e.g. output.format)"),
) -> None:
    """Get a specific configuration value."""
    config = get_config()
    conf_dict = config.model_dump()

    parts = key.split(".")
    current = conf_dict

    try:
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                console.print(f"[red]Error:[/red] Key '{key}' not found.")
                raise typer.Exit(1)

        # Format output based on type
        if isinstance(current, bool):
            val_str = str(current).lower()
            color = "green" if current else "red"
            console.print(f"[{color}]{val_str}[/{color}]")
        else:
            console.print(str(current))

    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise typer.Exit(1) from e


@app.command("set")
def set_config_value(
    key: str = typer.Argument(..., help="Configuration key (e.g. output.format)"),
    value: str = typer.Argument(..., help="Value to set"),
) -> None:
    """Set a configuration value."""
    config = get_config()

    parts = key.split(".")
    if len(parts) != 2:
        console.print("[red]Error:[/red] Invalid key format. Use section.key (e.g. output.format)")
        raise typer.Exit(1)

    section, field = parts

    # Validate section
    if not hasattr(config, section):
        console.print(f"[red]Error:[/red] Unknown section '{section}'")
        raise typer.Exit(1)

    section_obj = getattr(config, section)

    # Validate field
    if not hasattr(section_obj, field):
        console.print(f"[red]Error:[/red] Unknown field '{field}' in section '{section}'")
        raise typer.Exit(1)

    # Get field info for type conversion
    # Pydantic v2 uses model_fields
    field_info = section_obj.model_fields.get(field)
    target_type = field_info.annotation

    try:
        # Handle boolean conversion explicitly
        if target_type is bool:
            if value.lower() in ("true", "1", "yes", "on"):
                converted_val = True
            elif value.lower() in ("false", "0", "no", "off"):
                converted_val = False
            else:
                raise ValueError("Value must be true/false")
        else:
            # Basic casting for other types (int, float, str)
            # This is simplified; Pydantic model usage handles validation but we need native type for assignment
            if target_type is int:
                converted_val = int(value)
            elif target_type is float:
                converted_val = float(value)
            else:
                converted_val = value  # Default to string

        # Update the model
        setattr(section_obj, field, converted_val)

        # Save changes
        save_config(config)
        console.print(f"[green]✓[/green] Set {key} = {converted_val}")

    except ValueError as e:
        console.print(f"[red]Error:[/red] Invalid value for {key}: {str(e)}")
        raise typer.Exit(1) from e
    except Exception as e:
        console.print(f"[red]Error:[/red] Failed to update config: {str(e)}")
        raise typer.Exit(1) from e
