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
    notebook_share_batch,
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
    studio_revise,
)
from .chat import (
    notebook_query,
    chat_configure,
)
from .exports import (
    export_artifact,
)
from .notes import note
from .server import server_info
from .cache import cache_list, cache_clear
from .case_files import (
    case_file_list,
    case_file_get,
    case_file_save,
    case_file_search,
    case_file_delete,
    case_file_categories,
    case_file_from_source,
    batch_drive_to_case,
)
from .agents import (
    agent_registry_build,
    agent_registry_get,
    agent_registry_update,
    notebook_agent_query,
    notebook_agent_multi_query,
    notebook_agent_query_claude,
    notebook_prefetch,
)
from .gdoc_sync import (
    notebook_gdoc_link,
    notebook_gdoc_unlink,
    notebook_gdoc_list,
    notebook_gdoc_sync,
    notebook_gdoc_sync_all,
)

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
    # Sharing (4)
    "notebook_share_status",
    "notebook_share_public",
    "notebook_share_invite",
    "notebook_share_batch",
    # Research (3)
    "research_start",
    "research_status",
    "research_import",
    # Studio (4 - consolidated create + revise)
    "studio_create",
    "studio_status",
    "studio_delete",
    "studio_revise",
    # Chat (2)
    "notebook_query",
    "chat_configure",
    # Exports (1)
    "export_artifact",
    # Notes (1 consolidated)
    "note",
    # Server (1)
    "server_info",
    # Cache (2)
    "cache_list",
    "cache_clear",
    # Case Files (8)
    "case_file_list",
    "case_file_get",
    "case_file_save",
    "case_file_search",
    "case_file_delete",
    "case_file_categories",
    "case_file_from_source",
    "batch_drive_to_case",
    # Agents (7)
    "agent_registry_build",
    "agent_registry_get",
    "agent_registry_update",
    "notebook_agent_query",
    "notebook_agent_multi_query",
    "notebook_agent_query_claude",
    "notebook_prefetch",
    # Vectorize (3 - optional, requires CLOUDFLARE_API_TOKEN + CLOUDFLARE_ACCOUNT_ID)
    # vector_index_source, vector_index_notebook, vector_search (registered lazily)
    # GDoc Sync (5)
    "notebook_gdoc_link",
    "notebook_gdoc_unlink",
    "notebook_gdoc_list",
    "notebook_gdoc_sync",
    "notebook_gdoc_sync_all",
]
