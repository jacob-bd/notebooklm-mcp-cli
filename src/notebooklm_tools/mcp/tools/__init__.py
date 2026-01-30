"""MCP Tools - Modular tool definitions for NotebookLM MCP Server."""

# Import all tools from submodules for registration
from .downloads import download_artifact
from .auth import refresh_auth, save_auth_tokens
from .notebooks import (
    notebook_list,
    notebook_get,
    notebook_describe,
    notebook_create,
    notebook_rename,
    notebook_delete,
)
from .sources import (
    source_add,
    source_list_drive,
    source_sync_drive,
    source_delete,
    source_describe,
    source_get_content,
)
from .sharing import (
    notebook_share_status,
    notebook_share_public,
    notebook_share_invite,
)
from .research import (
    research_start,
    research_status,
    research_import,
)
from .studio import (
    studio_create,
    studio_status,
    studio_delete,
)
from .chat import (
    notebook_query,
    chat_configure,
)
from .exports import (
    export_artifact,
)
from .notes import note

__all__ = [
    # Downloads (1 consolidated)
    "download_artifact",
    # Auth (2)
    "refresh_auth",
    "save_auth_tokens",
    # Notebooks (6)
    "notebook_list",
    "notebook_get",
    "notebook_describe",
    "notebook_create",
    "notebook_rename",
    "notebook_delete",
    # Sources (6)
    "source_add",
    "source_list_drive",
    "source_sync_drive",
    "source_delete",
    "source_describe",
    "source_get_content",
    # Sharing (3)
    "notebook_share_status",
    "notebook_share_public",
    "notebook_share_invite",
    # Research (3)
    "research_start",
    "research_status",
    "research_import",
    # Studio (3 - consolidated create)
    "studio_create",
    "studio_status",
    "studio_delete",
    # Chat (2)
    "notebook_query",
    "chat_configure",
    # Exports (1)
    "export_artifact",
    # Notes (1 consolidated)
    "note",
]

