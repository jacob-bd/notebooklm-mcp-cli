"""Export tools - Export artifacts to Google Docs/Sheets."""

from ...services import ServiceError
from ...services import exports as export_service
from ._utils import ResultDict, error_result, get_client, logged_tool


@logged_tool()
def export_artifact(
    notebook_id: str,
    artifact_id: str,
    export_type: str,
    title: str | None = None,
) -> ResultDict:
    """Export a NotebookLM artifact to Google Docs or Sheets.

    Supports:
    - Data Tables → Google Sheets
    - Reports (Briefing Doc, Study Guide, Blog Post) → Google Docs

    Args:
        notebook_id: Notebook UUID
        artifact_id: Artifact UUID to export
        export_type: "docs" or "sheets"
        title: Title for exported document (optional)

    Returns: URL to the created Google Doc/Sheet
    """
    try:
        client = get_client()
        result = export_service.export_artifact(
            client=client,
            notebook_id=notebook_id,
            artifact_id=artifact_id,
            export_type=export_type,
            title=title,
        )
        return dict(result)
    except ServiceError as e:
        return error_result(e.user_message, hint=e.hint)
    except Exception as e:
        return error_result(str(e))
