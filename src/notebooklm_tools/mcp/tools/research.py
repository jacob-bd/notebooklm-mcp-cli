"""Research tools - Deep research and source discovery."""

from typing import Any

from ._utils import get_client, logged_tool


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

        if source not in ("web", "drive"):
            return {
                "status": "error",
                "error": f"Invalid source '{source}'. Use: web, drive",
            }

        if mode not in ("fast", "deep"):
            return {
                "status": "error",
                "error": f"Invalid mode '{mode}'. Use: fast, deep",
            }

        result = client.start_research(
            notebook_id=notebook_id,
            query=query,
            source=source,
            mode=mode,
        )

        if result:
            return {
                "status": "success",
                "task_id": result.get("task_id"),
                "notebook_id": result.get("notebook_id"),
                "query": query,
                "source": source,
                "mode": mode,
                "message": f"Research started. Use research_status to check progress.",
            }
        return {"status": "error", "error": "Failed to start research"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@logged_tool()
def research_status(
    notebook_id: str,
    poll_interval: int = 30,
    max_wait: int = 300,
    compact: bool = True,
    task_id: str | None = None,
) -> dict[str, Any]:
    """Poll research progress. Blocks until complete or timeout.

    Args:
        notebook_id: Notebook UUID
        poll_interval: Seconds between polls (default: 30)
        max_wait: Max seconds to wait (default: 300, 0=single poll)
        compact: If True (default), truncate report and limit sources shown to save tokens.
                Use compact=False to get full details.
        task_id: Optional Task ID to poll for a specific research task.
    """
    try:
        client = get_client()
        # Note: client.poll_research only supports notebook_id and target_task_id
        # poll_interval and max_wait are documented but not implemented in client
        result = client.poll_research(
            notebook_id=notebook_id,
            target_task_id=task_id,
        )

        if result:
            sources = result.get("sources", [])
            report = result.get("report", "")

            # Compact mode: limit output
            if compact:
                if len(report) > 500:
                    report = report[:500] + "...[truncated]"
                if len(sources) > 5:
                    sources = sources[:5]
                    sources.append({"note": f"...and {len(result.get('sources', [])) - 5} more sources"})

            return {
                "status": result.get("status", "unknown"),
                "notebook_id": notebook_id,
                "task_id": result.get("task_id"),
                "sources_found": len(result.get("sources", [])),
                "sources": sources,
                "report": report,
                "message": "Use research_import to add sources to notebook." if result.get("status") == "completed" else None,
            }
        return {"status": "error", "error": "Failed to get research status"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@logged_tool()
def research_import(
    notebook_id: str,
    task_id: str,
    source_indices: list[int] | None = None,
) -> dict[str, Any]:
    """Import discovered sources into notebook.

    Call after research_status shows status="completed".

    Args:
        notebook_id: Notebook UUID
        task_id: Research task ID
        source_indices: Source indices to import (default: all)
    """
    try:
        client = get_client()
        
        # First poll for the research results to get the sources
        research_result = client.poll_research(
            notebook_id=notebook_id,
            target_task_id=task_id,
        )
        
        if not research_result or research_result.get("status") == "no_research":
            return {"status": "error", "error": "Research task not found or not completed"}
        
        all_sources = research_result.get("sources", [])
        if not all_sources:
            return {"status": "error", "error": "No sources found in research results"}
        
        # Filter by indices if provided
        if source_indices is not None:
            sources_to_import = []
            for idx in source_indices:
                if 0 <= idx < len(all_sources):
                    sources_to_import.append(all_sources[idx])
        else:
            sources_to_import = all_sources
        
        if not sources_to_import:
            return {"status": "error", "error": "No valid sources to import"}
        
        # Now call the client with the actual source dicts
        result = client.import_research_sources(
            notebook_id=notebook_id,
            task_id=task_id,
            sources=sources_to_import,
        )

        if result:
            return {
                "status": "success",
                "notebook_id": notebook_id,
                "imported_count": len(result),
                "imported_sources": result,
                "message": f"Imported {len(result)} sources.",
            }
        return {"status": "error", "error": "Failed to import sources"}
    except Exception as e:
        return {"status": "error", "error": str(e)}
