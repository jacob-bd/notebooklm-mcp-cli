#!/usr/bin/env python3
"""Conversation and query mixin for NotebookLM client.

This module provides the ConversationMixin class which handles all query
and conversation-related operations.
"""

import json
import logging
import os
import urllib.parse
from typing import Any

from .base import BaseClient
from .data_types import ConversationTurn
from .errors import NotebookLMError

logger = logging.getLogger("notebooklm_mcp.api")

GOOGLE_ERROR_CODES = {
    1: "CANCELLED",
    2: "UNKNOWN",
    3: "INVALID_ARGUMENT",
    4: "DEADLINE_EXCEEDED",
    5: "NOT_FOUND",
    7: "PERMISSION_DENIED",
    8: "RESOURCE_EXHAUSTED",
    13: "INTERNAL",
    14: "UNAVAILABLE",
    16: "UNAUTHENTICATED",
}


class QueryRejectedError(NotebookLMError):
    """Raised when Google returns an error response instead of an answer."""

    def __init__(self, error_code: int, error_type: str = "", raw_detail: str = ""):
        code_name = GOOGLE_ERROR_CODES.get(error_code, "UNKNOWN")
        msg = f"Google rejected the query (error code {error_code}: {code_name})"
        if error_type:
            msg += f" [{error_type}]"
        super().__init__(msg)
        self.error_code = error_code
        self.code_name = code_name
        self.error_type = error_type
        self.raw_detail = raw_detail


class ConversationMixin(BaseClient):
    """Mixin providing query and conversation operations.
    
    Methods:
        - query: Query the notebook with questions
        - clear_conversation: Clear conversation cache
        - get_conversation_history: Get conversation history
    """
    
    # =========================================================================
    # Conversation Cache Management
    # =========================================================================
    
    def _build_conversation_history(self, conversation_id: str) -> list | None:
        """Build the conversation history array for follow-up queries.

        Chrome expects history in format: [[answer, null, 2], [query, null, 1], ...]
        where type 1 = user message, type 2 = AI response.

        The history includes ALL previous turns, not just the most recent one.
        Turns are added in chronological order (oldest first).

        Args:
            conversation_id: The conversation ID to get history for

        Returns:
            List in Chrome's expected format, or None if no history exists
        """
        turns = self._conversation_cache.get(conversation_id, [])
        if not turns:
            return None

        history = []
        # Add turns in chronological order (oldest first)
        # Each turn adds: [answer, null, 2] then [query, null, 1]
        for turn in turns:
            history.append([turn.answer, None, 2])
            history.append([turn.query, None, 1])

        return history if history else None

    def _cache_conversation_turn(
        self, conversation_id: str, query: str, answer: str
    ) -> None:
        """Cache a conversation turn for future follow-up queries."""
        if conversation_id not in self._conversation_cache:
            self._conversation_cache[conversation_id] = []

        turn_number = len(self._conversation_cache[conversation_id]) + 1
        turn = ConversationTurn(query=query, answer=answer, turn_number=turn_number)
        self._conversation_cache[conversation_id].append(turn)

    def clear_conversation(self, conversation_id: str) -> bool:
        """Clear the conversation cache for a specific conversation."""
        if conversation_id in self._conversation_cache:
            del self._conversation_cache[conversation_id]
            return True
        return False

    def get_conversation_history(self, conversation_id: str) -> list[dict] | None:
        """Get the conversation history for a specific conversation."""
        turns = self._conversation_cache.get(conversation_id)
        if not turns:
            return None

        return [
            {"turn": t.turn_number, "query": t.query, "answer": t.answer}
            for t in turns
        ]

    # =========================================================================
    # Query Operations
    # =========================================================================

    def query(
        self,
        notebook_id: str,
        query_text: str,
        source_ids: list[str] | None = None,
        conversation_id: str | None = None,
        timeout: float = 120.0,
    ) -> dict | None:
        """Query the notebook with a question.

        Supports both new conversations and follow-up queries. For follow-ups,
        the conversation history is automatically included from the cache.

        Args:
            notebook_id: The notebook UUID
            query_text: The question to ask
            source_ids: Optional list of source IDs to query (default: all sources)
            conversation_id: Optional conversation ID for follow-up questions.
                           If None, starts a new conversation.
                           If provided and exists in cache, includes conversation history.
            timeout: Request timeout in seconds (default: 120.0)

        Returns:
            Dict with:
            - answer: The AI's response text
            - conversation_id: ID to use for follow-up questions
            - sources_used: List of source IDs cited in the answer
            - citations: Dict mapping citation number to source ID (1-indexed)
            - turn_number: Which turn this is in the conversation (1 = first)
            - is_follow_up: Whether this was a follow-up query
            - raw_response: The raw parsed response (for debugging)
        """
        import uuid

        client = self._get_client()

        # If no source_ids provided, get them from the notebook
        if source_ids is None:
            notebook_data = self.get_notebook(notebook_id)
            source_ids = self._extract_source_ids_from_notebook(notebook_data)

        # Determine if this is a new conversation or follow-up
        is_new_conversation = conversation_id is None
        if is_new_conversation:
            conversation_id = str(uuid.uuid4())
            conversation_history = None
        else:
            # Check if we have cached history for this conversation
            conversation_history = self._build_conversation_history(conversation_id)

        # Build source IDs structure: [[[sid]]] for each source (3 brackets, not 4!)
        sources_array = [[[sid]] for sid in source_ids] if source_ids else []

        # Query params structure (from network capture)
        # For new conversations: params[2] = None
        # For follow-ups: params[2] = [[answer, null, 2], [query, null, 1], ...]
        params = [
            sources_array,
            query_text,
            conversation_history,  # None for new, history array for follow-ups
            [2, None, [1]],
            conversation_id,
        ]

        # Use compact JSON format matching Chrome (no spaces)
        params_json = json.dumps(params, separators=(",", ":"))

        f_req = [None, params_json]
        f_req_json = json.dumps(f_req, separators=(",", ":"))

        # URL encode with safe='' to encode all characters including /
        body_parts = [f"f.req={urllib.parse.quote(f_req_json, safe='')}"]
        if self.csrf_token:
            body_parts.append(f"at={urllib.parse.quote(self.csrf_token, safe='')}")
        # Add trailing & to match NotebookLM's format
        body = "&".join(body_parts) + "&"

        self._reqid_counter += 100000  # Increment counter
        url_params = {
            "bl": os.environ.get("NOTEBOOKLM_BL") or getattr(self, "_bl", "") or self._BL_FALLBACK,
            "hl": os.environ.get("NOTEBOOKLM_HL", "en"),
            "_reqid": str(self._reqid_counter),
            "rt": "c",
        }
        if self._session_id:
            url_params["f.sid"] = self._session_id

        query_string = urllib.parse.urlencode(url_params)
        url = f"{self.BASE_URL}{self.QUERY_ENDPOINT}?{query_string}"

        response = client.post(url, content=body, timeout=timeout)
        response.raise_for_status()

        logger.debug("Raw query response (first 2000 chars): %s", response.text[:2000])

        # Parse streaming response
        answer_text, citation_data = self._parse_query_response(response.text)

        # Cache this turn for future follow-ups (only if we got an answer)
        if answer_text:
            self._cache_conversation_turn(conversation_id, query_text, answer_text)

        # Calculate turn number
        turns = self._conversation_cache.get(conversation_id, [])
        turn_number = len(turns)

        return {
            "answer": answer_text,
            "conversation_id": conversation_id,
            "sources_used": citation_data.get("sources_used", []),
            "citations": citation_data.get("citations", {}),
            "turn_number": turn_number,
            "is_follow_up": not is_new_conversation,
            "raw_response": response.text[:1000] if response.text else "",
        }

    def _extract_source_ids_from_notebook(self, notebook_data: Any) -> list[str]:
        """Extract source IDs from notebook data."""
        source_ids = []
        if not notebook_data or not isinstance(notebook_data, list):
            return source_ids

        try:
            # Notebook structure: [[notebook_title, sources_array, notebook_id, ...]]
            # The outer array contains one element with all notebook info
            # Sources are at position [0][1]
            if len(notebook_data) > 0 and isinstance(notebook_data[0], list):
                notebook_info = notebook_data[0]
                if len(notebook_info) > 1 and isinstance(notebook_info[1], list):
                    sources = notebook_info[1]
                    for source in sources:
                        # Each source: [[source_id], title, metadata, [null, 2]]
                        if isinstance(source, list) and len(source) > 0:
                            source_id_wrapper = source[0]
                            if isinstance(source_id_wrapper, list) and len(source_id_wrapper) > 0:
                                source_id = source_id_wrapper[0]
                                if isinstance(source_id, str):
                                    source_ids.append(source_id)
        except (IndexError, TypeError):
            pass

        return source_ids

    # =========================================================================
    # Response Parsing
    # =========================================================================

    def _parse_query_response(self, response_text: str) -> tuple[str, dict]:
        """Parse the streaming query response and extract the final answer.

        The query endpoint returns a streaming response with multiple chunks.
        Each chunk has a type indicator: 1 = actual answer, 2 = thinking step.

        Response format:
        )]}'
        <byte_count>
        [[["wrb.fr", null, "<json_with_text>", ...]]]
        ...more chunks...

        Strategy: Find the LONGEST chunk that is marked as type 1 (actual answer).
        If no type 1 chunks found, fall back to longest overall.
        If no answer at all but Google returned an error, raise QueryRejectedError.

        Args:
            response_text: Raw response text from the query endpoint

        Returns:
            Tuple of (answer_text, citation_data) where citation_data has
            'sources_used' and 'citations' keys (or empty dict).

        Raises:
            QueryRejectedError: If Google returned an error instead of an answer
        """
        # Remove anti-XSSI prefix
        if response_text.startswith(")]}'"):
            response_text = response_text[4:]

        lines = response_text.strip().split("\n")
        longest_answer = ""
        longest_thinking = ""
        answer_citation_data: dict = {}
        detected_errors: list[dict] = []

        def _process_chunk(json_line: str) -> None:
            nonlocal longest_answer, longest_thinking, answer_citation_data
            error = self._extract_error_from_chunk(json_line)
            if error:
                detected_errors.append(error)
                return
            text, is_answer, cdata = self._extract_answer_from_chunk(json_line)
            if text:
                if is_answer and len(text) > len(longest_answer):
                    longest_answer = text
                    if cdata:
                        answer_citation_data = cdata
                elif not is_answer and len(text) > len(longest_thinking):
                    longest_thinking = text

        # Parse chunks - prioritize type 1 (answers) over type 2 (thinking)
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if not line:
                i += 1
                continue

            # Try to parse as byte count (indicates next line is JSON)
            try:
                int(line)
                i += 1
                if i < len(lines):
                    _process_chunk(lines[i])
                i += 1
            except ValueError:
                _process_chunk(line)
                i += 1

        result = longest_answer if longest_answer else longest_thinking

        if not result and detected_errors:
            err = detected_errors[0]
            raise QueryRejectedError(
                error_code=err["code"],
                error_type=err.get("type", ""),
                raw_detail=err.get("raw", ""),
            )

        return result, answer_citation_data

    def _extract_error_from_chunk(self, json_str: str) -> dict | None:
        """Check if a JSON chunk contains a Google API error.

        Error responses have item[2] as null/None and error info in item[5]:
          [["wrb.fr", null, null, null, null, [3]]]
          [["wrb.fr", null, null, null, null, [8, null, [["type.googleapis.com/...Error", [...]]]]]]

        Returns:
            Dict with 'code', 'type', 'raw' keys if error found, else None
        """
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            return None

        if not isinstance(data, list) or len(data) == 0:
            return None

        for item in data:
            if not isinstance(item, list) or len(item) < 6:
                continue
            if item[0] != "wrb.fr":
                continue
            if item[2] is not None:
                continue

            error_info = item[5]
            if not isinstance(error_info, list) or len(error_info) == 0:
                continue

            error_code = error_info[0]
            if not isinstance(error_code, int):
                continue

            error_type = ""
            if len(error_info) > 2 and isinstance(error_info[2], list):
                for detail in error_info[2]:
                    if isinstance(detail, list) and len(detail) > 0 and isinstance(detail[0], str):
                        error_type = detail[0]
                        break

            return {
                "code": error_code,
                "type": error_type,
                "raw": json_str[:500],
            }

        return None

    def _extract_answer_from_chunk(self, json_str: str) -> tuple[str | None, bool, dict]:
        """Extract answer text and citation data from a single JSON chunk.

        The chunk structure is:
        [["wrb.fr", null, "<nested_json>", ...]]

        The nested_json contains:
        [["answer_text", null, [conv_data], null, [fmt_segments, null, null, source_passages, type_code]]]

        type_code: 1 = actual answer, 2 = thinking step
        source_passages (at first_elem[4][3]): list of passage entries, each containing
        the parent source ID at passage[1][5][0][0][0].

        Args:
            json_str: A single JSON chunk from the response

        Returns:
            Tuple of (text, is_answer, citation_data) where:
            - is_answer is True for actual answers (type 1)
            - citation_data is {"sources_used": [...], "citations": {num: source_id}}
              or empty dict if no citation data found
        """
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            return None, False, {}

        if not isinstance(data, list) or len(data) == 0:
            return None, False, {}

        for item in data:
            if not isinstance(item, list) or len(item) < 3:
                continue
            if item[0] != "wrb.fr":
                continue

            inner_json_str = item[2]
            if not isinstance(inner_json_str, str):
                continue

            try:
                inner_data = json.loads(inner_json_str)
            except json.JSONDecodeError:
                continue

            # Type indicator is at inner_data[0][4][-1]: 1 = answer, 2 = thinking
            if isinstance(inner_data, list) and len(inner_data) > 0:
                first_elem = inner_data[0]
                if isinstance(first_elem, list) and len(first_elem) > 0:
                    answer_text = first_elem[0]
                    if isinstance(answer_text, str) and len(answer_text) > 20:
                        is_answer = False
                        citation_data: dict = {}
                        if len(first_elem) > 4 and isinstance(first_elem[4], list):
                            type_info = first_elem[4]
                            if len(type_info) > 0 and isinstance(type_info[-1], int):
                                is_answer = type_info[-1] == 1
                            if is_answer:
                                citation_data = self._extract_citation_data(type_info)
                        return answer_text, is_answer, citation_data
                elif isinstance(first_elem, str) and len(first_elem) > 20:
                    return first_elem, False, {}

        return None, False, {}

    @staticmethod
    def _extract_citation_data(type_info: list) -> dict:
        """Extract source IDs from the citation passages in a type-1 answer chunk.

        The source passages are at type_info[3] (i.e. first_elem[4][3]).
        Each passage entry: [["passage_id"], [null, null, confidence, ..., [[["SOURCE_ID"], ...]], ...]]
        The parent source ID is at passage[1][5][0][0][0].
        Citations in the answer text are 1-indexed into this array.

        Returns:
            Dict with 'sources_used' (unique source IDs) and
            'citations' (citation_number -> source_id mapping), or empty dict.
        """
        try:
            if len(type_info) < 4 or not isinstance(type_info[3], list):
                return {}

            passages = type_info[3]
            if not passages:
                return {}

            citations: dict[int, str] = {}
            seen_sources: dict[str, None] = {}  # ordered set via dict

            for i, passage in enumerate(passages):
                if not isinstance(passage, list) or len(passage) < 2:
                    continue
                detail = passage[1]
                if not isinstance(detail, list) or len(detail) < 6:
                    continue
                source_ref = detail[5]
                if not isinstance(source_ref, list) or len(source_ref) == 0:
                    continue
                first_ref = source_ref[0]
                if not isinstance(first_ref, list) or len(first_ref) == 0:
                    continue
                source_id_wrapper = first_ref[0]
                if not isinstance(source_id_wrapper, list) or len(source_id_wrapper) == 0:
                    continue
                source_id = source_id_wrapper[0]
                if isinstance(source_id, str):
                    citations[i + 1] = source_id
                    seen_sources[source_id] = None

            if not citations:
                return {}

            return {
                "sources_used": list(seen_sources.keys()),
                "citations": citations,
            }
        except (IndexError, TypeError):
            return {}
