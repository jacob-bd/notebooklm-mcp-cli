#!/usr/bin/env python3
"""Tests for ConversationMixin."""

import json

import pytest
from unittest.mock import patch

from notebooklm_tools.core.base import BaseClient
from notebooklm_tools.core.conversation import ConversationMixin, QueryRejectedError


class TestConversationMixinImport:
    """Test that ConversationMixin can be imported correctly."""

    def test_conversation_mixin_import(self):
        """Test that ConversationMixin can be imported."""
        assert ConversationMixin is not None

    def test_conversation_mixin_inherits_base(self):
        """Test that ConversationMixin inherits from BaseClient."""
        assert issubclass(ConversationMixin, BaseClient)

    def test_conversation_mixin_has_methods(self):
        """Test that ConversationMixin has expected methods."""
        expected_methods = [
            "query",
            "clear_conversation",
            "get_conversation_history",
            "_build_conversation_history",
            "_cache_conversation_turn",
            "_parse_query_response",
            "_extract_answer_from_chunk",
            "_extract_source_ids_from_notebook",
        ]
        for method in expected_methods:
            assert hasattr(ConversationMixin, method), f"Missing method: {method}"


class TestConversationMixinMethods:
    """Test ConversationMixin method behavior."""

    def test_clear_conversation_removes_from_cache(self):
        """Test that clear_conversation removes conversation from cache."""
        mixin = ConversationMixin(cookies={"test": "cookie"}, csrf_token="test")
        
        # Add a conversation to cache
        mixin._conversation_cache["test-conv-id"] = []
        
        # Clear it
        result = mixin.clear_conversation("test-conv-id")
        
        assert result is True
        assert "test-conv-id" not in mixin._conversation_cache

    def test_clear_conversation_returns_false_if_not_found(self):
        """Test that clear_conversation returns False if conversation not in cache."""
        mixin = ConversationMixin(cookies={"test": "cookie"}, csrf_token="test")
        
        result = mixin.clear_conversation("nonexistent-id")
        
        assert result is False

    def test_get_conversation_history_returns_none_if_not_found(self):
        """Test that get_conversation_history returns None if conversation not in cache."""
        mixin = ConversationMixin(cookies={"test": "cookie"}, csrf_token="test")
        
        result = mixin.get_conversation_history("nonexistent-id")
        
        assert result is None

    def test_parse_query_response_handles_empty(self):
        """Test that _parse_query_response handles empty input."""
        mixin = ConversationMixin(cookies={"test": "cookie"}, csrf_token="test")
        
        result = mixin._parse_query_response("")
        
        assert result == ""

    def test_extract_answer_from_chunk_handles_invalid_json(self):
        """Test that _extract_answer_from_chunk handles invalid JSON."""
        mixin = ConversationMixin(cookies={"test": "cookie"}, csrf_token="test")
        
        result = mixin._extract_answer_from_chunk("not valid json")
        
        assert result == (None, False)

    def test_extract_source_ids_from_notebook_handles_none(self):
        """Test that _extract_source_ids_from_notebook handles None input."""
        mixin = ConversationMixin(cookies={"test": "cookie"}, csrf_token="test")
        
        result = mixin._extract_source_ids_from_notebook(None)
        
        assert result == []

    def test_extract_source_ids_from_notebook_handles_empty_list(self):
        """Test that _extract_source_ids_from_notebook handles empty list."""
        mixin = ConversationMixin(cookies={"test": "cookie"}, csrf_token="test")
        
        result = mixin._extract_source_ids_from_notebook([])
        
        assert result == []


class TestErrorDetection:
    """Test Google API error detection in query response parsing."""

    def _make_mixin(self):
        return ConversationMixin(cookies={"test": "cookie"}, csrf_token="test")

    def test_extract_error_simple_code(self):
        """Error code 3 (INVALID_ARGUMENT) in wrb.fr chunk."""
        mixin = self._make_mixin()
        chunk = json.dumps([["wrb.fr", None, None, None, None, [3]]])
        result = mixin._extract_error_from_chunk(chunk)

        assert result is not None
        assert result["code"] == 3
        assert result["type"] == ""

    def test_extract_error_with_type_info(self):
        """Error code 8 with UserDisplayableError type."""
        mixin = self._make_mixin()
        error_type = "type.googleapis.com/google.internal.labs.tailwind.orchestration.v1.UserDisplayableError"
        chunk = json.dumps([
            ["wrb.fr", None, None, None, None,
             [8, None, [[error_type, [None, [None, [[1]]]]]]]]
        ])
        result = mixin._extract_error_from_chunk(chunk)

        assert result is not None
        assert result["code"] == 8
        assert result["type"] == error_type

    def test_extract_error_returns_none_for_normal_chunk(self):
        """Normal wrb.fr chunk with answer data should not be detected as error."""
        mixin = self._make_mixin()
        inner = json.dumps([["This is a long enough answer text for the test to pass properly.", None, [], None, [1]]])
        chunk = json.dumps([["wrb.fr", None, inner, None, None, None]])
        result = mixin._extract_error_from_chunk(chunk)

        assert result is None

    def test_extract_error_returns_none_for_invalid_json(self):
        mixin = self._make_mixin()
        assert mixin._extract_error_from_chunk("not json") is None

    def test_extract_error_returns_none_for_non_wrb_chunk(self):
        mixin = self._make_mixin()
        chunk = json.dumps([["di", 123], ["af.httprm", 456]])
        assert mixin._extract_error_from_chunk(chunk) is None

    @staticmethod
    def _build_raw_response(*chunks: str) -> str:
        """Build a raw Google API response with anti-XSSI prefix."""
        prefix = ")]}\'\n"
        parts = [prefix]
        for chunk in chunks:
            parts.append(str(len(chunk)))
            parts.append(chunk)
        return "\n".join(parts)

    def test_parse_response_raises_on_error_code_3(self):
        """Full response with error code 3 raises QueryRejectedError."""
        mixin = self._make_mixin()
        error_chunk = json.dumps([["wrb.fr", None, None, None, None, [3]]])
        metadata_chunk = json.dumps([["di", 206], ["af.httprm", 205, "-1728080960086747572", 21]])
        raw = self._build_raw_response(error_chunk, metadata_chunk)

        with pytest.raises(QueryRejectedError) as exc_info:
            mixin._parse_query_response(raw)

        assert exc_info.value.error_code == 3
        assert exc_info.value.code_name == "INVALID_ARGUMENT"

    def test_parse_response_raises_on_user_displayable_error(self):
        """Full response with UserDisplayableError raises QueryRejectedError."""
        mixin = self._make_mixin()
        error_type = "type.googleapis.com/google.internal.labs.tailwind.orchestration.v1.UserDisplayableError"
        error_chunk = json.dumps([
            ["wrb.fr", None, None, None, None,
             [8, None, [[error_type, [None, [None, [[1]]]]]]]]
        ])
        raw = self._build_raw_response(error_chunk)

        with pytest.raises(QueryRejectedError) as exc_info:
            mixin._parse_query_response(raw)

        assert exc_info.value.error_code == 8
        assert "UserDisplayableError" in exc_info.value.error_type

    def test_parse_response_prefers_answer_over_error(self):
        """If both an answer and error are present, answer wins."""
        mixin = self._make_mixin()
        answer_text = "This is a sufficiently long answer text that should be returned."
        inner = json.dumps([[answer_text, None, [], None, [1]]])
        answer_chunk = json.dumps([["wrb.fr", None, inner]])
        error_chunk = json.dumps([["wrb.fr", None, None, None, None, [3]]])
        raw = self._build_raw_response(answer_chunk, error_chunk)

        result = mixin._parse_query_response(raw)
        assert result == answer_text

    def test_parse_response_returns_empty_on_no_error_no_answer(self):
        """No error and no answer returns empty string (not an exception)."""
        mixin = self._make_mixin()
        metadata_chunk = json.dumps([["di", 206]])
        raw = self._build_raw_response(metadata_chunk)

        result = mixin._parse_query_response(raw)
        assert result == ""

    def test_query_rejected_error_attributes(self):
        """QueryRejectedError has correct attributes and message."""
        err = QueryRejectedError(error_code=3, error_type="SomeType")
        assert err.error_code == 3
        assert err.code_name == "INVALID_ARGUMENT"
        assert "error code 3" in str(err)
        assert "INVALID_ARGUMENT" in str(err)
        assert "SomeType" in str(err)

    def test_query_rejected_error_unknown_code(self):
        """Unknown error codes get 'UNKNOWN' label."""
        err = QueryRejectedError(error_code=999)
        assert err.code_name == "UNKNOWN"
        assert "error code 999" in str(err)
