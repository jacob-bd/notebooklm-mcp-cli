"""Tests for services.research module."""

import pytest
from unittest.mock import MagicMock

from notebooklm_tools.services.research import (
    start_research,
    poll_research,
    import_research,
)
from notebooklm_tools.services.errors import ValidationError, ServiceError


@pytest.fixture
def mock_client():
    return MagicMock()


class TestStartResearch:
    """Test start_research service function."""

    def test_successful_start(self, mock_client):
        mock_client.start_research.return_value = {
            "task_id": "task-123",
            "notebook_id": "nb-1",
        }

        result = start_research(mock_client, "nb-1", "quantum computing")

        assert result["task_id"] == "task-123"
        assert result["query"] == "quantum computing"
        assert result["source"] == "web"
        assert result["mode"] == "fast"

    def test_invalid_source_raises_validation_error(self, mock_client):
        with pytest.raises(ValidationError, match="Invalid source"):
            start_research(mock_client, "nb-1", "query", source="twitter")

    def test_invalid_mode_raises_validation_error(self, mock_client):
        with pytest.raises(ValidationError, match="Invalid mode"):
            start_research(mock_client, "nb-1", "query", mode="ultra")

    def test_deep_drive_raises_validation_error(self, mock_client):
        with pytest.raises(ValidationError, match="only available for web"):
            start_research(mock_client, "nb-1", "query", source="drive", mode="deep")

    def test_empty_query_raises_validation_error(self, mock_client):
        with pytest.raises(ValidationError, match="Query is required"):
            start_research(mock_client, "nb-1", "")

    def test_falsy_result_raises_service_error(self, mock_client):
        mock_client.start_research.return_value = None
        with pytest.raises(ServiceError, match="no data"):
            start_research(mock_client, "nb-1", "query")

    def test_api_error_raises_service_error(self, mock_client):
        mock_client.start_research.side_effect = RuntimeError("fail")
        with pytest.raises(ServiceError, match="Failed to start research"):
            start_research(mock_client, "nb-1", "query")

    def test_drive_fast_works(self, mock_client):
        mock_client.start_research.return_value = {"task_id": "t-1"}

        result = start_research(mock_client, "nb-1", "query", source="drive", mode="fast")

        assert result["source"] == "drive"
        assert result["mode"] == "fast"


class TestPollResearch:
    """Test poll_research service function."""

    def test_completed_status(self, mock_client):
        mock_client.poll_research.return_value = {
            "status": "completed",
            "task_id": "task-1",
            "sources": [{"title": "Source A"}],
            "report": "Research complete.",
        }

        result = poll_research(mock_client, "nb-1")

        assert result["status"] == "completed"
        assert result["sources_found"] == 1
        assert result["message"] is not None

    def test_no_research_returns_empty(self, mock_client):
        mock_client.poll_research.return_value = None

        result = poll_research(mock_client, "nb-1")

        assert result["status"] == "no_research"
        assert result["sources_found"] == 0

    def test_compact_truncates_report(self, mock_client):
        long_report = "x" * 1000
        mock_client.poll_research.return_value = {
            "status": "completed",
            "task_id": "t-1",
            "sources": [],
            "report": long_report,
        }

        result = poll_research(mock_client, "nb-1", compact=True)

        assert len(result["report"]) < 600
        assert "[truncated]" in result["report"]

    def test_compact_limits_sources(self, mock_client):
        mock_client.poll_research.return_value = {
            "status": "completed",
            "task_id": "t-1",
            "sources": [{"title": f"Source {i}"} for i in range(20)],
            "report": "",
        }

        result = poll_research(mock_client, "nb-1", compact=True)

        assert len(result["sources"]) == 6  # 5 + note
        assert "more sources" in str(result["sources"][-1])

    def test_api_error_raises_service_error(self, mock_client):
        mock_client.poll_research.side_effect = RuntimeError("fail")
        with pytest.raises(ServiceError, match="Failed to poll"):
            poll_research(mock_client, "nb-1")


class TestImportResearch:
    """Test import_research service function."""

    def test_import_all_sources(self, mock_client):
        mock_client.poll_research.return_value = {
            "status": "completed",
            "sources": [{"title": "A"}, {"title": "B"}, {"title": "C"}],
        }
        mock_client.import_research_sources.return_value = [
            {"title": "A"}, {"title": "B"}, {"title": "C"},
        ]

        result = import_research(mock_client, "nb-1", "task-1")

        assert result["imported_count"] == 3

    def test_import_selected_indices(self, mock_client):
        mock_client.poll_research.return_value = {
            "status": "completed",
            "sources": [{"title": "A"}, {"title": "B"}, {"title": "C"}],
        }
        mock_client.import_research_sources.return_value = [{"title": "B"}]

        result = import_research(mock_client, "nb-1", "task-1", source_indices=[1])

        # Verify the correct source was passed
        call_args = mock_client.import_research_sources.call_args
        assert call_args.kwargs["sources"] == [{"title": "B"}]

    def test_no_research_raises_service_error(self, mock_client):
        mock_client.poll_research.return_value = {"status": "no_research"}
        with pytest.raises(ServiceError, match="not found"):
            import_research(mock_client, "nb-1", "task-missing")

    def test_no_sources_raises_service_error(self, mock_client):
        mock_client.poll_research.return_value = {"status": "completed", "sources": []}
        with pytest.raises(ServiceError, match="No sources"):
            import_research(mock_client, "nb-1", "task-1")

    def test_invalid_indices_raises_validation_error(self, mock_client):
        mock_client.poll_research.return_value = {
            "status": "completed",
            "sources": [{"title": "A"}],
        }
        with pytest.raises(ValidationError, match="indices"):
            import_research(mock_client, "nb-1", "task-1", source_indices=[99])

    def test_import_api_error_raises_service_error(self, mock_client):
        mock_client.poll_research.return_value = {
            "status": "completed",
            "sources": [{"title": "A"}],
        }
        mock_client.import_research_sources.side_effect = RuntimeError("fail")
        with pytest.raises(ServiceError, match="Failed to import"):
            import_research(mock_client, "nb-1", "task-1")

    def test_falsy_import_result_raises_service_error(self, mock_client):
        mock_client.poll_research.return_value = {
            "status": "completed",
            "sources": [{"title": "A"}],
        }
        mock_client.import_research_sources.return_value = None
        with pytest.raises(ServiceError, match="no data"):
            import_research(mock_client, "nb-1", "task-1")

    def test_import_passes_custom_timeout(self, mock_client):
        """Verify that a custom timeout is forwarded to the client."""
        mock_client.poll_research.return_value = {
            "status": "completed",
            "sources": [{"title": "A"}],
        }
        mock_client.import_research_sources.return_value = [{"title": "A"}]

        import_research(mock_client, "nb-1", "task-1", timeout=600.0)

        call_kwargs = mock_client.import_research_sources.call_args.kwargs
        assert call_kwargs["timeout"] == 600.0

    def test_import_uses_default_timeout(self, mock_client):
        """Verify that the default 300s timeout is used when none specified."""
        mock_client.poll_research.return_value = {
            "status": "completed",
            "sources": [{"title": "A"}],
        }
        mock_client.import_research_sources.return_value = [{"title": "A"}]

        import_research(mock_client, "nb-1", "task-1")

        call_kwargs = mock_client.import_research_sources.call_args.kwargs
        assert call_kwargs["timeout"] == 300.0
