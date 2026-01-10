# Doc Refresh Epic

**Version:** 0.2.0
**Last Updated:** 2026-01-10
**Status:** Phase 1 Complete

## Overview

A portable Ralph Loop that maintains documentation across repositories and keeps NotebookLM notebooks synchronized with the latest docs.

## Problem Statement

Documentation drifts from reality. Code changes, but docs lag behind. NotebookLM notebooks become stale. Manual updates are tedious and inconsistent.

## Solution

A Ralph Loop (`/doc-refresh`) that:
1. Validates canonical docs against repo state
2. Updates metadata and fixes discrepancies
3. Syncs docs to NotebookLM
4. Conditionally regenerates artifacts

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Location** | C021 module + skill | Central to NotebookLM MCP; invocable from any repo |
| **Safety** | `--dry-run` default | No changes without explicit `--apply` |
| **Change Detection** | Hash-based + version | 15% delta OR major version bump triggers refresh |
| **Notebook Org** | One per repo | Simple 1:1 mapping; hybrid collections later |
| **Doc Tiers** | 3 tiers | Required → Extended → Kitted (auto-detected) |

## Phases

| Phase | Status | Description |
|-------|--------|-------------|
| [Phase 1: Foundation](./PHASE_1_FOUNDATION.md) | ✅ Complete | Skill, manifest, prompt, repo mapping |
| [Phase 2: Validation & Sync](./PHASE_2_VALIDATION_SYNC.md) | ⏳ Pending | Validation logic, hash tracking, NotebookLM sync |
| [Phase 3: Artifact Refresh](./PHASE_3_ARTIFACT_REFRESH.md) | ⏳ Pending | Conditional regeneration, Standard 7 artifacts |

## Interfaces

See [INTERFACES.md](./INTERFACES.md) for CLI flags, manifest schema, and API contracts.

## Success Criteria

- [ ] `/doc-refresh --dry-run` generates accurate validation report
- [ ] `/doc-refresh --apply --docs-only` updates docs and commits
- [ ] `/doc-refresh --apply --sync-only` syncs to NotebookLM
- [ ] `/doc-refresh --apply --full` regenerates artifacts when criteria met
- [ ] C017 and C021 notebooks stay current with < 5 min execution time

## Future Roadmap

| Feature | Priority | Description |
|---------|----------|-------------|
| Hybrid notebooks | Medium | "Notebook of notebooks" for related repos |
| Cross-repo glossary | Medium | Shared terms with repo-specific extensions |
| Scheduled refresh | Low | Cron-style automation |
| Diff reports | Low | Human-readable change summaries |
