"""Labels service — shared business logic for source label management."""

from ..core.client import NotebookLMClient
from ._compat import TypedDict
from .errors import ServiceError, ValidationError


class LabelInfo(TypedDict):
    """Details of a single label."""

    id: str
    name: str
    emoji: str
    source_ids: list[str]


class LabelListResult(TypedDict):
    """Result of listing or auto-labeling."""

    notebook_id: str
    labels: list[LabelInfo]
    count: int


class LabelMutateResult(TypedDict):
    """Result of a label mutation (rename, emoji, move-source, create)."""

    label_id: str
    message: str


class LabelDeleteResult(TypedDict):
    """Result of deleting labels."""

    deleted_label_ids: list[str]
    count: int
    message: str


def _make_list_result(notebook_id: str, labels: list[dict]) -> LabelListResult:
    return {
        "notebook_id": notebook_id,
        "labels": labels,
        "count": len(labels),
    }


def auto_label(client: NotebookLMClient, notebook_id: str) -> LabelListResult:
    """Auto-label all sources using AI-generated thematic categories.

    Requires 5+ sources. If labels already exist, returns the current state
    without re-running AI categorization.

    Args:
        client: Authenticated NotebookLM client
        notebook_id: Notebook UUID

    Returns:
        LabelListResult with auto-generated labels

    Raises:
        ServiceError: If the API call fails
    """
    if not notebook_id or not notebook_id.strip():
        raise ValidationError(
            "notebook_id is required.", user_message="Notebook ID cannot be empty."
        )
    try:
        labels = client.auto_label(notebook_id)
    except Exception as e:
        raise ServiceError(f"Failed to auto-label: {e}") from e
    return _make_list_result(notebook_id, labels)


def list_labels(client: NotebookLMClient, notebook_id: str) -> LabelListResult:
    """List current labels in a notebook.

    Uses the same mechanism as auto_label. If no labels exist, this will
    trigger AI auto-labeling.

    Args:
        client: Authenticated NotebookLM client
        notebook_id: Notebook UUID

    Returns:
        LabelListResult with current labels

    Raises:
        ServiceError: If the API call fails
    """
    if not notebook_id or not notebook_id.strip():
        raise ValidationError(
            "notebook_id is required.", user_message="Notebook ID cannot be empty."
        )
    try:
        labels = client.list_labels(notebook_id)
    except Exception as e:
        raise ServiceError(f"Failed to list labels: {e}") from e
    return _make_list_result(notebook_id, labels)


def create_label(
    client: NotebookLMClient,
    notebook_id: str,
    name: str,
    emoji: str = "",
) -> LabelMutateResult:
    """Create a new empty label manually.

    Args:
        client: Authenticated NotebookLM client
        notebook_id: Notebook UUID
        name: Display name for the new label
        emoji: Optional emoji marker (e.g. "📊")

    Returns:
        LabelMutateResult with new label ID

    Raises:
        ValidationError: If name is empty
        ServiceError: If creation fails
    """
    if not name or not name.strip():
        raise ValidationError("Label name is required.", user_message="Label name cannot be empty.")

    try:
        labels = client.create_label(notebook_id, name.strip(), emoji)
    except Exception as e:
        raise ServiceError(f"Failed to create label: {e}") from e

    new_label = next((lbl for lbl in labels if lbl["name"] == name.strip()), None)
    label_id = new_label["id"] if new_label else ""

    return {
        "label_id": label_id,
        "message": f"Label '{name.strip()}' created." + (f" emoji: {emoji}" if emoji else ""),
    }


def rename_label(
    client: NotebookLMClient,
    notebook_id: str,
    label_id: str,
    new_name: str,
) -> LabelMutateResult:
    """Rename an existing label.

    Args:
        client: Authenticated NotebookLM client
        notebook_id: Notebook UUID
        label_id: Label UUID to rename
        new_name: New display name

    Returns:
        LabelMutateResult

    Raises:
        ValidationError: If label_id or new_name is empty
        ServiceError: If rename fails
    """
    if not label_id or not label_id.strip():
        raise ValidationError("label_id is required.", user_message="Label ID cannot be empty.")
    if not new_name or not new_name.strip():
        raise ValidationError(
            "new_name is required.", user_message="New label name cannot be empty."
        )

    try:
        result = client.rename_label(notebook_id, label_id, new_name.strip())
    except Exception as e:
        raise ServiceError(f"Failed to rename label: {e}") from e

    if not result:
        raise ServiceError("Rename returned falsy result", user_message="Failed to rename label.")

    return {"label_id": label_id, "message": f"Label renamed to '{new_name.strip()}'."}


def set_label_emoji(
    client: NotebookLMClient,
    notebook_id: str,
    label_id: str,
    emoji: str,
) -> LabelMutateResult:
    """Set or clear the emoji marker on a label.

    Args:
        client: Authenticated NotebookLM client
        notebook_id: Notebook UUID
        label_id: Label UUID
        emoji: Emoji character or "" to clear

    Returns:
        LabelMutateResult

    Raises:
        ValidationError: If label_id is empty
        ServiceError: If the API call fails
    """
    if not label_id or not label_id.strip():
        raise ValidationError("label_id is required.", user_message="Label ID cannot be empty.")

    try:
        result = client.set_label_emoji(notebook_id, label_id, emoji)
    except Exception as e:
        raise ServiceError(f"Failed to set label emoji: {e}") from e

    if not result:
        raise ServiceError(
            "Set emoji returned falsy result", user_message="Failed to set label emoji."
        )

    msg = f"Emoji set to '{emoji}'." if emoji else "Emoji cleared."
    return {"label_id": label_id, "message": msg}


def move_source_to_label(
    client: NotebookLMClient,
    notebook_id: str,
    label_id: str,
    source_id: str,
) -> LabelMutateResult:
    """Assign a source to a label.

    Sources support multi-label assignment — this adds the source to the
    target label without removing it from any existing labels.

    Args:
        client: Authenticated NotebookLM client
        notebook_id: Notebook UUID
        label_id: Target label UUID
        source_id: Source UUID to assign

    Returns:
        LabelMutateResult

    Raises:
        ValidationError: If any required ID is empty
        ServiceError: If the API call fails
    """
    if not label_id or not label_id.strip():
        raise ValidationError("label_id is required.", user_message="Label ID cannot be empty.")
    if not source_id or not source_id.strip():
        raise ValidationError("source_id is required.", user_message="Source ID cannot be empty.")

    try:
        result = client.move_source_to_label(notebook_id, label_id, source_id)
    except Exception as e:
        raise ServiceError(f"Failed to move source to label: {e}") from e

    if not result:
        raise ServiceError(
            "Move source returned falsy result", user_message="Failed to move source."
        )

    return {"label_id": label_id, "message": f"Source {source_id[:8]}... assigned to label."}


def delete_labels(
    client: NotebookLMClient,
    notebook_id: str,
    label_ids: list[str],
) -> LabelDeleteResult:
    """Delete one or more labels. Sources are NOT deleted.

    Args:
        client: Authenticated NotebookLM client
        notebook_id: Notebook UUID
        label_ids: List of label UUIDs to delete

    Returns:
        LabelDeleteResult

    Raises:
        ValidationError: If label_ids is empty
        ServiceError: If deletion fails
    """
    if not label_ids:
        raise ValidationError(
            "label_ids is required.", user_message="Provide at least one label ID to delete."
        )

    clean_ids = [lid.strip() for lid in label_ids if lid and lid.strip()]
    if not clean_ids:
        raise ValidationError(
            "label_ids must contain valid IDs.", user_message="No valid label IDs provided."
        )

    try:
        result = client.delete_labels(notebook_id, clean_ids)
    except Exception as e:
        raise ServiceError(f"Failed to delete labels: {e}") from e

    if not result:
        raise ServiceError("Delete returned falsy result", user_message="Failed to delete labels.")

    count = len(clean_ids)
    noun = "label" if count == 1 else "labels"
    return {
        "deleted_label_ids": clean_ids,
        "count": count,
        "message": f"Deleted {count} {noun}. Sources are preserved.",
    }
