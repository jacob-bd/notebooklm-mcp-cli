# Doc Refresh Ralph Loop

**Completion Promise:** `<promise>DOC REFRESH COMPLETE</promise>`

You are executing a Ralph loop to refresh documentation and sync to NotebookLM.
Each iteration builds on your previous work. Continue until the promise can be truthfully output.

---

## Configuration Files

Load these from `~/SyncedProjects/C021_notebooklm-mcp/src/notebooklm_mcp/doc_refresh/`:
- `canonical_docs.yaml` - Document manifest (tiers, validation rules)
- `notebook_map.yaml` - Repo → NotebookLM notebook mapping

---

## Execution Phases

### Phase 1: DISCOVER

**Goal:** Identify target repo and scan for canonical documents.

1. **Determine target repo:**
   - If `--target PATH` provided, use that path
   - Otherwise, use current working directory
   - Verify it's a git repository

2. **Detect repo tier:**
   - Scan for Tier 1 docs (README.md, CHANGELOG.md, META.yaml)
   - Check for Tier 2 docs (CLAUDE.md, glossary.yaml, 10_docs/, 20_receipts/)
   - Check for Tier 3 docs (docs/OVERVIEW.md, docs/ARCHITECTURE.md, etc.)
   - Classify as: `simple` (Tier 1 only), `complex` (Tier 1+2), `kitted` (Tier 1+2+3)

3. **Load previous state:**
   - Read notebook_map.yaml for this repo
   - Get previous doc_hashes for change detection
   - Note last_sync date

4. **Gather context:**
   - Read 20_receipts/ (last 5 receipts) if exists
   - Read CHANGELOG.md if exists
   - Build understanding of recent changes

**Output:** List of discovered docs, repo tier, change context

---

### Phase 2: VALIDATE

**Goal:** Check each document against validation rules.

For each discovered canonical doc:

1. **Check metadata header:**
   - Look for YAML frontmatter (`---`)
   - Or inline header with `Version:` and `Last Updated:`
   - Flag if missing or outdated

2. **Verify claims:**
   - Check that file paths mentioned exist
   - Check that features described are implemented
   - Flag discrepancies for manual review

3. **Validate code references:**
   - Extract `file:line` patterns
   - Verify the files exist and have enough lines
   - Flag invalid references

4. **Compute content hash:**
   - Hash the document content (SHA256, first 12 chars)
   - Compare to stored hash from notebook_map.yaml
   - Track which docs changed

5. **Generate validation report:**
   ```
   VALIDATION REPORT
   =================
   Repo: {repo_name}
   Tier: {tier}

   Documents Checked: X
   - Valid: Y
   - Issues Found: Z

   Issues:
   - {doc}: {issue description}

   Change Summary:
   - Changed: {list of changed docs}
   - Unchanged: {list of unchanged docs}
   - Content Delta: X%
   ```

**Output:** Validation report with issues and change delta

---

### Phase 3: UPDATE

**Goal:** Fix discrepancies and update documents.

1. **Fix flagged issues:**
   - Add missing metadata headers
   - Update `Last Updated` to today's date
   - Fix invalid code references
   - Do NOT change content meaning without human approval

2. **Update META.yaml:**
   - Bump patch version if docs changed
   - Bump minor version if significant changes
   - Update last_modified date

3. **Commit changes:**
   - Stage modified files
   - Commit with message: `docs: refresh canonical documentation (doc-refresh loop)`
   - Include list of updated files in commit body

**Output:** List of files updated, commit hash

---

### Phase 4: NOTEBOOKLM SYNC

**Goal:** Sync documents to NotebookLM notebook.

1. **Look up or create notebook:**
   - Check notebook_map.yaml for notebook_id
   - If null, create new notebook: `notebook_create(title="{repo_name} Documentation Hub")`
   - Store notebook_id in notebook_map.yaml

2. **Determine docs to sync:**
   - Use change detection: only sync docs whose hash changed
   - Unless `--force` flag: sync all discovered docs

3. **Sync sources:**
   - For each changed doc:
     - Find existing source by title (if any)
     - Delete stale source: `source_delete(source_id, confirm=True)`
     - Add updated doc: `notebook_add_text(notebook_id, text=content, title=doc_path)`
   - Verify sources added via `notebook_get(notebook_id)`

4. **Update notebook_map.yaml:**
   - Store new doc_hashes
   - Update last_sync date
   - Save the file

**Output:** Sync summary (docs added, deleted, unchanged)

---

### Phase 5: ARTIFACT REFRESH (Conditional)

**Goal:** Regenerate NotebookLM artifacts if criteria met.

1. **Check refresh criteria:**
   - Content delta > 15%? → Refresh all
   - Major version bump in META.yaml? → Refresh all
   - `--force` flag? → Refresh all
   - `--docs-only` flag? → Skip this phase
   - None of above? → Skip with message

2. **If refresh triggered:**
   - Get current artifacts: `studio_status(notebook_id)`
   - For each Standard 7 artifact (or `--artifacts` subset):
     - Delete old: `studio_delete(notebook_id, artifact_id, confirm=True)`
     - Create new:
       - `mind_map_create(notebook_id, confirm=True)`
       - `report_create(notebook_id, report_format="Briefing Doc", confirm=True)`
       - `report_create(notebook_id, report_format="Study Guide", confirm=True)`
       - `audio_overview_create(notebook_id, format="deep_dive", confirm=True)`
       - `infographic_create(notebook_id, confirm=True)`
       - `flashcards_create(notebook_id, confirm=True)`
       - `quiz_create(notebook_id, question_count=5, confirm=True)`
   - Poll `studio_status` until generation complete
   - Store artifact IDs in notebook_map.yaml

3. **If skipped:**
   - Output: "Artifact refresh skipped (delta: X%, threshold: 15%)"

**Output:** Artifact refresh summary

---

### Phase 6: RECEIPT & COMPLETION

**Goal:** Write sync receipt and verify completion.

1. **Write sync receipt:**
   - Path: `20_receipts/{date}_doc_refresh.md` (in target repo)
   - Content:
     ```markdown
     # Doc Refresh Receipt

     **Date:** {today}
     **Repo:** {repo_name}
     **Tier:** {tier}

     ## Documents Synced
     - {list of docs}

     ## Validation Issues Fixed
     - {list of fixes or "None"}

     ## NotebookLM Sync
     - Notebook: {notebook_id}
     - Sources Updated: X
     - Artifacts Regenerated: Y/7 (or "Skipped")

     ## Commit
     - Hash: {commit_hash}
     ```

2. **Final verification:**
   - [ ] All Tier 1 docs exist and are valid
   - [ ] All discovered docs synced to NotebookLM
   - [ ] notebook_map.yaml updated with hashes
   - [ ] Receipt written

3. **Output completion promise:**
   - ONLY output if ALL checks pass
   - `<promise>DOC REFRESH COMPLETE</promise>`

---

## Flags Reference

| Flag | Effect |
|------|--------|
| `--target PATH` | Specify repo path (default: cwd) |
| `--force` | Force artifact regeneration |
| `--docs-only` | Skip artifact regeneration |
| `--artifacts "a,b"` | Only refresh specific artifacts |
| `--skip-unchanged` | Skip docs that haven't changed (default) |

---

## Important Notes

1. **Confirmation required:** All NotebookLM delete/create operations require `confirm=True`
2. **Idempotent:** Running twice should produce same result
3. **Non-destructive:** Don't change doc meaning without human approval
4. **Truthful promise:** Only output promise when genuinely complete

---

## Iteration Guidance

| Iteration | Expected Work |
|-----------|---------------|
| 1 | Discover docs, detect tier, gather context |
| 2 | Validate docs, generate report |
| 3 | Fix issues, update dates, commit |
| 4 | Sync to NotebookLM |
| 5 | Evaluate and execute artifact refresh |
| 6 | Write receipt, verify, output promise |

If blocked, explain what's preventing completion. Do NOT output false promises.
