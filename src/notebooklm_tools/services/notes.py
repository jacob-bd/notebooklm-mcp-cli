"""Notes service — shared business logic for note CRUD operations."""

from typing import TypedDict, Optional

from ..core.client import NotebookLMClient
from ..utils.cache import get_cache
from .errors import ValidationError, ServiceError


class NoteInfo(TypedDict):
    """Note details."""
    id: str
    title: str
    preview: str


class NoteListResult(TypedDict):
    """Result of listing notes."""
    notebook_id: str
    notes: list[NoteInfo]
    count: int


class NoteCreateResult(TypedDict):
    """Result of creating a note."""
    note_id: str
    title: str
    content_preview: str
    message: str


class NoteUpdateResult(TypedDict):
    """Result of updating a note."""
    note_id: str
    updated: bool
    message: str


class NoteDeleteResult(TypedDict):
    """Result of deleting a note."""
    note_id: str
    message: str


def list_notes(client: NotebookLMClient, notebook_id: str) -> NoteListResult:
    """List all notes in a notebook.

    Args:
        client: Authenticated NotebookLM client
        notebook_id: Notebook UUID

    Returns:
        NoteListResult with note list and count

    Raises:
        ServiceError: If the API call fails
    """
    try:
        notes = client.list_notes(notebook_id)
        return {
            "notebook_id": notebook_id,
            "notes": notes,
            "count": len(notes),
        }
    except Exception as e:
        raise ServiceError(f"Failed to list notes: {e}")


def create_note(
    client: NotebookLMClient,
    notebook_id: str,
    content: str,
    title: Optional[str] = None,
) -> NoteCreateResult:
    """Create a new note in a notebook.

    Args:
        client: Authenticated NotebookLM client
        notebook_id: Notebook UUID
        content: Note content (required)
        title: Note title (defaults to "New Note")

    Returns:
        NoteCreateResult with note ID and preview

    Raises:
        ValidationError: If content is empty
        ServiceError: If creation fails
    """
    if not content or not content.strip():
        raise ValidationError(
            "Content is required to create a note.",
            user_message="Note content cannot be empty.",
        )

    effective_title = title or "New Note"

    try:
        result = client.create_note(notebook_id, content, effective_title)
    except Exception as e:
        raise ServiceError(f"Failed to create note: {e}")

    if result and result.get("id"):
        get_cache().invalidate(f"notebook:{notebook_id}")
        preview = content[:100] + ("..." if len(content) > 100 else "")
        return {
            "note_id": result["id"],
            "title": result.get("title", effective_title),
            "content_preview": preview,
            "message": f"Note '{result.get('title', effective_title)}' created.",
        }

    raise ServiceError(
        "Note creation returned no ID",
        user_message="Failed to create note — no confirmation from API.",
    )


def update_note(
    client: NotebookLMClient,
    notebook_id: str,
    note_id: str,
    content: Optional[str] = None,
    title: Optional[str] = None,
) -> NoteUpdateResult:
    """Update a note's content and/or title.

    Args:
        client: Authenticated NotebookLM client
        notebook_id: Notebook UUID
        note_id: Note UUID
        content: New content (optional)
        title: New title (optional)

    Returns:
        NoteUpdateResult

    Raises:
        ValidationError: If neither content nor title is provided
        ServiceError: If update fails
    """
    if content is None and title is None:
        raise ValidationError(
            "Must provide content or title to update.",
            user_message="Provide at least --content or --title to update.",
        )

    try:
        result = client.update_note(note_id, content, title, notebook_id)
    except Exception as e:
        raise ServiceError(f"Failed to update note: {e}")

    if result:
        get_cache().invalidate(f"notebook:{notebook_id}")
        parts = []
        if title:
            parts.append(f"title → '{title}'")
        if content:
            parts.append(f"content ({len(content)} chars)")
        detail = ", ".join(parts) if parts else "updated"
        return {
            "note_id": note_id,
            "updated": True,
            "message": f"Note updated: {detail}.",
        }

    raise ServiceError(
        "Note update returned falsy result",
        user_message="Failed to update note — no confirmation from API.",
    )


def delete_note(
    client: NotebookLMClient,
    notebook_id: str,
    note_id: str,
) -> NoteDeleteResult:
    """Delete a note permanently.

    Args:
        client: Authenticated NotebookLM client
        notebook_id: Notebook UUID
        note_id: Note UUID

    Returns:
        NoteDeleteResult

    Raises:
        ServiceError: If deletion fails
    """
    try:
        result = client.delete_note(note_id, notebook_id)
    except Exception as e:
        raise ServiceError(f"Failed to delete note: {e}")

    if result:
        get_cache().invalidate(f"notebook:{notebook_id}")
        return {
            "note_id": note_id,
            "message": f"Note {note_id} deleted permanently.",
        }

    raise ServiceError(
        "Note deletion returned falsy result",
        user_message="Failed to delete note — no confirmation from API.",
    )
