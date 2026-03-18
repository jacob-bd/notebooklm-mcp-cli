"""Research service — shared business logic for research start, poll, and import."""

from typing import TypedDict, Optional, Literal

from ..core.client import NotebookLMClient
from .errors import ValidationError, ServiceError

VALID_SOURCES = ("web", "drive")
VALID_MODES = ("fast", "deep")


class ResearchStartResult(TypedDict):
    """Result of starting a research task."""
    task_id: str
    notebook_id: str
    query: str
    source: str
    mode: str
    message: str


class ResearchStatusResult(TypedDict):
    """Result of polling research status."""
    status: str
    notebook_id: str
    task_id: Optional[str]
    sources_found: int
    sources: list
    report: str
    message: Optional[str]


class ResearchImportResult(TypedDict):
    """Result of importing research sources."""
    notebook_id: str
    imported_count: int
    imported_sources: list
    message: str


def start_research(
    client: NotebookLMClient,
    notebook_id: str,
    query: str,
    source: str = "web",
    mode: str = "fast",
) -> ResearchStartResult:
    """Start a research task to find new sources.

    Args:
        client: Authenticated NotebookLM client
        notebook_id: Notebook UUID
        query: What to search for
        source: "web" or "drive"
        mode: "fast" (~30s) or "deep" (~5min, web only)

    Returns:
        ResearchStartResult with task details

    Raises:
        ValidationError: If source, mode, or combination is invalid
        ServiceError: If the API call fails
    """
    if source not in VALID_SOURCES:
        raise ValidationError(
            f"Invalid source '{source}'. Must be one of: {', '.join(VALID_SOURCES)}",
        )

    if mode not in VALID_MODES:
        raise ValidationError(
            f"Invalid mode '{mode}'. Must be one of: {', '.join(VALID_MODES)}",
        )

    if mode == "deep" and source != "web":
        raise ValidationError(
            "Deep research mode is only available for web sources.",
            user_message="Deep research is web-only. Use --mode fast for Drive search.",
        )

    if not query or not query.strip():
        raise ValidationError(
            "Query is required for research.",
            user_message="Please provide a search query.",
        )

    try:
        result = client.start_research(
            notebook_id=notebook_id,
            query=query,
            source=source,
            mode=mode,
        )
    except Exception as e:
        raise ServiceError(f"Failed to start research: {e}")

    if result:
        return {
            "task_id": result.get("task_id", ""),
            "notebook_id": result.get("notebook_id", notebook_id),
            "query": query,
            "source": source,
            "mode": mode,
            "message": "Research started. Use research_status to check progress.",
        }

    raise ServiceError(
        "Research start returned no data",
        user_message="Failed to start research — no confirmation from API.",
    )


def poll_research(
    client: NotebookLMClient,
    notebook_id: str,
    task_id: Optional[str] = None,
    query: Optional[str] = None,
    compact: bool = True,
) -> ResearchStatusResult:
    """Poll research progress (single check).

    Args:
        client: Authenticated NotebookLM client
        notebook_id: Notebook UUID
        task_id: Specific task ID to poll
        query: Query text for fallback matching
        compact: Truncate report and limit sources

    Returns:
        ResearchStatusResult with current status

    Raises:
        ServiceError: If the poll fails
    """
    try:
        result = client.poll_research(
            notebook_id=notebook_id,
            target_task_id=task_id,
            target_query=query,
        )
    except Exception as e:
        raise ServiceError(f"Failed to poll research: {e}")

    if not result:
        return {
            "status": "no_research",
            "notebook_id": notebook_id,
            "task_id": None,
            "sources_found": 0,
            "sources": [],
            "report": "",
            "message": None,
        }

    sources = result.get("sources", [])
    report = result.get("report", "")

    if compact:
        if len(report) > 500:
            report = report[:500] + "...[truncated]"
        if len(sources) > 5:
            total = len(sources)
            sources = sources[:5]
            sources.append({"note": f"...and {total - 5} more sources"})

    status = result.get("status", "unknown")
    return {
        "status": status,
        "notebook_id": notebook_id,
        "task_id": result.get("task_id"),
        "sources_found": len(result.get("sources", [])),
        "sources": sources,
        "report": report,
        "message": "Use research_import to add sources to notebook." if status == "completed" else None,
    }


def import_research(
    client: NotebookLMClient,
    notebook_id: str,
    task_id: str,
    source_indices: Optional[list[int]] = None,
    timeout: float = 300.0,
) -> ResearchImportResult:
    """Import discovered sources from a completed research task.

    Args:
        client: Authenticated NotebookLM client
        notebook_id: Notebook UUID
        task_id: Research task ID
        source_indices: Indices of sources to import (default: all)
        timeout: HTTP timeout in seconds (default: 300s)

    Returns:
        ResearchImportResult

    Raises:
        ServiceError: If import fails or no sources available
    """
    try:
        research_result = client.poll_research(
            notebook_id=notebook_id,
            target_task_id=task_id,
        )
    except Exception as e:
        raise ServiceError(f"Failed to retrieve research results: {e}")

    if not research_result or research_result.get("status") == "no_research":
        raise ServiceError(
            "Research task not found or not completed.",
            user_message="Research task not found. Ensure the task has completed.",
        )

    all_sources = research_result.get("sources", [])
    if not all_sources:
        raise ServiceError(
            "No sources found in research results.",
            user_message="No sources were found in the research results.",
        )

    # Filter by indices if provided
    if source_indices is not None:
        sources_to_import = [
            all_sources[idx]
            for idx in source_indices
            if 0 <= idx < len(all_sources)
        ]
    else:
        sources_to_import = all_sources

    if not sources_to_import:
        raise ValidationError(
            "No valid source indices provided.",
            user_message="None of the specified indices matched available sources.",
        )

    try:
        result = client.import_research_sources(
            notebook_id=notebook_id,
            task_id=task_id,
            sources=sources_to_import,
            timeout=timeout,
        )
    except Exception as e:
        raise ServiceError(f"Failed to import sources: {e}")

    if result:
        return {
            "notebook_id": notebook_id,
            "imported_count": len(result),
            "imported_sources": result,
            "message": f"Imported {len(result)} sources.",
        }

    raise ServiceError(
        "Source import returned no data",
        user_message="Failed to import sources — no confirmation from API.",
    )
