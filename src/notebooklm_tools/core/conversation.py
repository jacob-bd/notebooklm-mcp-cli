#!/usr/bin/env python3
"""Conversation and query mixin for NotebookLM client.

This module provides the ConversationMixin class which handles all query
and conversation-related operations.
"""

import json
import os
import urllib.parse
from typing import Any

from .base import BaseClient
from .data_types import ConversationTurn


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
            "bl": os.environ.get("NOTEBOOKLM_BL", "boq_labs-tailwind-frontend_20260108.06_p0"),
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

        # Parse streaming response
        answer_text = self._parse_query_response(response.text)

        # Cache this turn for future follow-ups (only if we got an answer)
        if answer_text:
            self._cache_conversation_turn(conversation_id, query_text, answer_text)

        # Calculate turn number
        turns = self._conversation_cache.get(conversation_id, [])
        turn_number = len(turns)

        return {
            "answer": answer_text,
            "conversation_id": conversation_id,
            "turn_number": turn_number,
            "is_follow_up": not is_new_conversation,
            "raw_response": response.text[:1000] if response.text else "",  # Truncate for debugging
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

    def _parse_query_response(self, response_text: str) -> str:
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

        Args:
            response_text: Raw response text from the query endpoint

        Returns:
            The extracted answer text, or empty string if parsing fails
        """
        # Remove anti-XSSI prefix
        if response_text.startswith(")]}'"):
            response_text = response_text[4:]

        lines = response_text.strip().split("\n")
        longest_answer = ""
        longest_thinking = ""

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
                    json_line = lines[i]
                    text, is_answer = self._extract_answer_from_chunk(json_line)
                    if text:
                        if is_answer and len(text) > len(longest_answer):
                            longest_answer = text
                        elif not is_answer and len(text) > len(longest_thinking):
                            longest_thinking = text
                i += 1
            except ValueError:
                # Not a byte count, try to parse as JSON directly
                text, is_answer = self._extract_answer_from_chunk(line)
                if text:
                    if is_answer and len(text) > len(longest_answer):
                        longest_answer = text
                    elif not is_answer and len(text) > len(longest_thinking):
                        longest_thinking = text
                i += 1

        # Return answer if found, otherwise fall back to thinking
        return longest_answer if longest_answer else longest_thinking

    def _extract_answer_from_chunk(self, json_str: str) -> tuple[str | None, bool]:
        """Extract answer text from a single JSON chunk.

        The chunk structure is:
        [["wrb.fr", null, "<nested_json>", ...]]

        The nested_json contains: [["answer_text", null, [...], null, [type_info]]]
        where type_info is an array ending with:
        - 1 = actual answer
        - 2 = thinking step

        Args:
            json_str: A single JSON chunk from the response

        Returns:
            Tuple of (text, is_answer) where is_answer is True for actual answers (type 1)
        """
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            return None, False

        if not isinstance(data, list) or len(data) == 0:
            return None, False

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
                        # Check type indicator at first_elem[4][-1]
                        is_answer = False
                        if len(first_elem) > 4 and isinstance(first_elem[4], list):
                            type_info = first_elem[4]
                            # The type is nested: [[...], None, None, None, type_code]
                            # where type_code is 1 (answer) or 2 (thinking)
                            if len(type_info) > 0 and isinstance(type_info[-1], int):
                                is_answer = type_info[-1] == 1
                        return answer_text, is_answer
                elif isinstance(first_elem, str) and len(first_elem) > 20:
                    return first_elem, False

        return None, False
