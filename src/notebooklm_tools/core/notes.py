"""NotesMixin - Note management operations.

This mixin provides note-related operations:
- create_note: Save a chat response as a note
- list_notes: Get all notes in a notebook
- update_note: Edit a note's content
- delete_note: Remove a note permanently
- get_note: Get a single note's details
"""

import json

from .base import BaseClient


class NotesMixin(BaseClient):
    """Mixin for note management operations."""

    def create_note(
        self,
        notebook_id: str,
        content: str,
        title: str | None = None,
        conversation_id: str | None = None,
    ) -> dict | None:
        """Create a note from content or a chat response.

        Args:
            notebook_id: The notebook UUID
            content: The note content (AI response text)
            title: Optional title for the note
            conversation_id: Optional conversation ID if saving from chat

        Returns:
            Dict with note_id and metadata, or None on failure
        """
        # Use default title if not provided
        if title is None:
            title = "New Note"

        # RPC format: [notebook_id, "", [1], None, title]
        # Then we need to update it with content using update_note
        params = [notebook_id, "", [1], None, title]
        result = self._call_rpc(self.RPC_CREATE_NOTE, params, f"/notebook/{notebook_id}")

        if result and isinstance(result, list) and len(result) > 0:
            # Response: [[note_id, ...]]
            note_data = result[0] if isinstance(result[0], list) else result
            note_id = note_data[0] if isinstance(note_data, list) and len(note_data) > 0 else note_data

            if note_id:
                # Now update with content if provided
                if content:
                    update_result = self.update_note(note_id, content=content, title=title, notebook_id=notebook_id)
                    if update_result:
                        return {
                            "id": note_id,
                            "title": title,
                            "content": content,
                        }
                else:
                    return {
                        "id": note_id,
                        "title": title,
                        "content": "",
                    }

        return None

    def list_notes(self, notebook_id: str) -> list[dict]:
        """List all notes in a notebook.

        Args:
            notebook_id: The notebook UUID

        Returns:
            List of note dicts with id, title, content, created_at
        """
        # RPC_GET_NOTES returns both notes and mind maps
        params = [notebook_id]
        result = self._call_rpc(self.RPC_GET_NOTES, params, f"/notebook/{notebook_id}")

        notes = []
        if result and isinstance(result, list) and len(result) > 0:
            # Response: [[note_items...], timestamp]
            # Each note: [note_id, [note_id, content, metadata, None, title], status]
            # Deleted notes: [note_id, None, 2]
            items = result[0] if isinstance(result[0], list) else []

            for item in items:
                if not isinstance(item, list) or len(item) < 2:
                    continue

                # Skip deleted items (status = 2 or data is None)
                if len(item) > 2 and item[2] == 2:
                    continue
                if item[1] is None:
                    continue

                note_id = item[0]
                note_data = item[1] if isinstance(item[1], list) and len(item[1]) > 0 else None

                if note_data and len(note_data) >= 5:
                    content = note_data[1] if len(note_data) > 1 else ""
                    title = note_data[4] if len(note_data) > 4 else "Untitled"

                    # Distinguish notes from mind maps by checking if content is JSON
                    # Mind maps have JSON with "children" or "nodes" keys
                    is_mind_map = False
                    if content:
                        try:
                            parsed = json.loads(content)
                            if isinstance(parsed, dict) and ("children" in parsed or "nodes" in parsed):
                                is_mind_map = True
                        except (json.JSONDecodeError, TypeError):
                            pass

                    # Only include notes, not mind maps
                    if not is_mind_map:
                        notes.append({
                            "id": note_id,
                            "title": title,
                            "content": content,
                            "preview": content[:100] if content else "",
                        })

        return notes

    def get_note(self, note_id: str) -> dict | None:
        """Get a single note's details.

        Args:
            note_id: The note UUID

        Returns:
            Dict with note details, or None if not found

        Note: This method fetches all notes and filters for the specific one.
        The API doesn't provide a direct get-by-id endpoint for notes.
        """
        # Note: We need the notebook_id to fetch notes, but we only have note_id.
        # This is a limitation - we'll need to store notebook context or
        # fetch from all notebooks. For now, this is a design issue.
        # The MCP tool layer should track notebook_id context.
        raise NotImplementedError(
            "get_note requires notebook_id context. "
            "Use list_notes with notebook_id and filter by note_id instead."
        )

    def update_note(
        self,
        note_id: str,
        content: str | None = None,
        title: str | None = None,
        notebook_id: str | None = None,
    ) -> dict | None:
        """Update a note's content or title.

        Args:
            note_id: The note UUID
            content: New content (optional)
            title: New title (optional)
            notebook_id: The notebook UUID (required for update)

        Returns:
            Updated note dict, or None on failure
        """
        if not notebook_id:
            raise ValueError("notebook_id is required for updating notes")

        if content is None and title is None:
            raise ValueError("Must provide content or title to update")

        # If both content and title are provided, we can skip fetching existing note
        # This fixes timing issues when called right after create_note
        if content is not None and title is not None:
            new_content = content
            new_title = title
        else:
            # Fetch current note to get existing values for partial updates
            all_notes = self.list_notes(notebook_id)
            current_note = next((n for n in all_notes if n["id"] == note_id), None)

            if not current_note:
                return None

            # Use existing values if not provided
            new_content = content if content is not None else current_note.get("content", "")
            new_title = title if title is not None else current_note.get("title", "")

        # RPC format: [notebook_id, note_id, [[[content, title, [], 0]]]]
        params = [
            notebook_id,
            note_id,
            [[[new_content, new_title, [], 0]]],
        ]

        result = self._call_rpc(self.RPC_UPDATE_NOTE, params, f"/notebook/{notebook_id}")

        # API returns the updated note data on success (not None as previously thought)
        # If we got here without exception, the update succeeded
        return {
            "id": note_id,
            "title": new_title,
            "content": new_content,
        }

    def delete_note(self, note_id: str, notebook_id: str) -> bool:
        """Delete a note permanently.

        Args:
            note_id: The note UUID
            notebook_id: The notebook UUID (required for deletion)

        Returns:
            True on success, False on failure
        """
        # RPC format: [notebook_id, None, [note_id]]
        params = [notebook_id, None, [note_id]]
        self._call_rpc(self.RPC_DELETE_NOTE, params, f"/notebook/{notebook_id}")

        # Returns null on success (soft-delete: clears content, keeps ID)
        return True  # If no exception was raised, consider it success
