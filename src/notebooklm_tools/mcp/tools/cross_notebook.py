"""Cross-notebook tools — query across multiple notebooks."""

from ...services import cross_notebook as cross_notebook_service
from ...services.errors import ServiceError
from ._utils import ResultDict, error_result, get_client, logged_tool


@logged_tool()
def cross_notebook_query(
    query: str,
    notebook_names: str | None = None,
    tags: str | None = None,
    all: bool = False,
) -> ResultDict:
    """Query multiple notebooks and get aggregated answers with per-notebook citations.

    Specify notebooks by name, by tags, or use all=True for all notebooks.

    Args:
        query: Question to ask across notebooks
        notebook_names: Comma-separated notebook names or IDs (e.g. "AI Research, Dev Tools")
        tags: Comma-separated tags to select notebooks (e.g. "ai,mcp")
        all: Query ALL notebooks (use with caution — rate limits apply)
    """
    try:
        client = get_client()

        names_list = None
        if notebook_names:
            names_list = [n.strip() for n in notebook_names.split(",") if n.strip()]

        tags_list = None
        if tags:
            tags_list = [t.strip() for t in tags.split(",") if t.strip()]

        result = cross_notebook_service.cross_notebook_query(
            client=client,
            query_text=query,
            notebook_names=names_list,
            tags=tags_list,
            all_notebooks=all,
        )

        return {"status": "success", **result}
    except ServiceError as e:
        return error_result(e.user_message, hint=e.hint)
    except Exception as e:
        return error_result(str(e))
