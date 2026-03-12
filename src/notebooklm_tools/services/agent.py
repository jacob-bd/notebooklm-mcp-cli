"""Agent service — bypass NotebookLM AI using raw source content + Claude API.

Use this when NotebookLM's rate limits (~50 queries/day) are exhausted.
Requires: pip install anthropic (or uv add anthropic)
Requires: ANTHROPIC_API_KEY environment variable
"""

from __future__ import annotations

import os
from typing import TypedDict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed


class AgentQueryResult(TypedDict):
    answer: str
    sources_used: list[str]
    source_titles: list[str]
    model: str
    tokens_used: int
    cached: bool


_SYSTEM_PROMPT = """\
You are answering questions using content extracted from a NotebookLM notebook.
Use ONLY the provided source documents. Cite source titles when relevant.
Be concise and accurate. If the answer is not in the sources, say so clearly."""


def query_with_agent(
    client,
    notebook_id: str,
    query: str,
    source_ids: Optional[list[str]] = None,
    model: str = "",
    max_sources: int = 0,
    max_chars_per_source: int = 0,
) -> AgentQueryResult:
    """Answer a query using raw source content + Claude API. No NotebookLM AI used.

    Args:
        client: Authenticated NotebookLMClient
        notebook_id: Notebook UUID
        query: Question to answer
        source_ids: Specific source IDs to use (None = all sources)
        model: Claude model ID (defaults to NOTEBOOKLM_AGENT_MODEL env var or claude-haiku-4-5-20251001)
        max_sources: Max sources to include (defaults to NOTEBOOKLM_AGENT_MAX_SOURCES or 20)
        max_chars_per_source: Max chars per source (defaults to NOTEBOOKLM_AGENT_MAX_CHARS or 50000)
    """
    try:
        import anthropic
    except ImportError:
        raise ImportError(
            "anthropic package required. Install with: pip install anthropic\n"
            "Or: uv add anthropic"
        )

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable is required.")

    effective_model = model or os.environ.get("NOTEBOOKLM_AGENT_MODEL", "claude-haiku-4-5-20251001")
    effective_max_sources = max_sources or int(os.environ.get("NOTEBOOKLM_AGENT_MAX_SOURCES", "20"))
    effective_max_chars = max_chars_per_source or int(os.environ.get("NOTEBOOKLM_AGENT_MAX_CHARS", "50000"))

    # Resolve source list from the notebook if not provided
    if source_ids is None:
        from .notebooks import get_notebook
        nb_detail = get_notebook(client, notebook_id, use_cache=True)
        sources_list = nb_detail.get("sources", [])
        source_ids = [s["id"] for s in sources_list if s.get("id")]

    source_ids = source_ids[:effective_max_sources]

    # Fetch source content in parallel (uses service cache)
    from .sources import get_source_content

    sources_context = []
    source_titles = []
    any_cached = True

    def fetch_one(sid: str) -> dict:
        try:
            return get_source_content(client, sid)
        except Exception as e:
            return {"source_id": sid, "title": sid, "content": "", "error": str(e)}

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(fetch_one, sid): sid for sid in source_ids}
        for future in as_completed(futures):
            r = future.result()
            if not r.get("cached", True):
                any_cached = False
            title = r.get("title", "Unknown")
            content = r.get("content", "")[:effective_max_chars]
            if content:
                sources_context.append(f"SOURCE: {title}\n{content}")
                source_titles.append(title)

    context_block = "\n\n---\n\n".join(sources_context)
    user_message = f"<sources>\n{context_block}\n</sources>\n\nQuestion: {query}"

    anthropic_client = anthropic.Anthropic(api_key=api_key)
    response = anthropic_client.messages.create(
        model=effective_model,
        max_tokens=4096,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    answer = response.content[0].text if response.content else ""
    tokens_used = response.usage.input_tokens + response.usage.output_tokens

    return {
        "answer": answer,
        "sources_used": source_ids,
        "source_titles": source_titles,
        "model": effective_model,
        "tokens_used": tokens_used,
        "cached": any_cached,
    }


def prefetch_notebook_sources(
    client,
    notebook_id: str,
    max_workers: int = 5,
) -> dict:
    """Pre-warm the source content cache for a notebook.

    Run this once before heavy agent usage to make all subsequent queries instant.
    """
    from .notebooks import get_notebook
    from .sources import get_source_content

    nb_detail = get_notebook(client, notebook_id, use_cache=True)
    sources_list = nb_detail.get("sources", [])
    source_ids = [s["id"] for s in sources_list if s.get("id")]

    results = []
    errors = []

    def fetch_one(sid: str) -> dict:
        try:
            r = get_source_content(client, sid)
            return {"source_id": sid, "chars": r.get("char_count", 0), "success": True, "cached": r.get("cached", False)}
        except Exception as e:
            return {"source_id": sid, "error": str(e), "success": False}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fetch_one, sid): sid for sid in source_ids}
        for future in as_completed(futures):
            r = future.result()
            if r.get("success"):
                results.append(r)
            else:
                errors.append(r)

    total_chars = sum(r.get("chars", 0) for r in results)
    return {
        "notebook_id": notebook_id,
        "prefetched": len(results),
        "failed": len(errors),
        "total_chars": total_chars,
        "errors": errors,
    }
