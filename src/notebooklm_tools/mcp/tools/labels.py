"""Label tools - Source label management with consolidated label tool."""

from ...services import ServiceError, ValidationError
from ...services import labels as labels_service
from ._utils import ResultDict, coerce_list, error_result, get_client, logged_tool


@logged_tool()
def label(
    notebook_id: str,
    action: str,
    label_id: str | None = None,
    label_ids: str | list[str] | None = None,
    name: str | None = None,
    emoji: str | None = None,
    source_id: str | None = None,
    confirm: bool = False,
) -> ResultDict:
    """Manage source labels in a notebook. Unified tool for all label operations.

    Labels let you organize sources into thematic categories. Requires 5+ sources
    for auto-labeling. Sources can belong to multiple labels simultaneously.

    Supports: auto, list, create, rename, set_emoji, move_source, delete

    Args:
        notebook_id: Notebook UUID
        action: Operation to perform:
            - auto: AI auto-labels all sources into thematic categories
            - list: List current labels (triggers AI if none exist)
            - create: Create a new empty label (requires name)
            - rename: Rename a label (requires label_id, name)
            - set_emoji: Set or clear emoji on a label (requires label_id, emoji)
            - move_source: Assign a source to a label (requires label_id, source_id)
            - delete: Delete label(s) permanently (requires label_id or label_ids, confirm=True)
        label_id: Label UUID (required for rename, set_emoji, move_source, delete)
        label_ids: List of label UUIDs for batch delete (alternative to label_id)
        name: Label display name (required for create and rename)
        emoji: Emoji character for set_emoji (e.g. "📊"), or "" to clear
        source_id: Source UUID to assign (required for move_source)
        confirm: Must be True for delete action

    Returns:
        Action-specific response with status

    Example:
        label(notebook_id="abc", action="auto")
        label(notebook_id="abc", action="list")
        label(notebook_id="abc", action="create", name="Research", emoji="📚")
        label(notebook_id="abc", action="rename", label_id="xyz", name="Better Name")
        label(notebook_id="abc", action="set_emoji", label_id="xyz", emoji="🎯")
        label(notebook_id="abc", action="move_source", label_id="xyz", source_id="src-id")
        label(notebook_id="abc", action="delete", label_id="xyz", confirm=True)
    """
    valid_actions = ("auto", "list", "create", "rename", "set_emoji", "move_source", "delete")

    if action not in valid_actions:
        return {
            "status": "error",
            "error": f"Unknown action '{action}'. Valid actions: {', '.join(valid_actions)}",
        }

    try:
        client = get_client()

        if action == "auto":
            result = labels_service.auto_label(client, notebook_id)
            return {"status": "success", "action": "auto", **result}

        elif action == "list":
            result = labels_service.list_labels(client, notebook_id)
            return {"status": "success", "action": "list", **result}

        elif action == "create":
            if not name:
                return error_result("name is required for action='create'")
            result = labels_service.create_label(client, notebook_id, name, emoji or "")
            return {"status": "success", "action": "create", **result}

        elif action == "rename":
            if not label_id:
                return error_result("label_id is required for action='rename'")
            if not name:
                return error_result("name is required for action='rename'")
            result = labels_service.rename_label(client, notebook_id, label_id, name)
            return {"status": "success", "action": "rename", **result}

        elif action == "set_emoji":
            if not label_id:
                return error_result("label_id is required for action='set_emoji'")
            if emoji is None:
                return error_result("emoji is required for action='set_emoji' (use \"\" to clear)")
            result = labels_service.set_label_emoji(client, notebook_id, label_id, emoji)
            return {"status": "success", "action": "set_emoji", **result}

        elif action == "move_source":
            if not label_id:
                return error_result("label_id is required for action='move_source'")
            if not source_id:
                return error_result("source_id is required for action='move_source'")
            result = labels_service.move_source_to_label(client, notebook_id, label_id, source_id)
            return {"status": "success", "action": "move_source", **result}

        elif action == "delete":
            ids = coerce_list(label_ids) or ([label_id] if label_id else None)
            if not ids:
                return error_result("label_id or label_ids is required for action='delete'")
            if not confirm:
                return error_result(
                    "Deletion not confirmed. Set confirm=True after user approval.",
                    warning="This action is IRREVERSIBLE. Sources will be preserved.",
                )
            result = labels_service.delete_labels(client, notebook_id, ids)
            return {"status": "success", "action": "delete", **result}

        return error_result(f"Unhandled action: {action}")

    except (ServiceError, ValidationError) as e:
        return error_result(e.user_message)
    except Exception as e:
        return error_result(str(e))
