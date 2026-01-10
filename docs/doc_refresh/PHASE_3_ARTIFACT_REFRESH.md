# Phase 3: Artifact Refresh

**Version:** 0.1.0
**Last Updated:** 2026-01-10
**Status:** ⏳ Pending

## Objective

Implement conditional artifact regeneration based on change thresholds, with manual override support.

## Deliverables

| Deliverable | Status | Description |
|-------------|--------|-------------|
| Change threshold logic | ⏳ | 15% delta or major version detection |
| Artifact management | ⏳ | Delete old, regenerate Standard 7 |
| Override flags | ⏳ | `--force`, `--artifacts` subset |
| Test run on C021 | ⏳ | Full cycle with artifact refresh |

## Implementation Plan

### 3.1 Change Threshold Logic

```
regenerate = (content_delta > 0.15) OR
             (major_version_bump) OR
             (--force flag)
```

**Major version detection:**
- Parse `META.yaml` for `version` field
- Compare against stored version in `notebook_map.yaml`
- Major bump = first segment increased (e.g., 1.x.x → 2.x.x)

### 3.2 Artifact Management

**Standard 7 Artifacts:**

| ID | Tool | Params |
|----|------|--------|
| `mind_map` | `mind_map_create` | - |
| `briefing_doc` | `report_create` | `report_format="Briefing Doc"` |
| `study_guide` | `report_create` | `report_format="Study Guide"` |
| `audio_overview` | `audio_overview_create` | `format="deep_dive"` |
| `infographic` | `infographic_create` | `orientation="landscape"` |
| `flashcards` | `flashcards_create` | `difficulty="medium"` |
| `quiz` | `quiz_create` | `question_count=5, difficulty=2` |

**Regeneration process:**
1. Get existing artifacts via `studio_status(notebook_id)`
2. Delete old artifacts via `studio_delete(notebook_id, artifact_id, confirm=True)`
3. Create new artifacts (all require `confirm=True`)
4. Poll `studio_status` until generation complete
5. Store new artifact IDs in `notebook_map.yaml`

### 3.3 Override Flags

| Flag | Effect |
|------|--------|
| `--force` | Skip threshold check, always regenerate |
| `--artifacts "a,b"` | Only regenerate specified artifacts |

## Acceptance Criteria

- [ ] Artifacts regenerated when delta > 15%
- [ ] Artifacts regenerated on major version bump
- [ ] `--force` bypasses threshold check
- [ ] `--artifacts` limits which artifacts are refreshed
- [ ] `studio_status` shows new artifacts after refresh
- [ ] `notebook_map.yaml` stores artifact IDs

## Dependencies

- Phase 1 complete ✅
- Phase 2 complete (hash tracking, sync)
- NotebookLM auth valid
- Sufficient API quota for artifact generation

## Notes

- Audio/video generation can take several minutes
- Poll `studio_status` with backoff
- Handle generation failures gracefully
- Consider parallel artifact creation where possible
