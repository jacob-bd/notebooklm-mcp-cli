"""Research tools - Deep research and source discovery."""

from typing import Any

from ._utils import get_client, logged_tool
from ...services import research as research_service, ServiceError


@logged_tool()
def research_start(
    query: str,
    source: str = "web",
    mode: str = "fast",
    notebook_id: str | None = None,
    title: str | None = None,
) -> dict[str, Any]:
    """Deep research / fast research: Search web or Google Drive to FIND NEW sources.

    Use this for: "deep research on X", "find sources about Y", "search web for Z", "search Drive".
    Workflow: research_start -> poll research_status -> research_import.

    Args:
        query: What to search for (e.g. "quantum computing advances")
        source: web|drive (where to search)
        mode: fast (~30s, ~10 sources) | deep (~5min, ~40 sources, web only)
        notebook_id: Existing notebook (creates new if not provided)
        title: Title for new notebook
    """
    try:
        client = get_client()
        result = research_service.start_research(
            client, notebook_id, query,
            source=source, mode=mode,
        )
        return {"status": "success", **result}
    except ServiceError as e:
        return {"status": "error", "error": e.user_message}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@logged_tool()
def research_status(
    notebook_id: str,
    poll_interval: int = 30,
    max_wait: int = 300,
    compact: bool = True,
    task_id: str | None = None,
    query: str | None = None,
) -> dict[str, Any]:
    """Poll research progress. Blocks until complete or timeout.

    Args:
        notebook_id: Notebook UUID
        poll_interval: Seconds between polls (default: 30)
        max_wait: Max seconds to wait (default: 300, 0=single poll)
        compact: If True (default), truncate report and limit sources shown to save tokens.
                Use compact=False to get full details.
        task_id: Optional Task ID to poll for a specific research task.
        query: Optional query text for fallback matching when task_id changes (deep research).
            Contributed by @saitrogen (PR #15).
    """
    try:
        client = get_client()
        result = research_service.poll_research(
            client, notebook_id,
            task_id=task_id,
            query=query,
            compact=compact,
        )
        return result
    except ServiceError as e:
        return {"status": "error", "error": e.user_message}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@logged_tool()
def research_import(
    notebook_id: str,
    task_id: str,
    source_indices: list[int] | None = None,
    timeout: float = 300.0,
) -> dict[str, Any]:
    """Import discovered sources into notebook.

    Call after research_status shows status="completed".

    Args:
        notebook_id: Notebook UUID
        task_id: Research task ID
        source_indices: Source indices to import (default: all)
        timeout: Import timeout in seconds (default: 300, increase for large notebooks)
    """
    try:
        client = get_client()
        result = research_service.import_research(
            client, notebook_id, task_id,
            source_indices=source_indices,
            timeout=timeout,
        )
        return {"status": "success", **result}
    except ServiceError as e:
        return {"status": "error", "error": e.user_message}
    except Exception as e:
        return {"status": "error", "error": str(e)}
