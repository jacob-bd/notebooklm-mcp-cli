"""
NotebookLM artifact refresh for doc-refresh.

Handles regeneration of Standard 7 artifacts when docs change:
- Mind Map
- Briefing Doc
- Study Guide
- Audio Overview
- Infographic
- Flashcards
- Quiz

Triggers: content delta > threshold, major version bump, or --force
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from .hashing import should_regenerate_artifacts
from .models import HashComparison


class ArtifactType(Enum):
    """Standard 7 artifact types."""

    MIND_MAP = "mind_map"
    BRIEFING_DOC = "briefing_doc"
    STUDY_GUIDE = "study_guide"
    AUDIO_OVERVIEW = "audio_overview"
    INFOGRAPHIC = "infographic"
    FLASHCARDS = "flashcards"
    QUIZ = "quiz"


# Artifact metadata: display name, MCP tool, creation params
ARTIFACT_METADATA: dict[ArtifactType, dict[str, Any]] = {
    ArtifactType.MIND_MAP: {
        "display_name": "Mind Map",
        "mcp_tool": "mind_map_create",
        "default_params": {"title": "Documentation Mind Map"},
    },
    ArtifactType.BRIEFING_DOC: {
        "display_name": "Briefing Doc",
        "mcp_tool": "report_create",
        "default_params": {"report_format": "Briefing Doc"},
    },
    ArtifactType.STUDY_GUIDE: {
        "display_name": "Study Guide",
        "mcp_tool": "report_create",
        "default_params": {"report_format": "Study Guide"},
    },
    ArtifactType.AUDIO_OVERVIEW: {
        "display_name": "Audio Overview",
        "mcp_tool": "audio_overview_create",
        "default_params": {"format": "deep_dive", "length": "default"},
    },
    ArtifactType.INFOGRAPHIC: {
        "display_name": "Infographic",
        "mcp_tool": "infographic_create",
        "default_params": {"orientation": "landscape", "detail_level": "standard"},
    },
    ArtifactType.FLASHCARDS: {
        "display_name": "Flashcards",
        "mcp_tool": "flashcards_create",
        "default_params": {"difficulty": "medium"},
    },
    ArtifactType.QUIZ: {
        "display_name": "Quiz",
        "mcp_tool": "quiz_create",
        "default_params": {"question_count": 5, "difficulty": 2},
    },
}

# Standard 7 - the default set of artifacts
STANDARD_7 = list(ArtifactType)

# Default regeneration threshold (15%)
DEFAULT_THRESHOLD = 0.15

# Polling configuration
DEFAULT_POLL_INTERVAL = 10  # seconds
DEFAULT_POLL_TIMEOUT = 300  # 5 minutes max


@dataclass
class ArtifactAction:
    """A single artifact action to perform."""

    artifact_type: ArtifactType
    action: str  # "create", "skip"
    reason: str


@dataclass
class ArtifactPlan:
    """Plan for refreshing artifacts."""

    repo_key: str
    notebook_id: str
    triggered: bool
    trigger_reason: Optional[str]
    change_delta: float
    actions: list[ArtifactAction] = field(default_factory=list)

    @property
    def creates(self) -> list[ArtifactAction]:
        return [a for a in self.actions if a.action == "create"]

    @property
    def skips(self) -> list[ArtifactAction]:
        return [a for a in self.actions if a.action == "skip"]

    @property
    def has_work(self) -> bool:
        return len(self.creates) > 0


@dataclass
class ArtifactResult:
    """Result of applying an artifact plan."""

    success: bool
    artifacts_created: int = 0
    artifacts_failed: int = 0
    errors: list[str] = field(default_factory=list)
    created_artifacts: dict[str, dict] = field(default_factory=dict)  # type -> status info


def parse_artifact_list(artifact_str: Optional[str]) -> list[ArtifactType]:
    """
    Parse comma-separated artifact list into ArtifactType list.

    Args:
        artifact_str: e.g., "audio,mind_map,briefing" or None for all

    Returns:
        List of ArtifactType to create
    """
    if not artifact_str:
        return STANDARD_7.copy()

    result = []
    for name in artifact_str.split(","):
        name = name.strip().lower()
        # Support various aliases
        aliases = {
            "audio": ArtifactType.AUDIO_OVERVIEW,
            "audio_overview": ArtifactType.AUDIO_OVERVIEW,
            "mind_map": ArtifactType.MIND_MAP,
            "mindmap": ArtifactType.MIND_MAP,
            "briefing": ArtifactType.BRIEFING_DOC,
            "briefing_doc": ArtifactType.BRIEFING_DOC,
            "study": ArtifactType.STUDY_GUIDE,
            "study_guide": ArtifactType.STUDY_GUIDE,
            "infographic": ArtifactType.INFOGRAPHIC,
            "flashcards": ArtifactType.FLASHCARDS,
            "quiz": ArtifactType.QUIZ,
        }
        if name in aliases:
            result.append(aliases[name])

    return result if result else STANDARD_7.copy()


def compute_artifact_plan(
    repo_key: str,
    notebook_id: str,
    hash_comparison: HashComparison,
    major_version_bump: bool = False,
    force: bool = False,
    threshold: float = DEFAULT_THRESHOLD,
    artifact_subset: Optional[list[ArtifactType]] = None,
) -> ArtifactPlan:
    """
    Compute the artifact refresh plan.

    Args:
        repo_key: Repository key
        notebook_id: NotebookLM notebook ID
        hash_comparison: Result of hash comparison
        major_version_bump: True if major version increased
        force: Force regeneration
        threshold: Change threshold (default 15%)
        artifact_subset: Specific artifacts to create (None = Standard 7)

    Returns:
        ArtifactPlan with actions
    """
    delta = hash_comparison.change_ratio_simple
    triggered = should_regenerate_artifacts(
        hash_comparison,
        major_version_bump=major_version_bump,
        force=force,
        threshold=threshold,
    )

    # Determine trigger reason
    trigger_reason = None
    if triggered:
        if force:
            trigger_reason = "--force flag"
        elif major_version_bump:
            trigger_reason = "Major version bump"
        elif delta > threshold:
            trigger_reason = f"Content delta {delta:.1%} > {threshold:.0%} threshold"

    plan = ArtifactPlan(
        repo_key=repo_key,
        notebook_id=notebook_id,
        triggered=triggered,
        trigger_reason=trigger_reason,
        change_delta=delta,
    )

    artifacts_to_check = artifact_subset or STANDARD_7
    for artifact_type in artifacts_to_check:
        if triggered:
            plan.actions.append(
                ArtifactAction(
                    artifact_type=artifact_type,
                    action="create",
                    reason=trigger_reason or "Triggered",
                )
            )
        else:
            plan.actions.append(
                ArtifactAction(
                    artifact_type=artifact_type,
                    action="skip",
                    reason=f"Change delta {delta:.1%} below {threshold:.0%} threshold",
                )
            )

    return plan


def get_notebook_source_ids(client: Any, notebook_id: str) -> list[str]:
    """
    Get all source IDs from a notebook.

    Args:
        client: NotebookLMClient instance
        notebook_id: NotebookLM notebook UUID

    Returns:
        List of source UUIDs
    """
    sources = client.get_notebook_sources_with_types(notebook_id)
    return [src.get("id", "") for src in sources if src.get("id")]


def apply_artifact_plan(
    client: Any,
    plan: ArtifactPlan,
    poll_interval: int = DEFAULT_POLL_INTERVAL,
    poll_timeout: int = DEFAULT_POLL_TIMEOUT,
    verbose: bool = False,
) -> ArtifactResult:
    """
    Apply an artifact plan to NotebookLM.

    Creates artifacts and polls studio_status until complete.

    Args:
        client: NotebookLMClient instance
        plan: ArtifactPlan to apply
        poll_interval: Seconds between status polls
        poll_timeout: Max seconds to wait for completion
        verbose: Print progress messages

    Returns:
        ArtifactResult with outcomes
    """
    result = ArtifactResult(success=True)

    if not plan.has_work:
        return result

    # Get source IDs from notebook (all artifact creation requires them)
    if verbose:
        print("  Fetching notebook source IDs...")
    source_ids = get_notebook_source_ids(client, plan.notebook_id)
    if not source_ids:
        result.success = False
        result.errors.append("No sources found in notebook")
        return result

    if verbose:
        print(f"  Found {len(source_ids)} sources")

    for action in plan.creates:
        artifact_type = action.artifact_type
        metadata = ARTIFACT_METADATA[artifact_type]
        tool_name = metadata["mcp_tool"]
        params = metadata["default_params"].copy()

        if verbose:
            print(f"  Creating {metadata['display_name']}...")

        try:
            response = None

            # Call the appropriate creation method (all require source_ids)
            if tool_name == "mind_map_create":
                # Mind map is two-step: generate + save
                gen_result = client.generate_mind_map(source_ids=source_ids)
                if gen_result and gen_result.get("mind_map_json"):
                    response = client.save_mind_map(
                        notebook_id=plan.notebook_id,
                        mind_map_json=gen_result["mind_map_json"],
                        source_ids=source_ids,
                        title=params.get("title", "Documentation Mind Map"),
                    )
                else:
                    result.errors.append("Failed to generate mind map JSON")
                    result.artifacts_failed += 1
                    continue

            elif tool_name == "report_create":
                response = client.create_report(
                    notebook_id=plan.notebook_id,
                    source_ids=source_ids,
                    report_format=params.get("report_format", "Briefing Doc"),
                )

            elif tool_name == "audio_overview_create":
                # Map string format to code
                format_map = {"deep_dive": 1, "brief": 2, "critique": 3, "debate": 4}
                length_map = {"short": 1, "default": 2, "long": 3}
                format_code = format_map.get(params.get("format", "deep_dive"), 1)
                length_code = length_map.get(params.get("length", "default"), 2)
                response = client.create_audio_overview(
                    notebook_id=plan.notebook_id,
                    source_ids=source_ids,
                    format_code=format_code,
                    length_code=length_code,
                )

            elif tool_name == "infographic_create":
                # Map string orientation/detail to codes
                orient_map = {"landscape": 1, "portrait": 2, "square": 3}
                detail_map = {"concise": 1, "standard": 2, "detailed": 3}
                orient_code = orient_map.get(params.get("orientation", "landscape"), 1)
                detail_code = detail_map.get(params.get("detail_level", "standard"), 2)
                response = client.create_infographic(
                    notebook_id=plan.notebook_id,
                    source_ids=source_ids,
                    orientation_code=orient_code,
                    detail_level_code=detail_code,
                )

            elif tool_name == "flashcards_create":
                response = client.create_flashcards(
                    notebook_id=plan.notebook_id,
                    source_ids=source_ids,
                    difficulty=params.get("difficulty", "medium"),
                )

            elif tool_name == "quiz_create":
                response = client.create_quiz(
                    notebook_id=plan.notebook_id,
                    source_ids=source_ids,
                    question_count=params.get("question_count", 5),
                    difficulty=params.get("difficulty", 2),
                )

            else:
                result.errors.append(f"Unknown tool: {tool_name}")
                result.artifacts_failed += 1
                continue

            if response:
                result.artifacts_created += 1
                result.created_artifacts[artifact_type.value] = {
                    "status": "initiated",
                    "response": response,
                }
            else:
                result.errors.append(f"Failed to create {metadata['display_name']}: no response")
                result.artifacts_failed += 1

        except Exception as e:
            result.errors.append(f"Failed to create {metadata['display_name']}: {e}")
            result.artifacts_failed += 1

    # Poll studio_status for completion
    if result.artifacts_created > 0 and poll_timeout > 0:
        if verbose:
            print(f"  Polling studio_status (timeout: {poll_timeout}s)...")

        start_time = time.time()
        while time.time() - start_time < poll_timeout:
            try:
                status = client.poll_studio_status(plan.notebook_id)
                if _all_artifacts_complete(status, result.created_artifacts):
                    if verbose:
                        print("  All artifacts complete.")
                    break
            except Exception as e:
                if verbose:
                    print(f"  Warning: status poll failed: {e}")

            time.sleep(poll_interval)
        else:
            result.errors.append(f"Timeout waiting for artifacts after {poll_timeout}s")

    if result.errors:
        result.success = False

    return result


def _all_artifacts_complete(status: Any, created: dict) -> bool:
    """
    Check if all created artifacts are complete.

    Args:
        status: Response from poll_studio_status (list of artifact dicts)
        created: Dict of artifact_type -> creation info

    Returns:
        True if all artifacts are ready
    """
    if not status:
        return False

    # poll_studio_status returns a list of artifact dicts directly
    # Each has: artifact_id, title, type, status, ...
    artifacts = status if isinstance(status, list) else []

    if not artifacts and not created:
        return True

    # Count completed artifacts
    # Status can be "in_progress", "completed", or "unknown"
    completed_count = sum(
        1 for a in artifacts
        if isinstance(a, dict) and a.get("status") in ("ready", "completed", "complete")
    )

    return completed_count >= len(created)


def format_artifact_plan(plan: ArtifactPlan) -> str:
    """Format an artifact plan as human-readable text."""
    lines: list[str] = []
    lines.append(f"# Artifact Plan: {plan.repo_key}")
    lines.append("")
    lines.append(f"**Notebook ID:** {plan.notebook_id}")
    lines.append(f"**Content Delta:** {plan.change_delta:.1%}")
    lines.append("")

    if plan.triggered:
        lines.append(f"**Status:** TRIGGERED ({plan.trigger_reason})")
        lines.append("")
        lines.append(f"## Artifacts to Create ({len(plan.creates)} total)")
        lines.append("")
        for action in plan.creates:
            metadata = ARTIFACT_METADATA[action.artifact_type]
            lines.append(f"- {metadata['display_name']}")
    else:
        lines.append("**Status:** NOT TRIGGERED")
        lines.append("")
        lines.append(f"Threshold not met. Use --force to regenerate anyway.")
        lines.append("")
        lines.append("## Artifacts Skipped")
        for action in plan.skips:
            metadata = ARTIFACT_METADATA[action.artifact_type]
            lines.append(f"- {metadata['display_name']} ({action.reason})")

    lines.append("")
    return "\n".join(lines)


def format_artifact_result(result: ArtifactResult) -> str:
    """Format an artifact result as human-readable text."""
    lines: list[str] = []
    lines.append("# Artifact Result")
    lines.append("")
    lines.append(f"**Success:** {'Yes' if result.success else 'No'}")
    lines.append(f"**Created:** {result.artifacts_created}")
    lines.append(f"**Failed:** {result.artifacts_failed}")

    if result.created_artifacts:
        lines.append("")
        lines.append("## Created Artifacts")
        for artifact_type, info in result.created_artifacts.items():
            metadata = ARTIFACT_METADATA[ArtifactType(artifact_type)]
            lines.append(f"- {metadata['display_name']}: {info.get('status', 'unknown')}")

    if result.errors:
        lines.append("")
        lines.append("## Errors")
        for err in result.errors:
            lines.append(f"- {err}")

    return "\n".join(lines)
