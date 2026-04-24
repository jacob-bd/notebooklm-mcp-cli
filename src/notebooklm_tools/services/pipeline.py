"""Pipeline automation service — define and execute multi-step notebook workflows."""

import time
from pathlib import Path
from typing import Any

import yaml

from ..core.client import NotebookLMClient
from ..utils.config import get_storage_dir
from . import chat as chat_service
from . import notebooks as notebooks_service
from . import sources as sources_service
from . import studio as studio_service
from ._compat import TypedDict
from .errors import ValidationError

PIPELINES_DIR = "pipelines"

# Built-in pipeline templates
BUILTIN_PIPELINES = {
    "ingest-and-podcast": {
        "name": "ingest-and-podcast",
        "description": "Add a URL source, query for summary, then generate audio podcast",
        "steps": [
            {"action": "source_add", "params": {"type": "url", "url": "$INPUT_URL"}},
            {
                "action": "notebook_query",
                "params": {"query": "Summarize the content that was just added"},
            },
            {"action": "studio_create", "params": {"artifact_type": "audio"}},
        ],
    },
    "research-and-report": {
        "name": "research-and-report",
        "description": "Add a URL source and generate a briefing doc report",
        "steps": [
            {"action": "source_add", "params": {"type": "url", "url": "$INPUT_URL"}},
            {
                "action": "studio_create",
                "params": {"artifact_type": "report", "report_format": "Briefing Doc"},
            },
        ],
    },
    "multi-format": {
        "name": "multi-format",
        "description": "Generate audio, report, and flashcards from a notebook",
        "steps": [
            {"action": "studio_create", "params": {"artifact_type": "audio"}},
            {"action": "studio_create", "params": {"artifact_type": "report"}},
            {"action": "studio_create", "params": {"artifact_type": "flashcards"}},
        ],
    },
}

# Valid pipeline actions mapped to service functions
VALID_ACTIONS = {
    "source_add",
    "notebook_query",
    "studio_create",
    "notebook_create",
    "notebook_delete",
}


class StepResult(TypedDict):
    """Result of a single pipeline step."""

    step: int
    action: str
    success: bool
    result: Any
    error: str | None
    duration_ms: int


class PipelineResult(TypedDict):
    """Result of a complete pipeline execution."""

    pipeline_name: str
    notebook_id: str
    steps: list[StepResult]
    total_steps: int
    succeeded: int
    failed: int
    total_duration_ms: int


class PipelineInfo(TypedDict):
    """Pipeline metadata."""

    name: str
    description: str
    steps_count: int
    source: str  # "builtin" or "user"


def _get_pipelines_dir() -> Path:
    """Get pipelines storage directory."""
    d = get_storage_dir() / PIPELINES_DIR
    d.mkdir(exist_ok=True)
    return d


def _substitute_vars(params: dict, variables: dict[str, str]) -> dict:
    """Replace $VARIABLE placeholders in params with actual values."""
    result = {}
    for key, value in params.items():
        if isinstance(value, str) and value.startswith("$"):
            var_name = value[1:]  # strip $
            if var_name in variables:  # noqa: SIM401
                result[key] = variables[var_name]
            else:
                result[key] = value  # keep as-is if not found
        else:
            result[key] = value
    return result


def _execute_step(
    client: NotebookLMClient,
    notebook_id: str,
    action: str,
    params: dict,
) -> Any:
    """Execute a single pipeline step."""
    if action == "source_add":
        source_type = params.get("type", "url")
        url = params.get("url", "")
        text = params.get("text", "")
        return sources_service.add_source(
            client,
            notebook_id,
            source_type=source_type,
            url=url if source_type == "url" else None,
            text=text if source_type == "text" else None,
        )

    elif action == "notebook_query":
        query_text = params.get("query", "")
        return chat_service.query(client, notebook_id, query_text)

    elif action == "studio_create":
        artifact_type = params.get("artifact_type", "audio")
        return studio_service.create_artifact(
            client,
            notebook_id,
            artifact_type,
            focus_prompt=params.get("focus_prompt", ""),
            audio_format=params.get("audio_format", "deep_dive"),
            audio_length=params.get("audio_length", "default"),
            report_format=params.get("report_format", "Briefing Doc"),
            custom_prompt=params.get("custom_prompt", ""),
            language=params.get("language", "en"),
        )

    elif action == "notebook_create":
        title = params.get("title", "")
        return notebooks_service.create_notebook(client, title)

    elif action == "notebook_delete":
        return notebooks_service.delete_notebook(client, notebook_id)

    else:
        raise ValidationError(
            f"Unknown action '{action}'. Valid: {', '.join(sorted(VALID_ACTIONS))}",
        )


def pipeline_run(
    client: NotebookLMClient,
    notebook_id: str,
    pipeline_name: str,
    variables: dict[str, str] | None = None,
) -> PipelineResult:
    """Execute a pipeline by name.

    Args:
        client: Authenticated client
        notebook_id: Target notebook UUID
        pipeline_name: Pipeline name (builtin or user-defined)
        variables: Variable substitutions (e.g. {"INPUT_URL": "https://..."})

    Returns:
        PipelineResult with per-step results

    Raises:
        ValidationError: If pipeline not found
    """
    variables = variables or {}

    # Look up pipeline definition
    pipeline_def = _load_pipeline(pipeline_name)
    if not pipeline_def:
        raise ValidationError(
            f"Pipeline '{pipeline_name}' not found.",
            user_message=f"Pipeline '{pipeline_name}' not found. Use pipeline_list to see available pipelines.",
        )

    steps = pipeline_def.get("steps", [])
    if not steps:
        raise ValidationError(
            f"Pipeline '{pipeline_name}' has no steps.",
            user_message=f"Pipeline '{pipeline_name}' is empty.",
        )

    step_results: list[StepResult] = []
    total_start = time.monotonic()

    for i, step in enumerate(steps):
        action = step.get("action", "")
        params = _substitute_vars(step.get("params", {}), variables)

        step_start = time.monotonic()
        try:
            result = _execute_step(client, notebook_id, action, params)
            duration = int((time.monotonic() - step_start) * 1000)
            step_results.append(
                {
                    "step": i + 1,
                    "action": action,
                    "success": True,
                    "result": result,
                    "error": None,
                    "duration_ms": duration,
                }
            )
        except Exception as e:
            duration = int((time.monotonic() - step_start) * 1000)
            step_results.append(
                {
                    "step": i + 1,
                    "action": action,
                    "success": False,
                    "result": None,
                    "error": str(e),
                    "duration_ms": duration,
                }
            )
            # Stop on failure (sequential pipeline)
            break

    total_duration = int((time.monotonic() - total_start) * 1000)
    succeeded = sum(1 for s in step_results if s["success"])

    return {
        "pipeline_name": pipeline_name,
        "notebook_id": notebook_id,
        "steps": step_results,
        "total_steps": len(steps),
        "succeeded": succeeded,
        "failed": len(step_results) - succeeded,
        "total_duration_ms": total_duration,
    }


def _load_pipeline(name: str) -> dict | None:
    """Load a pipeline by name. Checks builtin first, then user-defined."""
    # Check builtin
    if name in BUILTIN_PIPELINES:
        return BUILTIN_PIPELINES[name]

    # Check user-defined
    user_file = _get_pipelines_dir() / f"{name}.yaml"
    if user_file.exists():
        try:
            data = yaml.safe_load(user_file.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else None
        except yaml.YAMLError:
            return None

    return None


def pipeline_list() -> list[PipelineInfo]:
    """List all available pipelines (builtin + user-defined).

    Returns:
        List of PipelineInfo
    """
    pipelines: list[PipelineInfo] = []

    # Builtin
    for name, defn in BUILTIN_PIPELINES.items():
        pipelines.append(
            {
                "name": name,
                "description": defn.get("description", ""),
                "steps_count": len(defn.get("steps", [])),
                "source": "builtin",
            }
        )

    # User-defined
    pipelines_dir = _get_pipelines_dir()
    for f in sorted(pipelines_dir.glob("*.yaml")):
        try:
            data = yaml.safe_load(f.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                pipelines.append(
                    {
                        "name": f.stem,
                        "description": data.get("description", ""),
                        "steps_count": len(data.get("steps", [])),
                        "source": "user",
                    }
                )
        except yaml.YAMLError:
            continue

    return pipelines


def pipeline_create(
    name: str,
    description: str,
    steps: list[dict],
) -> PipelineInfo:
    """Create a user-defined pipeline.

    Args:
        name: Pipeline name (used as filename)
        description: Human-readable description
        steps: List of step definitions

    Returns:
        PipelineInfo for the created pipeline

    Raises:
        ValidationError: If name conflicts with builtin or steps invalid
    """
    if not name or not name.strip():
        raise ValidationError(
            "Pipeline name is required.", user_message="Please provide a pipeline name."
        )

    if name in BUILTIN_PIPELINES:
        raise ValidationError(
            f"Cannot overwrite builtin pipeline '{name}'.",
            user_message=f"'{name}' is a builtin pipeline. Choose a different name.",
        )

    if not steps:
        raise ValidationError(
            "At least one step is required.", user_message="Pipeline must have at least one step."
        )

    # Validate actions
    for i, step in enumerate(steps):
        action = step.get("action", "")
        if action not in VALID_ACTIONS:
            raise ValidationError(
                f"Step {i + 1}: Unknown action '{action}'. Valid: {', '.join(sorted(VALID_ACTIONS))}",
            )

    pipeline_def = {
        "name": name,
        "description": description,
        "steps": steps,
    }

    filepath = _get_pipelines_dir() / f"{name}.yaml"
    filepath.write_text(yaml.dump(pipeline_def, default_flow_style=False), encoding="utf-8")

    return {
        "name": name,
        "description": description,
        "steps_count": len(steps),
        "source": "user",
    }
