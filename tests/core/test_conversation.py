#!/usr/bin/env python3
"""Tests for ConversationMixin."""

import json
from unittest.mock import ANY, patch

import pytest

from notebooklm_tools.core.base import BaseClient
from notebooklm_tools.core.conversation import ConversationMixin, QueryRejectedError
from notebooklm_tools.core.data_types import ConversationTurn


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
            "get_conversation_id",
            "delete_chat_history",
            "_build_conversation_history",
            "_cache_conversation_turn",
            "_parse_query_response",
            "_extract_answer_from_chunk",
            "_extract_source_ids_from_notebook",
        ]
        for method in expected_methods:
            assert hasattr(ConversationMixin, method), f"Missing method: {method}"


class TestGetConversationId:
    """Test get_conversation_id method for fetching server-side conversation IDs."""

    def _make_mixin(self):
        return ConversationMixin(cookies={"test": "cookie"}, csrf_token="test")

    def test_returns_id_from_nested_list(self):
        """Server returns [[conv_id, ...]] — extract the conv_id string."""
        mixin = self._make_mixin()
        with patch.object(mixin, "_call_rpc", return_value=[["conv-uuid-123", None, 12345]]):
            result = mixin.get_conversation_id("nb-123")
        assert result == "conv-uuid-123"

    def test_returns_id_from_flat_string_list(self):
        """Server returns [[conv_id]] — double-nested format."""
        mixin = self._make_mixin()
        with patch.object(mixin, "_call_rpc", return_value=[["conv-uuid-456"]]):
            result = mixin.get_conversation_id("nb-123")
        assert result == "conv-uuid-456"

    def test_returns_none_on_null_response(self):
        """Server returns None — no conversation exists."""
        mixin = self._make_mixin()
        with patch.object(mixin, "_call_rpc", return_value=None):
            result = mixin.get_conversation_id("nb-123")
        assert result is None

    def test_returns_none_on_empty_list(self):
        """Server returns [] — no conversation exists."""
        mixin = self._make_mixin()
        with patch.object(mixin, "_call_rpc", return_value=[]):
            result = mixin.get_conversation_id("nb-123")
        assert result is None

    def test_returns_none_on_malformed_inner_list(self):
        """Server returns [[]] — malformed but no crash."""
        mixin = self._make_mixin()
        with patch.object(mixin, "_call_rpc", return_value=[[]]):
            result = mixin.get_conversation_id("nb-123")
        assert result is None

    def test_returns_none_on_rpc_exception(self):
        """RPC call fails — returns None gracefully, not an exception."""
        mixin = self._make_mixin()
        with patch.object(mixin, "_call_rpc", side_effect=Exception("network error")):
            result = mixin.get_conversation_id("nb-123")
        assert result is None

    def test_calls_correct_rpc(self):
        """Verifies it calls the correct RPC ID with right params."""
        mixin = self._make_mixin()
        with patch.object(mixin, "_call_rpc", return_value=None) as mock_rpc:
            mixin.get_conversation_id("nb-123")
        mock_rpc.assert_called_once_with(
            mixin.RPC_GET_CONVERSATIONS,
            [[], None, "nb-123", 20],
            path="/notebook/nb-123",
        )


class TestDeleteChatHistory:
    """Test delete_chat_history method."""

    def _make_mixin(self):
        return ConversationMixin(cookies={"test": "cookie"}, csrf_token="test")

    def test_delete_success(self):
        """Server acknowledges deletion — returns True."""
        mixin = self._make_mixin()
        with patch.object(mixin, "_call_rpc", return_value=[]):
            result = mixin.delete_chat_history("nb-123", "conv-456")
        assert result is True

    def test_delete_clears_local_cache(self):
        """Deletion also clears the local conversation cache."""
        mixin = self._make_mixin()
        mixin._conversation_cache["conv-456"] = [
            ConversationTurn(query="q", answer="a", turn_number=1)
        ]
        with patch.object(mixin, "_call_rpc", return_value=[]):
            mixin.delete_chat_history("nb-123", "conv-456")
        assert "conv-456" not in mixin._conversation_cache

    def test_delete_no_local_cache_no_crash(self):
        """Deletion when no local cache exists doesn't crash."""
        mixin = self._make_mixin()
        with patch.object(mixin, "_call_rpc", return_value=[]):
            result = mixin.delete_chat_history("nb-123", "conv-789")
        assert result is True

    def test_calls_correct_rpc(self):
        """Verifies it calls the correct RPC ID with right params."""
        mixin = self._make_mixin()
        with patch.object(mixin, "_call_rpc", return_value=[]) as mock_rpc:
            mixin.delete_chat_history("nb-123", "conv-456")
        mock_rpc.assert_called_once_with(
            mixin.RPC_DELETE_CHAT_HISTORY,
            ["nb-123", "conv-456"],
            path="/notebook/nb-123",
        )


class TestQueryUsesServerConversationId:
    """Test that query() fetches server-side conversation ID when no ID is provided."""

    def _make_mixin(self):
        return ConversationMixin(cookies={"test": "cookie"}, csrf_token="test")

    def test_uses_server_conversation_id(self):
        """When server has a conversation ID, query() uses it instead of uuid."""
        mixin = self._make_mixin()
        with (
            patch.object(mixin, "get_conversation_id", return_value="server-conv-id"),
            patch("notebooklm_tools.core.conversation._httpx.Client") as mock_client_class,
        ):
            mock_response = mock_client_class.return_value.__enter__.return_value.post.return_value
            mock_response.text = ")]}'\n100\n" + json.dumps(
                [
                    [
                        "wrb.fr",
                        None,
                        json.dumps([["A long answer from the server.", None, [], None, [1]]]),
                    ]
                ]
            )
            mock_response.raise_for_status = lambda: None

            result = mixin.query("nb-123", "Hello?", source_ids=["src-1"])

        mock_client_class.assert_called_once_with(
            timeout=120.0,
            cookies=ANY,
            headers={"Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"},
        )
        assert result["conversation_id"] == "server-conv-id"

    def test_falls_back_to_uuid_when_no_server_id(self):
        """When server returns None, query() generates a random UUID."""
        mixin = self._make_mixin()
        with (
            patch.object(mixin, "get_conversation_id", return_value=None),
            patch("notebooklm_tools.core.conversation._httpx.Client") as mock_client_class,
        ):
            mock_response = mock_client_class.return_value.__enter__.return_value.post.return_value
            mock_response.text = ")]}'\n100\n" + json.dumps(
                [
                    [
                        "wrb.fr",
                        None,
                        json.dumps([["A long answer from the server.", None, [], None, [1]]]),
                    ]
                ]
            )
            mock_response.raise_for_status = lambda: None

            result = mixin.query("nb-123", "Hello?", source_ids=["src-1"])

        # Should be a valid UUID (36 chars with hyphens)
        assert result["conversation_id"] != "server-conv-id"
        assert len(result["conversation_id"]) == 36


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

        answer, citation_data, _ = mixin._parse_query_response("")

        assert answer == ""
        assert citation_data == {}

    def test_extract_answer_from_chunk_handles_invalid_json(self):
        """Test that _extract_answer_from_chunk handles invalid JSON."""
        mixin = ConversationMixin(cookies={"test": "cookie"}, csrf_token="test")

        text, is_answer, cdata, _ = mixin._extract_answer_from_chunk("not valid json")

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
        chunk = json.dumps(
            [["wrb.fr", None, None, None, None, [8, None, [[error_type, [None, [None, [[1]]]]]]]]]
        )
        result = mixin._extract_error_from_chunk(chunk)

        assert result is not None
        assert result["code"] == 8
        assert result["type"] == error_type

    def test_extract_error_returns_none_for_normal_chunk(self):
        """Normal wrb.fr chunk with answer data should not be detected as error."""
        mixin = self._make_mixin()
        inner = json.dumps(
            [
                [
                    "This is a long enough answer text for the test to pass properly.",
                    None,
                    [],
                    None,
                    [1],
                ]
            ]
        )
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
        prefix = ")]}'\n"
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
        error_chunk = json.dumps(
            [["wrb.fr", None, None, None, None, [8, None, [[error_type, [None, [None, [[1]]]]]]]]]
        )
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

        answer, _, _ = mixin._parse_query_response(raw)
        assert answer == answer_text

    def test_parse_response_returns_empty_on_no_error_no_answer(self):
        """No error and no answer returns empty string (not an exception)."""
        mixin = self._make_mixin()
        metadata_chunk = json.dumps([["di", 206]])
        raw = self._build_raw_response(metadata_chunk)

        answer, citation_data, _ = mixin._parse_query_response(raw)
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
        prefix = ")]}'\n"
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

        text, is_answer, cdata, _ = mixin._extract_answer_from_chunk(chunk)

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
        inner = self._build_answer_inner(
            "A long enough answer text to pass the length check.", passages
        )
        chunk = json.dumps([["wrb.fr", None, inner]])

        _, _, cdata, _ = mixin._extract_answer_from_chunk(chunk)

        assert cdata["sources_used"] == ["source-B", "source-A"]

    def test_extract_citations_no_passages(self):
        """Answer chunk without source passages returns empty citation data."""
        mixin = self._make_mixin()
        inner = self._build_answer_inner(
            "A long enough answer text to pass the length check.", passages=None
        )
        chunk = json.dumps([["wrb.fr", None, inner]])

        text, is_answer, cdata, _ = mixin._extract_answer_from_chunk(chunk)

        assert text is not None
        assert is_answer is True
        assert cdata == {}

    def test_extract_citations_empty_passages_list(self):
        """Answer chunk with empty passages list returns empty citation data."""
        mixin = self._make_mixin()
        inner = self._build_answer_inner(
            "A long enough answer text to pass the length check.", passages=[]
        )
        chunk = json.dumps([["wrb.fr", None, inner]])

        _, _, cdata, _ = mixin._extract_answer_from_chunk(chunk)

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
        inner = self._build_answer_inner(
            "A long enough answer text to pass the length check.", passages
        )
        chunk = json.dumps([["wrb.fr", None, inner]])

        _, _, cdata, _ = mixin._extract_answer_from_chunk(chunk)

        assert cdata["sources_used"] == ["source-A", "source-B"]
        assert cdata["citations"] == {1: "source-A", 4: "source-B"}

    def test_thinking_chunk_has_no_citations(self):
        """Thinking chunks (type 2) do not return citation data."""
        mixin = self._make_mixin()
        type_info = [None, None, None, None, 2]
        first_elem = ["A long enough thinking step text for the check.", None, [], None, type_info]
        inner = json.dumps([first_elem])
        chunk = json.dumps([["wrb.fr", None, inner]])

        text, is_answer, cdata, _ = mixin._extract_answer_from_chunk(chunk)

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
        long_answer = (
            "This is the longer answer text with citations [1] and [2] referencing sources."
        )
        short_inner = self._build_answer_inner(short_answer, [self._build_passage("p0", "src-Z")])
        long_inner = self._build_answer_inner(long_answer, passages)
        short_chunk = json.dumps([["wrb.fr", None, short_inner]])
        long_chunk = json.dumps([["wrb.fr", None, long_inner]])
        raw = self._build_raw_response(short_chunk, long_chunk)

        answer, citation_data, _ = mixin._parse_query_response(raw)

        assert answer == long_answer
        assert citation_data["sources_used"] == ["src-X", "src-Y"]
        assert citation_data["citations"] == {1: "src-X", 2: "src-Y"}

    def test_parse_response_no_citations_returns_empty_dict(self):
        """Response with answer but no citation data returns empty dict."""
        mixin = self._make_mixin()
        inner = json.dumps(
            [["A long enough answer text to pass the length check.", None, [], None, [1]]]
        )
        chunk = json.dumps([["wrb.fr", None, inner]])
        raw = self._build_raw_response(chunk)

        answer, citation_data, _ = mixin._parse_query_response(raw)

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


class TestCitedTextParsing:
    """Test _extract_cited_text with direct segments, wrapped segments, and tables."""

    def test_wrapped_segments_extract_text(self):
        """Wrapped segments [[seg], ...] extract text correctly (original format)."""
        detail = [
            None,
            None,
            0.75,
            None,
            [
                [[0, 50, [[[0, 50, ["Hello world."]]]]]],
            ],
        ]
        result = ConversationMixin._extract_cited_text(detail)
        assert result == "Hello world."

    def test_direct_segments_extract_text(self):
        """Direct segments [int, int, nested] extract text correctly (PR #84 fix)."""
        detail = [
            None,
            None,
            0.75,
            None,
            [[0, 100, [[[0, 100, ["Direct segment text."]]]]]],
        ]
        result = ConversationMixin._extract_cited_text(detail)
        assert result == "Direct segment text."

    def test_mixed_direct_and_wrapped_segments(self):
        """Both direct and wrapped segments are extracted together."""
        detail = [
            None,
            None,
            0.75,
            None,
            [
                # Wrapped segment
                [[0, 30, [[[0, 30, ["Wrapped text."]]]]]],
                # Direct segment
                [31, 60, [[[31, 60, ["Direct text."]]]]],
            ],
        ]
        result = ConversationMixin._extract_cited_text(detail)
        assert result == "Wrapped text. Direct text."

    def test_table_segment_inserts_placeholder(self):
        """Table segments (nested=null, data at segment[4]) insert <cited_table>."""
        # Table segment: [start, end, null, null, [dim1, dim2, rows_array]]
        # Use minimal but valid rows so the table detection triggers
        cell_a = [0, 10, [[0, 1, [[[[0, 1, ["A"]], None]]]]]]
        cell_b = [11, 20, [[0, 1, [[[[0, 1, ["B"]], None]]]]]]
        table_rows = [[0, 50, [cell_a, cell_b]]]
        detail = [
            None,
            None,
            0.75,
            None,
            [
                [0, 100, None, None, [2, 1, table_rows]],
            ],
        ]
        result = ConversationMixin._extract_cited_text(detail)
        assert result == "<cited_table>"

    def test_text_and_table_segments_combined(self):
        """Text followed by table produces text with placeholder."""
        cell_x = [0, 10, [[0, 1, [[[[0, 1, ["X"]], None]]]]]]
        cell_y = [11, 20, [[0, 1, [[[[0, 1, ["Y"]], None]]]]]]
        table_rows = [[0, 50, [cell_x, cell_y]]]
        detail = [
            None,
            None,
            0.75,
            None,
            [
                [0, 30, [[[0, 30, ["Some intro text."]]]]],
                [31, 100, None, None, [2, 1, table_rows]],
            ],
        ]
        result = ConversationMixin._extract_cited_text(detail)
        assert result == "Some intro text. <cited_table>"

    def test_detail_too_short_returns_none(self):
        """detail with fewer than 5 elements returns None."""
        assert ConversationMixin._extract_cited_text([None, None, 0.75, None]) is None

    def test_detail_index_4_not_list_returns_none(self):
        """detail[4] being non-list returns None."""
        assert ConversationMixin._extract_cited_text([None, None, 0.75, None, "not a list"]) is None

    def test_empty_elements_returns_none(self):
        """Empty elements in detail[4] are skipped, returns None."""
        detail = [None, None, 0.75, None, [[], None, "string"]]
        assert ConversationMixin._extract_cited_text(detail) is None


class TestTableRowParsing:
    """Test _extract_text_from_table_rows for structured table extraction."""

    @staticmethod
    def _make_cell(text: str) -> list:
        """Build a single table cell matching _extract_text_from_table_rows format.

        Structure: [start, end, [[sub_start, sub_end, [content_item]]]]
        content_item: [[text_start, text_end, text_val]]
        """
        return [0, 10, [[0, len(text), [[[0, len(text), text]]]]]]

    @staticmethod
    def _make_row(start: int, end: int, cells: list) -> list:
        """Build a table row."""
        return [start, end, cells]

    def test_simple_table(self):
        """Parse a simple 2x2 table."""
        rows = [
            self._make_row(0, 50, [self._make_cell("Header1"), self._make_cell("Header2")]),
            self._make_row(51, 100, [self._make_cell("Val1"), self._make_cell("Val2")]),
        ]
        result = ConversationMixin._extract_text_from_table_rows(rows)
        assert len(result) == 2
        assert result[0] == ["Header1", "Header2"]
        assert result[1] == ["Val1", "Val2"]

    def test_empty_rows_skipped(self):
        """Rows that are too short are skipped."""
        rows = [[0, 10], "not a list"]
        result = ConversationMixin._extract_text_from_table_rows(rows)
        assert result == []

    def test_empty_cells(self):
        """Empty cells (short lists) produce empty strings."""
        rows = [
            self._make_row(
                0,
                50,
                [
                    [0, 25],  # empty cell (no third element)
                    self._make_cell("Data"),
                ],
            ),
        ]
        result = ConversationMixin._extract_text_from_table_rows(rows)
        assert len(result) == 1
        assert result[0] == ["", "Data"]


class TestTableFromDetail:
    """Test _extract_table_from_detail for extracting structured table data."""

    @staticmethod
    def _make_cell(text: str) -> list:
        """Build a single table cell matching _extract_text_from_table_rows format.

        Structure: [start, end, [[sub_start, sub_end, [content_item]]]]
        content_item: [[text_start, text_end, text_val]]
        """
        return [0, 10, [[0, len(text), [[[0, len(text), text]]]]]]

    def test_extracts_table_from_detail(self):
        """Table segment in detail[4] is extracted with num_columns and rows."""
        table_rows = [
            [0, 50, [self._make_cell("Col1"), self._make_cell("Col2")]],
        ]
        detail = [
            None,
            None,
            0.75,
            None,
            [
                [0, 100, None, None, [2, 1, table_rows]],
            ],
            [["source-id"], "hash"],
        ]
        result = ConversationMixin._extract_table_from_detail(detail)
        assert result is not None
        assert result["num_columns"] == 2
        assert result["rows"] == [["Col1", "Col2"]]

    def test_returns_none_for_text_only_detail(self):
        """detail with only text segments (no tables) returns None."""
        detail = [
            None,
            None,
            0.75,
            None,
            [
                [[0, 50, [[[0, 50, ["Just text."]]]]]],
            ],
            [["source-id"], "hash"],
        ]
        result = ConversationMixin._extract_table_from_detail(detail)
        assert result is None

    def test_returns_none_for_short_detail(self):
        """detail shorter than 5 elements returns None."""
        assert ConversationMixin._extract_table_from_detail([None, None]) is None

    def test_returns_none_for_non_list_index_4(self):
        """detail[4] being non-list returns None."""
        assert (
            ConversationMixin._extract_table_from_detail([None, None, 0.75, None, "not_a_list"])
            is None
        )


class TestCitationDataWithTable:
    """Test _extract_citation_data includes cited_table when table is present."""

    @staticmethod
    def _make_cell(text: str) -> list:
        """Build a single table cell matching _extract_text_from_table_rows format.

        Structure: [start, end, [[sub_start, sub_end, [content_item]]]]
        content_item: [[text_start, text_end, text_val]]
        """
        return [0, 10, [[0, len(text), [[[0, len(text), text]]]]]]

    @classmethod
    def _build_passage_with_table(
        cls, passage_id: str, source_id: str, cell_texts: list[list[str]]
    ) -> list:
        """Build a passage entry that contains a table segment."""
        table_rows = []
        offset = 0
        for row_texts in cell_texts:
            cells = [cls._make_cell(t) for t in row_texts]
            table_rows.append([offset, offset + 50, cells])
            offset += 51
        return [
            [passage_id],
            [
                None,
                None,
                0.75,
                [[None, 0, 500]],
                [
                    [0, 200, None, None, [len(cell_texts[0]), len(cell_texts), table_rows]],
                ],
                [[[source_id], "hash"]],
                [passage_id],
            ],
        ]

    def test_citation_data_includes_cited_table(self):
        """References include cited_table when passage has table data."""
        passages = [
            self._build_passage_with_table("p1", "src-1", [["A", "B"]]),
        ]
        type_info = [None, None, None, passages, 1]

        result = ConversationMixin._extract_citation_data(type_info)

        assert result["sources_used"] == ["src-1"]
        assert len(result["references"]) == 1
        ref = result["references"][0]
        assert ref["source_id"] == "src-1"
        assert "cited_table" in ref
        assert ref["cited_table"]["num_columns"] == 2
        assert ref["cited_table"]["rows"] == [["A", "B"]]

    def test_citation_data_without_table_has_no_cited_table(self):
        """References without tables do not include cited_table key."""
        passages = [
            [
                ["pass-1"],
                [
                    None,
                    None,
                    0.75,
                    [[None, 0, 500]],
                    [[[0, 500, [[[0, 500, ["Normal text."]]]]]]],
                    [[["src-1"], "hash"]],
                    ["pass-1"],
                ],
            ],
        ]
        type_info = [None, None, None, passages, 1]

        result = ConversationMixin._extract_citation_data(type_info)

        assert result["sources_used"] == ["src-1"]
        ref = result["references"][0]
        assert "cited_table" not in ref
        assert ref.get("cited_text") == "Normal text."
