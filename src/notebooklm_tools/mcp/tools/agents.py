"""Agent tools - Registry, routing, and Claude API query bypass."""

from typing import Any, Optional
from ._utils import get_client, logged_tool
from ...services import agent_registry as registry_service
from ...services import agent_routing as routing_service
from ...services import agent as agent_service
from ...services import gdoc_sync as gdoc_service


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
def agent_gdoc_check() -> dict[str, Any]:
    """Audit which notebooks have a designated GDoc linked and which don't.

    Shows coverage: linked notebooks (with agent instructions) vs unlinked.
    Use this before running agent queries to identify gaps.
    Rebuild the registry after linking new GDocs to pick up instructions.
    """
    try:
        result = registry_service.check_gdoc_coverage()
        return {"status": "success", **result}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@logged_tool()
def agent_gdoc_link(
    notebook_id: str,
    gdoc_id: str,
    source_id: str = "",
    gdoc_url: str = "",
) -> dict[str, Any]:
    """Link a designated Google Doc to a notebook for agent instructions and data.

    The GDoc is the single source of truth for this notebook's agent:
    - Its content feeds the notebook as a Drive source
    - Its '## AGENT INSTRUCTIONS' section drives agent persona and behavior
    - Agent findings are written back as notes, ready to be added to the GDoc

    GDoc structure (recommended):
      ## AGENT INSTRUCTIONS
      You are the [Title] agent. [Describe scope, persona, response style.]

      ## DATA
      [Facts, records, findings — updated by humans or copied from agent notes]

    After linking, run agent_registry_build(force=True) to load the instructions.
    Then call agent_gdoc_refresh_instructions to pull the latest instructions.

    Args:
        notebook_id: Notebook UUID
        gdoc_id: Google Doc ID (from the URL: /document/d/<gdoc_id>/edit)
        source_id: NotebookLM source ID for the GDoc (enables instruction loading)
        gdoc_url: Full GDoc URL (inferred if omitted)
    """
    try:
        result = gdoc_service.link_notebook_gdoc(
            notebook_id, gdoc_id, gdoc_url=gdoc_url, source_id=source_id
        )
        return {"status": "success", **result}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@logged_tool()
def agent_gdoc_refresh_instructions(notebook_id: str) -> dict[str, Any]:
    """Re-read agent instructions from the designated GDoc source and cache them.

    Call this after updating the '## AGENT INSTRUCTIONS' section of a GDoc.
    The instructions are cached in gdoc_links.json and loaded by the registry.

    Args:
        notebook_id: Notebook UUID
    """
    try:
        client = get_client()
        instructions = gdoc_service.read_gdoc_instructions(client, notebook_id)
        if instructions:
            return {
                "status": "success",
                "notebook_id": notebook_id,
                "instructions_chars": len(instructions),
                "instructions_preview": instructions[:200],
                "message": "Instructions loaded and cached. Run agent_registry_build(force=True) to apply.",
            }
        else:
            link = gdoc_service.get_gdoc_link(notebook_id)
            if not link:
                return {"status": "error", "error": "No GDoc linked to this notebook. Use agent_gdoc_link first."}
            if not link.get("source_id"):
                return {"status": "error", "error": "No source_id set. Provide the NotebookLM source ID for the GDoc when calling agent_gdoc_link."}
            return {"status": "success", "notebook_id": notebook_id, "message": "No '## AGENT INSTRUCTIONS' section found in GDoc. Add one to enable per-notebook agent behavior."}
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
