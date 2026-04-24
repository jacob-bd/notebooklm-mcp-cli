"""Chat service — shared business logic for notebook querying and chat configuration."""

import logging
import threading
import time
import uuid
from typing import Any, cast

from ..core.client import NotebookLMClient
from ..core.conversation import QueryRejectedError
from . import notebooks as notebook_service
from ._compat import TypedDict
from .errors import ServiceError, ValidationError

logger = logging.getLogger(__name__)

VALID_GOALS = ("default", "learning_guide", "custom")
VALID_RESPONSE_LENGTHS = ("default", "longer", "shorter")
MAX_PROMPT_LENGTH = 10_000


class QueryResult(TypedDict):
    """Result of a notebook query."""

    answer: str
    conversation_id: str | None
    sources_used: list[Any]
    citations: dict[str, Any]
    references: list[dict[str, Any]]


class PendingQueryState(TypedDict):
    """Tracked state for an async query."""

    status: str
    result: QueryResult | None
    error: str | None
    created_at: float


# --- Async query state management ---
_QUERY_TTL_SECONDS = 600  # 10 minutes
_pending_queries: dict[str, PendingQueryState] = {}
_pending_lock = threading.Lock()


class ConfigureResult(TypedDict):
    """Result of configuring chat settings."""

    notebook_id: str
    goal: str
    response_length: str
    message: str


def query(
    client: NotebookLMClient,
    notebook_id: str,
    query_text: str,
    source_ids: list[str] | None = None,
    conversation_id: str | None = None,
    timeout: float | None = None,
) -> QueryResult:
    """Query a notebook's sources with AI.

    Args:
        client: Authenticated NotebookLM client
        notebook_id: Notebook UUID
        query_text: Question to ask
        source_ids: Source IDs to query (default: all)
        conversation_id: For follow-up questions
        timeout: Request timeout in seconds

    Returns:
        QueryResult with answer, conversation_id, and sources_used

    Raises:
        ValidationError: If query is empty
        ServiceError: If the query fails
    """
    if not query_text or not query_text.strip():
        raise ValidationError(
            "Query text is required.",
            user_message="Please provide a question to ask.",
        )

    # Validate notebook has sources
    if not source_ids:
        # We only check if we target the whole notebook
        try:
            nb = notebook_service.get_notebook(client, notebook_id)
            if nb["source_count"] == 0:
                raise ValidationError(
                    "Cannot query an empty notebook.",
                    user_message="This notebook has no sources to query. Add a source first using 'nlm source add' or 'nlm research start'.",
                )
        except ValidationError:
            raise
        except Exception:
            pass  # Suppress failure to fetch notebook details; let query try anyway

    try:
        result = client.query(
            notebook_id=notebook_id,
            query_text=query_text,
            source_ids=source_ids,
            conversation_id=conversation_id,
            **({"timeout": cast(float, timeout)} if timeout is not None else {}),
        )
    except QueryRejectedError as e:
        raise ServiceError(
            f"Query failed: {e}",
            user_message=(
                f"{e}. This may indicate account-level restrictions on "
                "programmatic access. Try re-authenticating with 'nlm login' "
                "or using a different account."
            ),
        ) from e
    except Exception as e:
        raise ServiceError(f"Query failed: {e}") from e

    if result:
        return {
            "answer": result.get("answer", ""),
            "conversation_id": result.get("conversation_id"),
            "sources_used": result.get("sources_used", []),
            "citations": result.get("citations", {}),
            "references": result.get("references", []),
        }

    raise ServiceError(
        "Query returned empty result",
        user_message="Failed to get a response from the notebook.",
    )


def configure_chat(
    client: NotebookLMClient,
    notebook_id: str,
    goal: str = "default",
    custom_prompt: str | None = None,
    response_length: str = "default",
) -> ConfigureResult:
    """Configure notebook chat settings.

    Args:
        client: Authenticated NotebookLM client
        notebook_id: Notebook UUID
        goal: default, learning_guide, or custom
        custom_prompt: Required when goal=custom (max 10000 chars)
        response_length: default, longer, or shorter

    Returns:
        ConfigureResult with updated settings

    Raises:
        ValidationError: If goal, response_length, or prompt is invalid
        ServiceError: If configuration fails
    """
    if goal not in VALID_GOALS:
        raise ValidationError(
            f"Invalid goal '{goal}'. Must be one of: {', '.join(VALID_GOALS)}",
        )

    if goal == "custom" and not custom_prompt:
        raise ValidationError(
            "Custom prompt is required when goal is 'custom'.",
            user_message="--prompt is required when goal is 'custom'.",
        )

    if custom_prompt and len(custom_prompt) > MAX_PROMPT_LENGTH:
        raise ValidationError(
            f"Custom prompt exceeds {MAX_PROMPT_LENGTH} character limit ({len(custom_prompt)} chars).",
            user_message=f"Custom prompt must be {MAX_PROMPT_LENGTH} characters or less.",
        )

    if response_length not in VALID_RESPONSE_LENGTHS:
        raise ValidationError(
            f"Invalid response_length '{response_length}'. Must be one of: {', '.join(VALID_RESPONSE_LENGTHS)}",
        )

    try:
        result = client.configure_chat(
            notebook_id=notebook_id,
            goal=goal,
            custom_prompt=custom_prompt,
            response_length=response_length,
        )
    except Exception as e:
        raise ServiceError(f"Failed to configure chat: {e}") from e

    if result:
        return {
            "notebook_id": notebook_id,
            "goal": goal,
            "response_length": response_length,
            "message": "Chat settings updated.",
        }

    raise ServiceError(
        "Chat configuration returned falsy result",
        user_message="Failed to configure chat — no confirmation from API.",
    )


class DeleteChatHistoryResult(TypedDict):
    """Result of deleting chat history."""

    notebook_id: str
    message: str


def delete_chat_history(
    client: NotebookLMClient,
    notebook_id: str,
) -> DeleteChatHistoryResult:
    """Delete the chat history for a notebook.

    Fetches the notebook's persistent conversation ID, then deletes
    the associated chat history from the server.

    Args:
        client: Authenticated NotebookLM client
        notebook_id: Notebook UUID

    Returns:
        DeleteChatHistoryResult with confirmation message

    Raises:
        ServiceError: If no chat history exists or deletion fails
    """
    conv_id = client.get_conversation_id(notebook_id)
    if not conv_id:
        raise ServiceError(
            "No chat history found for this notebook.",
            user_message="This notebook has no chat history to delete.",
        )

    try:
        client.delete_chat_history(notebook_id, conv_id)
    except Exception as e:
        raise ServiceError(f"Failed to delete chat history: {e}") from e

    return {
        "notebook_id": notebook_id,
        "message": "Chat history deleted.",
    }


# --- Async query polling ---


class QueryStartResult(TypedDict):
    """Result of starting an async query."""

    query_id: str
    status: str
    message: str


class QueryStatusResult(TypedDict):
    """Result of polling an async query."""

    query_id: str
    status: str
    result: QueryResult | None
    error: str | None


def _cleanup_expired_queries() -> None:
    """Remove entries older than _QUERY_TTL_SECONDS. Must be called with _pending_lock held."""
    now = time.monotonic()
    expired = [
        qid
        for qid, entry in _pending_queries.items()
        if now - entry["created_at"] > _QUERY_TTL_SECONDS
    ]
    for qid in expired:
        logger.debug("Evicting expired async query %s", qid)
        del _pending_queries[qid]


def _run_query_in_background(
    query_id: str,
    client: NotebookLMClient,
    notebook_id: str,
    query_text: str,
    source_ids: list[str] | None,
    conversation_id: str | None,
    timeout: float | None,
) -> None:
    """Background thread target that executes the query and stores the result."""
    try:
        result = query(
            client,
            notebook_id,
            query_text,
            source_ids=source_ids,
            conversation_id=conversation_id,
            timeout=timeout,
        )
        with _pending_lock:
            if query_id in _pending_queries:
                _pending_queries[query_id]["status"] = "completed"
                _pending_queries[query_id]["result"] = result
    except Exception as e:
        with _pending_lock:
            if query_id in _pending_queries:
                _pending_queries[query_id]["status"] = "error"
                _pending_queries[query_id]["error"] = str(e)


def query_start(
    client: NotebookLMClient,
    notebook_id: str,
    query_text: str,
    source_ids: list[str] | None = None,
    conversation_id: str | None = None,
    timeout: float | None = None,
) -> QueryStartResult:
    """Start a notebook query in a background thread for async polling.

    Returns immediately with a query_id. Use query_status() to poll for the result.
    This avoids MCP client timeouts on large notebooks where Google's response
    takes longer than the client allows.

    Args:
        client: Authenticated NotebookLM client
        notebook_id: Notebook UUID
        query_text: Question to ask
        source_ids: Source IDs to query (default: all)
        conversation_id: For follow-up questions
        timeout: Request timeout in seconds

    Returns:
        QueryStartResult with query_id and initial status

    Raises:
        ValidationError: If query text is empty
    """
    if not query_text or not query_text.strip():
        raise ValidationError(
            "Query text is required.",
            user_message="Please provide a question to ask.",
        )

    # Validate notebook has sources
    if not source_ids:
        try:
            nb = notebook_service.get_notebook(client, notebook_id)
            if nb["source_count"] == 0:
                raise ValidationError(
                    "Cannot query an empty notebook.",
                    user_message="This notebook has no sources to query. Add a source first using 'nlm source add' or 'nlm research start'.",
                )
        except ValidationError:
            raise
        except Exception:
            pass

    query_id = uuid.uuid4().hex[:12]

    with _pending_lock:
        _cleanup_expired_queries()
        _pending_queries[query_id] = {
            "status": "in_progress",
            "result": None,
            "error": None,
            "created_at": time.monotonic(),
        }

    thread = threading.Thread(
        target=_run_query_in_background,
        args=(query_id, client, notebook_id, query_text, source_ids, conversation_id, timeout),
        daemon=True,
    )
    thread.start()

    return {
        "query_id": query_id,
        "status": "in_progress",
        "message": "Query started. Use notebook_query_status to poll for the result.",
    }


def query_status(query_id: str) -> QueryStatusResult:
    """Check the status of an async query.

    Args:
        query_id: The query ID returned by query_start()

    Returns:
        QueryStatusResult with current status and result if completed

    Raises:
        ValidationError: If query_id is not found
    """
    with _pending_lock:
        entry = _pending_queries.get(query_id)
        if entry is None:
            raise ValidationError(
                f"Query ID '{query_id}' not found.",
                user_message=(
                    f"Query ID '{query_id}' not found. It may have expired "
                    f"(queries are kept for {_QUERY_TTL_SECONDS // 60} minutes) "
                    "or was never started."
                ),
            )

        result: QueryStatusResult = {
            "query_id": query_id,
            "status": entry["status"],
            "result": entry["result"],
            "error": entry["error"],
        }

        # Clean up completed/errored entries after reading
        if entry["status"] in ("completed", "error"):
            del _pending_queries[query_id]

        return result
