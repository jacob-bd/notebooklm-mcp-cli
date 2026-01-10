"""
Document validation: metadata headers, links, and code references.

Validates canonical documents against their expected structure.
"""

import re
from pathlib import Path
from typing import Optional

from .models import (
    DiscoveryResult,
    DocItem,
    IssueSeverity,
    ValidationIssue,
    ValidationReport,
)


# Patterns for extracting metadata and references
YAML_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)
VERSION_RE = re.compile(r"\*\*Version:\*\*\s*(\S+)", re.IGNORECASE)
LAST_UPDATED_RE = re.compile(
    r"\*\*Last Updated:\*\*\s*(\d{4}-\d{2}-\d{2})", re.IGNORECASE
)
# Match file:line references like `src/foo.py:123`
# Must have a file extension or path separator to avoid matching hostnames
CODE_REF_RE = re.compile(r"`([^`]*[./][^`]+):(\d+)`")  # file.py:123 or src/file:123
INTERNAL_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")  # [text](path)


def validate_discovery(
    result: DiscoveryResult,
) -> ValidationReport:
    """
    Validate all discovered documents in a repository.

    Args:
        result: DiscoveryResult from discover_repo()

    Returns:
        ValidationReport with all issues found
    """
    issues: list[ValidationIssue] = []

    # Check for missing required docs
    for doc in result.docs:
        if doc.required and not doc.exists:
            issues.append(
                ValidationIssue(
                    doc_path=doc.path,
                    rule="required_doc_exists",
                    severity=IssueSeverity.ERROR,
                    message=f"Required document missing: {doc.path}",
                )
            )

    # Validate each existing document (skip directories)
    for doc in result.docs:
        if doc.exists:
            # Skip directories
            full_path = result.repo_path / doc.path
            if full_path.is_dir():
                continue
            doc_issues = validate_document(doc, result.repo_path)
            issues.extend(doc_issues)

    return ValidationReport(
        discovery=result,
        issues=issues,
    )


def validate_document(
    doc: DocItem,
    repo_path: Path,
) -> list[ValidationIssue]:
    """
    Validate a single document.

    Checks:
    - Metadata header (Version, Last Updated)
    - Internal links (relative paths exist)
    - Code references (file:line format resolves)

    Args:
        doc: DocItem to validate
        repo_path: Repository root path

    Returns:
        List of validation issues found
    """
    issues: list[ValidationIssue] = []
    full_path = repo_path / doc.path

    try:
        content = full_path.read_text(encoding="utf-8")
    except Exception as e:
        issues.append(
            ValidationIssue(
                doc_path=doc.path,
                rule="readable",
                severity=IssueSeverity.ERROR,
                message=f"Cannot read file: {e}",
            )
        )
        return issues

    # Validate metadata header
    metadata_issues = _validate_metadata(doc, content)
    issues.extend(metadata_issues)

    # Validate internal links
    link_issues = _validate_links(doc, content, repo_path)
    issues.extend(link_issues)

    # Validate code references
    code_ref_issues = _validate_code_refs(doc, content, repo_path)
    issues.extend(code_ref_issues)

    return issues


def _validate_metadata(doc: DocItem, content: str) -> list[ValidationIssue]:
    """
    Validate document has proper metadata header.

    Looks for either:
    - YAML frontmatter with version/date fields
    - **Version:** and **Last Updated:** markers
    """
    issues: list[ValidationIssue] = []

    # Check for YAML frontmatter
    frontmatter_match = YAML_FRONTMATTER_RE.match(content)

    has_version = False
    has_date = False

    if frontmatter_match:
        frontmatter = frontmatter_match.group(1)
        has_version = "version:" in frontmatter.lower()
        has_date = any(
            x in frontmatter.lower()
            for x in ["date:", "last_updated:", "updated:"]
        )
    else:
        # Check for inline markers (common in markdown)
        has_version = VERSION_RE.search(content) is not None
        has_date = LAST_UPDATED_RE.search(content) is not None

    if not has_version:
        issues.append(
            ValidationIssue(
                doc_path=doc.path,
                rule="has_version",
                severity=IssueSeverity.WARNING,
                message="Document missing version indicator",
            )
        )

    if not has_date:
        issues.append(
            ValidationIssue(
                doc_path=doc.path,
                rule="has_last_updated",
                severity=IssueSeverity.WARNING,
                message="Document missing last updated date",
            )
        )

    return issues


def _validate_links(
    doc: DocItem,
    content: str,
    repo_path: Path,
) -> list[ValidationIssue]:
    """
    Validate internal markdown links resolve to existing files.

    Only checks relative links (not http:// or https://).
    """
    issues: list[ValidationIssue] = []
    doc_dir = (repo_path / doc.path).parent

    for match in INTERNAL_LINK_RE.finditer(content):
        link_text = match.group(1)
        link_path = match.group(2)

        # Skip external links
        if link_path.startswith(("http://", "https://", "#", "mailto:")):
            continue

        # Skip anchor-only links
        if link_path.startswith("#"):
            continue

        # Handle links with anchors
        path_part = link_path.split("#")[0]
        if not path_part:
            continue

        # Resolve relative to document's directory
        target_path = (doc_dir / path_part).resolve()

        if not target_path.exists():
            # Find line number
            line_num = _find_line_number(content, match.start())
            issues.append(
                ValidationIssue(
                    doc_path=doc.path,
                    rule="link_resolves",
                    severity=IssueSeverity.WARNING,
                    message=f"Broken link: [{link_text}]({link_path})",
                    line_number=line_num,
                    context=link_path,
                )
            )

    return issues


def _validate_code_refs(
    doc: DocItem,
    content: str,
    repo_path: Path,
) -> list[ValidationIssue]:
    """
    Validate code references in file:line format.

    Checks that:
    - Referenced file exists
    - Line number is within file bounds (if reasonable to check)
    """
    issues: list[ValidationIssue] = []

    for match in CODE_REF_RE.finditer(content):
        file_ref = match.group(1)
        line_num_str = match.group(2)

        # Skip if it looks like a URL, protocol, or hostname
        if file_ref.startswith(("http", "https", "ftp", "bolt", "neo4j")):
            continue
        # Skip localhost references (commonly port numbers, not line numbers)
        if "localhost" in file_ref.lower():
            continue
        # Skip if no file extension and doesn't look like a path
        if "/" not in file_ref and "." not in file_ref:
            continue

        # Resolve file path
        ref_path = repo_path / file_ref

        if not ref_path.exists():
            line_num = _find_line_number(content, match.start())
            issues.append(
                ValidationIssue(
                    doc_path=doc.path,
                    rule="code_ref_file_exists",
                    severity=IssueSeverity.WARNING,
                    message=f"Code reference to non-existent file: {file_ref}",
                    line_number=line_num,
                    context=f"`{file_ref}:{line_num_str}`",
                )
            )
            continue

        # Check line number is valid (file has that many lines)
        try:
            line_num_int = int(line_num_str)
            if ref_path.is_file():
                line_count = len(ref_path.read_text().splitlines())
                if line_num_int > line_count:
                    line_num = _find_line_number(content, match.start())
                    issues.append(
                        ValidationIssue(
                            doc_path=doc.path,
                            rule="code_ref_line_valid",
                            severity=IssueSeverity.INFO,
                            message=(
                                f"Code reference line {line_num_int} exceeds "
                                f"file length ({line_count} lines): {file_ref}"
                            ),
                            line_number=line_num,
                            context=f"`{file_ref}:{line_num_str}`",
                        )
                    )
        except (ValueError, IOError):
            pass  # Skip if we can't parse line number or read file

    return issues


def _find_line_number(content: str, char_pos: int) -> int:
    """Find the line number for a character position in content."""
    return content[:char_pos].count("\n") + 1


def extract_version(content: str) -> Optional[str]:
    """
    Extract version string from document content.

    Looks for YAML frontmatter or **Version:** marker.
    """
    # Check YAML frontmatter
    frontmatter_match = YAML_FRONTMATTER_RE.match(content)
    if frontmatter_match:
        frontmatter = frontmatter_match.group(1)
        for line in frontmatter.split("\n"):
            if line.strip().lower().startswith("version:"):
                return line.split(":", 1)[1].strip().strip("'\"")

    # Check inline marker
    version_match = VERSION_RE.search(content)
    if version_match:
        return version_match.group(1)

    return None


def is_major_version_bump(old_version: Optional[str], new_version: Optional[str]) -> bool:
    """
    Check if version change represents a major bump.

    Major bump = first segment increased (e.g., 1.x.x -> 2.x.x)

    Args:
        old_version: Previous version string (e.g., "1.2.3")
        new_version: Current version string (e.g., "2.0.0")

    Returns:
        True if major version increased
    """
    if not old_version or not new_version:
        return False

    def get_major(v: str) -> Optional[int]:
        # Strip leading 'v' if present
        v = v.lstrip("vV")
        parts = v.split(".")
        try:
            return int(parts[0])
        except (ValueError, IndexError):
            return None

    old_major = get_major(old_version)
    new_major = get_major(new_version)

    if old_major is None or new_major is None:
        return False

    return new_major > old_major
