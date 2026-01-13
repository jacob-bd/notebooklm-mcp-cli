# Receipt: PROJECT_PRIMER Rollout - C021_notebooklm-mcp

**Date**: 2026-01-12
**Operator**: Claude Code (Opus 4.5)
**Session**: PROJECT_PRIMER harness rollout (batch 2)

## Summary

Generated PROJECT_PRIMER.md for C021_notebooklm-mcp (this repo). Created v2 RELATIONS.yaml with ownership boundaries. Updated notebook_map.yaml tracking.

## Documents Modified

| File | Action | Description |
|------|--------|-------------|
| `RELATIONS.yaml` | Created | New v2 format with owns/must_not_own/depends_on |
| `PROJECT_PRIMER.md` | Generated | Single-file documentation bundle |

## RELATIONS.yaml v2 Content

```yaml
version: 2
repo: C021_notebooklm-mcp

owns:
  - "NotebookLM MCP Server (programmatic access to notebooklm.google.com)"
  - "Reverse-engineered NotebookLM internal APIs (batchexecute protocol)"
  - "Auth token caching and extraction (cookies, CSRF, session)"
  - "31 MCP tools for notebook/source/studio operations"
  - "Doc-refresh Ralph loop for syncing canonical docs to NotebookLM"
  - "PROJECT_PRIMER generator (primer_gen module)"
  - "notebook_map.yaml tracking for doc sync state"

must_not_own:
  - "NotebookLM service itself (Google owns that)"
  - "Workspace governance rules or protocols (belongs to C010_standards)"
  - "Source document authoring (documents live in their source repos)"
  - "Credential storage (uses C001_mission-control vault for API keys)"
  - "Memory infrastructure or SADB pipeline (belongs to C002/C003)"

depends_on:
  - repo: C010_standards
    reason: "Betty Protocol, README repo card standard, workspace conventions"
  - repo: C001_mission-control
    reason: "Credential vault for any API keys needed"
  - repo: C017_brain-on-tap
    reason: "Primary test target for doc-refresh; has active NotebookLM notebook"
```

## Primer Generation Output

```
Repo ID:       C021_notebooklm-mcp
Tier:          kitted (detected: complex)
Source docs:   5
Repo SHA:      337cf4b
Output:        /Users/jeremybradford/SyncedProjects/C021_notebooklm-mcp/PROJECT_PRIMER.md
Hash:          sha256:63243804daa7
Generated:     2026-01-12T21:52:13

WARNINGS:
  ⚠  Tier mismatch: detected=complex, target=kitted
```

## Verification

- [x] README exists (no BOT markers - open source project)
- [x] META.yaml exists with required fields
- [x] RELATIONS.yaml v2 format with owns/must_not_own/depends_on
- [x] PROJECT_PRIMER.md generated with populated boundaries
- [x] Integration Map populated with 3 upstream dependencies
- [x] Quick Routing table present
- [x] Provenance block with SHA and timestamp
- [x] notebook_map.yaml updated with primer entry

## Notes

- Tier mismatch warning: This repo is declared as `kitted` but tier detection found `complex`. This is because the Tier 3 docs are in `docs/notebooklm_mcp/` rather than `10_docs/`. The primer still generates correctly.
- README does not have BOT repo card markers - this is an open source project with standard PyPI README format.

## notebook_map.yaml Entry

```yaml
C021_notebooklm-mcp:
  enabled: true
  tier: kitted
  repo_sha: 337cf4b
  generated_at: '2026-01-12T21:52:13Z'
  primer_path: PROJECT_PRIMER.md
  primer_hash: 'sha256:63243804daa7'
  platforms:
    chatgpt: { status: pending }
    claude_projects: { status: pending }
    gemini: { status: not_started }
```

## Known Issues

- Tier 3 docs in `docs/` not `10_docs/` causes tier mismatch warning (cosmetic only)

## Next Steps

1. Upload PROJECT_PRIMER.md to ChatGPT/Claude Projects
2. Test with deep dive kickoff prompt
3. Consider adding BOT repo card to README (optional for open source)
