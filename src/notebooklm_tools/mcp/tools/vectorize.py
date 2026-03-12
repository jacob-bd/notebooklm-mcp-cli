"""Vectorize tools — semantic vector search over NotebookLM source content."""

from typing import Any, Optional
from ._utils import get_client, logged_tool
from ...services import vectorize as vec_service


@logged_tool()
def vector_index_source(
    source_id: str,
    notebook_id: str,
) -> dict[str, Any]:
    """Index a single NotebookLM source into Cloudflare Vectorize.

    Extracts source content, chunks it, generates embeddings via Cloudflare AI,
    and upserts vectors to the Vectorize index.

    Requires: CLOUDFLARE_API_TOKEN, CLOUDFLARE_ACCOUNT_ID env vars.

    Args:
        source_id: Source UUID
        notebook_id: Notebook UUID (for metadata filtering)
    """
    try:
        client = get_client()
        result = vec_service.index_source(client, source_id, notebook_id)
        return {"status": "success", **result}
    except ValueError as e:
        return {"status": "error", "error": str(e), "hint": "Set CLOUDFLARE_API_TOKEN and CLOUDFLARE_ACCOUNT_ID"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@logged_tool()
def vector_index_notebook(
    notebook_id: str,
    max_workers: int = 3,
) -> dict[str, Any]:
    """Index ALL sources in a notebook into Cloudflare Vectorize.

    Processes sources in parallel (up to max_workers concurrent). Uses cached
    source content to minimize NotebookLM API calls.

    Requires: CLOUDFLARE_API_TOKEN, CLOUDFLARE_ACCOUNT_ID env vars.

    Args:
        notebook_id: Notebook UUID
        max_workers: Max parallel indexing workers (default 3)
    """
    try:
        client = get_client()
        result = vec_service.index_notebook(client, notebook_id, max_workers=max_workers)
        return {"status": "success", **result}
    except ValueError as e:
        return {"status": "error", "error": str(e), "hint": "Set CLOUDFLARE_API_TOKEN and CLOUDFLARE_ACCOUNT_ID"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@logged_tool()
def vector_search(
    query: str,
    top_k: int = 10,
    notebook_id: str = "",
    answer: bool = False,
) -> dict[str, Any]:
    """Semantic vector search over indexed source content.

    Embeds the query via Cloudflare AI, searches the Vectorize index for
    nearest-neighbor chunks, and optionally answers using Claude API.

    Much faster than notebook_query for repeat/similar questions since content
    is pre-indexed (no NotebookLM AI rate limits).

    Requires: CLOUDFLARE_API_TOKEN, CLOUDFLARE_ACCOUNT_ID env vars.
    Optional: ANTHROPIC_API_KEY (for answer=True).

    Args:
        query: Natural language search query
        top_k: Number of matching chunks to return (default 10)
        notebook_id: Filter to specific notebook (empty = search all indexed content)
        answer: Use Claude API to synthesize an answer from retrieved chunks
    """
    try:
        result = vec_service.vector_search(
            query,
            top_k=top_k,
            notebook_id=notebook_id or None,
            answer_with_claude=answer,
        )
        return {"status": "success", **result}
    except ValueError as e:
        return {"status": "error", "error": str(e), "hint": "Set CLOUDFLARE_API_TOKEN and CLOUDFLARE_ACCOUNT_ID"}
    except Exception as e:
        return {"status": "error", "error": str(e)}
