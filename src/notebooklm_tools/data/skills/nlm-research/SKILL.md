---
name: nlm-research
description: "NotebookLM web and Drive research — automatically discover and import sources on a topic. Use to populate a notebook with relevant web articles or Google Drive documents."
metadata:
  openclaw:
    category: "productivity"
    requires:
      bins: ["nlm"]
    cliHelp: "nlm research --help"
---

# nlm research

Discover and import sources into a NotebookLM notebook via web or Google Drive search.

## See Also

- **[nlm-skill](../nlm-skill/SKILL.md)** — Full reference
- **[nlm-source](../nlm-source/SKILL.md)** — Manually add sources
- **[recipe-research-report](../recipe-research-report/SKILL.md)** — Research → report full workflow

## Research Sources

| Source | Flag | Description |
|--------|------|-------------|
| Web | `--source web` (default) | Search the public web |
| Google Drive | `--source drive` | Search user's Drive |

## Research Modes (Web Only)

| Mode | Time | Sources |
|------|------|---------|
| `fast` (default) | ~30 seconds | ~10 sources |
| `deep` | ~5 minutes | ~40+ sources |

## CLI Commands

```bash
# Start research (--notebook-id is REQUIRED)
nlm research start "query" --notebook-id <nb-id>
nlm research start "query" --notebook-id <nb-id> --mode deep
nlm research start "query" --notebook-id <nb-id> --source drive

# Check progress (polls until done)
nlm research status <nb-id>                     # Poll up to 5 min
nlm research status <nb-id> --max-wait 0        # Single check, no wait
nlm research status <nb-id> --task-id <tid>     # Specific task
nlm research status <nb-id> --full              # Full details

# Import discovered sources
nlm research import <nb-id> <task-id>                      # Import all
nlm research import <nb-id> <task-id> --indices 0,2,5      # Import specific by index
```

## MCP Tools

```python
# Start research
result = research_start(notebook_id="...", query="topic", source="web", mode="fast")
task_id = result["task_id"]

# Poll status
status = research_status(notebook_id="...", task_id=task_id)
# status["state"] is "complete" when done

# Import sources
research_import(notebook_id="...", task_id=task_id)
# Or import specific indices:
research_import(notebook_id="...", task_id=task_id, source_indices=[0, 2, 5])
```

## Research Workflow

```bash
# 1. Start research (capture task ID)
TASK=$(nlm research start "agentic AI 2025" --notebook-id <nb-id> --quiet)

# 2. Wait for completion
nlm research status <nb-id> --max-wait 300

# 3. Review results before importing
nlm research status <nb-id> --full

# 4. Import all (or selective)
nlm research import <nb-id> $TASK

# 5. Verify sources added
nlm source list <nb-id>
```

## Tips

- **Start broad, filter on import**: Use `research start` to find many sources, then use `--indices` to import only the relevant ones.
- **Drive research**: Great for finding existing internal documents. Returns filenames and Drive IDs.
- **Force restart**: If research is stuck, use `nlm research start ... --force` to cancel the in-progress task and start fresh.
- **Rate limiting**: Wait 2 seconds between API calls when batching.
