"""NotebookLM MCP Server - Modular Architecture.

This is the main server facade that initializes FastMCP and registers all tools
from the modular tools package. Tools are organized into domain-specific modules
under the `tools/` directory.

Tool Modules:
- auth.py: Authentication management (refresh_auth, save_auth_tokens)
- notebooks.py: Notebook CRUD operations
- sources.py: Source management with consolidated source_add
- sharing.py: Sharing and collaboration
- research.py: Deep research and source discovery
- studio.py: Artifact creation with consolidated studio_create
- downloads.py: Artifact downloads with consolidated download_artifact
- chat.py: Query and conversation management
- exports.py: Export artifacts to Google Docs/Sheets
- notes.py: Note management (create, list, update, delete)
"""

import argparse
import logging
import os

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from notebooklm_tools import __version__

# Initialize MCP server
mcp = FastMCP(
    name="notebooklm",
    instructions="""NotebookLM MCP - Access NotebookLM (notebooklm.google.com).

**Auth:** If you get authentication errors, run `nlm login` via your Bash/terminal tool. This is the automated authentication method that handles everything. Only use save_auth_tokens as a fallback if the CLI fails.
**Account Switching:** To switch Google Accounts for the MCP server, run `nlm login switch <profile>` in Bash. The MCP server instantly uses the active default profile.
**Confirmation:** Tools with confirm param require user approval before setting confirm=True.
**Studio:** After creating audio/video/infographic/slides, poll studio_status for completion.

Consolidated tools:
- source_add(type=url|text|drive|file): Add any source type
- studio_create(type=audio|video|...): Create any artifact type
- studio_revise: Revise individual slides in an existing slide deck
- download_artifact(type=audio|video|...): Download any artifact type
- note_create/note_list/note_update/note_delete: Manage notes in notebooks""",
)

# MCP request/response logger
mcp_logger = logging.getLogger("notebooklm_tools.mcp")


# Health check endpoint
@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> JSONResponse:
    """Health check endpoint for load balancers and monitoring."""
    return JSONResponse({
        "status": "healthy",
        "service": "notebooklm-mcp",
        "version": __version__,
    })


def _register_tools():
    """Import and register all tools from the modular tools package."""
    from .tools._utils import register_all_tools
    
    # Import all tool modules to populate the registry
    from .tools import (  # noqa: F401
        downloads,
        auth,
        notebooks,
        sources,
        sharing,
        research,
        studio,
        chat,
        exports,
        notes,
    )
    
    # Register collected tools with mcp
    register_all_tools(mcp)


# Register tools on import
_register_tools()


def main():
    """Run the MCP server.
    
    Supports multiple transports:
    - stdio (default): For desktop apps like Claude Desktop
    - http: Streamable HTTP for network access
    - sse: Legacy SSE transport (backwards compatibility)
    """
    parser = argparse.ArgumentParser(
        description="NotebookLM MCP Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Environment Variables:
  NOTEBOOKLM_MCP_TRANSPORT     Transport type (stdio, http, sse)
  NOTEBOOKLM_MCP_HOST          Host to bind (default: 127.0.0.1)
  NOTEBOOKLM_MCP_PORT          Port to listen on (default: 8000)
  NOTEBOOKLM_MCP_PATH          MCP endpoint path (default: /mcp)
  NOTEBOOKLM_MCP_STATELESS     Enable stateless mode for scaling (true/false)
  NOTEBOOKLM_MCP_DEBUG         Enable debug logging (true/false)
  NOTEBOOKLM_HL                Interface language and default artifact language (default: en)
  NOTEBOOKLM_QUERY_TIMEOUT     Query timeout in seconds (default: 120.0)

Examples:
  notebooklm-mcp                              # Default stdio transport
  notebooklm-mcp --transport http             # HTTP on localhost:8000
  notebooklm-mcp --transport http --port 3000 # HTTP on custom port
  notebooklm-mcp --debug                      # Enable debug logging
        """
    )
    
    parser.add_argument(
        "--transport", "-t",
        choices=["stdio", "http", "sse"],
        default=os.environ.get("NOTEBOOKLM_MCP_TRANSPORT", "stdio"),
        help="Transport protocol (default: stdio)"
    )
    parser.add_argument(
        "--host", "-H",
        default=os.environ.get("NOTEBOOKLM_MCP_HOST", "127.0.0.1"),
        help="Host to bind for HTTP/SSE (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=int(os.environ.get("NOTEBOOKLM_MCP_PORT", "8000")),
        help="Port for HTTP/SSE transport (default: 8000)"
    )
    parser.add_argument(
        "--path",
        default=os.environ.get("NOTEBOOKLM_MCP_PATH", "/mcp"),
        help="MCP endpoint path for HTTP (default: /mcp)"
    )
    parser.add_argument(
        "--stateless",
        action="store_true",
        default=os.environ.get("NOTEBOOKLM_MCP_STATELESS", "").lower() == "true",
        help="Enable stateless mode for horizontal scaling"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        default=os.environ.get("NOTEBOOKLM_MCP_DEBUG", "").lower() == "true",
        help="Enable debug logging"
    )
    parser.add_argument(
        "--query-timeout",
        type=float,
        default=float(os.environ.get("NOTEBOOKLM_QUERY_TIMEOUT", "120.0")),
        help="Query timeout in seconds (default: 120.0)"
    )
    
    args = parser.parse_args()
    
    # Configure debug logging
    if args.debug:
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        mcp_logger.setLevel(logging.DEBUG)
        # Also enable core client logging
        logging.getLogger("notebooklm_tools.core").setLevel(logging.DEBUG)
    
    # Set query timeout
    from .tools._utils import set_query_timeout
    set_query_timeout(args.query_timeout)
    
    # Run server with appropriate transport
    # show_banner=False prevents Rich box-drawing output that can corrupt
    # the JSON-RPC protocol on Windows (especially with non-English locales)
    if args.transport == "stdio":
        mcp.run(show_banner=False)
    elif args.transport == "http":
        mcp.run(
            transport="streamable-http",
            host=args.host,
            port=args.port,
            path=args.path,
            stateless_http=args.stateless,
            show_banner=False,
        )
    elif args.transport == "sse":
        mcp.run(
            transport="sse",
            host=args.host,
            port=args.port,
            show_banner=False,
        )


if __name__ == "__main__":
    main()
