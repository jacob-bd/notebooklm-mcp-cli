# src/notebooklm_tools/core/data_types.py
"""Dataclasses for NotebookLM API client.

This module contains the core data structures used throughout the NotebookLM
API client. These are dataclasses (not Pydantic models) for lightweight
internal use.

For external-facing Pydantic models (CLI/MCP output), see models.py.
"""

from dataclasses import dataclass


@dataclass
class ConversationTurn:
    """Represents a single turn in a conversation (query + response).

    Used to track conversation history for follow-up queries.
    NotebookLM requires the full conversation history in follow-up requests.
    """

    query: str  # The user's question
    answer: str  # The AI's response
    turn_number: int  # 1-indexed turn number in the conversation


@dataclass
class Collaborator:
    """A user with access to a notebook."""

    email: str
    role: str  # "owner", "editor", "viewer"
    is_pending: bool = False
    display_name: str | None = None


@dataclass
class ShareStatus:
    """Current sharing state of a notebook."""

    is_public: bool
    access_level: str  # "restricted" or "public"
    collaborators: list[Collaborator]
    public_link: str | None = None


@dataclass
class Notebook:
    """Represents a NotebookLM notebook.

    This is the primary notebook data structure used throughout the API client.
    Contains notebook metadata, source information, and computed properties.
    """

    id: str
    title: str
    source_count: int
    sources: list[dict]
    is_owned: bool = True  # True if owned by user, False if shared with user
    is_shared: bool = False  # True if shared with others (for owned notebooks)
    created_at: str | None = None  # ISO format timestamp
    modified_at: str | None = None  # ISO format timestamp

    @property
    def url(self) -> str:
        """Get the NotebookLM web URL for this notebook."""
        from notebooklm_tools.utils.config import get_base_url
        return f"{get_base_url()}/notebook/{self.id}"

    @property
    def ownership(self) -> str:
        """Return human-readable ownership status."""
        if self.is_owned:
            return "owned"
        return "shared_with_me"
