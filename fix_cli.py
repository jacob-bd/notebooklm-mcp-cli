import os
import re
import glob

commands_dir = "src/notebooklm_tools/cli/commands"

for filepath in glob.glob(f"{commands_dir}/*.py"):
    with open(filepath, "r") as f:
        content = f.read()
    
    # Identify standard blocks matching:
    #     except ServiceError as e:
    #         console.print(f"[red]Error:[/red] {e.user_message}")
    #         raise typer.Exit(1)
    #     except NLMError as e:
    #         console.print(f"[red]Error:[/red] {e.message}")
    #         if getattr(e, "hint", None):  # or if e.hint:
    #             console.print(...)
    #         raise typer.Exit(1)
    
    pattern = r'( +)except ServiceError as e:\n(?: +.*\n)+? +raise typer\.Exit\((?:1|e\.code|.*)\)\n( +)except NLMError as e:\n(?: +.*\n)+? +raise typer\.Exit\((?:1|e\.code|.*)\)'
    
    def replacer(match):
        indent = match.group(1)
        return (f"{indent}except (ServiceError, NLMError) as e:\n"
                f"{indent}    handle_error(e, json_output=locals().get('json_output', False))")
        
    new_content = re.sub(pattern, replacer, content)
    
    if new_content != content:
        if "handle_error" not in new_content:
            new_content = new_content.replace(
                "from notebooklm_tools.cli.utils import get_client",
                "from notebooklm_tools.cli.utils import get_client, handle_error"
            )
            if "handle_error" not in new_content:
                new_content = new_content.replace(
                    "from notebooklm_tools.cli.utils import",
                    "from notebooklm_tools.cli.utils import handle_error,"
                )
                
        with open(filepath, "w") as f:
            f.write(new_content)
        print(f"Updated {filepath}")
