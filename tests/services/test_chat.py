"""Tests for services.chat module."""

from unittest.mock import MagicMock, patch

import pytest

from notebooklm_tools.services.chat import (
    configure_chat,
    delete_chat_history,
    query,
    query_start,
    query_status,
)
from notebooklm_tools.services.errors import ServiceError, ValidationError


@pytest.fixture
def mock_client():
    return MagicMock()


class TestQuery:
    """Test query service function."""

    def test_successful_query(self, mock_client):
        mock_client.query.return_value = {
            "answer": "The answer is 42.",
            "conversation_id": "conv-123",
            "sources_used": ["src-1", "src-2"],
            "citations": {1: "src-1", 2: "src-1", 3: "src-2"},
        }

        result = query(mock_client, "nb-123", "What is the meaning?")

        assert result["answer"] == "The answer is 42."
        assert result["conversation_id"] == "conv-123"
        assert result["sources_used"] == ["src-1", "src-2"]
        assert result["citations"] == {1: "src-1", 2: "src-1", 3: "src-2"}

    def test_empty_query_raises_validation_error(self, mock_client):
        with pytest.raises(ValidationError, match="Query text is required"):
            query(mock_client, "nb-123", "")

    @patch("notebooklm_tools.services.chat.notebook_service")
    def test_empty_notebook_raises_validation_error(self, mock_notebook_service, mock_client):
        """Querying an empty notebook should raise a ValidationError."""
        mock_notebook_service.get_notebook.return_value = {"source_count": 0}
        with pytest.raises(ValidationError, match="Cannot query an empty notebook"):
            query(mock_client, "nb-123", "question")

    def test_whitespace_query_raises_validation_error(self, mock_client):
        with pytest.raises(ValidationError, match="Query text is required"):
            query(mock_client, "nb-123", "   ")

    def test_falsy_result_raises_service_error(self, mock_client):
        mock_client.query.return_value = None
        with pytest.raises(ServiceError, match="empty result"):
            query(mock_client, "nb-123", "question")

    def test_api_error_raises_service_error(self, mock_client):
        mock_client.query.side_effect = RuntimeError("timeout")
        with pytest.raises(ServiceError, match="Query failed"):
            query(mock_client, "nb-123", "question")

    def test_source_ids_passed_through(self, mock_client):
        mock_client.query.return_value = {"answer": "ok"}
        query(mock_client, "nb-123", "question", source_ids=["src-1"])
        mock_client.query.assert_called_once_with(
            notebook_id="nb-123",
            query_text="question",
            source_ids=["src-1"],
            conversation_id=None,
        )

    def test_timeout_passed_through(self, mock_client):
        mock_client.query.return_value = {"answer": "ok"}
        query(mock_client, "nb-123", "question", timeout=30.0)
        mock_client.query.assert_called_once_with(
            notebook_id="nb-123",
            query_text="question",
            source_ids=None,
            conversation_id=None,
            timeout=30.0,
        )


class TestConfigureChat:
    """Test configure_chat service function."""

    def test_successful_default_config(self, mock_client):
        mock_client.configure_chat.return_value = {"status": "ok"}

        result = configure_chat(mock_client, "nb-123")

        assert result["goal"] == "default"
        assert result["response_length"] == "default"
        assert "updated" in result["message"].lower()

    def test_invalid_goal_raises_validation_error(self, mock_client):
        with pytest.raises(ValidationError, match="Invalid goal"):
            configure_chat(mock_client, "nb-123", goal="invalid")

    def test_custom_goal_without_prompt_raises_validation_error(self, mock_client):
        with pytest.raises(ValidationError, match="Custom prompt is required"):
            configure_chat(mock_client, "nb-123", goal="custom")

    def test_custom_goal_with_prompt_works(self, mock_client):
        mock_client.configure_chat.return_value = {"status": "ok"}

        result = configure_chat(
            mock_client,
            "nb-123",
            goal="custom",
            custom_prompt="Be a pirate.",
        )

        assert result["goal"] == "custom"

    def test_prompt_too_long_raises_validation_error(self, mock_client):
        long_prompt = "x" * 10_001
        with pytest.raises(ValidationError, match="10000 character"):
            configure_chat(
                mock_client,
                "nb-123",
                goal="custom",
                custom_prompt=long_prompt,
            )

    def test_invalid_response_length_raises_validation_error(self, mock_client):
        with pytest.raises(ValidationError, match="Invalid response_length"):
            configure_chat(mock_client, "nb-123", response_length="huge")

    def test_learning_guide_goal_works(self, mock_client):
        mock_client.configure_chat.return_value = {"status": "ok"}

        result = configure_chat(mock_client, "nb-123", goal="learning_guide")

        assert result["goal"] == "learning_guide"

    def test_shorter_response_length_works(self, mock_client):
        mock_client.configure_chat.return_value = {"status": "ok"}

        result = configure_chat(mock_client, "nb-123", response_length="shorter")

        assert result["response_length"] == "shorter"

    def test_falsy_result_raises_service_error(self, mock_client):
        mock_client.configure_chat.return_value = None
        with pytest.raises(ServiceError, match="falsy result"):
            configure_chat(mock_client, "nb-123")

    def test_api_error_raises_service_error(self, mock_client):
        mock_client.configure_chat.side_effect = RuntimeError("fail")
        with pytest.raises(ServiceError, match="Failed to configure"):
            configure_chat(mock_client, "nb-123")


class TestDeleteChatHistory:
    """Test delete_chat_history service function."""

    def test_successful_deletion(self, mock_client):
        mock_client.get_conversation_id.return_value = "conv-123"
        mock_client.delete_chat_history.return_value = True

        result = delete_chat_history(mock_client, "nb-123")

        assert result["notebook_id"] == "nb-123"
        assert "deleted" in result["message"].lower()
        mock_client.delete_chat_history.assert_called_once_with("nb-123", "conv-123")

    def test_no_history_raises_service_error(self, mock_client):
        mock_client.get_conversation_id.return_value = None

        with pytest.raises(ServiceError, match="No chat history"):
            delete_chat_history(mock_client, "nb-123")

    def test_api_failure_raises_service_error(self, mock_client):
        mock_client.get_conversation_id.return_value = "conv-123"
        mock_client.delete_chat_history.side_effect = RuntimeError("server error")

        with pytest.raises(ServiceError, match="Failed to delete"):
            delete_chat_history(mock_client, "nb-123")


class TestQueryStart:
    """Test async query_start service function."""

    def test_returns_immediately_with_query_id(self, mock_client):
        # Make the mock query block for 2 seconds to prove we return immediately
        import time as _time

        def slow_query(**kwargs):
            _time.sleep(2)
            return {"answer": "done"}

        mock_client.query.side_effect = slow_query

        start = _time.monotonic()
        result = query_start(mock_client, "nb-123", "question")
        elapsed = _time.monotonic() - start

        assert elapsed < 1.0, "query_start should return immediately"
        assert "query_id" in result
        assert result["status"] == "in_progress"
        assert len(result["query_id"]) == 12

    def test_empty_query_raises_validation_error(self, mock_client):
        with pytest.raises(ValidationError, match="Query text is required"):
            query_start(mock_client, "nb-123", "")

    @patch("notebooklm_tools.services.chat.notebook_service")
    def test_empty_notebook_raises_validation_error(self, mock_notebook_service, mock_client):
        """Querying an empty notebook via async query_start should raise ValidationError."""
        mock_notebook_service.get_notebook.return_value = {"source_count": 0}
        with pytest.raises(ValidationError, match="Cannot query an empty notebook"):
            query_start(mock_client, "nb-123", "question")

    def test_whitespace_query_raises_validation_error(self, mock_client):
        with pytest.raises(ValidationError, match="Query text is required"):
            query_start(mock_client, "nb-123", "   ")

    def test_multiple_starts_get_unique_ids(self, mock_client):
        mock_client.query.return_value = {"answer": "ok"}
        r1 = query_start(mock_client, "nb-123", "q1")
        r2 = query_start(mock_client, "nb-123", "q2")
        assert r1["query_id"] != r2["query_id"]

    def test_ttl_cleanup_evicts_expired(self, mock_client):
        """Verify stale entries get cleaned up on the next query_start call."""
        import time as _time

        from notebooklm_tools.services.chat import (
            _pending_lock,
            _pending_queries,
        )

        mock_client.query.return_value = {"answer": "ok"}

        # Manually inject an expired entry
        with _pending_lock:
            _pending_queries["expired-id"] = {
                "status": "in_progress",
                "result": None,
                "error": None,
                "created_at": _time.monotonic() - 9999,
            }

        # Starting a new query should trigger cleanup
        query_start(mock_client, "nb-123", "question")

        with _pending_lock:
            assert "expired-id" not in _pending_queries


class TestQueryStatus:
    """Test async query_status service function."""

    def test_completed_query_returns_result(self, mock_client):
        import time as _time

        mock_client.query.return_value = {
            "answer": "The answer is 42.",
            "conversation_id": "conv-1",
            "sources_used": [],
            "citations": {},
            "references": [],
        }

        result = query_start(mock_client, "nb-123", "question")
        query_id = result["query_id"]

        # Wait for background thread to finish
        _time.sleep(1)

        status = query_status(query_id)
        assert status["status"] == "completed"
        assert status["result"]["answer"] == "The answer is 42."

    def test_in_progress_query(self, mock_client):
        import time as _time

        def slow_query(**kwargs):
            _time.sleep(5)
            return {"answer": "done"}

        mock_client.query.side_effect = slow_query

        result = query_start(mock_client, "nb-123", "question")
        query_id = result["query_id"]

        # Check immediately - should still be in progress
        status = query_status(query_id)
        assert status["status"] == "in_progress"
        assert status["result"] is None

    def test_error_query_returns_error_message(self, mock_client):
        import time as _time

        mock_client.query.side_effect = RuntimeError("API exploded")

        result = query_start(mock_client, "nb-123", "question")
        query_id = result["query_id"]

        # Wait for background thread to fail
        _time.sleep(1)

        status = query_status(query_id)
        assert status["status"] == "error"
        assert "API exploded" in status["error"]

    def test_unknown_query_id_raises_validation_error(self, mock_client):
        with pytest.raises(ValidationError, match="not found"):
            query_status("nonexistent-id")

    def test_completed_entry_cleaned_after_read(self, mock_client):
        import time as _time

        mock_client.query.return_value = {"answer": "ok"}

        result = query_start(mock_client, "nb-123", "question")
        query_id = result["query_id"]

        _time.sleep(1)

        # First read should return the result
        status = query_status(query_id)
        assert status["status"] == "completed"

        # Second read should fail because the entry was cleaned up
        with pytest.raises(ValidationError, match="not found"):
            query_status(query_id)
