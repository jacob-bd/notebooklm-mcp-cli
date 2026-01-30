"""Notes tools - Note management with consolidated note tool."""

from typing import Any
from ._utils import get_client, logged_tool


@logged_tool()
def note(
    notebook_id: str,
    action: str,
    note_id: str | None = None,
    content: str | None = None,
    title: str | None = None,
    confirm: bool = False,
) -> dict[str, Any]:
    """Manage notes in a notebook. Unified tool for all note operations.

    Supports: create, list, update, delete

    Args:
        notebook_id: Notebook UUID
        action: Operation to perform:
            - create: Create a new note
            - list: List all notes in notebook
            - update: Update an existing note
            - delete: Delete a note permanently (requires confirm=True)
        note_id: Note UUID (required for update/delete)
        content: Note content (required for create, optional for update)
        title: Note title (optional for create/update)
        confirm: Must be True for delete action

    Returns:
        Action-specific response with status

    Example:
        note(notebook_id="abc", action="list")
        note(notebook_id="abc", action="create", content="My note", title="Title")
        note(notebook_id="abc", action="update", note_id="xyz", content="Updated")
        note(notebook_id="abc", action="delete", note_id="xyz", confirm=True)
    """
    valid_actions = ["create", "list", "update", "delete"]

    if action not in valid_actions:
        return {
            "status": "error",
            "error": f"Unknown action '{action}'. Valid actions: {', '.join(valid_actions)}",
        }

    try:
        client = get_client()

        if action == "create":
            if not content:
                return {"status": "error", "error": "content is required for action='create'"}

            result = client.create_note(notebook_id, content, title)

            if result and result.get("id"):
                return {
                    "status": "success",
                    "action": "create",
                    "note_id": result["id"],
                    "title": result.get("title", ""),
                    "content_preview": content[:100] if len(content) > 100 else content,
                }
            return {"status": "error", "error": "Failed to create note"}

        elif action == "list":
            notes = client.list_notes(notebook_id)

            return {
                "status": "success",
                "action": "list",
                "notebook_id": notebook_id,
                "notes": notes,
                "count": len(notes),
            }

        elif action == "update":
            if not note_id:
                return {"status": "error", "error": "note_id is required for action='update'"}
            if content is None and title is None:
                return {"status": "error", "error": "Must provide content or title to update"}

            result = client.update_note(note_id, content, title, notebook_id)

            if result:
                return {
                    "status": "success",
                    "action": "update",
                    "note_id": note_id,
                    "updated": True,
                }
            return {"status": "error", "error": "Failed to update note"}

        elif action == "delete":
            if not note_id:
                return {"status": "error", "error": "note_id is required for action='delete'"}
            if not confirm:
                return {
                    "status": "error",
                    "error": "Deletion not confirmed. Set confirm=True after user approval.",
                    "warning": "This action is IRREVERSIBLE.",
                }

            result = client.delete_note(note_id, notebook_id)

            if result:
                return {
                    "status": "success",
                    "action": "delete",
                    "message": f"Note {note_id} has been permanently deleted.",
                }
            return {"status": "error", "error": "Failed to delete note"}

        return {"status": "error", "error": f"Unhandled action: {action}"}

    except Exception as e:
        return {"status": "error", "error": str(e)}
