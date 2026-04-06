"""Standalone Podcast tool — generate podcasts from text via GCP Discovery Engine.

Uses the Discovery Engine Podcast API (v1, stable) to generate audio podcasts
from raw text without requiring a NotebookLM notebook.

Requirements:
  - Google Cloud SDK installed (`brew install google-cloud-sdk`)
  - `gcloud auth login` completed with an account that has access
  - `roles/discoveryengine.podcastApiUser` IAM role on the GCP project
  - NOTEBOOKLM_PROJECT_ID environment variable set (GCP project number)
"""

import os
import subprocess
from pathlib import Path
from typing import Any

from ._utils import logged_tool

_PODCAST_API = "https://discoveryengine.googleapis.com/v1"


def _gcp_token() -> str | None:
    """Get a GCP OAuth2 access token via gcloud. Returns None if unavailable."""
    try:
        result = subprocess.run(
            ["gcloud", "auth", "print-access-token"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        token = result.stdout.strip()
        return token if result.returncode == 0 and token else None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


def _project_id() -> str:
    """Get GCP project ID from env var."""
    return os.environ.get("NOTEBOOKLM_PROJECT_ID", "")


@logged_tool()
def podcast_create(
    text: str | list[str],
    project_id: str = "",
    title: str = "",
    description: str = "",
    focus: str = "",
    length: str = "STANDARD",
    language: str = "en",
) -> dict[str, Any]:
    """Generate a standalone podcast from text using GCP Discovery Engine (v1).

    Creates an audio podcast from raw text content without requiring a NotebookLM
    notebook. Runs as a long-running operation — use podcast_status to poll for
    completion, then podcast_download to save the MP3.

    Requirements:
      - `gcloud auth login` completed
      - `roles/discoveryengine.podcastApiUser` IAM role
      - NOTEBOOKLM_PROJECT_ID env var (or pass project_id directly)

    Args:
        text: Text content to convert to a podcast. Can be a single string or a
              list of strings (each treated as a separate source context).
        project_id: GCP project number (overrides NOTEBOOKLM_PROJECT_ID env var)
        title: Optional podcast title
        description: Optional podcast description
        focus: Optional topic focus prompt to guide the podcast content
        length: "SHORT" (~4-5 min) or "STANDARD" (~10 min, default)
        language: BCP-47 language code (default: "en")

    Returns:
        Dict with operation_name for use with podcast_status / podcast_download.

    Example:
        podcast_create(text="The history of the Roman Empire...", length="SHORT")
    """
    import httpx

    pid = project_id or _project_id()
    if not pid:
        return {
            "status": "error",
            "error": "project_id is required. Set NOTEBOOKLM_PROJECT_ID env var or pass project_id.",
            "hint": "Find your project number in the GCP console or NotebookLM enterprise URL.",
        }

    token = _gcp_token()
    if not token:
        return {
            "status": "error",
            "error": "GCP auth token not found.",
            "hint": "Run 'gcloud auth login' and ensure the Google Cloud SDK is installed.",
        }

    text_list = [text] if isinstance(text, str) else list(text)
    if not text_list or not any(t.strip() for t in text_list):
        return {"status": "error", "error": "text cannot be empty."}

    body: dict[str, Any] = {
        "podcastConfig": {
            "length": length.upper(),
            "languageCode": language,
        },
        "contexts": [{"text": t} for t in text_list],
    }
    if focus:
        body["podcastConfig"]["focus"] = focus
    if title:
        body["title"] = title
    if description:
        body["description"] = description

    url = f"{_PODCAST_API}/projects/{pid}/locations/global/podcasts"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    try:
        response = httpx.post(url, headers=headers, json=body, timeout=30)
        response.raise_for_status()
        data = response.json()
        operation_name = data.get("name", "")
        return {
            "status": "success",
            "operation_name": operation_name,
            "message": (
                "Podcast generation started. "
                "Use podcast_status(operation_name=...) to check progress, "
                "then podcast_download(operation_name=...) when done."
            ),
        }
    except httpx.HTTPStatusError as e:
        code = e.response.status_code
        if code == 401:
            return {"status": "error", "error": "GCP token expired. Run 'gcloud auth login'."}
        if code == 403:
            return {
                "status": "error",
                "error": f"Permission denied (HTTP 403). Project: {pid}",
                "hint": "Ensure your account has roles/discoveryengine.podcastApiUser on this project.",
            }
        return {"status": "error", "error": f"Podcast API error: HTTP {code}"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@logged_tool()
def podcast_status(operation_name: str) -> dict[str, Any]:
    """Check the status of a podcast generation operation.

    Args:
        operation_name: The operation name returned by podcast_create

    Returns:
        Dict with done (bool), and audio_uri when complete.
    """
    import httpx

    if not operation_name:
        return {"status": "error", "error": "operation_name is required."}

    token = _gcp_token()
    if not token:
        return {"status": "error", "error": "GCP auth token not found. Run 'gcloud auth login'."}

    url = f"{_PODCAST_API}/{operation_name}"
    headers = {"Authorization": f"Bearer {token}"}

    try:
        response = httpx.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
        done = data.get("done", False)

        result: dict[str, Any] = {
            "status": "success",
            "done": done,
            "operation_name": operation_name,
        }

        if done:
            if "error" in data:
                result["generation_error"] = data["error"].get("message", "Unknown error")
            elif "response" in data:
                result["audio_uri"] = data["response"].get("audioUri", "")
                result["message"] = "Podcast ready. Use podcast_download to save the MP3."
        else:
            result["message"] = "Still generating — check again in 30-60 seconds."

        return result
    except httpx.HTTPStatusError as e:
        return {"status": "error", "error": f"Status check failed: HTTP {e.response.status_code}"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@logged_tool()
def podcast_download(
    operation_name: str,
    output_path: str = "",
) -> dict[str, Any]:
    """Download a completed podcast as an MP3.

    Call podcast_status first to confirm the operation is done before downloading.

    Args:
        operation_name: The operation name from podcast_create
        output_path: Local file path to save the MP3 (default: ~/Downloads/podcast.mp3)

    Returns:
        Dict with file_path of the saved MP3.
    """
    import httpx

    if not operation_name:
        return {"status": "error", "error": "operation_name is required."}

    token = _gcp_token()
    if not token:
        return {"status": "error", "error": "GCP auth token not found. Run 'gcloud auth login'."}

    save_path = output_path or os.path.expanduser("~/Downloads/podcast.mp3")
    url = f"{_PODCAST_API}/{operation_name}:download?alt=media"
    headers = {"Authorization": f"Bearer {token}"}

    try:
        with httpx.stream("GET", url, headers=headers, follow_redirects=True, timeout=120) as r:
            if r.status_code == 404:
                return {
                    "status": "error",
                    "error": "Podcast not found or not yet ready.",
                    "hint": "Use podcast_status to confirm done=True before downloading.",
                }
            r.raise_for_status()
            dest = Path(save_path)
            dest.parent.mkdir(parents=True, exist_ok=True)
            with open(dest, "wb") as f:
                for chunk in r.iter_bytes(65536):
                    f.write(chunk)
        return {
            "status": "success",
            "file_path": str(dest),
            "message": f"Podcast saved to {dest}",
        }
    except httpx.HTTPStatusError as e:
        return {"status": "error", "error": f"Download failed: HTTP {e.response.status_code}"}
    except Exception as e:
        return {"status": "error", "error": str(e)}
