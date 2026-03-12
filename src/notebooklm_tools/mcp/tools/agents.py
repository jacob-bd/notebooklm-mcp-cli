"""Agent tools - Registry, routing, and Claude API query bypass."""

from typing import Any, Optional
from ._utils import get_client, logged_tool
from ...services import agent_registry as registry_service
from ...services import agent_routing as routing_service
from ...services import agent as agent_service


@logged_tool()
def agent_registry_build(force: bool = False) -> dict[str, Any]:
    """Build or rebuild the agent registry by indexing all notebooks.

    Args:
        force: Rebuild even if registry already exists (default False)
    """
    try:
        client = get_client()
        result = registry_service.build_registry(client, force=force)
        return {"status": "success", **result}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@logged_tool()
def agent_registry_get(domain: str = "") -> dict[str, Any]:
    """Get the agent registry. Lists all notebooks with domains and keywords.

    Args:
        domain: Filter by domain (foreclosure, violations, discovery, etc.). Empty = all.
    """
    result = registry_service.get_registry(filter_domain=domain or None)
    return {"status": "success", **result}


@logged_tool()
def agent_registry_update(
    notebook_id: str,
    domain: str = "",
    keywords: list[str] = [],
) -> dict[str, Any]:
    """Update a single registry entry's domain or keywords manually.

    Args:
        notebook_id: Notebook UUID to update
        domain: New domain classification
        keywords: New keyword list
    """
    try:
        result = registry_service.update_registry_entry(
            notebook_id,
            domain=domain or None,
            keywords=keywords or None,
        )
        return {"status": "success", **result}
    except (ValueError, Exception) as e:
        return {"status": "error", "error": str(e)}


@logged_tool()
def notebook_agent_query(
    query: str,
    domain: str = "",
) -> dict[str, Any]:
    """Route a query to the best-matching notebook and return the AI answer.

    Checks case files first (instant local lookup). If no hit, routes to the
    best-matching notebook in the registry using keyword scoring.

    Args:
        query: Question to answer
        domain: Optionally restrict to a specific domain (foreclosure, violations, etc.)
    """
    try:
        client = get_client()
        result = routing_service.notebook_agent_query(
            client, query, domain_filter=domain or None
        )
        return {"status": "success", **result}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@logged_tool()
def notebook_agent_multi_query(
    query: str,
    top_k: int = 3,
    aggregate: bool = True,
    domain: str = "",
) -> dict[str, Any]:
    """Fan-out query to top_k matching notebooks in parallel, optionally synthesizing results.

    Args:
        query: Question to answer
        top_k: Number of notebooks to query (default 3)
        aggregate: Combine answers into a synthesis (default True)
        domain: Optionally restrict to a specific domain
    """
    try:
        client = get_client()
        result = routing_service.notebook_agent_multi_query(
            client, query, top_k=top_k, aggregate=aggregate, domain_filter=domain or None
        )
        return {"status": "success", **result}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@logged_tool()
def notebook_agent_query_claude(
    notebook_id: str,
    query: str,
    source_ids: list[str] = [],
) -> dict[str, Any]:
    """Query notebook sources via Claude API — bypasses NotebookLM AI entirely.

    Uses raw source text content + Claude API. No rate limits.
    Requires ANTHROPIC_API_KEY environment variable.

    Args:
        notebook_id: Notebook UUID
        query: Question to answer
        source_ids: Specific source IDs to use (empty = all sources)
    """
    try:
        client = get_client()
        result = agent_service.query_with_agent(
            client, notebook_id, query,
            source_ids=source_ids or None,
        )
        return {"status": "success", **result}
    except ImportError as e:
        return {"status": "error", "error": str(e), "hint": "Install anthropic: pip install anthropic"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@logged_tool()
def notebook_prefetch(notebook_id: str) -> dict[str, Any]:
    """Pre-warm source content cache for a notebook before heavy agent usage.

    Fetches all source text content in parallel and stores in SQLite cache.
    Run this once to make all subsequent queries instant.

    Args:
        notebook_id: Notebook UUID
    """
    try:
        client = get_client()
        result = agent_service.prefetch_notebook_sources(client, notebook_id)
        return {"status": "success", **result}
    except Exception as e:
        return {"status": "error", "error": str(e)}
