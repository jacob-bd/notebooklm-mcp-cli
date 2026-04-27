"""LabelsMixin - Source label management operations.

This mixin provides label-related operations for organizing notebook sources:
- auto_label: AI-generated thematic categorization of all sources
- list_labels: List current labels (re-triggers AI if none exist)
- create_label: Manually create a new empty label
- rename_label: Rename an existing label
- set_label_emoji: Set or clear an emoji marker on a label
- move_source_to_label: Assign a source to a label (multi-label supported)
- delete_labels: Delete one or more labels (sources are preserved)

Requires 5+ sources for auto-label to be available in the NotebookLM UI.
"""

from .base import BaseClient


class LabelsMixin(BaseClient):
    """Mixin for source label management operations."""

    def _nb_path(self, notebook_id: str) -> str:
        return f"/notebook/{notebook_id}"

    def _parse_label_response(self, result: list | None) -> list[dict]:
        """Parse raw agX4Bc response into list of label dicts.

        Raw format: [null, [[name, [[src_id], ...], label_id, emoji], ...]]
        Returns: [{"id": ..., "name": ..., "emoji": ..., "source_ids": [...]}, ...]
        """
        if not result or not isinstance(result, list) or len(result) < 2:
            return []
        raw_labels = result[1]
        if not raw_labels or not isinstance(raw_labels, list):
            return []
        labels = []
        for lbl in raw_labels:
            if not isinstance(lbl, list) or len(lbl) < 3:
                continue
            name = lbl[0] or ""
            sources = lbl[1] or []
            label_id = lbl[2] or ""
            emoji = lbl[3] if len(lbl) > 3 else ""
            source_ids = [s[0] for s in sources if isinstance(s, list) and s]
            labels.append(
                {"id": label_id, "name": name, "emoji": emoji or "", "source_ids": source_ids}
            )
        return labels

    def auto_label(self, notebook_id: str) -> list[dict]:
        """Auto-label all sources using AI-generated thematic categories.

        Sends all sources to NotebookLM's AI to suggest category groupings.
        If labels already exist, returns the current label state without
        re-running AI categorization.

        Args:
            notebook_id: The notebook UUID

        Returns:
            List of label dicts: [{"id", "name", "emoji", "source_ids"}, ...]
        """
        params = [[2], notebook_id, None, None, []]
        result = self._call_rpc(self.RPC_LABEL_MANAGE, params, self._nb_path(notebook_id))
        return self._parse_label_response(result)

    def list_labels(self, notebook_id: str) -> list[dict]:
        """List current labels in a notebook.

        Uses the same RPC as auto_label. If no labels exist, this will
        trigger AI auto-labeling. If labels already exist, returns them.

        Args:
            notebook_id: The notebook UUID

        Returns:
            List of label dicts: [{"id", "name", "emoji", "source_ids"}, ...]
        """
        return self.auto_label(notebook_id)

    def create_label(self, notebook_id: str, name: str, emoji: str = "") -> list[dict]:
        """Create a new empty label manually.

        Args:
            notebook_id: The notebook UUID
            name: Display name for the new label
            emoji: Optional emoji marker (e.g. "📊")

        Returns:
            Updated list of all labels including the new one
        """
        params = [[2], notebook_id, None, None, None, [[name, emoji]]]
        result = self._call_rpc(self.RPC_LABEL_MANAGE, params, self._nb_path(notebook_id))
        return self._parse_label_response(result)

    def rename_label(self, notebook_id: str, label_id: str, new_name: str) -> bool:
        """Rename an existing label.

        Args:
            notebook_id: The notebook UUID
            label_id: The label UUID to rename
            new_name: New display name

        Returns:
            True on success
        """
        params = [[2], notebook_id, label_id, [[[new_name]]]]
        result = self._call_rpc(self.RPC_LABEL_MUTATE, params, self._nb_path(notebook_id))
        return result == [] or result is not None

    def set_label_emoji(self, notebook_id: str, label_id: str, emoji: str) -> bool:
        """Set or clear the emoji marker on a label.

        Args:
            notebook_id: The notebook UUID
            label_id: The label UUID
            emoji: Emoji character (e.g. "📊") or "" to clear

        Returns:
            True on success
        """
        params = [[2], notebook_id, label_id, [[[None, emoji]]]]
        result = self._call_rpc(self.RPC_LABEL_MUTATE, params, self._nb_path(notebook_id))
        return result == [] or result is not None

    def move_source_to_label(self, notebook_id: str, label_id: str, source_id: str) -> bool:
        """Assign a source to a label.

        Sources support multi-label assignment — this adds the source to the
        target label without removing it from any existing labels.

        Args:
            notebook_id: The notebook UUID
            label_id: Target label UUID
            source_id: Source UUID to assign

        Returns:
            True on success
        """
        params = [[2], notebook_id, label_id, [[None, [[source_id]]]]]
        result = self._call_rpc(self.RPC_LABEL_MUTATE, params, self._nb_path(notebook_id))
        return result == [] or result is not None

    def delete_labels(self, notebook_id: str, label_ids: list[str]) -> bool:
        """Delete one or more labels. Sources are NOT deleted.

        Args:
            notebook_id: The notebook UUID
            label_ids: List of label UUIDs to delete

        Returns:
            True on success
        """
        params = [[2], notebook_id, label_ids]
        result = self._call_rpc(self.RPC_LABEL_DELETE, params, self._nb_path(notebook_id))
        return result == [] or result is not None
