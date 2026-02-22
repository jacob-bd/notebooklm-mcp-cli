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
        
        answer, citation_data = mixin._parse_query_response("")
        
        assert answer == ""
        assert citation_data == {}

    def test_extract_answer_from_chunk_handles_invalid_json(self):
        """Test that _extract_answer_from_chunk handles invalid JSON."""
        mixin = ConversationMixin(cookies={"test": "cookie"}, csrf_token="test")
        
        text, is_answer, cdata = mixin._extract_answer_from_chunk("not valid json")
        
        assert text is None
        assert is_answer is False
        assert cdata == {}

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

        answer, _ = mixin._parse_query_response(raw)
        assert answer == answer_text

    def test_parse_response_returns_empty_on_no_error_no_answer(self):
        """No error and no answer returns empty string (not an exception)."""
        mixin = self._make_mixin()
        metadata_chunk = json.dumps([["di", 206]])
        raw = self._build_raw_response(metadata_chunk)

        answer, citation_data = mixin._parse_query_response(raw)
        assert answer == ""
        assert citation_data == {}

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


class TestCitationExtraction:
    """Test citation/source extraction from query response chunks."""

    def _make_mixin(self):
        return ConversationMixin(cookies={"test": "cookie"}, csrf_token="test")

    @staticmethod
    def _build_passage(passage_id: str, source_id: str, confidence: float = 0.75) -> list:
        """Build a realistic source passage entry for first_elem[4][3]."""
        return [
            [passage_id],
            [
                None,
                None,
                confidence,
                [[None, 0, 500]],
                [[[0, 500, [[[0, 500, ["Some source text passage content."]]]]]]],
                [[[source_id], "other-uuid-hash"]],
                [passage_id],
            ],
        ]

    @staticmethod
    def _build_answer_inner(answer_text: str, passages: list | None = None) -> str:
        """Build the inner JSON for a wrb.fr answer chunk with optional citation data."""
        type_info: list = [None, None, None]
        if passages is not None:
            type_info.append(passages)
            type_info.append(1)
        else:
            type_info.append(None)
            type_info.append(1)
        # first_elem: [text, null, conv_data, null, type_info]
        first_elem = [answer_text, None, ["conv-id", "hash", 12345], None, type_info]
        return json.dumps([first_elem])

    @staticmethod
    def _build_raw_response(*chunks: str) -> str:
        prefix = ")]}\'\n"
        parts = [prefix]
        for chunk in chunks:
            parts.append(str(len(chunk)))
            parts.append(chunk)
        return "\n".join(parts)

    def test_extract_citations_from_answer_chunk(self):
        """Answer chunk with source passages returns correct citation data."""
        mixin = self._make_mixin()
        passages = [
            self._build_passage("pass-1", "source-A"),
            self._build_passage("pass-2", "source-A"),
            self._build_passage("pass-3", "source-B"),
        ]
        answer = "Here are the results [1] and more details [2] from another doc [3]."
        inner = self._build_answer_inner(answer, passages)
        chunk = json.dumps([["wrb.fr", None, inner]])

        text, is_answer, cdata = mixin._extract_answer_from_chunk(chunk)

        assert text == answer
        assert is_answer is True
        assert cdata["sources_used"] == ["source-A", "source-B"]
        assert cdata["citations"] == {1: "source-A", 2: "source-A", 3: "source-B"}

    def test_extract_citations_preserves_source_order(self):
        """sources_used preserves first-seen order of source IDs."""
        mixin = self._make_mixin()
        passages = [
            self._build_passage("p1", "source-B"),
            self._build_passage("p2", "source-A"),
            self._build_passage("p3", "source-B"),
        ]
        inner = self._build_answer_inner("A long enough answer text to pass the length check.", passages)
        chunk = json.dumps([["wrb.fr", None, inner]])

        _, _, cdata = mixin._extract_answer_from_chunk(chunk)

        assert cdata["sources_used"] == ["source-B", "source-A"]

    def test_extract_citations_no_passages(self):
        """Answer chunk without source passages returns empty citation data."""
        mixin = self._make_mixin()
        inner = self._build_answer_inner("A long enough answer text to pass the length check.", passages=None)
        chunk = json.dumps([["wrb.fr", None, inner]])

        text, is_answer, cdata = mixin._extract_answer_from_chunk(chunk)

        assert text is not None
        assert is_answer is True
        assert cdata == {}

    def test_extract_citations_empty_passages_list(self):
        """Answer chunk with empty passages list returns empty citation data."""
        mixin = self._make_mixin()
        inner = self._build_answer_inner("A long enough answer text to pass the length check.", passages=[])
        chunk = json.dumps([["wrb.fr", None, inner]])

        _, _, cdata = mixin._extract_answer_from_chunk(chunk)

        assert cdata == {}

    def test_extract_citations_malformed_passage_skipped(self):
        """Malformed passage entries are skipped without crashing."""
        mixin = self._make_mixin()
        passages = [
            self._build_passage("p1", "source-A"),
            [["bad-passage"]],
            "not even a list",
            self._build_passage("p3", "source-B"),
        ]
        inner = self._build_answer_inner("A long enough answer text to pass the length check.", passages)
        chunk = json.dumps([["wrb.fr", None, inner]])

        _, _, cdata = mixin._extract_answer_from_chunk(chunk)

        assert cdata["sources_used"] == ["source-A", "source-B"]
        assert cdata["citations"] == {1: "source-A", 4: "source-B"}

    def test_thinking_chunk_has_no_citations(self):
        """Thinking chunks (type 2) do not return citation data."""
        mixin = self._make_mixin()
        type_info = [None, None, None, None, 2]
        first_elem = ["A long enough thinking step text for the check.", None, [], None, type_info]
        inner = json.dumps([first_elem])
        chunk = json.dumps([["wrb.fr", None, inner]])

        text, is_answer, cdata = mixin._extract_answer_from_chunk(chunk)

        assert text is not None
        assert is_answer is False
        assert cdata == {}

    def test_parse_response_returns_citation_data(self):
        """Full response parsing returns citation data from the longest answer chunk."""
        mixin = self._make_mixin()
        passages = [
            self._build_passage("p1", "src-X"),
            self._build_passage("p2", "src-Y"),
        ]
        short_answer = "Short answer text that is long enough."
        long_answer = "This is the longer answer text with citations [1] and [2] referencing sources."
        short_inner = self._build_answer_inner(short_answer, [self._build_passage("p0", "src-Z")])
        long_inner = self._build_answer_inner(long_answer, passages)
        short_chunk = json.dumps([["wrb.fr", None, short_inner]])
        long_chunk = json.dumps([["wrb.fr", None, long_inner]])
        raw = self._build_raw_response(short_chunk, long_chunk)

        answer, citation_data = mixin._parse_query_response(raw)

        assert answer == long_answer
        assert citation_data["sources_used"] == ["src-X", "src-Y"]
        assert citation_data["citations"] == {1: "src-X", 2: "src-Y"}

    def test_parse_response_no_citations_returns_empty_dict(self):
        """Response with answer but no citation data returns empty dict."""
        mixin = self._make_mixin()
        inner = json.dumps([["A long enough answer text to pass the length check.", None, [], None, [1]]])
        chunk = json.dumps([["wrb.fr", None, inner]])
        raw = self._build_raw_response(chunk)

        answer, citation_data = mixin._parse_query_response(raw)

        assert answer != ""
        assert citation_data == {}

    def test_static_extract_citation_data_handles_none_passages(self):
        """_extract_citation_data handles type_info with None at index 3."""
        result = ConversationMixin._extract_citation_data([None, None, None, None, 1])
        assert result == {}

    def test_static_extract_citation_data_handles_short_type_info(self):
        """_extract_citation_data handles type_info shorter than 4 elements."""
        result = ConversationMixin._extract_citation_data([1])
        assert result == {}
