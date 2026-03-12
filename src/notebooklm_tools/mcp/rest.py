"""REST API routes for NotebookLM MCP server.

Provides standard REST endpoints alongside the MCP protocol,
allowing any HTTP client to interact with the service directly.

All responses: {"data": ..., "error": null} or {"data": null, "error": "message"}

Routes:
  GET  /api/notebooks                    — list notebooks
  GET  /api/notebooks/{id}               — get notebook details
  GET  /api/notebooks/{id}/sources       — list sources
  GET  /api/notebooks/{id}/summary       — AI summary
  POST /api/notebooks/{id}/query         — query notebook (NLM AI or Claude API)
  GET  /api/cache                        — list cache entries
  DELETE /api/cache                      — clear all cache
  DELETE /api/cache/{key}                — clear by key prefix
  GET  /api/case-files                   — list case files
  GET  /api/case-files/search            — search case files (?q=keyword)
  POST /api/vector/search                — semantic vector search
  GET  /api/registry                     — agent registry
"""

from __future__ import annotations

from starlette.requests import Request
from starlette.responses import JSONResponse


def _ok(data) -> JSONResponse:
    return JSONResponse({"data": data, "error": None})


def _err(message: str, status_code: int = 400) -> JSONResponse:
    return JSONResponse({"data": None, "error": message}, status_code=status_code)


def _get_client():
    from .tools._utils import get_client
    return get_client()


def register_rest_routes(mcp) -> None:
    """Register all REST API routes with the FastMCP instance."""

    # ------------------------------------------------------------------
    # Notebooks
    # ------------------------------------------------------------------

    @mcp.custom_route("/api/notebooks", methods=["GET"])
    async def api_notebooks_list(request: Request) -> JSONResponse:
        """List all notebooks."""
        try:
            from ..services.notebooks import list_notebooks
            client = _get_client()
            use_cache = request.query_params.get("cache", "true").lower() != "false"
            max_results = int(request.query_params.get("max", "100"))
            result = list_notebooks(client, max_results=max_results, use_cache=use_cache)
            return _ok(result)
        except Exception as e:
            return _err(str(e), 500)

    @mcp.custom_route("/api/notebooks/{notebook_id}", methods=["GET"])
    async def api_notebook_get(request: Request) -> JSONResponse:
        """Get notebook details."""
        try:
            from ..services.notebooks import get_notebook
            client = _get_client()
            notebook_id = request.path_params["notebook_id"]
            result = get_notebook(client, notebook_id)
            return _ok(result)
        except Exception as e:
            return _err(str(e), 500)

    @mcp.custom_route("/api/notebooks/{notebook_id}/summary", methods=["GET"])
    async def api_notebook_summary(request: Request) -> JSONResponse:
        """Get AI-generated notebook summary."""
        try:
            from ..services.notebooks import describe_notebook
            client = _get_client()
            notebook_id = request.path_params["notebook_id"]
            result = describe_notebook(client, notebook_id)
            return _ok(result)
        except Exception as e:
            return _err(str(e), 500)

    @mcp.custom_route("/api/notebooks/{notebook_id}/query", methods=["POST"])
    async def api_notebook_query(request: Request) -> JSONResponse:
        """Query a notebook.

        Body: {"query": "...", "source_ids": [...], "use_agent": false}
        - use_agent=false (default): NotebookLM AI (rate-limited ~50/day)
        - use_agent=true: Claude API bypass (requires ANTHROPIC_API_KEY, unlimited)
        """
        try:
            body = await request.json()
            query = body.get("query", "")
            if not query:
                return _err("'query' field is required")

            notebook_id = request.path_params["notebook_id"]
            use_agent = body.get("use_agent", False)
            source_ids = body.get("source_ids") or None

            client = _get_client()

            if use_agent:
                from ..services.agent import query_with_agent
                result = query_with_agent(client, notebook_id, query, source_ids=source_ids)
            else:
                from ..services.chat import query_notebook
                answer = query_notebook(client, notebook_id, query)
                result = {"answer": answer, "notebook_id": notebook_id}

            return _ok(result)
        except Exception as e:
            return _err(str(e), 500)

    # ------------------------------------------------------------------
    # Cache
    # ------------------------------------------------------------------

    @mcp.custom_route("/api/cache", methods=["GET"])
    async def api_cache_list(request: Request) -> JSONResponse:
        """List all cache entries."""
        try:
            from ..utils.cache import get_cache
            entries = get_cache().list_entries()
            return _ok({"entries": entries, "count": len(entries)})
        except Exception as e:
            return _err(str(e), 500)

    @mcp.custom_route("/api/cache", methods=["DELETE"])
    async def api_cache_clear_all(request: Request) -> JSONResponse:
        """Clear all cache entries."""
        try:
            from ..utils.cache import get_cache
            get_cache().clear_all()
            return _ok({"cleared": "all"})
        except Exception as e:
            return _err(str(e), 500)

    @mcp.custom_route("/api/cache/{key:path}", methods=["DELETE"])
    async def api_cache_clear_key(request: Request) -> JSONResponse:
        """Clear cache entries by key prefix."""
        try:
            from ..utils.cache import get_cache
            key = request.path_params["key"]
            get_cache().invalidate(key)
            return _ok({"cleared": key})
        except Exception as e:
            return _err(str(e), 500)

    # ------------------------------------------------------------------
    # Case Files
    # ------------------------------------------------------------------

    @mcp.custom_route("/api/case-files", methods=["GET"])
    async def api_case_files_list(request: Request) -> JSONResponse:
        """List case files."""
        try:
            from ..services.case_files import case_file_list
            category = request.query_params.get("category") or None
            result = case_file_list(category=category)
            return _ok(result)
        except Exception as e:
            return _err(str(e), 500)

    @mcp.custom_route("/api/case-files/search", methods=["GET"])
    async def api_case_files_search(request: Request) -> JSONResponse:
        """Search case files by keyword (?q=term)."""
        try:
            from ..services.case_files import case_file_search
            query = request.query_params.get("q", "")
            if not query:
                return _err("'q' query parameter is required")
            result = case_file_search(query)
            return _ok(result)
        except Exception as e:
            return _err(str(e), 500)

    @mcp.custom_route("/api/case-files/{key:path}", methods=["GET"])
    async def api_case_file_get(request: Request) -> JSONResponse:
        """Get a case file by key (e.g. /api/case-files/evidence/INDEX.md)."""
        try:
            from ..services.case_files import case_file_get
            key = request.path_params["key"]
            result = case_file_get(key=key)
            return _ok(result)
        except FileNotFoundError as e:
            return _err(str(e), 404)
        except Exception as e:
            return _err(str(e), 500)

    # ------------------------------------------------------------------
    # Vector Search
    # ------------------------------------------------------------------

    @mcp.custom_route("/api/vector/search", methods=["POST"])
    async def api_vector_search(request: Request) -> JSONResponse:
        """Semantic vector search over indexed sources.

        Body: {"query": "...", "top_k": 10, "notebook_id": "...", "answer": false}
        Requires: CLOUDFLARE_API_TOKEN, CLOUDFLARE_ACCOUNT_ID
        """
        try:
            from ..services.vectorize import vector_search
            body = await request.json()
            query = body.get("query", "")
            if not query:
                return _err("'query' field is required")
            result = vector_search(
                query,
                top_k=body.get("top_k", 10),
                notebook_id=body.get("notebook_id") or None,
                answer_with_claude=body.get("answer", False),
            )
            return _ok(result)
        except ValueError as e:
            return _err(str(e), 400)
        except Exception as e:
            return _err(str(e), 500)

    # ------------------------------------------------------------------
    # Agent Registry
    # ------------------------------------------------------------------

    @mcp.custom_route("/api/registry", methods=["GET"])
    async def api_registry_get(request: Request) -> JSONResponse:
        """Get the agent registry."""
        try:
            from ..services.agent_registry import get_registry
            domain = request.query_params.get("domain") or None
            result = get_registry(filter_domain=domain)
            return _ok(result)
        except Exception as e:
            return _err(str(e), 500)

    # ------------------------------------------------------------------
    # GDoc Sync
    # ------------------------------------------------------------------

    @mcp.custom_route("/api/gdoc-links", methods=["GET"])
    async def api_gdoc_list(request: Request) -> JSONResponse:
        """List all notebook↔GDoc links."""
        try:
            from ..services.gdoc_sync import list_gdoc_links
            result = list_gdoc_links()
            return _ok(result)
        except Exception as e:
            return _err(str(e), 500)

    @mcp.custom_route("/api/gdoc-links/{notebook_id}/sync", methods=["POST"])
    async def api_gdoc_sync(request: Request) -> JSONResponse:
        """Sync a notebook to its linked GDoc."""
        try:
            from ..services.gdoc_sync import sync_notebook_to_gdoc
            notebook_id = request.path_params["notebook_id"]
            client = _get_client()
            result = sync_notebook_to_gdoc(client, notebook_id)
            return _ok(result)
        except ValueError as e:
            return _err(str(e), 404)
        except Exception as e:
            return _err(str(e), 500)
