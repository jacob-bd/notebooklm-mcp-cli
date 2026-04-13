"""Chat tools - Query and conversation management."""

from ...services import ServiceError
from ...services import chat as chat_service
from ._utils import (
    ResultDict,
    coerce_list,
    error_result,
    get_client,
    get_query_timeout,
    logged_tool,
)


@logged_tool()
def notebook_query(
    notebook_id: str,
    query: str,
    source_ids: list[str] | None = None,
    conversation_id: str | None = None,
    timeout: float | None = None,
) -> ResultDict:
    """Ask AI about EXISTING sources already in notebook. NOT for finding new sources.

    Use research_start instead for: deep research, web search, find new sources, Drive search.

    Args:
        notebook_id: Notebook UUID
        query: Question to ask
        source_ids: Source IDs to query (default: all)
        conversation_id: For follow-up questions
        timeout: Request timeout in seconds (default: from env NOTEBOOKLM_QUERY_TIMEOUT or 120.0)
    """
    try:
        client = get_client()
        # Coerce list params from MCP clients (may arrive as strings)
        coerced_source_ids: list[str] | None = coerce_list(source_ids)
        effective_timeout = timeout or get_query_timeout()
        result = chat_service.query(
            client,
            notebook_id,
            query,
            source_ids=coerced_source_ids,
            conversation_id=conversation_id,
            timeout=effective_timeout,
        )
        return {"status": "success", **result}
    except ServiceError as e:
        return error_result(e.user_message, hint=e.hint)
    except Exception as e:
        return error_result(str(e))


@logged_tool()
def chat_configure(
    notebook_id: str,
    goal: str = "default",
    custom_prompt: str | None = None,
    response_length: str = "default",
) -> ResultDict:
    """Configure notebook chat settings.

    Args:
        notebook_id: Notebook UUID
        goal: default|learning_guide|custom
        custom_prompt: Required when goal=custom (max 10000 chars)
        response_length: default|longer|shorter
    """
    try:
        client = get_client()
        result = chat_service.configure_chat(
            client,
            notebook_id,
            goal=goal,
            custom_prompt=custom_prompt,
            response_length=response_length,
        )
        return {"status": "success", **result}
    except ServiceError as e:
        return error_result(e.user_message, hint=e.hint)
    except Exception as e:
        return error_result(str(e))


@logged_tool()
def notebook_query_start(
    notebook_id: str,
    query: str,
    source_ids: list[str] | None = None,
    conversation_id: str | None = None,
    timeout: float | None = None,
) -> ResultDict:
    """Start a notebook query asynchronously for large notebooks that may timeout.

    Use this instead of notebook_query when querying notebooks with many sources
    (50+) where the response may take longer than 60 seconds. Returns immediately
    with a query_id. Poll notebook_query_status with the query_id to get the result.

    Workflow: notebook_query_start -> poll notebook_query_status until completed.

    Args:
        notebook_id: Notebook UUID
        query: Question to ask
        source_ids: Source IDs to query (default: all)
        conversation_id: For follow-up questions
        timeout: Request timeout in seconds (default: from env NOTEBOOKLM_QUERY_TIMEOUT or 120.0)
    """
    try:
        client = get_client()
        coerced_source_ids: list[str] | None = coerce_list(source_ids)
        effective_timeout = timeout or get_query_timeout()
        result = chat_service.query_start(
            client,
            notebook_id,
            query,
            source_ids=coerced_source_ids,
            conversation_id=conversation_id,
            timeout=effective_timeout,
        )
        return {"status": "success", **result}
    except ServiceError as e:
        return error_result(e.user_message, hint=e.hint)
    except Exception as e:
        return error_result(str(e))


@logged_tool()
def notebook_query_status(
    query_id: str,
) -> ResultDict:
    """Check the status of an async notebook query started with notebook_query_start.

    Returns the query result when completed, or current status if still in progress.
    Poll this tool every few seconds until status is 'completed' or 'error'.

    Args:
        query_id: The query ID returned by notebook_query_start
    """
    try:
        result = chat_service.query_status(query_id)
        return {"status": "success", **result}
    except ServiceError as e:
        return error_result(e.user_message, hint=e.hint)
    except Exception as e:
        return error_result(str(e))
