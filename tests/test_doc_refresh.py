"""
Tests for doc_refresh module.
"""

import tempfile
from pathlib import Path

import pytest

from notebooklm_mcp.doc_refresh import (
    Tier,
    compute_content_hash,
    compute_file_hash,
    discover_repo,
    extract_version,
    is_major_version_bump,
    load_manifest,
    resolve_tier3_root,
)
from notebooklm_mcp.doc_refresh.manifest import _extract_short_name


class TestManifest:
    """Tests for manifest loading and resolution."""

    def test_load_manifest(self):
        """Manifest loads and has expected structure."""
        manifest = load_manifest()
        assert "tiers" in manifest
        assert "tier1" in manifest["tiers"]
        assert "tier2" in manifest["tiers"]
        assert "tier3" in manifest["tiers"]

    def test_extract_short_name_with_prefix(self):
        """Extract short name from prefixed repo name."""
        assert _extract_short_name("C017_brain-on-tap") == "brain_on_tap"
        assert _extract_short_name("P051_mcp-servers") == "mcp_servers"

    def test_extract_short_name_without_prefix(self):
        """Extract short name from non-prefixed repo name."""
        assert _extract_short_name("some-repo") == "some_repo"
        assert _extract_short_name("my_project") == "my_project"

    def test_resolve_tier3_root_with_override(self):
        """Tier 3 root resolves from repo_overrides."""
        manifest = load_manifest()
        # Create temp repo structure
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            # Create the expected tier3 path from override
            (repo_path / "docs" / "brain_on_tap").mkdir(parents=True)

            result = resolve_tier3_root(repo_path, "C017_brain-on-tap", manifest)
            assert result is not None
            assert result.name == "brain_on_tap"


class TestHashing:
    """Tests for content hashing."""

    def test_compute_content_hash(self):
        """Content hash is deterministic."""
        content = "Hello, World!"
        hash1 = compute_content_hash(content)
        hash2 = compute_content_hash(content)
        assert hash1 == hash2
        assert len(hash1) == 12  # Truncated to 12 chars

    def test_compute_content_hash_different_content(self):
        """Different content produces different hashes."""
        hash1 = compute_content_hash("Hello")
        hash2 = compute_content_hash("World")
        assert hash1 != hash2

    def test_compute_file_hash(self):
        """File hash matches content hash."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".md") as f:
            f.write("Test content for hashing")
            f.flush()
            file_hash = compute_file_hash(Path(f.name))

        content_hash = compute_content_hash("Test content for hashing")
        assert file_hash == content_hash


class TestDiscovery:
    """Tests for repository discovery."""

    def test_discover_simple_repo(self):
        """Discover a minimal (simple tier) repository."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            # Create minimal tier 1 structure
            (repo_path / "README.md").write_text("# Test")
            (repo_path / "CHANGELOG.md").write_text("# Changes")
            (repo_path / "META.yaml").write_text("version: 1.0.0")

            result = discover_repo(repo_path)

            assert result.tier == Tier.SIMPLE
            assert result.repo_name == repo_path.name
            # All tier 1 docs should be found
            tier1_existing = [d for d in result.tier1_docs if d.exists]
            assert len(tier1_existing) == 3

    def test_discover_complex_repo(self):
        """Discover a complex tier repository (has Tier 2 docs)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            # Tier 1
            (repo_path / "README.md").write_text("# Test")
            # Tier 2
            (repo_path / "CLAUDE.md").write_text("# Claude instructions")

            result = discover_repo(repo_path)

            assert result.tier == Tier.COMPLEX


class TestValidation:
    """Tests for validation helpers."""

    def test_extract_version_from_frontmatter(self):
        """Extract version from YAML frontmatter."""
        content = """---
version: 1.2.3
---

# Document
"""
        version = extract_version(content)
        assert version == "1.2.3"

    def test_extract_version_from_marker(self):
        """Extract version from **Version:** marker."""
        content = """# Document

**Version:** 2.0.0

Some content.
"""
        version = extract_version(content)
        assert version == "2.0.0"

    def test_extract_version_none(self):
        """Return None when no version found."""
        content = "# Document without version"
        version = extract_version(content)
        assert version is None

    def test_is_major_version_bump(self):
        """Detect major version bumps."""
        assert is_major_version_bump("1.0.0", "2.0.0") is True
        assert is_major_version_bump("1.5.3", "2.0.0") is True
        assert is_major_version_bump("v1.0.0", "v2.0.0") is True

    def test_is_not_major_version_bump(self):
        """Non-major bumps return False."""
        assert is_major_version_bump("1.0.0", "1.1.0") is False
        assert is_major_version_bump("1.0.0", "1.0.1") is False
        assert is_major_version_bump("2.0.0", "2.5.0") is False

    def test_is_major_version_bump_edge_cases(self):
        """Edge cases return False."""
        assert is_major_version_bump(None, "2.0.0") is False
        assert is_major_version_bump("1.0.0", None) is False
        assert is_major_version_bump(None, None) is False
