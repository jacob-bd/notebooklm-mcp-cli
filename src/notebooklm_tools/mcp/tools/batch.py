"""Batch operations — consolidated tool for multi-notebook actions."""

from ...services import batch as batch_service
from ...services.errors import ServiceError
from ._utils import ResultDict, error_result, get_client, logged_tool


@logged_tool()
def batch(
    action: str,
    query: str | None = None,
    source_url: str | None = None,
    titles: str | None = None,
    artifact_type: str = "audio",
    notebook_names: str | None = None,
    tags: str | None = None,
    all: bool = False,
    confirm: bool = False,
) -> ResultDict:
    """Perform batch operations across multiple notebooks.

    Actions:
    - query: Query multiple notebooks with the same question
    - add_source: Add the same source URL to multiple notebooks
    - create: Create multiple notebooks at once
    - delete: Delete multiple notebooks (IRREVERSIBLE, requires confirm=True)
    - studio: Generate studio artifacts across multiple notebooks

    Args:
        action: Operation to perform (query, add_source, create, delete, studio)
        query: Question to ask (for action=query)
        source_url: URL to add (for action=add_source)
        titles: Comma-separated notebook titles (for action=create)
        artifact_type: Artifact type (for action=studio): audio, video, report, etc.
        notebook_names: Comma-separated notebook names or IDs
        tags: Comma-separated tags to select notebooks
        all: Apply to ALL notebooks
        confirm: Must be True for delete action
    """
    try:
        names = (
            [n.strip() for n in notebook_names.split(",") if n.strip()] if notebook_names else None
        )
        tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None

        if action == "query":
            if not query:
                return error_result("query parameter is required for action=query")
            client = get_client()
            result = batch_service.batch_query(client, query, names, tag_list, all)
            return {"status": "success", **result}

        elif action == "add_source":
            if not source_url:
                return {
                    "status": "error",
                    "error": "source_url parameter is required for action=add_source",
                }
            client = get_client()
            result = batch_service.batch_add_source(client, source_url, names, tag_list, all)
            return {"status": "success", **result}

        elif action == "create":
            if not titles:
                return {
                    "status": "error",
                    "error": "titles parameter is required for action=create",
                }
            client = get_client()
            title_list = [t.strip() for t in titles.split(",") if t.strip()]
            result = batch_service.batch_create(client, title_list)
            return {"status": "success", **result}

        elif action == "delete":
            if not confirm:
                return {
                    "status": "error",
                    "error": "Batch delete not confirmed. Ask the user to confirm before setting confirm=True.",
                    "warning": "This action is IRREVERSIBLE. Multiple notebooks will be permanently deleted.",
                }
            client = get_client()
            result = batch_service.batch_delete(client, names, tag_list, confirm=True)
            return {"status": "success", **result}

        elif action == "studio":
            client = get_client()
            result = batch_service.batch_studio(client, artifact_type, names, tag_list, all)
            return {"status": "success", **result}

        else:
            return {
                "status": "error",
                "error": f"Unknown action: {action}. Use: query, add_source, create, delete, studio",
            }

    except ServiceError as e:
        return error_result(e.user_message, hint=e.hint)
    except Exception as e:
        return error_result(str(e))
