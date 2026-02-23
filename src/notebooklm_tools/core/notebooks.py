"""NotebookMixin - Notebook management operations.

This mixin provides all notebook-related operations:
- list_notebooks: List all notebooks
- get_notebook: Get notebook details
- get_notebook_summary: Get AI-generated summary
- create_notebook: Create a new notebook
- rename_notebook: Rename a notebook
- configure_chat: Configure chat settings
- delete_notebook: Delete a notebook
"""

import logging
from typing import Any

from .base import BaseClient
from . import constants
from .data_types import Notebook
from .utils import parse_timestamp

logger = logging.getLogger(__name__)


# Ownership constants (from metadata position 0)
OWNERSHIP_MINE = constants.OWNERSHIP_MINE
OWNERSHIP_SHARED = constants.OWNERSHIP_SHARED


class NotebookMixin(BaseClient):
    """Mixin for notebook management operations.
    
    This class inherits from BaseClient and provides all notebook-related
    operations. It is designed to be composed with other mixins via
    multiple inheritance in the final NotebookLMClient class.
    """

    def list_notebooks(self, debug: bool = False) -> list[Notebook]:
        """List all notebooks."""
        # [null, 1, null, [2]] - params for list notebooks
        params = [None, 1, None, [2]]

        result = self._call_rpc(self.RPC_LIST_NOTEBOOKS, params)

        if debug:
            logger.debug(f"Result type: {type(result)}")
            if result:
                logger.debug(f"Result length: {len(result) if isinstance(result, list) else 'N/A'}")
                if isinstance(result, list) and len(result) > 0:
                    logger.debug(f"First item type: {type(result[0])}")
                    logger.debug(f"First item: {str(result[0])[:500]}...")

        notebooks = []
        if result and isinstance(result, list):
            #   [0] = "Title"
            #   [1] = [sources]
            #   [2] = "notebook-uuid"
            #   [3] = "emoji" or null
            #   [4] = null
            #   [5] = [metadata] where metadata[0] = ownership (1=mine, 2=shared_with_me)
            notebook_list = result[0] if result and isinstance(result[0], list) else result

            for nb_data in notebook_list:
                if isinstance(nb_data, list) and len(nb_data) >= 3:
                    title = nb_data[0] if isinstance(nb_data[0], str) else "Untitled"
                    sources_data = nb_data[1] if len(nb_data) > 1 else []
                    notebook_id = nb_data[2] if len(nb_data) > 2 else None

                    is_owned = True  # Default to owned
                    is_shared = False  # Default to not shared
                    created_at = None
                    modified_at = None

                    if len(nb_data) > 5 and isinstance(nb_data[5], list) and len(nb_data[5]) > 0:
                        metadata = nb_data[5]
                        ownership_value = metadata[0]
                        # 1 = mine (owned), 2 = shared with me
                        is_owned = ownership_value == OWNERSHIP_MINE

                        # Check if shared (for owned notebooks)
                        # Based on observation: [1, true, true, ...] -> Shared
                        #                       [1, false, true, ...] -> Private
                        if len(metadata) > 1:
                            is_shared = bool(metadata[1])

                        # metadata[5] = [seconds, nanos] = last modified
                        # metadata[8] = [seconds, nanos] = created
                        if len(metadata) > 5:
                            modified_at = parse_timestamp(metadata[5])
                        if len(metadata) > 8:
                            created_at = parse_timestamp(metadata[8])

                    sources = []
                    if isinstance(sources_data, list):
                        for src in sources_data:
                            if isinstance(src, list) and len(src) >= 2:
                                # Source structure: [[source_id], title, metadata, ...]
                                src_ids = src[0] if src[0] else []
                                src_title = src[1] if len(src) > 1 else "Untitled"

                                # Extract the source ID (might be in a list)
                                src_id = src_ids[0] if isinstance(src_ids, list) and src_ids else src_ids

                                sources.append({
                                    "id": src_id,
                                    "title": src_title,
                                })

                    if notebook_id:
                        notebooks.append(Notebook(
                            id=notebook_id,
                            title=title,
                            source_count=len(sources),
                            sources=sources,
                            is_owned=is_owned,
                            is_shared=is_shared,
                            created_at=created_at,
                            modified_at=modified_at,
                        ))

        return notebooks

    def get_notebook(self, notebook_id: str) -> dict | None:
        """Get notebook details."""
        return self._call_rpc(
            self.RPC_GET_NOTEBOOK,
            [notebook_id, None, [2], None, 0],
            f"/notebook/{notebook_id}",
        )

    def get_notebook_summary(self, notebook_id: str) -> dict[str, Any]:
        """Get AI-generated summary and suggested topics for a notebook."""
        result = self._call_rpc(
            self.RPC_GET_SUMMARY, [notebook_id, [2]], f"/notebook/{notebook_id}"
        )
        summary = ""
        suggested_topics = []

        if result and isinstance(result, list):
            # Summary is at result[0][0]
            if len(result) > 0 and isinstance(result[0], list) and len(result[0]) > 0:
                summary = result[0][0]

            # Suggested topics are at result[1][0]
            if len(result) > 1 and result[1]:
                topics_data = result[1][0] if isinstance(result[1], list) and len(result[1]) > 0 else []
                for topic in topics_data:
                    if isinstance(topic, list) and len(topic) >= 2:
                        suggested_topics.append({
                            "question": topic[0],
                            "prompt": topic[1],
                        })

        return {
            "summary": summary,
            "suggested_topics": suggested_topics,
        }

    def create_notebook(self, title: str = "") -> Notebook | None:
        """Create a new notebook."""
        params = [title, None, None, [2], [1, None, None, None, None, None, None, None, None, None, [1]]]
        result = self._call_rpc(self.RPC_CREATE_NOTEBOOK, params)
        if result and isinstance(result, list) and len(result) >= 3:
            notebook_id = result[2]
            if notebook_id:
                return Notebook(
                    id=notebook_id,
                    title=title or "Untitled notebook",
                    source_count=0,
                    sources=[],
                )
        return None

    def rename_notebook(self, notebook_id: str, new_title: str) -> bool:
        """Rename a notebook."""
        params = [notebook_id, [[None, None, None, [None, new_title]]]]
        result = self._call_rpc(self.RPC_RENAME_NOTEBOOK, params, f"/notebook/{notebook_id}")
        return result is not None

    def configure_chat(
        self,
        notebook_id: str,
        goal: str = "default",
        custom_prompt: str | None = None,
        response_length: str = "default",
    ) -> dict[str, Any]:
        """Configure chat goal/style and response length for a notebook."""
        goal_code = constants.CHAT_GOALS.get_code(goal)

        # Validate custom prompt
        if goal == "custom":
            if not custom_prompt:
                raise ValueError("custom_prompt is required when goal='custom'")
            if len(custom_prompt) > 10000:
                raise ValueError(f"custom_prompt exceeds 10000 chars (got {len(custom_prompt)})")

        # Map response length string to code
        length_code = constants.CHAT_RESPONSE_LENGTHS.get_code(response_length)

        if goal == "custom" and custom_prompt:
            goal_setting = [goal_code, custom_prompt]
        else:
            goal_setting = [goal_code]

        chat_settings = [goal_setting, [length_code]]
        params = [notebook_id, [[None, None, None, None, None, None, None, chat_settings]]]
        result = self._call_rpc(self.RPC_RENAME_NOTEBOOK, params, f"/notebook/{notebook_id}")

        if result:
            # Response format: [title, null, id, emoji, null, metadata, null, [[goal_code, prompt?], [length_code]]]
            settings = result[7] if len(result) > 7 else None
            return {
                "status": "success",
                "notebook_id": notebook_id,
                "goal": goal,
                "custom_prompt": custom_prompt if goal == "custom" else None,
                "response_length": response_length,
                "raw_settings": settings,
            }

        return {
            "status": "error",
            "error": "Failed to configure chat settings",
        }

    def delete_notebook(self, notebook_id: str) -> bool:
        """Delete a notebook permanently.

        WARNING: This action is IRREVERSIBLE. The notebook and all its sources,
        notes, and generated content will be permanently deleted.

        Args:
            notebook_id: The notebook UUID to delete

        Returns:
            True on success, False on failure
        """
        params = [[notebook_id], [2]]
        result = self._call_rpc(self.RPC_DELETE_NOTEBOOK, params)

        return result is not None
