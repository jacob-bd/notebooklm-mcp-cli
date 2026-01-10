"""
Report formatting for validation results.

Outputs human-readable and machine-parseable reports.
"""

from typing import Optional

from .models import (
    DiscoveryResult,
    DocItem,
    HashComparison,
    IssueSeverity,
    Tier,
    ValidationIssue,
    ValidationReport,
)


def format_discovery_report(result: DiscoveryResult) -> str:
    """
    Format a discovery result as human-readable text.

    Args:
        result: DiscoveryResult from discover_repo()

    Returns:
        Formatted string report
    """
    lines: list[str] = []
    lines.append(f"# Discovery Report: {result.repo_name}")
    lines.append("")
    lines.append(f"**Repo Path:** {result.repo_path}")
    lines.append(f"**Tier Classification:** {result.tier.value.upper()}")

    if result.tier3_root:
        lines.append(f"**Tier 3 Root:** {result.tier3_root.relative_to(result.repo_path)}")

    lines.append("")

    # Tier 1 docs
    lines.append("## Tier 1 (Required)")
    lines.append("")
    for doc in result.tier1_docs:
        status = "x" if doc.exists else " "
        lines.append(f"- [{status}] {doc.path}")
    lines.append("")

    # Tier 2 docs (if any exist or repo is complex+)
    if result.tier2_docs:
        lines.append("## Tier 2 (Extended)")
        lines.append("")
        for doc in result.tier2_docs:
            status = "x" if doc.exists else " "
            lines.append(f"- [{status}] {doc.path}")
        lines.append("")

    # Tier 3 docs (if kitted)
    if result.tier == Tier.KITTED and result.tier3_docs:
        lines.append("## Tier 3 (Deep Reference)")
        lines.append("")
        for doc in result.tier3_docs:
            status = "x" if doc.exists else " "
            lines.append(f"- [{status}] {doc.path}")
        lines.append("")

    # Summary
    existing = len([d for d in result.docs if d.exists])
    total = len(result.docs)
    lines.append(f"**Summary:** {existing}/{total} documents found")

    return "\n".join(lines)


def format_validation_report(report: ValidationReport) -> str:
    """
    Format a validation report as human-readable text.

    Args:
        report: ValidationReport from validate_discovery()

    Returns:
        Formatted string report
    """
    lines: list[str] = []
    lines.append(f"# Validation Report: {report.discovery.repo_name}")
    lines.append("")

    # Discovery summary
    lines.append(f"**Tier:** {report.discovery.tier.value.upper()}")
    lines.append(f"**Docs Found:** {len(report.discovery.existing_docs)}/{len(report.discovery.docs)}")
    lines.append("")

    # Overall status
    if report.is_valid:
        lines.append("## Status: VALID")
        if report.warnings:
            lines.append(f"({len(report.warnings)} warnings)")
    else:
        lines.append(f"## Status: INVALID ({len(report.errors)} errors)")
    lines.append("")

    # Errors
    if report.errors:
        lines.append("## Errors (must fix)")
        lines.append("")
        for issue in report.errors:
            lines.append(_format_issue(issue))
        lines.append("")

    # Warnings
    if report.warnings:
        lines.append("## Warnings (should fix)")
        lines.append("")
        for issue in report.warnings:
            lines.append(_format_issue(issue))
        lines.append("")

    # Info
    info_issues = [i for i in report.issues if i.severity == IssueSeverity.INFO]
    if info_issues:
        lines.append("## Info")
        lines.append("")
        for issue in info_issues:
            lines.append(_format_issue(issue))
        lines.append("")

    # Hash comparison (if available)
    if report.hash_comparison:
        lines.append(_format_hash_comparison(report.hash_comparison))

    return "\n".join(lines)


def _format_issue(issue: ValidationIssue) -> str:
    """Format a single validation issue."""
    severity_icon = {
        IssueSeverity.ERROR: "E",
        IssueSeverity.WARNING: "W",
        IssueSeverity.INFO: "I",
    }
    icon = severity_icon[issue.severity]

    line_info = f":{issue.line_number}" if issue.line_number else ""
    msg = f"- [{icon}] {issue.doc_path}{line_info}: {issue.message}"

    if issue.context:
        msg += f"\n  Context: {issue.context}"

    return msg


def _format_hash_comparison(comparison: HashComparison) -> str:
    """Format hash comparison results."""
    lines: list[str] = []
    lines.append("## Change Detection")
    lines.append("")
    lines.append(f"**Total Docs:** {comparison.total_docs}")
    lines.append(f"**Changed:** {len(comparison.changed_docs)}")
    lines.append(f"**Unchanged:** {len(comparison.unchanged_docs)}")
    lines.append(f"**New (no stored hash):** {len(comparison.new_docs)}")
    lines.append(f"**Change Delta:** {comparison.change_ratio_simple:.1%}")
    lines.append("")

    if comparison.changed_docs:
        lines.append("### Changed Documents")
        lines.append("")
        for doc in comparison.changed_docs:
            lines.append(f"- {doc.path}")
            lines.append(f"  - Old: {doc.stored_hash}")
            lines.append(f"  - New: {doc.content_hash}")
        lines.append("")

    if comparison.new_docs:
        lines.append("### New Documents (not previously tracked)")
        lines.append("")
        for doc in comparison.new_docs:
            lines.append(f"- {doc.path} ({doc.content_hash})")
        lines.append("")

    return "\n".join(lines)


def format_compact_report(report: ValidationReport) -> str:
    """
    Format a compact one-line summary suitable for CI/CD output.

    Args:
        report: ValidationReport

    Returns:
        Single line summary
    """
    status = "VALID" if report.is_valid else "INVALID"
    errors = len(report.errors)
    warnings = len(report.warnings)
    docs = len(report.discovery.existing_docs)
    total = len(report.discovery.docs)
    tier = report.discovery.tier.value

    return f"{report.discovery.repo_name}: {status} [{tier}] {docs}/{total} docs, {errors}E/{warnings}W"


def format_doc_table(docs: list[DocItem]) -> str:
    """
    Format a list of docs as a markdown table.

    Args:
        docs: List of DocItem

    Returns:
        Markdown table string
    """
    lines: list[str] = []
    lines.append("| Path | Tier | Exists | Hash | Changed |")
    lines.append("|------|------|--------|------|---------|")

    for doc in docs:
        exists = "Yes" if doc.exists else "No"
        hash_val = doc.content_hash or "-"
        changed = "-"
        if doc.is_changed is True:
            changed = "Yes"
        elif doc.is_changed is False:
            changed = "No"

        lines.append(f"| {doc.path} | {doc.tier} | {exists} | {hash_val} | {changed} |")

    return "\n".join(lines)


def format_for_yaml(
    report: ValidationReport,
    comparison: Optional[HashComparison] = None,
) -> dict:
    """
    Format report as a dict suitable for YAML serialization.

    Useful for storing in notebook_map.yaml or receipts.

    Args:
        report: ValidationReport
        comparison: Optional HashComparison

    Returns:
        Dict ready for yaml.dump()
    """
    result: dict = {
        "repo_name": report.discovery.repo_name,
        "tier": report.discovery.tier.value,
        "valid": report.is_valid,
        "docs_found": len(report.discovery.existing_docs),
        "docs_total": len(report.discovery.docs),
        "errors": len(report.errors),
        "warnings": len(report.warnings),
    }

    if comparison:
        result["change_detection"] = {
            "changed": len(comparison.changed_docs),
            "unchanged": len(comparison.unchanged_docs),
            "new": len(comparison.new_docs),
            "delta": round(comparison.change_ratio_simple, 3),
        }

    if report.discovery.tier3_root:
        result["tier3_root"] = str(
            report.discovery.tier3_root.relative_to(report.discovery.repo_path)
        )

    # Include doc hashes for storage
    result["doc_hashes"] = {}
    for doc in report.discovery.docs:
        if doc.content_hash:
            result["doc_hashes"][str(doc.path)] = doc.content_hash

    return result
