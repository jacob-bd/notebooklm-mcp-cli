"""
DEPRECATED: The primer generator has moved to C010_standards.

Install:
    uv tool install --editable ~/SyncedProjects/C010_standards

Then run:
    generate-project-primer <repo_id>
"""

import sys
import warnings


def main() -> int:
    """Main CLI entry point — deprecated."""
    warnings.warn(
        "The primer generator in C021_notebooklm-mcp is deprecated. "
        "Install C010_standards instead: "
        "uv tool install --editable ~/SyncedProjects/C010_standards",
        DeprecationWarning,
        stacklevel=2,
    )
    print(
        "ERROR: This tool has moved to C010_standards.",
        file=sys.stderr,
    )
    print(file=sys.stderr)
    print(
        "Install with: uv tool install --editable ~/SyncedProjects/C010_standards",
        file=sys.stderr,
    )
    print("Then run: generate-project-primer <repo>", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
