---
description: "Refresh documentation and sync to NotebookLM"
argument-hint: "[--target PATH] [--force] [--docs-only] [--artifacts LIST]"
---

# Doc Refresh Command

This command initiates a Ralph loop to:
1. Validate and update canonical documentation in a repo
2. Sync updated docs to the repo's NotebookLM notebook
3. Conditionally regenerate NotebookLM artifacts

## Usage

```
/doc-refresh                          # Refresh docs in current repo
/doc-refresh --target ~/path/to/repo  # Refresh docs in specified repo
/doc-refresh --force                  # Force artifact regeneration
/doc-refresh --docs-only              # Skip artifact regeneration
/doc-refresh --artifacts "audio,mind_map"  # Only refresh specific artifacts
```

## Instructions

Read the Ralph loop prompt from `src/notebooklm_mcp/doc_refresh/PROMPT.md` in the C021_notebooklm-mcp repository and execute it.

**Target repo:** $ARGUMENTS (if provided, use `--target` value; otherwise use current working directory)

**Important:** This is a Ralph loop. Each iteration builds on the previous. Output `<promise>DOC REFRESH COMPLETE</promise>` only when ALL of the following are true:
- All canonical documents have been validated
- All discrepancies have been fixed
- Documents have been synced to NotebookLM
- Artifacts have been refreshed (if criteria met or --force)
- Sync receipt has been written

Begin by reading the PROMPT.md file and following its instructions.
