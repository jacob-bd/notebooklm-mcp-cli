"""Path-traversal regression tests for pipeline names (GHSA-596g-p98x-c7hw).

`_load_pipeline` (read, reachable over MCP) and `pipeline_create` (write, CLI)
interpolated a caller-supplied name straight into a filesystem path. Both `..`
sequences and absolute paths escaped the pipelines directory. Names are
identifiers, not paths, so they must be validated.
"""

import pytest

from notebooklm_tools.services.errors import ValidationError
from notebooklm_tools.services.pipeline import (
    _get_pipelines_dir,
    _load_pipeline,
    pipeline_create,
)

_VALID_STEP = [{"action": "notebook_query", "params": {"query": "x"}}]

_MALICIOUS_NAMES = [
    "../evil",
    "../../evil",
    "/etc/passwd",
    "sub/dir/evil",
    "..",
    ".",
    "evil\x00",
    "a" * 200,
    "..\\evil",
]


@pytest.mark.parametrize("name", _MALICIOUS_NAMES)
def test_load_pipeline_rejects_traversal_names(name):
    with pytest.raises(ValidationError):
        _load_pipeline(name)


@pytest.mark.parametrize("name", _MALICIOUS_NAMES)
def test_pipeline_create_rejects_traversal_names(name):
    with pytest.raises(ValidationError):
        pipeline_create(name, "desc", _VALID_STEP)


def test_load_pipeline_does_not_read_outside_dir(tmp_path):
    """A traversal name must not load a .yaml planted outside the pipelines dir."""
    pipelines_dir = _get_pipelines_dir()
    outside = pipelines_dir.parent.parent / "outside"
    outside.mkdir(parents=True, exist_ok=True)
    (outside / "planted.yaml").write_text(
        "name: planted\nsteps:\n  - action: notebook_delete\n    params: {}\n",
        encoding="utf-8",
    )

    # Relative traversal and absolute path both point at the planted file.
    with pytest.raises(ValidationError):
        _load_pipeline("../../outside/planted")
    with pytest.raises(ValidationError):
        _load_pipeline(str(outside / "planted"))


def test_pipeline_create_does_not_write_outside_dir(tmp_path):
    """A traversal name must not write a .yaml outside the pipelines dir."""
    pipelines_dir = _get_pipelines_dir()
    target = pipelines_dir.parent.parent / "victim"
    target.mkdir(parents=True, exist_ok=True)

    with pytest.raises(ValidationError):
        pipeline_create("../../victim/written", "desc", _VALID_STEP)

    assert not (target / "written.yaml").exists()


def test_valid_name_still_round_trips():
    """A normal identifier name still creates and loads inside the pipelines dir."""
    info = pipeline_create("my-pipeline_v2.1", "desc", _VALID_STEP)
    assert info["name"] == "my-pipeline_v2.1"
    assert (_get_pipelines_dir() / "my-pipeline_v2.1.yaml").exists()

    loaded = _load_pipeline("my-pipeline_v2.1")
    assert loaded is not None
    assert loaded["name"] == "my-pipeline_v2.1"
