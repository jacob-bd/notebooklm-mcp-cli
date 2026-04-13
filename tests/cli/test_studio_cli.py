"""Tests for the `nlm slides revise` CLI command."""

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from notebooklm_tools.cli.commands.studio import slides_app
from notebooklm_tools.services.errors import ServiceError


@pytest.fixture
def runner():
    return CliRunner()


def test_slides_revise_surfaces_service_hint(runner):
    mock_client = MagicMock()
    mock_client.__enter__ = lambda s: s
    mock_client.__exit__ = MagicMock(return_value=False)
    alias_mgr = MagicMock()
    alias_mgr.resolve.side_effect = lambda x: x

    with (
        patch("notebooklm_tools.cli.commands.studio.get_alias_manager", return_value=alias_mgr),
        patch("notebooklm_tools.cli.commands.studio.get_client", return_value=mock_client),
        patch(
            "notebooklm_tools.cli.commands.studio.studio_service.revise_artifact",
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
        result = runner.invoke(
            slides_app,
            [
                "revise",
                "art-1",
                "--slide",
                "1 Tighten the title",
                "--confirm",
            ],
        )

    assert result.exit_code == 1
    assert "PERMISSION_DENIED" in result.output
    assert "Hint:" in result.output
    assert "editable" in result.output
    assert "notebook you own" in result.output
