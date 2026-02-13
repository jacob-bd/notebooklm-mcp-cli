"""Tests for services.exports module."""

import pytest
from unittest.mock import MagicMock

from notebooklm_tools.services.exports import export_artifact, ExportResult
from notebooklm_tools.services.errors import ValidationError, ExportError


@pytest.fixture
def mock_client():
    """Create a mock NotebookLMClient."""
    return MagicMock()


class TestExportArtifactValidation:
    """Test input validation in export_artifact."""

    def test_invalid_export_type_raises_validation_error(self, mock_client):
        with pytest.raises(ValidationError, match="Invalid export type"):
            export_artifact(
                client=mock_client,
                notebook_id="nb-123",
                artifact_id="art-456",
                export_type="invalid",
            )

    def test_export_type_case_insensitive(self, mock_client):
        """'DOCS' should be normalized to 'docs'."""
        mock_client.export_artifact.return_value = {
            "url": "https://docs.google.com/doc/123"
        }
        result = export_artifact(
            client=mock_client,
            notebook_id="nb-123",
            artifact_id="art-456",
            export_type="DOCS",
        )
        assert result["status"] == "success"
        assert result["export_type"] == "docs"

    def test_docs_type_accepted(self, mock_client):
        mock_client.export_artifact.return_value = {
            "url": "https://docs.google.com/doc/123"
        }
        result = export_artifact(
            client=mock_client,
            notebook_id="nb-123",
            artifact_id="art-456",
            export_type="docs",
        )
        assert result["status"] == "success"

    def test_sheets_type_accepted(self, mock_client):
        mock_client.export_artifact.return_value = {
            "url": "https://docs.google.com/spreadsheets/123"
        }
        result = export_artifact(
            client=mock_client,
            notebook_id="nb-123",
            artifact_id="art-456",
            export_type="sheets",
        )
        assert result["status"] == "success"


class TestExportArtifactSuccess:
    """Test successful export operations."""

    def test_docs_export_returns_correct_result(self, mock_client):
        mock_client.export_artifact.return_value = {
            "url": "https://docs.google.com/doc/123"
        }
        result = export_artifact(
            client=mock_client,
            notebook_id="nb-123",
            artifact_id="art-456",
            export_type="docs",
            title="My Report",
        )
        assert result["status"] == "success"
        assert result["notebook_id"] == "nb-123"
        assert result["artifact_id"] == "art-456"
        assert result["export_type"] == "docs"
        assert result["url"] == "https://docs.google.com/doc/123"
        assert "Google Docs" in result["message"]

    def test_sheets_export_returns_correct_result(self, mock_client):
        mock_client.export_artifact.return_value = {
            "url": "https://docs.google.com/spreadsheets/123"
        }
        result = export_artifact(
            client=mock_client,
            notebook_id="nb-123",
            artifact_id="art-456",
            export_type="sheets",
        )
        assert result["status"] == "success"
        assert result["export_type"] == "sheets"
        assert "Google Sheets" in result["message"]

    def test_default_title_used_when_none(self, mock_client):
        mock_client.export_artifact.return_value = {
            "url": "https://docs.google.com/doc/123"
        }
        export_artifact(
            client=mock_client,
            notebook_id="nb-123",
            artifact_id="art-456",
            export_type="docs",
        )
        # Check the client was called with default title
        mock_client.export_artifact.assert_called_once_with(
            notebook_id="nb-123",
            artifact_id="art-456",
            title="NotebookLM Export",
            export_type="docs",
        )

    def test_custom_title_passed_through(self, mock_client):
        mock_client.export_artifact.return_value = {
            "url": "https://docs.google.com/doc/123"
        }
        export_artifact(
            client=mock_client,
            notebook_id="nb-123",
            artifact_id="art-456",
            export_type="docs",
            title="Custom Title",
        )
        mock_client.export_artifact.assert_called_once_with(
            notebook_id="nb-123",
            artifact_id="art-456",
            title="Custom Title",
            export_type="docs",
        )


class TestExportArtifactFailure:
    """Test error handling in export_artifact."""

    def test_no_url_raises_export_error(self, mock_client):
        """Fail-fast: if API returns no URL, raise ExportError."""
        mock_client.export_artifact.return_value = {
            "message": "Quota exceeded"
        }
        with pytest.raises(ExportError, match="no document URL"):
            export_artifact(
                client=mock_client,
                notebook_id="nb-123",
                artifact_id="art-456",
                export_type="docs",
            )

    def test_no_url_preserves_api_message_in_user_message(self, mock_client):
        mock_client.export_artifact.return_value = {
            "message": "Quota exceeded"
        }
        with pytest.raises(ExportError) as exc_info:
            export_artifact(
                client=mock_client,
                notebook_id="nb-123",
                artifact_id="art-456",
                export_type="docs",
            )
        assert exc_info.value.user_message == "Quota exceeded"

    def test_empty_result_raises_export_error(self, mock_client):
        mock_client.export_artifact.return_value = {}
        with pytest.raises(ExportError, match="no document URL"):
            export_artifact(
                client=mock_client,
                notebook_id="nb-123",
                artifact_id="art-456",
                export_type="docs",
            )

    def test_api_exception_wrapped_in_export_error(self, mock_client):
        mock_client.export_artifact.side_effect = RuntimeError("Connection refused")
        with pytest.raises(ExportError, match="API call failed"):
            export_artifact(
                client=mock_client,
                notebook_id="nb-123",
                artifact_id="art-456",
                export_type="docs",
            )
