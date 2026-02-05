"""
Primer markdown rendering.

Generates PROJECT_PRIMER.md content from gathered sources.
"""

import posixpath
import re
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any, Optional

from ..doc_refresh.models import Tier
from .sources import RepoSources, SourceDoc


def render_primer(sources: RepoSources) -> str:
    """
    Render a complete PROJECT_PRIMER.md from gathered sources.

    Args:
        sources: RepoSources with all gathered documentation

    Returns:
        Complete primer markdown content
    """
    sections = []

    # Header
    sections.append(_render_header(sources))

    # Provenance
    sections.append(_render_provenance(sources))

    # Quick Facts
    sections.append(_render_quick_facts(sources))

    # What This Repo IS / IS NOT
    sections.append(_render_purpose_section(sources))

    # Responsibility Boundaries
    sections.append(_render_boundaries(sources))

    # Integration Map
    sections.append(_render_integration_map(sources))

    # Quick Routing
    sections.append(_render_routing_table(sources))

    # Canonical Extracts (README, META.yaml, CLAUDE.md)
    sections.append(_render_canonical_extracts(sources))

    # Tier 3 sections (if kitted)
    if sources.tier == Tier.KITTED:
        sections.append(_render_tier3_sections(sources))

    # Standards Snapshot
    sections.append(_render_standards_snapshot())

    return "\n".join(sections)


def _render_header(sources: RepoSources) -> str:
    """Render primer header."""
    return f"# PROJECT PRIMER — {sources.repo_id}\n"


def _render_provenance(sources: RepoSources) -> str:
    """Render provenance section."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    source_docs = "\n".join(f"  - {d.path}" for d in sources.docs)

    return f"""## Provenance

- **Generated**: {now}
- **Repo SHA**: {sources.repo_sha}
- **Generator**: generate-project-primer v1.0.0
- **Source Docs**:
{source_docs}

> **Derived document.** If conflicts exist, source docs override this primer.

---
"""


def _render_quick_facts(sources: RepoSources) -> str:
    """Render quick facts table from META.yaml."""
    meta = sources.meta_yaml or {}
    project = meta.get("project", {})

    # Extract facts
    status = project.get("status", "unknown")
    # Owner: prefer project.owner, fall back to project.maintainer, then "unknown"
    owner = project.get("owner") or project.get("maintainer") or "unknown"
    port = project.get("port", "—")

    # Extract series from repo_id (C/P/W/U prefix)
    series = "—"
    if sources.repo_id[0] in "CPWU" and sources.repo_id[1:4].isdigit():
        series_map = {"C": "Core", "P": "Project", "W": "Work", "U": "Utility"}
        series = f"{sources.repo_id[0]} ({series_map.get(sources.repo_id[0], '')})"

    # Try to find entry point from CLAUDE.md or META.yaml
    entry_point = _extract_entry_point(sources)

    return f"""## Quick Facts

| Field | Value |
|-------|-------|
| **Repo ID** | {sources.repo_id} |
| **Status** | {status} |
| **Owner** | {owner} |
| **Series** | {series} |
| **Tier** | {sources.tier.value} |
| **Entry Point** | {entry_point} |
| **Port** | {port} |

---
"""


def _extract_entry_point(sources: RepoSources) -> str:
    """Try to extract entry point from docs."""
    # Check META.yaml first
    if sources.meta_yaml:
        services = sources.meta_yaml.get("project", {}).get("services", {})
        if services:
            first_service = list(services.values())[0]
            if "command" in first_service:
                return f"`{first_service['command']}`"

    # Check CLAUDE.md for commands
    claude_doc = sources.claude_md
    if claude_doc:
        # Look for a dev command pattern
        content = claude_doc.content
        if "```bash" in content:
            # Simple heuristic: find first bash command block
            start = content.find("```bash")
            end = content.find("```", start + 6)
            if start >= 0 and end > start:
                block = content[start + 7:end].strip()
                first_line = block.split("\n")[0].strip()
                if first_line and not first_line.startswith("#"):
                    return f"`{first_line}`"

    return "See Quickstart"


def _render_purpose_section(sources: RepoSources) -> str:
    """Render What This Repo IS / IS NOT sections."""
    # Try to extract from README
    purpose = _extract_purpose(sources)
    not_this = _extract_not_this(sources)

    return f"""## What This Repo IS

{purpose}

---

## What This Repo IS NOT

{not_this}

---
"""


def _extract_purpose(sources: RepoSources) -> str:
    """Extract purpose from META.yaml, README, or OVERVIEW.

    Priority:
    1. META.yaml project.summary (canonical, if present)
    2. README first paragraph after title (skipping badges)
    3. OVERVIEW "What Is" section
    """
    # 1. Try META.yaml summary first (most reliable)
    if sources.meta_yaml:
        project = sources.meta_yaml.get("project", {})
        summary = project.get("summary") or project.get("description")
        if summary and isinstance(summary, str):
            return summary.strip()

    # 2. Try README - skip badges and find first real paragraph
    readme = sources.readme
    if readme:
        lines = readme.content.split("\n")
        in_content = False
        para_lines = []
        for line in lines:
            if line.startswith("# "):
                in_content = True
                continue
            if in_content:
                stripped = line.strip()
                # Skip empty lines before paragraph starts
                if stripped == "":
                    if para_lines:
                        break
                    continue
                # Skip badge lines: [![...] or ![...](...) patterns
                if stripped.startswith("[![") or stripped.startswith("!["):
                    continue
                # Skip pure link lines: [...](...)
                if stripped.startswith("[") and "](" in stripped and stripped.endswith(")"):
                    # Check if it's just a badge/link with no other text
                    if stripped.count("[") == stripped.count("]"):
                        continue
                # Stop at headers or code blocks
                if stripped.startswith("#") or stripped.startswith("```"):
                    break
                para_lines.append(stripped)

        if para_lines:
            return " ".join(para_lines)

    # 3. Try OVERVIEW "What Is" section
    overview = sources.get_tier3_doc("OVERVIEW.md")
    if overview:
        content = overview.content
        what_is_start = content.lower().find("## what is")
        if what_is_start >= 0:
            section_end = content.find("\n## ", what_is_start + 10)
            if section_end < 0:
                section_end = len(content)
            section = content[what_is_start:section_end]
            # Extract first paragraph after header
            lines = section.split("\n")[2:]  # Skip header
            para_lines = []
            for line in lines:
                if line.strip() == "":
                    if para_lines:
                        break
                    continue
                para_lines.append(line.strip())
            if para_lines:
                return " ".join(para_lines)

    return "*Purpose not extracted. Check META.yaml, README.md, or OVERVIEW.md.*"


def _extract_not_this(sources: RepoSources) -> str:
    """Extract 'what this is not' from repo card or generate placeholder."""
    # Try README repo card "## What it is not" section
    readme = sources.readme
    if readme:
        content = readme.content
        # Look for repo card section
        section_start = content.lower().find("## what it is not")
        if section_start >= 0:
            # Find next section
            section_end = content.find("\n## ", section_start + 18)
            if section_end < 0:
                section_end = len(content)
            section = content[section_start:section_end]
            # Extract bullet points
            lines = section.split("\n")[1:]  # Skip header
            bullets = []
            for line in lines:
                stripped = line.strip()
                if stripped.startswith("- "):
                    bullets.append(stripped)
                elif stripped.startswith("* "):
                    bullets.append("- " + stripped[2:])
            if bullets:
                return "\n".join(bullets)

    return """- *TODO: Document what this repo does NOT do*
- *TODO: List explicit deferrals to other repos*
- *Example: Does NOT handle credentials (defer to C001_mission-control)*"""


def _render_boundaries(sources: RepoSources) -> str:
    """Render responsibility boundaries section."""
    # Try to extract from RELATIONS.yaml or generate template
    owns = _extract_owns(sources)
    must_not = _extract_must_not(sources)

    return f"""## Responsibility Boundaries

### This Repo OWNS
{owns}

### This Repo MUST NOT Own
{must_not}

---
"""


def _extract_owns(sources: RepoSources) -> str:
    """Extract what this repo owns from README repo card or RELATIONS.yaml."""
    # Try README repo card "### This repo OWNS" section first
    readme = sources.readme
    if readme:
        content = readme.content
        # Look for repo card section (case-insensitive)
        lower_content = content.lower()
        section_start = lower_content.find("### this repo owns")
        if section_start >= 0:
            # Process line by line from section start
            rest = content[section_start:]
            lines = rest.split("\n")
            bullets = []
            in_bullets = False
            for i, line in enumerate(lines):
                if i == 0:  # Skip the header line
                    continue
                stripped = line.strip()
                # Stop at next section header
                if stripped.startswith("## ") or stripped.startswith("### "):
                    break
                if stripped.startswith("- "):
                    bullets.append(stripped)
                    in_bullets = True
                elif stripped.startswith("* "):
                    bullets.append("- " + stripped[2:])
                    in_bullets = True
                elif in_bullets and stripped == "":
                    continue  # Allow blank lines within bullet list
                elif in_bullets and stripped != "":
                    break  # Non-bullet, non-blank line ends the section
            if bullets:
                return "\n".join(bullets)

    # Fall back to RELATIONS.yaml
    relations_doc = next(
        (d for d in sources.docs if d.name.upper() == "RELATIONS.YAML"),
        None
    )
    if relations_doc:
        try:
            relations = yaml.safe_load(relations_doc.content)
            # Try "owns" first (v2 format), then "provides" (v1 format)
            owns = relations.get("owns") or relations.get("provides", [])
            if owns:
                return "\n".join(f"- {item}" for item in owns)
        except Exception:
            pass

    return """- *TODO: Document what this repo owns*
- *Extract from existing docs or define*"""


def _extract_must_not(sources: RepoSources) -> str:
    """Extract what this repo must not own from README repo card or RELATIONS.yaml."""
    # Try README repo card "### This repo MUST NOT own" section first
    readme = sources.readme
    if readme:
        content = readme.content
        # Look for repo card section (case-insensitive)
        lower_content = content.lower()
        section_start = lower_content.find("### this repo must not own")
        if section_start >= 0:
            # Process line by line from section start
            rest = content[section_start:]
            lines = rest.split("\n")
            bullets = []
            in_bullets = False
            for i, line in enumerate(lines):
                if i == 0:  # Skip the header line
                    continue
                stripped = line.strip()
                # Stop at next section header
                if stripped.startswith("## ") or stripped.startswith("### "):
                    break
                if stripped.startswith("- "):
                    bullets.append(stripped)
                    in_bullets = True
                elif stripped.startswith("* "):
                    bullets.append("- " + stripped[2:])
                    in_bullets = True
                elif in_bullets and stripped == "":
                    continue  # Allow blank lines within bullet list
                elif in_bullets and stripped != "":
                    break  # Non-bullet, non-blank line ends the section
            if bullets:
                return "\n".join(bullets)

    # Fall back to RELATIONS.yaml must_not_own
    relations_doc = next(
        (d for d in sources.docs if d.name.upper() == "RELATIONS.YAML"),
        None
    )
    if relations_doc:
        try:
            relations = yaml.safe_load(relations_doc.content)
            # Try must_not_own first (preferred)
            must_not = relations.get("must_not_own", [])
            if must_not:
                return "\n".join(f"- {item}" for item in must_not)
            # Fall back to depends_on
            depends = relations.get("depends_on", [])
            if depends:
                items = []
                for dep in depends:
                    if isinstance(dep, dict):
                        repo = dep.get("repo", "unknown")
                        reason = dep.get("reason") or dep.get("for", "unknown purpose")
                        items.append(f"- {reason} (defer to {repo})")
                    else:
                        items.append(f"- Functionality from {dep}")
                if items:
                    return "\n".join(items)
        except Exception:
            pass

    return """- *TODO: Document explicit deferrals*
- *Example: Credentials (defer to C001_mission-control)*"""


def _render_integration_map(sources: RepoSources) -> str:
    """Render integration map table."""
    # Try RELATIONS.yaml or META.yaml
    integrations = _extract_integrations(sources)

    return f"""## Integration Map

{integrations}

---
"""


def _extract_integrations(sources: RepoSources) -> str:
    """Extract integration points from README Related repos, RELATIONS.yaml, or META.yaml."""
    rows = []

    # Try README "## Related repos" section first
    readme = sources.readme
    if readme:
        content = readme.content
        # Look for Related repos section (case-insensitive)
        section_start = content.lower().find("## related repos")
        if section_start >= 0:
            # Find next section
            section_end = content.find("\n## ", section_start + 16)
            if section_end < 0:
                section_end = len(content)
            section = content[section_start:section_end]
            # Extract bullet points with repo info
            lines = section.split("\n")[1:]  # Skip header
            for line in lines:
                stripped = line.strip()
                if stripped.startswith("- "):
                    # Parse "- **RepoName** — description" or "- RepoName: description"
                    item = stripped[2:]
                    # Try **Name** — format
                    if item.startswith("**"):
                        end_bold = item.find("**", 2)
                        if end_bold > 2:
                            repo = item[2:end_bold]
                            rest = item[end_bold + 2:].strip()
                            if rest.startswith("—") or rest.startswith("-"):
                                purpose = rest[1:].strip()
                            else:
                                purpose = rest
                            rows.append(f"| {repo} | relates to | {purpose or '—'} | active |")
                            continue
                    # Try Name: format
                    if ":" in item:
                        parts = item.split(":", 1)
                        repo = parts[0].strip()
                        purpose = parts[1].strip() if len(parts) > 1 else "—"
                        rows.append(f"| {repo} | relates to | {purpose} | active |")
                        continue
                    # Plain item
                    rows.append(f"| {item} | relates to | — | active |")

    # If no README rows, try RELATIONS.yaml
    if not rows:
        relations_doc = next(
            (d for d in sources.docs if d.name.upper() == "RELATIONS.YAML"),
            None
        )
        if relations_doc:
            try:
                relations = yaml.safe_load(relations_doc.content)

                # depends_on
                for dep in relations.get("depends_on", []):
                    if isinstance(dep, dict):
                        repo = dep.get("repo", "unknown")
                        reason = dep.get("reason") or dep.get("for", "—")
                        rows.append(f"| {repo} | depends on | {reason} | active |")
                    else:
                        rows.append(f"| {dep} | depends on | — | active |")

                # provides (consumed by others)
                for prov in relations.get("provides", []):
                    if isinstance(prov, dict):
                        consumer = prov.get("consumer", "various")
                        interface = prov.get("interface", "—")
                        rows.append(f"| {consumer} | consumed by | {interface} | active |")
            except Exception:
                pass

    # If still no rows, try META.yaml relates_to
    if not rows and sources.meta_yaml:
        relates_to = sources.meta_yaml.get("relates_to", [])
        for rel in relates_to:
            if isinstance(rel, str):
                rows.append(f"| {rel} | relates to | — | — |")
            elif isinstance(rel, dict):
                for repo, desc in rel.items():
                    rows.append(f"| {repo} | relates to | {desc} | active |")

    if rows:
        header = "| External System | Direction | Interface | Status |\n|-----------------|-----------|-----------|--------|"
        return header + "\n" + "\n".join(rows)

    return """| External System | Direction | Interface | Status |
|-----------------|-----------|-----------|--------|
| *TODO* | depends on | — | — |"""


def _render_routing_table(sources: RepoSources) -> str:
    """Render quick routing table."""
    # Standard routing based on tier
    rows = [
        "| Understand purpose | What This Repo IS |",
    ]

    if sources.tier in (Tier.COMPLEX, Tier.KITTED):
        rows.extend([
            "| Run locally | Quickstart |",
            "| Debug issues | Operations |",
        ])

    if sources.tier == Tier.KITTED:
        rows.extend([
            "| Find code | Code Tour |",
            "| Understand architecture | Architecture |",
            "| Security rules | Security & Privacy |",
            "| Current roadmap | Open Questions |",
        ])

    return f"""## Quick Routing

| If you want to... | Read this section |
|-------------------|-------------------|
{chr(10).join(rows)}

---
"""


def _render_canonical_extracts(sources: RepoSources) -> str:
    """Render README, META.yaml, and CLAUDE.md extracts."""
    parts = []

    # README
    readme = sources.readme
    if readme:
        parts.append(f"""## README

{readme.content}

---
""")

    # META.yaml
    meta_doc = sources.meta_yaml_doc
    if meta_doc:
        parts.append(f"""## META.yaml

```yaml
{meta_doc.content}
```

---
""")

    # CLAUDE.md
    claude_doc = sources.claude_md
    if claude_doc:
        parts.append(f"""## CLAUDE.md

{claude_doc.content}

---
""")

    return "\n".join(parts) if parts else ""


def _rewrite_relative_links(content: str, doc_path: Path) -> str:
    """Rewrite relative markdown links to be valid from repo root.

    When Tier 3 doc content is embedded in the primer at repo root,
    relative links need adjusting from the doc's original directory.
    """
    doc_dir = str(PurePosixPath(doc_path.parent))

    if doc_dir == '.':
        return content  # Already at repo root

    def _rewrite(match):
        target = match.group(1)

        # Skip URLs, anchors, absolute paths
        if target.startswith(('http://', 'https://', '#', 'mailto:', '/')):
            return match.group(0)

        # Handle targets with anchors: path.md#section
        if '#' in target:
            path_part, fragment = target.split('#', 1)
            fragment = '#' + fragment
        else:
            path_part = target
            fragment = ''

        if not path_part:
            return match.group(0)  # Pure anchor

        # Resolve relative to doc's directory, normalize away ../
        resolved = posixpath.normpath(posixpath.join(doc_dir, path_part))

        # Safety: if resolved goes above repo root, leave unchanged
        if resolved.startswith('..'):
            return match.group(0)

        return f']({resolved}{fragment})'

    return re.sub(r'\]\(([^)]+)\)', _rewrite, content)


def _render_tier3_sections(sources: RepoSources) -> str:
    """Render all Tier 3 sections for kitted repos."""
    tier3_names = [
        ("OVERVIEW.md", "Overview"),
        ("QUICKSTART.md", "Quickstart"),
        ("ARCHITECTURE.md", "Architecture"),
        ("CODE_TOUR.md", "Code Tour"),
        ("OPERATIONS.md", "Operations"),
        ("SECURITY_AND_PRIVACY.md", "Security & Privacy"),
        ("OPEN_QUESTIONS.md", "Open Questions"),
    ]

    parts = []
    for filename, title in tier3_names:
        doc = sources.get_tier3_doc(filename)
        if doc:
            # Strip the H1 header if present to avoid duplication
            content = doc.content
            lines = content.split("\n")
            if lines and lines[0].startswith("# "):
                content = "\n".join(lines[1:]).lstrip()

            # Rewrite relative links from doc's directory to repo root
            content = _rewrite_relative_links(content, doc.path)

            parts.append(f"""## {title}

{content}

---
""")

    return "\n".join(parts)


def _render_standards_snapshot() -> str:
    """Render standards snapshot section."""
    return """## Standards Snapshot (C010)

This repo follows workspace standards from C010_standards:

- **Betty Protocol**: Evidence in 20_receipts/, no self-certification
- **META.yaml**: Keep `last_reviewed` current
- **Cross-platform**: Commands work on macOS, Windows, Linux
- **Closeout**: Git status clean, stash triaged, receipts written

Full standards are canonical in C010_standards.
"""


# Need to import yaml for RELATIONS.yaml parsing
import yaml
