"""Enterprise NotebookLM client using the official Discovery Engine REST API.

This client talks to the stable, documented GCP REST API instead of scraping
the web UI's batchexecute endpoint. It uses GCP OAuth2 bearer tokens for auth.

Environment variables:
    NOTEBOOKLM_PROJECT_ID: GCP project number (required)
    NOTEBOOKLM_LOCATION: GCP location - "global", "us", or "eu" (default: "global")

Auth: Requires `gcloud auth login`.
"""

import logging
import os
import subprocess
from pathlib import Path
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

        self._endpoint_location = self.location
        self._base_url = (
            f"https://{self._endpoint_location}-discoveryengine.googleapis.com/v1alpha"
            f"/projects/{self.project_id}/locations/{self.location}"
        )
        # Upload endpoint uses a different URL prefix
        self._upload_base_url = (
            f"https://{self._endpoint_location}-discoveryengine.googleapis.com"
            f"/upload/v1alpha/projects/{self.project_id}/locations/{self.location}"
        )
        self._access_token = access_token
        self._client = httpx.Client(timeout=120.0)
        self._web_base = "https://notebooklm.cloud.google.com"

    def close(self):
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    # =========================================================================
    # Auth
    # =========================================================================

    def _get_token(self) -> str:
        """Get a valid access token via gcloud CLI."""
        if self._access_token:
            return self._access_token

        for cmd in [
            ["gcloud", "auth", "print-access-token"],
            ["gcloud", "auth", "application-default", "print-access-token"],
        ]:
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                if result.returncode == 0 and result.stdout.strip():
                    self._access_token = result.stdout.strip()
                    return self._access_token
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue

        raise ValueError(
            "Could not get GCP access token. Please run:\n"
            "  gcloud auth login"
        )

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._get_token()}",
            "Content-Type": "application/json",
        }

    def _request(self, method: str, path: str, base_url: str | None = None, **kwargs) -> Any:
        """Make an authenticated API request."""
        url = f"{base_url or self._base_url}/{path.lstrip('/')}"
        response = self._client.request(method, url, headers=self._headers(), **kwargs)

        if response.status_code == 401:
            self._access_token = None
            response = self._client.request(method, url, headers=self._headers(), **kwargs)

        response.raise_for_status()
        return response.json() if response.content else None

    # =========================================================================
    # Helpers
    # =========================================================================

    def _resource_name(self, notebook_id: str) -> str:
        """Full resource name for a notebook."""
        return f"projects/{self.project_id}/locations/{self.location}/notebooks/{notebook_id}"

    def web_url(self, notebook_id: str) -> str:
        return f"{self._web_base}/{self.location}/notebook/{notebook_id}?project={self.project_id}"

    # =========================================================================
    # Notebooks
    # =========================================================================

    def list_notebooks(self, page_size: int = 500) -> list[dict]:
        """List recently viewed notebooks."""
        result = self._request("GET", f"notebooks:listRecentlyViewed?pageSize={page_size}")
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
        result = self._request("GET", f"notebooks/{notebook_id}")
        if result:
            # Parse sources from the notebook response
            sources = []
            for src in result.get("sources", []):
                sid = src.get("sourceId", {})
                source_id = sid.get("id", "") if isinstance(sid, dict) else str(sid)
                sources.append({
                    "id": source_id,
                    "title": src.get("title", "Untitled"),
                    "status": src.get("settings", {}).get("status", ""),
                    "name": src.get("name", ""),
                })
            return {
                "notebook_id": result.get("notebookId", notebook_id),
                "title": result.get("title", "Untitled"),
                "url": self.web_url(notebook_id),
                "metadata": result.get("metadata", {}),
                "name": result.get("name", ""),
                "sources": sources,
            }
        return None

    def create_notebook(self, title: str = "") -> dict | None:
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
        """Delete notebook(s) via batchDelete (POST, not DELETE)."""
        body = {"names": [self._resource_name(notebook_id)]}
        self._request("POST", "notebooks:batchDelete", json=body)
        return True

    def share_notebook(self, notebook_id: str, email: str, role: str = "PROJECT_ROLE_READER") -> bool:
        """Share a notebook. Roles: PROJECT_ROLE_OWNER, PROJECT_ROLE_WRITER, PROJECT_ROLE_READER."""
        body = {"accountAndRoles": [{"email": email, "role": role}]}
        self._request("POST", f"notebooks/{notebook_id}:share", json=body)
        return True

    # =========================================================================
    # Sources
    # =========================================================================

    def get_source(self, notebook_id: str, source_id: str) -> dict | None:
        """Get a single source's details."""
        result = self._request("GET", f"notebooks/{notebook_id}/sources/{source_id}")
        if result:
            sid = result.get("sourceId", {})
            return {
                "id": sid.get("id", source_id) if isinstance(sid, dict) else sid,
                "title": result.get("title", "Untitled"),
                "status": result.get("settings", {}).get("status", ""),
                "metadata": result.get("metadata", {}),
                "name": result.get("name", ""),
            }
        return None

    def add_source_url(self, notebook_id: str, url: str, name: str = "") -> dict | None:
        """Add a web URL source via batchCreate."""
        content = {"webContent": {"url": url}}
        if name:
            content["webContent"]["sourceName"] = name
        body = {"userContents": [content]}
        result = self._request("POST", f"notebooks/{notebook_id}/sources:batchCreate", json=body)
        return self._parse_source_result(result)

    def add_source_text(self, notebook_id: str, text: str, name: str = "Pasted Text") -> dict | None:
        """Add a text source via batchCreate."""
        body = {"userContents": [{"textContent": {"sourceName": name, "content": text}}]}
        result = self._request("POST", f"notebooks/{notebook_id}/sources:batchCreate", json=body)
        return self._parse_source_result(result)

    def add_source_youtube(self, notebook_id: str, youtube_url: str) -> dict | None:
        """Add a YouTube video source via batchCreate."""
        body = {"userContents": [{"videoContent": {"youtubeUrl": youtube_url}}]}
        result = self._request("POST", f"notebooks/{notebook_id}/sources:batchCreate", json=body)
        return self._parse_source_result(result)

    def add_source_drive(self, notebook_id: str, document_id: str, mime_type: str, name: str = "") -> dict | None:
        """Add a Google Drive source via batchCreate."""
        content = {"googleDriveContent": {"documentId": document_id, "mimeType": mime_type}}
        if name:
            content["googleDriveContent"]["sourceName"] = name
        body = {"userContents": [content]}
        result = self._request("POST", f"notebooks/{notebook_id}/sources:batchCreate", json=body)
        return self._parse_source_result(result)

    def upload_file(self, notebook_id: str, file_path: str, display_name: str = "") -> dict | None:
        """Upload a local file as a source."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Determine content type
        suffix_map = {
            ".pdf": "application/pdf",
            ".txt": "text/plain",
            ".md": "text/markdown",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".mp3": "audio/mpeg",
            ".wav": "audio/wav",
            ".mp4": "video/mp4",
        }
        content_type = suffix_map.get(path.suffix.lower(), "application/octet-stream")
        fname = display_name or path.name

        headers = {
            "Authorization": f"Bearer {self._get_token()}",
            "Content-Type": content_type,
            "X-Goog-Upload-File-Name": fname,
            "X-Goog-Upload-Protocol": "raw",
        }

        url = f"{self._upload_base_url}/notebooks/{notebook_id}/sources:uploadFile"
        with open(path, "rb") as f:
            response = self._client.post(url, headers=headers, content=f.read())

        if response.status_code == 401:
            self._access_token = None
            headers["Authorization"] = f"Bearer {self._get_token()}"
            with open(path, "rb") as f:
                response = self._client.post(url, headers=headers, content=f.read())

        response.raise_for_status()
        result = response.json() if response.content else None
        return self._parse_source_result(result)

    def delete_source(self, notebook_id: str, source_id: str) -> bool:
        """Delete source(s) via batchDelete (POST, not DELETE)."""
        # Note: resource name uses singular "source" not "sources"
        name = f"projects/{self.project_id}/locations/{self.location}/notebooks/{notebook_id}/source/{source_id}"
        body = {"names": [name]}
        self._request("POST", f"notebooks/{notebook_id}/sources:batchDelete", json=body)
        return True

    def _parse_source_result(self, result: Any) -> dict | None:
        """Parse source creation response (batchCreate wraps in 'sources' array)."""
        if not result:
            return None
        # batchCreate returns {"sources": [{sourceId: {id: ...}, title: ..., ...}]}
        sources = result.get("sources", [])
        if sources:
            src = sources[0]
            sid = src.get("sourceId", {})
            source_id = sid.get("id", "") if isinstance(sid, dict) else str(sid)
            return {
                "id": source_id,
                "title": src.get("title", ""),
                "name": src.get("name", ""),
                "status": src.get("settings", {}).get("status", ""),
            }
        # uploadFile returns sourceId directly
        sid = result.get("sourceId", {})
        source_id = sid.get("id", "") if isinstance(sid, dict) else str(sid)
        return {
            "id": source_id,
            "title": result.get("title", ""),
            "name": result.get("name", ""),
        }

    # =========================================================================
    # Audio Overview
    # =========================================================================

    def generate_audio_overview(
        self,
        notebook_id: str,
        source_ids: list[str] | None = None,
        focus: str = "",
        language: str = "en",
    ) -> dict | None:
        """Generate an audio overview for a notebook."""
        body: dict[str, Any] = {}
        if source_ids:
            body["sourceIds"] = [{"id": sid} for sid in source_ids]
        if focus:
            body["episodeFocus"] = focus
        if language != "en":
            body["languageCode"] = language
        result = self._request("POST", f"notebooks/{notebook_id}/audioOverviews", json=body)
        return result

    def delete_audio_overview(self, notebook_id: str) -> bool:
        """Delete the audio overview for a notebook."""
        self._request("DELETE", f"notebooks/{notebook_id}/audioOverviews/default")
        return True

    # =========================================================================
    # Query (not available in REST API)
    # =========================================================================

    def query(self, notebook_id: str, query_text: str, **kwargs) -> dict:
        raise NotImplementedError(
            "Chat/query is not available in the Enterprise REST API. "
            "Use the web UI for chat queries."
        )
