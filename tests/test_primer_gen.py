"""
Tests for primer_gen module.
"""

from pathlib import Path

import pytest

from notebooklm_mcp.doc_refresh.models import Tier
from notebooklm_mcp.primer_gen.render import _render_quick_facts
from notebooklm_mcp.primer_gen.sources import RepoSources


def _make_sources(meta_yaml: dict | None = None) -> RepoSources:
    """Create a minimal RepoSources for testing."""
    return RepoSources(
        repo_id="C010_standards",
        repo_path=Path("/fake/path"),
        tier=Tier.SIMPLE,
        repo_sha="abc1234",
        docs=[],
        meta_yaml=meta_yaml,
    )


class TestQuickFactsOwner:
    """Tests for Owner field mapping in Quick Facts."""

    def test_owner_field_populated_from_project_owner(self):
        """Owner field comes from META.yaml project.owner."""
        sources = _make_sources(meta_yaml={
            "project": {
                "owner": "Jeremy Bradford",
                "status": "active",
            }
        })
        output = _render_quick_facts(sources)
        assert "| **Owner** | Jeremy Bradford |" in output

    def test_owner_fallback_to_maintainer(self):
        """When owner is missing, fall back to maintainer field."""
        sources = _make_sources(meta_yaml={
            "project": {
                "maintainer": "Jane Doe",
                "status": "active",
            }
        })
        output = _render_quick_facts(sources)
        assert "| **Owner** | Jane Doe |" in output

    def test_owner_prefers_owner_over_maintainer(self):
        """When both exist, owner takes precedence over maintainer."""
        sources = _make_sources(meta_yaml={
            "project": {
                "owner": "Jeremy Bradford",
                "maintainer": "Jane Doe",
                "status": "active",
            }
        })
        output = _render_quick_facts(sources)
        assert "| **Owner** | Jeremy Bradford |" in output
        assert "Jane Doe" not in output

    def test_owner_unknown_when_missing(self):
        """When neither owner nor maintainer exists, show 'unknown'."""
        sources = _make_sources(meta_yaml={
            "project": {
                "status": "active",
            }
        })
        output = _render_quick_facts(sources)
        assert "| **Owner** | unknown |" in output

    def test_owner_unknown_when_no_meta(self):
        """When META.yaml is None, show 'unknown'."""
        sources = _make_sources(meta_yaml=None)
        output = _render_quick_facts(sources)
        assert "| **Owner** | unknown |" in output

    def test_owner_handles_empty_owner_string(self):
        """Empty owner string should fall back to maintainer or unknown."""
        sources = _make_sources(meta_yaml={
            "project": {
                "owner": "",
                "maintainer": "Jane Doe",
                "status": "active",
            }
        })
        output = _render_quick_facts(sources)
        assert "| **Owner** | Jane Doe |" in output

    def test_owner_handles_none_owner_value(self):
        """Explicit None owner should fall back to maintainer or unknown."""
        sources = _make_sources(meta_yaml={
            "project": {
                "owner": None,
                "status": "active",
            }
        })
        output = _render_quick_facts(sources)
        assert "| **Owner** | unknown |" in output
