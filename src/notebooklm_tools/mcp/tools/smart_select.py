"""Smart select tools — consolidated tag management and notebook selection."""

from ...services import smart_select as smart_select_service
from ...services.errors import ServiceError
from ._utils import ResultDict, error_result, logged_tool


@logged_tool()
def tag(
    action: str,
    notebook_id: str | None = None,
    tags: str | None = None,
    notebook_title: str = "",
    query: str | None = None,
) -> ResultDict:
    """Manage notebook tags and find relevant notebooks by tag matching.

    Actions:
    - add: Add tags to a notebook for smart selection
    - remove: Remove tags from a notebook
    - list: List all tagged notebooks with their tags
    - select: Find notebooks relevant to a query using tag matching

    Args:
        action: Operation to perform (add, remove, list, select)
        notebook_id: Notebook UUID (required for add, remove)
        tags: Comma-separated tags (required for add, remove; e.g. "ai,research,llm")
        notebook_title: Optional display title (for add)
        query: Search query (required for select; e.g. "ai mcp" or "ai,mcp")
    """
    try:
        if action == "add":
            if not notebook_id:
                return error_result("notebook_id is required for action=add")
            if not tags:
                return error_result("tags parameter is required for action=add")
            tag_list = [t.strip() for t in tags.split(",") if t.strip()]
            add_result = smart_select_service.tag_add(notebook_id, tag_list, notebook_title)
            return {"status": "success", "notebook_id": notebook_id, "tags": add_result["tags"]}

        elif action == "remove":
            if not notebook_id:
                return error_result("notebook_id is required for action=remove")
            if not tags:
                return error_result("tags parameter is required for action=remove")
            tag_list = [t.strip() for t in tags.split(",") if t.strip()]
            remove_result = smart_select_service.tag_remove(notebook_id, tag_list)
            return {
                "status": "success",
                "notebook_id": notebook_id,
                "tags": remove_result["tags"],
            }

        elif action == "list":
            list_result = smart_select_service.tag_list()
            return {"status": "success", **list_result}

        elif action == "select":
            if not query:
                return error_result("query parameter is required for action=select")
            select_result = smart_select_service.smart_select(query)
            return {"status": "success", **select_result}

        else:
            return {
                "status": "error",
                "error": f"Unknown action: {action}. Use: add, remove, list, select",
            }

    except ServiceError as e:
        return error_result(e.user_message, hint=e.hint)
    except Exception as e:
        return error_result(str(e))
