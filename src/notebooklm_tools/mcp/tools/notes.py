"""Notes tools - Note management with consolidated note tool."""

from ...services import ServiceError, ValidationError
from ...services import notes as notes_service
from ._utils import ResultDict, error_result, get_client, logged_tool


@logged_tool()
def note(
    notebook_id: str,
    action: str,
    note_id: str | None = None,
    content: str | None = None,
    title: str | None = None,
    confirm: bool = False,
) -> ResultDict:
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
    valid_actions = ("create", "list", "update", "delete")

    if action not in valid_actions:
        return {
            "status": "error",
            "error": f"Unknown action '{action}'. Valid actions: {', '.join(valid_actions)}",
        }

    try:
        client = get_client()

        if action == "create":
            create_result = notes_service.create_note(client, notebook_id, content or "", title)
            return {"status": "success", "action": "create", **create_result}

        elif action == "list":
            list_result = notes_service.list_notes(client, notebook_id)
            return {"status": "success", "action": "list", **list_result}

        elif action == "update":
            if not note_id:
                return error_result("note_id is required for action='update'")
            update_result = notes_service.update_note(client, notebook_id, note_id, content, title)
            return {"status": "success", "action": "update", **update_result}

        elif action == "delete":
            if not note_id:
                return error_result("note_id is required for action='delete'")
            if not confirm:
                return error_result(
                    "Deletion not confirmed. Set confirm=True after user approval.",
                    warning="This action is IRREVERSIBLE.",
                )
            delete_result = notes_service.delete_note(client, notebook_id, note_id)
            return {"status": "success", "action": "delete", **delete_result}

        return error_result(f"Unhandled action: {action}")

    except (ServiceError, ValidationError) as e:
        return error_result(e.user_message)
    except Exception as e:
        return error_result(str(e))
