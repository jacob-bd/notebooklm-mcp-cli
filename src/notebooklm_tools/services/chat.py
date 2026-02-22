"""Chat service — shared business logic for notebook querying and chat configuration."""

from typing import TypedDict, Optional

from ..core.client import NotebookLMClient
from ..core.conversation import QueryRejectedError
from .errors import ValidationError, ServiceError

VALID_GOALS = ("default", "learning_guide", "custom")
VALID_RESPONSE_LENGTHS = ("default", "longer", "shorter")
MAX_PROMPT_LENGTH = 10_000


class QueryResult(TypedDict):
    """Result of a notebook query."""
    answer: str
    conversation_id: Optional[str]
    sources_used: list
    citations: dict


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
    source_ids: Optional[list[str]] = None,
    conversation_id: Optional[str] = None,
    timeout: Optional[float] = None,
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

    try:
        result = client.query(
            notebook_id=notebook_id,
            query_text=query_text,
            source_ids=source_ids,
            conversation_id=conversation_id,
            timeout=timeout,
        )
    except QueryRejectedError as e:
        raise ServiceError(
            f"Query failed: {e}",
            user_message=(
                f"{e}. This may indicate account-level restrictions on "
                "programmatic access. Try re-authenticating with 'nlm login' "
                "or using a different account."
            ),
        )
    except Exception as e:
        raise ServiceError(f"Query failed: {e}")

    if result:
        return {
            "answer": result.get("answer", ""),
            "conversation_id": result.get("conversation_id"),
            "sources_used": result.get("sources_used", []),
            "citations": result.get("citations", {}),
        }

    raise ServiceError(
        "Query returned empty result",
        user_message="Failed to get a response from the notebook.",
    )


def configure_chat(
    client: NotebookLMClient,
    notebook_id: str,
    goal: str = "default",
    custom_prompt: Optional[str] = None,
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
        raise ServiceError(f"Failed to configure chat: {e}")

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
