"""Notebooks service — shared business logic for notebook CRUD and metadata operations."""

from typing import TypedDict, Optional

from ..core.client import NotebookLMClient
from ..utils.cache import get_cache, TTL
from .errors import ValidationError, ServiceError, NotFoundError, CreationError


class NotebookInfo(TypedDict):
    """Notebook summary info."""
    id: str
    title: str
    source_count: int
    url: str
    ownership: str
    is_shared: bool
    created_at: Optional[str]
    modified_at: Optional[str]


class NotebookListResult(TypedDict):
    """Result of listing notebooks."""
    notebooks: list[NotebookInfo]
    count: int
    owned_count: int
    shared_count: int
    shared_by_me_count: int


class SourceInfo(TypedDict):
    """Source summary in notebook details."""
    id: str
    title: str


class NotebookDetailResult(TypedDict):
    """Result of getting a single notebook's details."""
    notebook_id: str
    title: str
    source_count: int
    url: str
    sources: list[SourceInfo]


class NotebookSummaryResult(TypedDict):
    """Result of AI-generated notebook summary."""
    summary: str
    suggested_topics: list[str]


class NotebookCreateResult(TypedDict):
    """Result of creating a notebook."""
    notebook_id: str
    title: str
    url: str
    message: str


class NotebookRenameResult(TypedDict):
    """Result of renaming a notebook."""
    notebook_id: str
    new_title: str
    message: str


class NotebookDeleteResult(TypedDict):
    """Result of deleting a notebook."""
    message: str


def list_notebooks(
    client: NotebookLMClient,
    max_results: int = 100,
    use_cache: bool = True,
) -> NotebookListResult:
    """List all notebooks.

    Args:
        client: Authenticated NotebookLM client
        max_results: Maximum notebooks to return
        use_cache: Whether to return cached data (default True)

    Returns:
        NotebookListResult with notebooks and counts

    Raises:
        ServiceError: If listing fails
    """
    cache = get_cache()
    cache_key = "notebook_list"
    if use_cache:
        cached = cache.get(cache_key)
        if cached is not None:
            # Apply max_results to cached result
            if max_results < len(cached.get("notebooks", [])):
                cached = dict(cached)
                cached["notebooks"] = cached["notebooks"][:max_results]
            return cached

    try:
        notebooks = client.list_notebooks()
    except Exception as e:
        raise ServiceError(f"Failed to list notebooks: {e}")

    owned_count = sum(1 for nb in notebooks if nb.is_owned)
    shared_count = len(notebooks) - owned_count
    shared_by_me_count = sum(1 for nb in notebooks if nb.is_owned and nb.is_shared)

    result: NotebookListResult = {
        "notebooks": [
            {
                "id": nb.id,
                "title": nb.title,
                "source_count": nb.source_count,
                "url": nb.url,
                "ownership": nb.ownership,
                "is_shared": nb.is_shared,
                "created_at": nb.created_at,
                "modified_at": nb.modified_at,
            }
            for nb in notebooks
        ],
        "count": len(notebooks),
        "owned_count": owned_count,
        "shared_count": shared_count,
        "shared_by_me_count": shared_by_me_count,
    }
    cache.set(cache_key, result, TTL["notebook_list"])
    # Apply max_results after caching full list
    if max_results < len(result["notebooks"]):
        result = dict(result)  # type: ignore[assignment]
        result["notebooks"] = result["notebooks"][:max_results]
    return result


def get_notebook(
    client: NotebookLMClient,
    notebook_id: str,
    use_cache: bool = True,
) -> NotebookDetailResult:
    """Get notebook details including source list.

    Handles raw RPC list responses from the API, normalising them into a
    clean typed dict.

    Args:
        client: Authenticated NotebookLM client
        notebook_id: Notebook UUID

    Returns:
        NotebookDetailResult with title, sources, etc.

    Raises:
        NotFoundError: If notebook not found
        ServiceError: If the API call fails
    """
    cache = get_cache()
    cache_key = f"notebook:{notebook_id}"
    if use_cache:
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

    try:
        nb = client.get_notebook(notebook_id)
    except Exception as e:
        raise ServiceError(f"Failed to get notebook: {e}")

    if not nb:
        raise NotFoundError(
            f"Notebook {notebook_id} not found",
            user_message=f"Notebook {notebook_id} not found.",
        )

    # The client may return raw RPC data (nested list) instead of a Notebook object.
    # Normalise that into a consistent result.
    if isinstance(nb, list):
        data = nb[0] if nb and isinstance(nb[0], list) else nb
        if isinstance(data, list) and len(data) >= 3:
            title = data[0] if isinstance(data[0], str) else "Untitled"
            sources_data = data[1] if len(data) > 1 and isinstance(data[1], list) else []
            nb_id = data[2] if len(data) > 2 else notebook_id

            sources: list[SourceInfo] = []
            for src in sources_data:
                if isinstance(src, list) and len(src) >= 2:
                    src_id = src[0][0] if isinstance(src[0], list) and src[0] else src[0]
                    src_title = src[1] if len(src) > 1 else "Untitled"
                    sources.append({"id": src_id, "title": src_title})

            detail: NotebookDetailResult = {
                "notebook_id": nb_id,
                "title": title,
                "source_count": len(sources),
                "url": f"https://notebooklm.google.com/notebook/{nb_id}",
                "sources": sources,
            }
            cache.set(cache_key, detail, TTL["notebook"])
            return detail

    # Fallback: if nb is a dataclass-like object with attrs (e.g. from list_notebooks)
    if hasattr(nb, "id"):
        detail = {
            "notebook_id": nb.id,
            "title": getattr(nb, "title", "Untitled"),
            "source_count": getattr(nb, "source_count", 0),
            "url": getattr(nb, "url", f"https://notebooklm.google.com/notebook/{nb.id}"),
            "sources": [],
        }
        cache.set(cache_key, detail, TTL["notebook"])
        return detail

    # Last-resort fallback
    raise ServiceError(
        f"Unexpected notebook data format: {str(nb)[:200]}",
        user_message="Received unexpected data format from the API.",
    )


def describe_notebook(
    client: NotebookLMClient,
    notebook_id: str,
    use_cache: bool = True,
) -> NotebookSummaryResult:
    """Get AI-generated notebook summary with suggested topics.

    Args:
        client: Authenticated NotebookLM client
        notebook_id: Notebook UUID
        use_cache: Whether to return cached summary (default True, 24hr TTL)

    Returns:
        NotebookSummaryResult with summary and topics

    Raises:
        ServiceError: If the summary call fails
    """
    cache = get_cache()
    cache_key = f"notebook_summary:{notebook_id}"
    if use_cache:
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

    try:
        result = client.get_notebook_summary(notebook_id)
    except Exception as e:
        raise ServiceError(f"Failed to get notebook summary: {e}")

    if result:
        summary_result: NotebookSummaryResult = {
            "summary": result.get("summary", ""),
            "suggested_topics": result.get("suggested_topics", []),
        }
        cache.set(cache_key, summary_result, TTL["notebook_summary"])
        return summary_result

    raise ServiceError(
        "Notebook summary returned no data",
        user_message="Failed to get notebook summary — no data returned.",
    )


def create_notebook(
    client: NotebookLMClient,
    title: str = "",
) -> NotebookCreateResult:
    """Create a new notebook.

    Args:
        client: Authenticated NotebookLM client
        title: Notebook title (optional)

    Returns:
        NotebookCreateResult with notebook ID and URL

    Raises:
        CreationError: If creation fails
    """
    try:
        nb = client.create_notebook(title)
    except Exception as e:
        raise CreationError(f"Failed to create notebook: {e}")

    if nb and hasattr(nb, "id"):
        get_cache().invalidate("notebook_list")  # list is now stale
        return {
            "notebook_id": nb.id,
            "title": nb.title,
            "url": nb.url,
            "message": f"Created notebook: {nb.title}",
        }

    raise CreationError(
        "Notebook creation returned no data",
        user_message="Failed to create notebook — no confirmation from API.",
    )


def rename_notebook(
    client: NotebookLMClient,
    notebook_id: str,
    new_title: str,
) -> NotebookRenameResult:
    """Rename a notebook.

    Args:
        client: Authenticated NotebookLM client
        notebook_id: Notebook UUID
        new_title: New title

    Returns:
        NotebookRenameResult

    Raises:
        ValidationError: If title is empty
        ServiceError: If rename fails
    """
    if not new_title or not new_title.strip():
        raise ValidationError(
            "New title is required.",
            user_message="Notebook title cannot be empty.",
        )

    try:
        result = client.rename_notebook(notebook_id, new_title)
    except Exception as e:
        raise ServiceError(f"Failed to rename notebook: {e}")

    if result:
        cache = get_cache()
        cache.invalidate("notebook_list")
        cache.invalidate(f"notebook:{notebook_id}")
        cache.invalidate(f"notebook_summary:{notebook_id}")
        return {
            "notebook_id": notebook_id,
            "new_title": new_title,
            "message": f"Renamed notebook to: {new_title}",
        }

    raise ServiceError(
        "Rename returned falsy result",
        user_message="Rename may have failed — no confirmation from API.",
    )


def delete_notebook(
    client: NotebookLMClient,
    notebook_id: str,
) -> NotebookDeleteResult:
    """Delete a notebook permanently.

    Args:
        client: Authenticated NotebookLM client
        notebook_id: Notebook UUID

    Returns:
        NotebookDeleteResult

    Raises:
        ServiceError: If deletion fails
    """
    try:
        result = client.delete_notebook(notebook_id)
    except Exception as e:
        raise ServiceError(f"Failed to delete notebook: {e}")

    if result:
        cache = get_cache()
        cache.invalidate("notebook_list")
        cache.invalidate(f"notebook:{notebook_id}")
        cache.invalidate(f"notebook_summary:{notebook_id}")
        return {
            "message": f"Notebook {notebook_id} has been permanently deleted.",
        }

    raise ServiceError(
        "Notebook deletion returned falsy result",
        user_message="Failed to delete notebook — no confirmation from API.",
    )
