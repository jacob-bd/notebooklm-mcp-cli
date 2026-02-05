"""
Tests for primer_gen module.
"""

from pathlib import Path

import pytest

from notebooklm_mcp.doc_refresh.models import Tier
from notebooklm_mcp.primer_gen.render import (
    _render_quick_facts,
    _render_tier3_sections,
    _rewrite_relative_links,
)
from notebooklm_mcp.primer_gen.sources import RepoSources, SourceDoc


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


class TestRewriteRelativeLinks:
    """Tests for _rewrite_relative_links()."""

    def test_rewrite_links_doc_at_root(self):
        """Doc at repo root returns content unchanged."""
        content = "See [ops](OPERATIONS.md) for details."
        result = _rewrite_relative_links(content, Path("ARCHITECTURE.md"))
        assert result == content

    def test_rewrite_links_sibling_file(self):
        """Sibling link in subdirectory gets prefixed with doc's dir."""
        content = "See [ops](OPERATIONS.md) for details."
        result = _rewrite_relative_links(content, Path("docs/ti/ARCHITECTURE.md"))
        assert "](docs/ti/OPERATIONS.md)" in result

    def test_rewrite_links_parent_traversal(self):
        """Parent traversal ../  is resolved correctly."""
        content = "See [api](../API_REF.md) for details."
        result = _rewrite_relative_links(content, Path("docs/ti/ARCHITECTURE.md"))
        assert "](docs/API_REF.md)" in result

    def test_rewrite_links_preserves_urls(self):
        """HTTP/HTTPS URLs are left unchanged."""
        content = "See [example](https://example.com) and [http](http://foo.bar)."
        result = _rewrite_relative_links(content, Path("docs/ti/ARCHITECTURE.md"))
        assert "](https://example.com)" in result
        assert "](http://foo.bar)" in result

    def test_rewrite_links_preserves_anchors(self):
        """Pure anchor links are left unchanged."""
        content = "See [section](#setup) for details."
        result = _rewrite_relative_links(content, Path("docs/ti/ARCHITECTURE.md"))
        assert "](#setup)" in result

    def test_rewrite_links_with_fragment(self):
        """Link with anchor fragment preserves the fragment."""
        content = "See [ops](OPERATIONS.md#setup) for details."
        result = _rewrite_relative_links(content, Path("docs/ti/ARCHITECTURE.md"))
        assert "](docs/ti/OPERATIONS.md#setup)" in result

    def test_rewrite_links_escaping_repo_root(self):
        """Links that escape repo root are left unchanged (safety)."""
        content = "See [secret](../../../secret.md) for details."
        result = _rewrite_relative_links(content, Path("docs/ti/ARCHITECTURE.md"))
        assert "](../../../secret.md)" in result

    def test_render_tier3_rewrites_links(self):
        """Integration: _render_tier3_sections rewrites links in embedded docs."""
        doc = SourceDoc(
            path=Path("docs/terminal_insights/ARCHITECTURE.md"),
            tier=3,
            name="ARCHITECTURE.md",
            content="# Architecture\n\nSee [ops](OPERATIONS.md) and [api](../API_REF.md).",
            purpose="Architecture docs",
        )
        sources = RepoSources(
            repo_id="C018_terminal-insights",
            repo_path=Path("/fake/path"),
            tier=Tier.KITTED,
            repo_sha="abc1234",
            docs=[doc],
        )
        output = _render_tier3_sections(sources)
        assert "](docs/terminal_insights/OPERATIONS.md)" in output
        assert "](docs/API_REF.md)" in output
        # H1 should be stripped, but ## header should be present
        assert "\n# Architecture\n" not in output
        assert "## Architecture" in output
