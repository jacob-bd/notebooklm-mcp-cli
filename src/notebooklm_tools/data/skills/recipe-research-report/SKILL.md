---
name: recipe-research-report
description: "Automated research pipeline: search the web for a topic, import top sources into NotebookLM, generate a Briefing Doc report, and export to Google Docs."
metadata:
  openclaw:
    category: "recipe"
    domain: "research"
    requires:
      bins: ["nlm"]
      skills: ["nlm-notebook", "nlm-research", "nlm-studio"]
---

# Recipe: Research → Report → Google Docs

Automatically research a topic, populate a notebook, generate a report, and export to Google Docs.

## Prerequisites

- `nlm` installed and authenticated (`nlm login`)
- Google account with NotebookLM access

## Steps

### 1. Create a notebook for this research

```bash
TOPIC="agentic AI trends 2025"
NB_ID=$(nlm notebook create "Research: $TOPIC" --quiet)
nlm alias set research $NB_ID
echo "Notebook: $NB_ID"
```

### 2. Run web research

```bash
# Fast mode (~30s, ~10 sources)
nlm research start "$TOPIC" --notebook-id research

# Or deep mode (~5min, 40+ sources) for comprehensive coverage
nlm research start "$TOPIC" --notebook-id research --mode deep
```

### 3. Wait for research to complete

```bash
nlm research status research --max-wait 300
```

### 4. Review discovered sources

```bash
# See all discovered sources with titles and URLs
nlm research status research --full
```

### 5. Import sources (all or selective)

```bash
# Capture the task ID from step 2's output, then:

# Import all discovered sources
nlm research import research <task-id>

# Or import only the best ones (e.g., indices 0, 1, 2, 4, 7)
nlm research import research <task-id> --indices 0,1,2,4,7
```

### 6. Verify sources were added

```bash
nlm source list research
```

### 7. Generate a Briefing Doc report

```bash
nlm report create research --format "Briefing Doc" --confirm
```

### 8. Monitor progress

```bash
nlm studio status research
# Wait for "completed" status (usually < 2 minutes for reports)
```

### 9. Export to Google Docs

```bash
# Get artifact ID from studio status
ARTIFACT_ID=$(nlm studio status research --json | python3 -c "
import sys, json
artifacts = json.load(sys.stdin)['artifacts']
reports = [a for a in artifacts if a['type'] == 'report']
print(reports[-1]['id'])
")

nlm export docs research $ARTIFACT_ID --title "Research Report: $TOPIC"
```

## Variations

### Study Guide instead of Briefing Doc

```bash
nlm report create research --format "Study Guide" --confirm
```

### Custom report with specific focus

```bash
nlm report create research --format "Create Your Own" \
    --prompt "Focus on practical business applications and key statistics. Use executive summary format." \
    --confirm
```

### Deep research + All content types

```bash
# After importing sources, generate multiple artifacts
nlm report create research --format "Briefing Doc" --confirm
nlm mindmap create research --confirm
nlm slides create research --format detailed --confirm
```

## Full Automated Pipeline (One-Liner Script)

```bash
#!/usr/bin/env bash
TOPIC="${1:-AI trends 2025}"
NB_ID=$(nlm notebook create "Research: $TOPIC" --quiet)

echo "Created notebook: $NB_ID"
echo "Starting research..."
nlm research start "$TOPIC" --notebook-id "$NB_ID"
nlm research status "$NB_ID" --max-wait 300

TASK_ID=$(nlm research status "$NB_ID" --json | python3 -c "
import sys, json; d=json.load(sys.stdin); print(d['tasks'][-1]['id'])")

echo "Importing sources..."
nlm research import "$NB_ID" "$TASK_ID"

echo "Generating report..."
nlm report create "$NB_ID" --format "Briefing Doc" --confirm
nlm studio status "$NB_ID" --max-wait 120

echo "Done! Download with: nlm download report $NB_ID --output report.md"
```

## MCP Version

```python
# 1. Create notebook
nb = notebook_create(title=f"Research: {topic}")
nb_id = nb["notebook_id"]

# 2. Start research
task = research_start(notebook_id=nb_id, query=topic, source="web", mode="fast")
task_id = task["task_id"]

# 3. Poll until complete
import time
while True:
    status = research_status(notebook_id=nb_id, task_id=task_id)
    if status["state"] == "complete":
        break
    time.sleep(10)

# 4. Import all sources
research_import(notebook_id=nb_id, task_id=task_id)

# 5. Generate report
studio_create(notebook_id=nb_id, artifact_type="report",
              report_format="Briefing Doc", confirm=True)

# 6. Export to Google Docs (after polling studio_status for completion)
export_artifact(notebook_id=nb_id, artifact_id=artifact_id,
                export_type="docs", title=f"Report: {topic}")
```
