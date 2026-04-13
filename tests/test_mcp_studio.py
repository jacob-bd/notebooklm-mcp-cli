"""Unit tests for MCP studio tools."""

from unittest.mock import MagicMock, patch

from notebooklm_tools.mcp.tools import studio
from notebooklm_tools.services.errors import ServiceError


def test_studio_revise_preserves_hint_on_service_error():
    mock_client = MagicMock()

    with (
        patch("notebooklm_tools.mcp.tools.studio.get_client", return_value=mock_client),
        patch(
            "notebooklm_tools.mcp.tools.studio.studio_service.revise_artifact",
            side_effect=ServiceError(
                "backend rejected revision",
                user_message="Failed to revise slide deck — Google API error code 7 (PERMISSION_DENIED).",
                hint=(
                    "Verify the artifact_id points to a completed slide deck in an editable "
                    "notebook you own. NotebookLM rejects revisions for view-only/shared decks."
                ),
            ),
        ),
    ):
        result = studio.studio_revise(
            notebook_id="nb-1",
            artifact_id="art-1",
            slide_instructions=[{"slide": 1, "instruction": "Tighten the title"}],
            confirm=True,
        )

    assert result["status"] == "error"
    assert "PERMISSION_DENIED" in result["error"]
    assert "editable notebook you own" in result["hint"]
