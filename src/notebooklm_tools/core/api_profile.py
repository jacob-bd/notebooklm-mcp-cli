"""API profiles for personal and enterprise NotebookLM.

Enterprise NotebookLM (notebooklm.cloud.google.com) uses a completely different
API surface than personal (notebooklm.google.com): different service name,
RPC IDs, URL structure, and resource path format.

This module defines profiles that encapsulate those differences so the rest
of the codebase can work with either backend.
"""

import os
from dataclasses import dataclass, field


@dataclass
class APIProfile:
    """Configuration profile for a NotebookLM API backend."""

    # Identity
    is_enterprise: bool = False

    # URL construction
    service_name: str = "LabsTailwindUi"
    base_url: str = "https://notebooklm.google.com"
    location: str = ""  # Enterprise only: "global", "us", or "eu"
    project_id: str = ""  # Enterprise only: GCP project number

    # Streaming query endpoint path (after /{location}/_/{service_name}/data/)
    query_service: str = "google.internal.labs.tailwind.orchestration.v1.LabsTailwindOrchestrationService"

    # Build label fallback prefix
    bl_fallback: str = "boq_labs-tailwind-frontend_20260108.06_p0"

    # Extra query params added to every batchexecute request
    extra_query_params: dict = field(default_factory=dict)

    # RPC ID overrides — keys match the class attribute names on BaseClient
    rpc_ids: dict = field(default_factory=dict)

    # --- Helpers ---

    @property
    def resource_prefix(self) -> str:
        """GCP resource prefix, e.g. 'projects/123/locations/global'."""
        if not self.is_enterprise:
            return ""
        return f"projects/{self.project_id}/locations/{self.location}"

    def notebook_path(self, notebook_id: str) -> str:
        """Full resource path for a notebook."""
        if not self.is_enterprise:
            return notebook_id
        return f"{self.resource_prefix}/notebooks/{notebook_id}"

    def source_path(self, notebook_id: str, source_id: str) -> str:
        """Full resource path for a source."""
        if not self.is_enterprise:
            return source_id
        return f"{self.resource_prefix}/notebooks/{notebook_id}/sources/{source_id}"

    def notebook_url_path(self, notebook_id: str) -> str:
        """URL path segment for a notebook (for source-path query param)."""
        if self.is_enterprise:
            return f"/{self.location}/notebook/{notebook_id}"
        return f"/notebook/{notebook_id}"

    def web_url(self, notebook_id: str) -> str:
        """Full web URL for a notebook."""
        if self.is_enterprise:
            return f"{self.base_url}/{self.location}/notebook/{notebook_id}?project={self.project_id}"
        return f"{self.base_url}/notebook/{notebook_id}"

    @property
    def batchexecute_path(self) -> str:
        """URL path for batchexecute endpoint."""
        loc = f"/{self.location}" if self.location else ""
        return f"{loc}/_/{self.service_name}/data/batchexecute"

    @property
    def query_endpoint(self) -> str:
        """URL path for the streaming query endpoint."""
        loc = f"/{self.location}" if self.location else ""
        return f"{loc}/_/{self.service_name}/data/{self.query_service}/GenerateFreeFormStreamed"

    def notebook_metadata(self, notebook_id: str) -> dict | None:
        """Build the {"70000": ...} metadata dict for enterprise, or None for personal."""
        if not self.is_enterprise:
            return None
        return {"70000": self.notebook_path(notebook_id)}


def _personal_profile() -> APIProfile:
    """Create a personal NotebookLM profile."""
    return APIProfile(
        is_enterprise=False,
        service_name="LabsTailwindUi",
        base_url=os.environ.get("NOTEBOOKLM_BASE_URL", "https://notebooklm.google.com").rstrip("/"),
        query_service="google.internal.labs.tailwind.orchestration.v1.LabsTailwindOrchestrationService",
        bl_fallback="boq_labs-tailwind-frontend_20260108.06_p0",
    )


def _enterprise_profile(project_id: str, location: str = "global") -> APIProfile:
    """Create an enterprise NotebookLM profile."""
    return APIProfile(
        is_enterprise=True,
        service_name="CloudNotebookLmUi",
        base_url="https://notebooklm.cloud.google.com",
        location=location,
        project_id=project_id,
        query_service="google.cloud.notebooklm.v1main.NotebookService",
        bl_fallback="boq_cloud-ml-notebooklm-ui_20260324.07_p0",
        extra_query_params={"authuser": "0", "pageId": "none"},
        rpc_ids={
            # Notebook operations
            "RPC_LIST_NOTEBOOKS": "rG2vCb",
            "RPC_GET_NOTEBOOK": "tHcQ6c",
            "RPC_CREATE_NOTEBOOK": "AzXHBd",
            # Source operations
            "RPC_ADD_SOURCE": "kqBlec",
            # Notes operations
            "RPC_CREATE_NOTE": "YoTKpc",
            "RPC_GET_NOTES": "a0XDpc",
            # Studio / artifacts
            "RPC_CREATE_STUDIO": "aNc62",
            "RPC_POLL_STUDIO": "aKrKnb",
            # Other
            "RPC_GET_SUMMARY": "LmGGPd",
            "RPC_PREFERENCES": "y2DRud",
            # Artifacts list (enterprise-specific, no personal equivalent)
            "RPC_LIST_ARTIFACTS": "ca0cne",
        },
    )


def get_api_profile() -> APIProfile:
    """Get the appropriate API profile based on config.toml and environment.

    Resolution chain: env var > config.toml > default ("personal")
    """
    from notebooklm_tools.utils.config import get_config

    config = get_config()
    mode = config.enterprise.mode.lower()

    if mode == "enterprise":
        project_id = config.enterprise.project_id
        if not project_id:
            raise ValueError(
                "Enterprise mode requires a project ID.\n"
                "Set it with: nlm config set enterprise.project_id YOUR_PROJECT_ID\n"
                "Or: export NOTEBOOKLM_PROJECT_ID=YOUR_PROJECT_ID"
            )
        location = config.enterprise.location or "global"
        return _enterprise_profile(project_id, location)

    return _personal_profile()
