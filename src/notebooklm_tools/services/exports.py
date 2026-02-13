"""Export service — shared business logic for Google Docs/Sheets exports."""

from typing import TypedDict, Literal, Optional

from ..core.client import NotebookLMClient
from .errors import ValidationError, ExportError

ExportType = Literal["docs", "sheets"]

class ExportResult(TypedDict):
    """Result of an export operation."""
    status: Literal["success", "error"]
    notebook_id: str
    artifact_id: str
    export_type: ExportType
    url: str
    message: str

def export_artifact(
    client: NotebookLMClient,
    notebook_id: str,
    artifact_id: str,
    export_type: str,
    title: Optional[str] = None,
) -> ExportResult:
    """Export a NotebookLM artifact to Google Docs or Sheets.

    Args:
        client: Authenticated NotebookLM client
        notebook_id: Notebook UUID
        artifact_id: Artifact UUID
        export_type: "docs" or "sheets"
        title: Optional title for the exported document

    Returns:
        ExportResult dict with url on success

    Raises:
        ValidationError: If export_type is invalid
        ExportError: If export fails or no URL is returned
    """
    # 1. Validation
    clean_type = export_type.lower()
    if clean_type not in ("docs", "sheets"):
        raise ValidationError(
            f"Invalid export type '{export_type}'. Must be 'docs' or 'sheets'.",
            user_message=f"Export type must be 'docs' or 'sheets' (got '{export_type}')"
        )

    # 2. Execution
    try:
        result = client.export_artifact(
            notebook_id=notebook_id,
            artifact_id=artifact_id,
            title=title or "NotebookLM Export",
            export_type=clean_type,
        )
    except Exception as e:
        raise ExportError(f"API call failed: {e}", user_message=f"Export failed: {e}")

    # 3. Result Normalization
    if result.get("url"):
        export_label = "Google Docs" if clean_type == "docs" else "Google Sheets"
        return {
            "status": "success",
            "notebook_id": notebook_id,
            "artifact_id": artifact_id,
            "export_type": clean_type,  # type: ignore
            "url": result["url"],
            "message": f"Exported to {export_label}: {result['url']}",
        }
    else:
        # Fail-fast
        raise ExportError(
            f"Export failed - no document URL returned. Response: {result}",
            user_message=result.get("message", "Export failed - no document URL returned")
        )
