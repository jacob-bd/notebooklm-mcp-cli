"""Tests for services.research module."""

from unittest.mock import MagicMock, patch

import pytest

from notebooklm_tools.core.errors import RPCError
from notebooklm_tools.services.errors import ServiceError, ValidationError
from notebooklm_tools.services.research import (
    import_research,
    poll_research,
    start_research,
)


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

    def test_rpc_error_provides_user_friendly_message(self, mock_client):
        """Issue #98: transient DeepResearchErrorDetail should give actionable message."""
        mock_client.start_research.side_effect = RPCError(
            "API error (code 3): DeepResearchErrorDetail",
            error_code=3,
            detail_type="type.googleapis.com/google.internal.labs.tailwind.orchestration.v1.DeepResearchErrorDetail",
            detail_data=[4],
        )
        with pytest.raises(ServiceError) as exc_info:
            start_research(mock_client, "nb-1", "quantum computing", mode="deep")

        assert "error code 3" in exc_info.value.user_message
        assert "DeepResearchErrorDetail" in exc_info.value.user_message
        assert "transient" in exc_info.value.user_message.lower()
        assert "--mode fast" in exc_info.value.user_message

    def test_rpc_error_extracts_short_detail_name(self, mock_client):
        """The service should show only the short detail name, not full type URL."""
        mock_client.start_research.side_effect = RPCError(
            "test",
            error_code=7,
            detail_type="type.googleapis.com/some.long.package.SpecificErrorDetail",
        )
        with pytest.raises(ServiceError) as exc_info:
            start_research(mock_client, "nb-1", "query")

        # Should use short name only
        assert "SpecificErrorDetail" in exc_info.value.user_message
        assert "type.googleapis.com" not in exc_info.value.user_message

    def test_rpc_error_not_swallowed_as_generic(self, mock_client):
        """RPCError must NOT be caught by the generic Exception handler."""
        mock_client.start_research.side_effect = RPCError(
            "API error (code 3)",
            error_code=3,
        )
        with pytest.raises(ServiceError) as exc_info:
            start_research(mock_client, "nb-1", "query")

        # Should mention method-specific error code, not generic "Failed to start research"
        assert "error code 3" in str(exc_info.value)

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

    def test_single_check_default(self, mock_client):
        """Default max_wait=0 does a single check and returns immediately."""
        mock_client.poll_research.return_value = {
            "status": "in_progress",
            "task_id": "task-1",
            "sources": [],
            "report": "",
        }

        result = poll_research(mock_client, "nb-1")

        assert result["status"] == "in_progress"
        assert mock_client.poll_research.call_count == 1

    @patch("notebooklm_tools.services.research.time")
    def test_blocking_polls_until_completed(self, mock_time, mock_client):
        """With max_wait > 0, polls repeatedly until status is completed."""
        # Simulate monotonic clock advancing by poll_interval each call
        mock_time.monotonic.side_effect = [0, 0, 5, 5, 10]
        mock_time.sleep = MagicMock()

        mock_client.poll_research.side_effect = [
            {"status": "in_progress", "task_id": "t-1", "sources": [], "report": ""},
            {
                "status": "completed",
                "task_id": "t-1",
                "sources": [{"title": "A"}],
                "report": "Done",
            },
        ]

        result = poll_research(mock_client, "nb-1", poll_interval=5, max_wait=30)

        assert result["status"] == "completed"
        assert mock_client.poll_research.call_count == 2
        mock_time.sleep.assert_called_once_with(5)

    @patch("notebooklm_tools.services.research.time")
    def test_blocking_respects_timeout(self, mock_time, mock_client):
        """Polling stops and returns in_progress when max_wait is exceeded."""
        # monotonic calls: [deadline calc, remaining check after poll]
        # deadline = 0 + 10 = 10; remaining = 10 - 11 = -1 → break
        mock_time.monotonic.side_effect = [0, 11]
        mock_time.sleep = MagicMock()

        mock_client.poll_research.return_value = {
            "status": "in_progress",
            "task_id": "t-1",
            "sources": [],
            "report": "",
        }

        result = poll_research(mock_client, "nb-1", poll_interval=5, max_wait=10)

        assert result["status"] == "in_progress"
        assert mock_client.poll_research.call_count == 1
        mock_time.sleep.assert_not_called()

    @patch("notebooklm_tools.services.research.time")
    def test_blocking_sleep_clamped_to_remaining(self, mock_time, mock_client):
        """Sleep duration is clamped to remaining time when less than poll_interval."""
        # monotonic calls: [deadline calc, remaining after poll 1, remaining after poll 2]
        # deadline = 0 + 8 = 8; remaining = 8 - 5 = 3 → sleep(min(5,3)=3);
        # remaining = 8 - 9 = -1 → break
        mock_time.monotonic.side_effect = [0, 5, 9]
        mock_time.sleep = MagicMock()

        mock_client.poll_research.side_effect = [
            {"status": "in_progress", "task_id": "t-1", "sources": [], "report": ""},
            {"status": "in_progress", "task_id": "t-1", "sources": [], "report": ""},
        ]

        result = poll_research(mock_client, "nb-1", poll_interval=5, max_wait=8)

        assert result["status"] == "in_progress"
        assert mock_client.poll_research.call_count == 2
        # Sleep should be clamped to remaining (3), not full poll_interval (5)
        mock_time.sleep.assert_called_once_with(3)

    @patch("notebooklm_tools.services.research.time")
    def test_blocking_no_research_returns_immediately(self, mock_time, mock_client):
        """If no research is found, returns immediately even with max_wait > 0."""
        mock_time.monotonic.side_effect = [0]
        mock_time.sleep = MagicMock()

        mock_client.poll_research.return_value = None

        result = poll_research(mock_client, "nb-1", max_wait=300)

        assert result["status"] == "no_research"
        assert mock_client.poll_research.call_count == 1
        mock_time.sleep.assert_not_called()


class TestImportResearch:
    """Test import_research service function."""

    def test_import_all_sources(self, mock_client):
        mock_client.poll_research.return_value = {
            "status": "completed",
            "sources": [{"title": "A"}, {"title": "B"}, {"title": "C"}],
        }
        mock_client.import_research_sources.return_value = [
            {"title": "A"},
            {"title": "B"},
            {"title": "C"},
        ]

        result = import_research(mock_client, "nb-1", "task-1")

        assert result["imported_count"] == 3

    def test_import_selected_indices(self, mock_client):
        mock_client.poll_research.return_value = {
            "status": "completed",
            "sources": [{"title": "A"}, {"title": "B"}, {"title": "C"}],
        }
        mock_client.import_research_sources.return_value = [{"title": "B"}]

        import_research(mock_client, "nb-1", "task-1", source_indices=[1])

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
