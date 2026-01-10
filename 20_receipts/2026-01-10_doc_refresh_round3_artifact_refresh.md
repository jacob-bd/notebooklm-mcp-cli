# Doc Refresh Round 3: Artifact Refresh Receipt

**Date:** 2026-01-10
**Status:** Complete

## Summary

Implemented NotebookLM artifact refresh for doc-refresh, including Standard 7 artifacts, delta-based triggering, and --force/--artifacts flags.

## Files Created

| File | Purpose |
|------|---------|
| `src/notebooklm_mcp/doc_refresh/artifact_refresh.py` | Standard 7 artifact types, plan/apply logic, studio polling |

## Files Modified

| File | Change |
|------|--------|
| `src/notebooklm_mcp/doc_refresh/__init__.py` | Exported artifact functions, version 0.3.0 |
| `src/notebooklm_mcp/doc_refresh/runner.py` | Added --artifacts, --force, --skip-artifacts flags, run_artifacts() |

## Implementation Highlights

### Standard 7 Artifacts

| Artifact | MCP Tool | Default Params |
|----------|----------|----------------|
| Mind Map | generate_mind_map + save_mind_map | title: "Documentation Mind Map" |
| Briefing Doc | create_report | report_format: "Briefing Doc" |
| Study Guide | create_report | report_format: "Study Guide" |
| Audio Overview | create_audio_overview | format: deep_dive, length: default |
| Infographic | create_infographic | orientation: landscape, detail: standard |
| Flashcards | create_flashcards | difficulty: medium |
| Quiz | create_quiz | question_count: 5, difficulty: 2 |

### Trigger Logic

Artifacts regenerate when ANY of:
1. `--force` flag is set
2. Major version bump in META.yaml
3. Content delta > 15% threshold

```python
def should_regenerate_artifacts(
    comparison: HashComparison,
    major_version_bump: bool = False,
    force: bool = False,
    threshold: float = 0.15,
) -> bool:
    if force: return True
    if major_version_bump: return True
    return comparison.change_ratio_simple > threshold
```

### CLI Flags

| Flag | Description |
|------|-------------|
| `--force` | Force artifact regeneration regardless of threshold |
| `--artifacts LIST` | Comma-separated subset (e.g., "audio,briefing,mind_map") |
| `--skip-artifacts` | Skip artifact refresh phase entirely |

### Artifact Aliases

```python
aliases = {
    "audio": ArtifactType.AUDIO_OVERVIEW,
    "audio_overview": ArtifactType.AUDIO_OVERVIEW,
    "mind_map": ArtifactType.MIND_MAP,
    "mindmap": ArtifactType.MIND_MAP,
    "briefing": ArtifactType.BRIEFING_DOC,
    "briefing_doc": ArtifactType.BRIEFING_DOC,
    "study": ArtifactType.STUDY_GUIDE,
    "study_guide": ArtifactType.STUDY_GUIDE,
    "infographic": ArtifactType.INFOGRAPHIC,
    "flashcards": ArtifactType.FLASHCARDS,
    "quiz": ArtifactType.QUIZ,
}
```

## Verification

### Dry-Run (No Changes - Threshold Not Met)
```
uv run python -m notebooklm_mcp.doc_refresh.runner --sync-only -v --target /Users/jeremybradford/SyncedProjects/C017_brain-on-tap

# Artifact Plan: C017_brain-on-tap

**Notebook ID:** c0b11752-c427-4191-ac73-5dc27b879750
**Content Delta:** 0.0%

**Status:** NOT TRIGGERED

Threshold not met. Use --force to regenerate anyway.

## Artifacts Skipped
- Mind Map (Change delta 0.0% below 15% threshold)
- Briefing Doc (Change delta 0.0% below 15% threshold)
- Study Guide (Change delta 0.0% below 15% threshold)
- Audio Overview (Change delta 0.0% below 15% threshold)
- Infographic (Change delta 0.0% below 15% threshold)
- Flashcards (Change delta 0.0% below 15% threshold)
- Quiz (Change delta 0.0% below 15% threshold)
```

### Dry-Run (--force Flag)
```
uv run python -m notebooklm_mcp.doc_refresh.runner --sync-only -v --force --target /Users/jeremybradford/SyncedProjects/C017_brain-on-tap

# Artifact Plan: C017_brain-on-tap

**Notebook ID:** c0b11752-c427-4191-ac73-5dc27b879750
**Content Delta:** 0.0%

**Status:** TRIGGERED (--force flag)

## Artifacts to Create (7 total)

- Mind Map
- Briefing Doc
- Study Guide
- Audio Overview
- Infographic
- Flashcards
- Quiz
```

### Dry-Run (--artifacts Subset)
```
uv run python -m notebooklm_mcp.doc_refresh.runner --sync-only -v --force --artifacts "audio,briefing" --target /Users/jeremybradford/SyncedProjects/C017_brain-on-tap

# Artifact Plan: C017_brain-on-tap

**Notebook ID:** c0b11752-c427-4191-ac73-5dc27b879750
**Content Delta:** 0.0%

**Status:** TRIGGERED (--force flag)

## Artifacts to Create (2 total)

- Audio Overview
- Briefing Doc
```

### Dry-Run (--skip-artifacts)
```
uv run python -m notebooklm_mcp.doc_refresh.runner --sync-only -v --skip-artifacts --target /Users/jeremybradford/SyncedProjects/C017_brain-on-tap

# Sync Plan: C017_brain-on-tap

**Notebook ID:** c0b11752-c427-4191-ac73-5dc27b879750

No changes needed - notebook is in sync.
# (No artifact plan output - skipped)
```

## NOT Implemented (Deferred)

- [ ] Apply artifact creation (requires --apply flag and live API test)
- [ ] Artifact deletion before recreation
- [ ] Artifact status persistence in notebook_map.yaml

## Notes

- Artifact creation requires `--apply` flag (same gating as sync)
- Mind map uses two-step API: generate_mind_map() + save_mind_map()
- All artifact creation methods require source_ids (fetched from notebook)
- Studio polling with configurable timeout (default 5 minutes)

## Next Steps

- Test actual artifact creation with `--apply --force`
- Add artifact tracking to notebook_map.yaml
- Consider artifact versioning/retention
