"""Enterprise NotebookLM client using the official Discovery Engine REST API.

This client talks to the stable, documented GCP REST API instead of scraping
the web UI's batchexecute endpoint. It uses GCP OAuth2 bearer tokens for auth.

Environment variables:
    NOTEBOOKLM_PROJECT_ID: GCP project number (required)
    NOTEBOOKLM_LOCATION: GCP location - "global", "us", or "eu" (default: "global")

Auth: Requires `gcloud auth application-default login` or a service account.
"""

import json
import logging
import os
import subprocess
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class EnterpriseClient:
    """Client for the NotebookLM Enterprise REST API (Discovery Engine)."""

    def __init__(
        self,
        project_id: str | None = None,
        location: str | None = None,
        access_token: str | None = None,
    ):
        self.project_id = project_id or os.environ.get("NOTEBOOKLM_PROJECT_ID", "")
        self.location = location or os.environ.get("NOTEBOOKLM_LOCATION", "global")

        if not self.project_id:
            raise ValueError(
                "NOTEBOOKLM_PROJECT_ID is required for enterprise mode.\n"
                "Find it in your NotebookLM URL: ...?project=YOUR_PROJECT_ID"
            )

        # Determine endpoint location for the REST API URL
        # "global" location uses "global" endpoint; "us"/"eu" use their own
        self._endpoint_location = self.location

        self._base_url = (
            f"https://{self._endpoint_location}-discoveryengine.googleapis.com/v1alpha"
            f"/projects/{self.project_id}/locations/{self.location}"
        )
        self._access_token = access_token
        self._client = httpx.Client(timeout=60.0)

        # Web UI base for notebook URLs
        self._web_base = "https://notebooklm.cloud.google.com"

    def close(self):
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    # =========================================================================
    # Auth
    # =========================================================================

    def _get_token(self) -> str:
        """Get a valid access token, refreshing if needed."""
        if self._access_token:
            return self._access_token

        # Try gcloud CLI
        try:
            result = subprocess.run(
                ["gcloud", "auth", "print-access-token"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0 and result.stdout.strip():
                self._access_token = result.stdout.strip()
                return self._access_token
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        # Try application default credentials
        try:
            result = subprocess.run(
                ["gcloud", "auth", "application-default", "print-access-token"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0 and result.stdout.strip():
                self._access_token = result.stdout.strip()
                return self._access_token
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        raise ValueError(
            "Could not get GCP access token. Please run:\n"
            "  gcloud auth login\n"
            "  gcloud auth application-default login"
        )

    def _headers(self) -> dict[str, str]:
        """Build request headers with auth."""
        return {
            "Authorization": f"Bearer {self._get_token()}",
            "Content-Type": "application/json",
        }

    def _request(self, method: str, path: str, **kwargs) -> Any:
        """Make an authenticated API request."""
        url = f"{self._base_url}/{path.lstrip('/')}"
        response = self._client.request(method, url, headers=self._headers(), **kwargs)

        if response.status_code == 401:
            # Token expired — clear and retry once
            self._access_token = None
            response = self._client.request(
                method, url, headers=self._headers(), **kwargs
            )

        response.raise_for_status()

        if response.content:
            return response.json()
        return None

    # =========================================================================
    # Notebook URL helper
    # =========================================================================

    def web_url(self, notebook_id: str) -> str:
        """Get the web UI URL for a notebook."""
        return (
            f"{self._web_base}/{self.location}/notebook/{notebook_id}"
            f"?project={self.project_id}"
        )

    # =========================================================================
    # Notebooks
    # =========================================================================

    def list_notebooks(self, page_size: int = 500) -> list[dict]:
        """List recently viewed notebooks."""
        result = self._request(
            "GET",
            f"notebooks:listRecentlyViewed?pageSize={page_size}",
        )
        notebooks = []
        if result and "notebooks" in result:
            for nb in result["notebooks"]:
                nb_id = nb.get("notebookId", "")
                notebooks.append({
                    "notebook_id": nb_id,
                    "title": nb.get("title", "Untitled"),
                    "url": self.web_url(nb_id),
                    "metadata": nb.get("metadata", {}),
                    "name": nb.get("name", ""),
                })
        return notebooks

    def get_notebook(self, notebook_id: str) -> dict | None:
        """Get notebook details."""
        result = self._request("GET", f"notebooks/{notebook_id}")
        if result:
            return {
                "notebook_id": result.get("notebookId", notebook_id),
                "title": result.get("title", "Untitled"),
                "url": self.web_url(notebook_id),
                "metadata": result.get("metadata", {}),
                "name": result.get("name", ""),
            }
        return None

    def create_notebook(self, title: str = "") -> dict | None:
        """Create a new notebook."""
        body = {"title": title} if title else {}
        result = self._request("POST", "notebooks", json=body)
        if result:
            nb_id = result.get("notebookId", "")
            return {
                "notebook_id": nb_id,
                "title": result.get("title", title or "Untitled notebook"),
                "url": self.web_url(nb_id),
                "name": result.get("name", ""),
            }
        return None

    def delete_notebook(self, notebook_id: str) -> bool:
        """Delete a notebook permanently."""
        self._request("DELETE", f"notebooks/{notebook_id}")
        return True

    def share_notebook(
        self, notebook_id: str, email: str, role: str = "NOTEBOOK_VIEWER"
    ) -> bool:
        """Share a notebook with a user in the same GCP project."""
        body = {"role": role, "userEmail": email}
        self._request("POST", f"notebooks/{notebook_id}:share", json=body)
        return True

    # =========================================================================
    # Sources
    # =========================================================================

    def list_sources(self, notebook_id: str) -> list[dict]:
        """List sources in a notebook."""
        result = self._request("GET", f"notebooks/{notebook_id}/sources")
        sources = []
        if result and "sources" in result:
            for src in result["sources"]:
                sources.append({
                    "id": src.get("sourceId", ""),
                    "title": src.get("title", "Untitled"),
                    "url": src.get("url", ""),
                    "name": src.get("name", ""),
                })
        return sources

    def add_source(self, notebook_id: str, url: str) -> dict | None:
        """Add a URL source to a notebook."""
        body = {"source": {"url": url}}
        result = self._request(
            "POST", f"notebooks/{notebook_id}/sources", json=body
        )
        if result:
            return {
                "id": result.get("sourceId", ""),
                "title": result.get("title", ""),
                "name": result.get("name", ""),
            }
        return None

    def delete_source(self, notebook_id: str, source_id: str) -> bool:
        """Delete a source from a notebook."""
        self._request("DELETE", f"notebooks/{notebook_id}/sources/{source_id}")
        return True

    # =========================================================================
    # Audio Overview
    # =========================================================================

    def generate_audio_overview(self, notebook_id: str) -> dict | None:
        """Generate an audio overview for a notebook."""
        result = self._request(
            "POST", f"notebooks/{notebook_id}:generateAudioOverview", json={}
        )
        return result

    # =========================================================================
    # Query (falls back to batchexecute — not available in REST API)
    # =========================================================================

    def query(self, notebook_id: str, query_text: str, **kwargs) -> dict:
        """Query is not available via the REST API.

        The official Discovery Engine REST API does not expose a query/chat
        endpoint for NotebookLM notebooks. This operation requires the
        batchexecute streaming endpoint.
        """
        raise NotImplementedError(
            "Chat/query is not available in the Enterprise REST API. "
            "This operation requires batchexecute (cookie-based auth). "
            "Use the web UI for chat queries, or authenticate with "
            "'nlm login' to use the batchexecute fallback."
        )
