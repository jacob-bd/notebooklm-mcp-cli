"""Setup tools — Configure NotebookLM mode (personal/enterprise)."""

import subprocess
from typing import Any

from ._utils import logged_tool, reset_client


@logged_tool()
def configure_mode(
    mode: str = "personal",
    project_id: str = "",
    location: str = "global",
) -> dict[str, Any]:
    """Configure NotebookLM mode (personal or enterprise).

    IMPORTANT: Enterprise and personal use SEPARATE authentication.
    - Enterprise: requires `gcloud auth login` (GCP OAuth2)
    - Personal: requires `nlm login` (browser cookie auth)
    Switching modes without the correct auth will cause 400/401 errors.
    Always confirm the user has authenticated for the target mode before switching.

    Args:
        mode: "personal" or "enterprise"
        project_id: GCP project number (required for enterprise, found in NotebookLM URL)
        location: GCP location - "global", "us", or "eu" (default: "global")

    Returns:
        Dictionary with status, configuration, and auth requirements.
    """
    if mode not in ("personal", "enterprise"):
        return {"status": "error", "error": "mode must be 'personal' or 'enterprise'"}

    if mode == "enterprise" and not project_id:
        # Check if we already have a project_id in config
        from notebooklm_tools.utils.config import get_config

        existing = get_config().enterprise.project_id
        if not existing:
            return {
                "status": "error",
                "error": "project_id is required for enterprise mode. "
                "Find it in your NotebookLM URL: ...?project=YOUR_PROJECT_ID",
            }
        project_id = existing

    # Pre-check auth for the target mode
    if mode == "personal":
        from notebooklm_tools.core.auth import load_cached_tokens

        cached = load_cached_tokens()
        if not cached or not cached.cookies:
            return {
                "status": "error",
                "mode": mode,
                "message": "Cannot switch to personal mode — no personal auth tokens found. "
                "Run 'nlm login' in your terminal first to authenticate "
                "with your personal Google account.",
                "auth_required": True,
            }

    if mode == "enterprise":
        try:
            result = subprocess.run(
                ["gcloud", "auth", "print-access-token"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0 or not result.stdout.strip():
                return {
                    "status": "error",
                    "mode": mode,
                    "message": "Cannot switch to enterprise mode — no GCP auth token found. "
                    "Run 'gcloud auth login' in your terminal first.",
                    "auth_required": True,
                }
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return {
                "status": "error",
                "message": "gcloud CLI not found or timed out. "
                "Install it with 'brew install google-cloud-sdk' and run 'gcloud auth login'.",
            }

    from notebooklm_tools.utils.config import get_config, reset_config, save_config

    config = get_config()
    config.enterprise.mode = mode
    if project_id:
        config.enterprise.project_id = project_id
    config.enterprise.location = location
    save_config(config)

    # Reset cached config and client so next call uses new mode
    reset_config()
    reset_client()

    result = {
        "status": "success",
        "mode": mode,
        "message": f"Mode set to {mode}. All subsequent calls will use {mode} mode.",
    }

    if mode == "enterprise":
        result["project_id"] = project_id
        result["location"] = location
        result["auth"] = "GCP OAuth2 (gcloud)"
    else:
        result["auth"] = "Browser cookies (nlm login)"

    return result
