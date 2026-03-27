"""Adapter that makes EnterpriseClient look like NotebookLMClient.

The MCP tools and services call methods on the personal client like
client.list_notebooks(), client.add_url_source(), etc. This adapter
wraps EnterpriseClient to provide the same interface, translating
responses into the data structures the service layer expects.
"""

from .api_profile import get_api_profile
from .data_types import Notebook
from .enterprise_client import EnterpriseClient


class EnterpriseAdapter:
    """Wraps EnterpriseClient to match the NotebookLMClient interface.

    Only implements methods that are available via the Enterprise REST API.
    Methods that aren't available raise NotImplementedError with a clear message.
    """

    def __init__(self, enterprise_client: EnterpriseClient):
        self._ec = enterprise_client
        self._profile = get_api_profile()
        # Conversation cache stub (query not supported via REST)
        self._conversation_cache: dict = {}

    def close(self):
        self._ec.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    # =========================================================================
    # Notebooks
    # =========================================================================

    def list_notebooks(self, debug: bool = False) -> list[Notebook]:
        """List all notebooks."""
        results = self._ec.list_notebooks()
        notebooks = []
        for nb in results:
            notebooks.append(Notebook(
                id=nb["notebook_id"],
                title=nb["title"],
                source_count=0,  # REST API doesn't return source count in list
                sources=[],
            ))
        return notebooks

    def get_notebook(self, notebook_id: str) -> dict | None:
        """Get notebook details."""
        return self._ec.get_notebook(notebook_id)

    def create_notebook(self, title: str = "") -> Notebook | None:
        """Create a new notebook."""
        result = self._ec.create_notebook(title)
        if result:
            return Notebook(
                id=result["notebook_id"],
                title=result["title"],
                source_count=0,
                sources=[],
            )
        return None

    def delete_notebook(self, notebook_id: str) -> bool:
        """Delete a notebook permanently."""
        return self._ec.delete_notebook(notebook_id)

    def get_notebook_summary(self, notebook_id: str) -> dict:
        """Not available via REST API — stub."""
        return {
            "summary": "(Notebook summary is not available via the Enterprise REST API. Use the web UI.)",
            "suggested_topics": [],
        }

    def rename_notebook(self, notebook_id: str, new_title: str) -> bool:
        """Not available via REST API."""
        raise NotImplementedError(
            "Rename notebook is not available in the Enterprise REST API. Use the web UI."
        )

    # =========================================================================
    # Sources
    # =========================================================================

    def get_notebook_sources_with_types(self, notebook_id: str) -> list[dict]:
        """List sources in a notebook (from GET notebook response)."""
        nb = self._ec.get_notebook(notebook_id)
        if nb and "sources" in nb:
            return nb["sources"]
        return []

    def add_url_source(self, notebook_id: str, url: str, **kwargs) -> dict | None:
        """Add a URL source."""
        return self._ec.add_source_url(notebook_id, url)

    def add_text_source(self, notebook_id: str, text: str, title: str = "", **kwargs) -> dict | None:
        """Add a text source."""
        return self._ec.add_source_text(notebook_id, text, title or "Pasted Text")

    def delete_source(self, notebook_id: str, source_id: str) -> bool:
        """Delete a source."""
        return self._ec.delete_source(notebook_id, source_id)

    # =========================================================================
    # Query / Chat
    # =========================================================================

    def query(self, notebook_id: str, query_text: str, **kwargs) -> dict:
        """Not available via REST API."""
        raise NotImplementedError(
            "Chat/query is not available in the Enterprise REST API. "
            "Use the web UI for chat queries."
        )

    def get_conversation_id(self, notebook_id: str) -> str | None:
        return None

    def clear_conversation(self, conversation_id: str) -> bool:
        return False

    # =========================================================================
    # Studio / Audio
    # =========================================================================

    def create_audio_overview(
        self,
        notebook_id: str,
        source_ids: list[str] | None = None,
        language: str = "en",
        focus_prompt: str = "",
        **kwargs,
    ) -> dict | None:
        """Generate an audio overview via Enterprise REST API."""
        result = self._ec.generate_audio_overview(
            notebook_id,
            source_ids=source_ids,
            focus=focus_prompt,
            language=language,
        )
        if result:
            ao = result.get("audioOverview", result)
            return {
                "artifact_id": ao.get("audioOverviewId", ""),
                "status": ao.get("status", "in_progress"),
            }
        return None

    def create_video_overview(self, notebook_id: str, **kwargs):
        raise NotImplementedError(
            "Video generation is not available in the Enterprise REST API. Use the web UI."
        )

    def create_infographic(self, notebook_id: str, **kwargs):
        raise NotImplementedError(
            "Infographic generation is not available in the Enterprise REST API. Use the web UI."
        )

    def create_slide_deck(self, notebook_id: str, **kwargs):
        raise NotImplementedError(
            "Slide deck generation is not available in the Enterprise REST API. Use the web UI."
        )

    def create_report(self, notebook_id: str, **kwargs):
        raise NotImplementedError(
            "Report generation is not available in the Enterprise REST API. Use the web UI."
        )

    def create_flashcards(self, notebook_id: str, **kwargs):
        raise NotImplementedError(
            "Flashcard generation is not available in the Enterprise REST API. Use the web UI."
        )

    def create_quiz(self, notebook_id: str, **kwargs):
        raise NotImplementedError(
            "Quiz generation is not available in the Enterprise REST API. Use the web UI."
        )

    def create_data_table(self, notebook_id: str, **kwargs):
        raise NotImplementedError(
            "Data table generation is not available in the Enterprise REST API. Use the web UI."
        )

    def generate_mind_map(self, notebook_id: str, **kwargs):
        raise NotImplementedError(
            "Mind map generation is not available in the Enterprise REST API. Use the web UI."
        )

    def poll_studio_status(self, notebook_id: str) -> list:
        """Not available via REST API."""
        return []

    def get_studio_status(self, notebook_id: str) -> dict:
        """Not available via REST API — stub."""
        return {"total": 0, "completed": 0, "in_progress": 0, "artifacts": []}

    # =========================================================================
    # Sharing
    # =========================================================================

    def get_share_status(self, notebook_id: str) -> dict:
        """Not available via REST API — stub."""
        return {"is_public": False, "access_level": "restricted", "collaborators": []}

    def set_public_access(self, notebook_id: str, is_public: bool = True):
        """Enterprise does not support public sharing."""
        raise NotImplementedError(
            "Public sharing is not available in Enterprise. "
            "Use notebook_share_invite to share with specific users."
        )

    def add_collaborator(self, notebook_id: str, email: str, role: str = "viewer", **kwargs) -> bool:
        """Share notebook with a user."""
        role_map = {
            "viewer": "PROJECT_ROLE_READER",
            "editor": "PROJECT_ROLE_WRITER",
            "owner": "PROJECT_ROLE_OWNER",
        }
        api_role = role_map.get(role, "PROJECT_ROLE_READER")
        return self._ec.share_notebook(notebook_id, email, api_role)

    # =========================================================================
    # Notes (not in REST API)
    # =========================================================================

    def create_note(self, notebook_id: str, content: str, **kwargs):
        raise NotImplementedError("Notes are not available in the Enterprise REST API.")

    def list_notes(self, notebook_id: str) -> list:
        return []

    def update_note(self, note_id: str, **kwargs):
        raise NotImplementedError("Notes are not available in the Enterprise REST API.")

    def delete_note(self, note_id: str, notebook_id: str) -> bool:
        raise NotImplementedError("Notes are not available in the Enterprise REST API.")

    # =========================================================================
    # Research (not in REST API)
    # =========================================================================

    def start_research(self, *args, **kwargs):
        raise NotImplementedError("Research is not available in the Enterprise REST API.")

    def poll_research(self, *args, **kwargs):
        raise NotImplementedError("Research is not available in the Enterprise REST API.")
