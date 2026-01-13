# Receipt: PROJECT_PRIMER System Implementation

**Date**: 2026-01-12
**Session**: PROJECT_PRIMER.md generator implementation
**Status**: Complete (Phase 1-4)

---

## Summary

Implemented a PROJECT_PRIMER.md generation system that creates single-file documentation bundles for LLM Projects (ChatGPT, Claude, Gemini). This extends the NotebookLM doc sync infrastructure with a parallel workflow for platforms requiring manual file upload.

## Problem Addressed

1. **Context drift**: Starting repo conversations without context led to redundant build plans
2. **Accidental duplication**: Repos were rebuilding components that exist elsewhere
3. **Upload friction**: LLM Projects require file uploads; many files = high friction
4. **Missing boundaries**: No clear "this repo OWNS X, does NOT own Y" documentation

## Deliverables

### 1. Protocol Specification
- **Location**: `C010_standards/protocols/project_primer_protocol.md`
- **Version**: 1.0.0
- **Contents**: Required sections, tier rules, validation, LLM project setup instructions

### 2. Generator Module
- **Location**: `src/notebooklm_mcp/primer_gen/`
- **Files**:
  - `__init__.py` - Module exports
  - `sources.py` - Document gathering from repos
  - `render.py` - Markdown rendering
  - `generator.py` - Orchestration
  - `cli.py` - CLI entry point

### 3. CLI Command
- **Command**: `generate-project-primer <repo_id>`
- **Entry**: Added to `pyproject.toml` scripts
- **Dependency**: Added `pyyaml>=6.0` to project dependencies

### 4. Tracking Integration
- **Location**: `notebook_map.yaml` → `primers:` section
- **Schema**: repo_sha, generated_at, primer_hash, platforms (status tracking)

## Test Results

| Repo | Tier | Docs | SHA | Hash |
|------|------|------|-----|------|
| C017_brain-on-tap | kitted | 11 | d25dbc4 | sha256:58f4d2295865 |
| C021_notebooklm-mcp | complex* | 4 | 337cf4b | sha256:c1da531faec4 |

*C021 detected as "complex" instead of "kitted" - tier detection issue with path resolution (non-blocking).

## Files Changed

### C010_standards
- `protocols/project_primer_protocol.md` (NEW)

### C021_notebooklm-mcp
- `src/notebooklm_mcp/primer_gen/__init__.py` (NEW)
- `src/notebooklm_mcp/primer_gen/sources.py` (NEW)
- `src/notebooklm_mcp/primer_gen/render.py` (NEW)
- `src/notebooklm_mcp/primer_gen/generator.py` (NEW)
- `src/notebooklm_mcp/primer_gen/cli.py` (NEW)
- `pyproject.toml` (MODIFIED - script entry, pyyaml dependency)
- `src/notebooklm_mcp/doc_refresh/notebook_map.yaml` (MODIFIED - primers section)

### Generated Artifacts
- `C017_brain-on-tap/PROJECT_PRIMER.md` (NEW)
- `C021_notebooklm-mcp/PROJECT_PRIMER.md` (NEW)

## Known Issues

1. **Tier detection for C021**: Shows as "complex" instead of "kitted" - the Tier 3 path resolution doesn't find `docs/notebooklm_mcp/` correctly. Non-blocking; primer still generates.

2. **"What This Repo IS" extraction**: Sometimes extracts badges instead of description paragraph. README content is included verbatim below, so information is available.

3. **Responsibility boundaries**: Generated as TODOs when RELATIONS.yaml is missing. Manual population required.

## Next Steps

1. **Upload primers**: Upload C017 and C021 primers to ChatGPT Projects
2. **Test kickoff prompt**: Run deep dive kickoff to verify Betty respects boundaries
3. **Fix tier detection**: Debug path resolution for C021 Tier 3 docs
4. **Generate more primers**: Expand to C010, C001, C003

## Verification

```bash
# Verify command installed
which generate-project-primer

# Test generation
generate-project-primer C017_brain-on-tap
generate-project-primer C021_notebooklm-mcp

# Verify outputs exist
ls -la ~/SyncedProjects/C017_brain-on-tap/PROJECT_PRIMER.md
ls -la ~/SyncedProjects/C021_notebooklm-mcp/PROJECT_PRIMER.md
```

## Architecture Decision

**Single consolidated doc as primary deliverable**: Rather than uploading multiple files to LLM Projects, we generate one PROJECT_PRIMER.md that concatenates all relevant documentation. This reduces upload friction and gives LLMs better context navigation.

**Extend notebook_map.yaml**: Added `primers:` section to existing map rather than creating separate file. Single source of truth for all doc sync operations.

---

**Signed**: Claude (Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>)
