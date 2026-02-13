"""Service layer for NotebookLM MCP CLI.

This package contains the shared business logic, validation, and error handling
used by both the CLI and MCP interfaces.
"""

from .errors import (
    ServiceError,
    ValidationError,
    NotFoundError,
    CreationError,
    ExportError,
)

__all__ = [
    "ServiceError",
    "ValidationError",
    "NotFoundError",
    "CreationError",
    "ExportError",
]
