# NotebookLM CLI - Complete Workflow Sequences

This document provides end-to-end workflow sequences for common tasks with the `nlm` CLI.

## Critical AI Behavior Rules

### Always Confirm Destructive Operations

**Before executing ANY delete operation, ALWAYS ask the user for explicit confirmation.** Deletions are irreversible.

Commands requiring user confirmation before AI execution:
- `nlm notebook delete <id> --confirm`
- `nlm source delete <id> --confirm`
- `nlm studio delete <notebook-id> <artifact-id> --confirm`
- `nlm auth delete <profile> --confirm`

**Example AI behavior:**
```
User: "Delete that notebook"

AI: "I found notebook 'AI Research' (ID: abc123...). 
⚠️ This will PERMANENTLY delete the notebook and all its sources, generated content, and history. 
This action cannot be undone.

Do you want me to proceed with deletion?"

[Wait for user confirmation before running: nlm notebook delete abc123... --confirm]
```

---

## Workflow 1: First-Time Setup

### Goal: Authenticate and create first notebook

```bash
# Step 1: Authenticate (opens Chrome)
nlm login

# Step 2: Verify authentication
nlm login --check
# Expected: "Authentication valid! Notebooks found: N"

# Step 3: Create a notebook
nlm notebook create "My First Notebook"
# Output: Created notebook: <notebook-id>

# Step 4: Set alias for convenience
nlm alias set first <notebook-id>

# Step 5: Verify
nlm notebook get first
```

---

## Workflow 2: Content Ingestion

### Goal: Add multiple sources to a notebook

```bash
# Prerequisites: Authenticated, have notebook ID

# Add web pages
nlm source add <notebook-id> --url "https://example.com/article1"
sleep 2  # Throttle to avoid rate limits

nlm source add <notebook-id> --url "https://example.com/article2"
sleep 2

# Add YouTube video
nlm source add <notebook-id> --url "https://youtube.com/watch?v=VIDEO_ID"
sleep 2

# Add pasted text/notes
nlm source add <notebook-id> --text "My personal notes and observations about this topic..." --title "My Notes"
sleep 2

# Add Google Drive document
nlm source add <notebook-id> --drive 1KQH3eW0hMBp7WKukQ1oURhnW-SdOT1qq --type doc
sleep 2

# Verify all sources added
nlm source list <notebook-id>
```

---

## Workflow 3: Research → Podcast Pipeline

### Goal: Discover sources via research and generate a podcast

```bash
# Step 1: Create dedicated notebook
nlm notebook create "AI Trends Research 2026"
# Capture: NOTEBOOK_ID=<id>

# Step 2: Set alias
nlm alias set research <notebook-id>

# Step 3: Start deep research (takes ~5 minutes)
nlm research start "agentic AI and autonomous systems trends 2026" --notebook-id research --mode deep
# Capture: TASK_ID=<task_id>

# Step 4: Monitor progress (polls until complete or timeout)
nlm research status research --max-wait 300

# Step 5: View discovered sources
nlm research status research --full

# Step 6: Import all discovered sources
nlm research import research <task-id>
# Or import specific sources:
# nlm research import research <task-id> --indices 0,2,5,7

# Step 7: Generate podcast
nlm audio create research --format deep_dive --length default --confirm

# Step 8: Check generation status (podcast takes 2-5 minutes)
nlm studio status research
# Repeat until status shows "completed"

# Step 9: Get podcast URL from studio status output
```

---

## Workflow 4: Study Materials Generation

### Goal: Create comprehensive study materials from sources

```bash
# Prerequisites: Notebook with sources already added

# Step 1: Verify sources exist
nlm source list <notebook-id>

# Step 2: Generate study guide report
nlm report create <notebook-id> --format "Study Guide" --confirm
sleep 5

# Step 3: Generate quiz (10 questions, medium difficulty)
nlm quiz create <notebook-id> --count 10 --difficulty 3 --focus "Comprehensive review" --confirm
sleep 3

# Step 4: Generate flashcards
nlm flashcards create <notebook-id> --difficulty medium --focus "Important definitions" --confirm
sleep 3

# Step 5: Generate mind map for visual overview
nlm mindmap create <notebook-id> --title "Topic Overview" --confirm

# Step 6: Check all generated artifacts
nlm studio status <notebook-id>
```

---

## Workflow 5: Quick Q&A Session

### Goal: Ask questions about sources

```bash
# Option A: One-shot questions
nlm notebook query <notebook-id> "What are the main themes across these sources?"
# Capture: CONVERSATION_ID from output

# Follow-up (maintains context)
nlm notebook query <notebook-id> "Can you elaborate on the first theme?" --conversation-id <conv-id>

# Option B: Interactive chat session
nlm chat start <notebook-id>
# In REPL:
#   Type questions naturally
#   /sources - see available sources
#   /clear - reset conversation
#   /exit - exit REPL
```

---

## Workflow 6: Drive Document Sync

### Goal: Keep Drive sources up-to-date

```bash
# Step 1: Check current freshness status
nlm source list <notebook-id> --drive
# Shows: Source ID, Title, Type, Fresh status

# Step 2: Quick check (skip freshness API calls)
nlm source list <notebook-id> --drive -S

# Step 3: Find stale sources
nlm source stale <notebook-id>
# Lists sources that have been modified in Drive since import

# Step 4: Sync all stale sources
nlm source sync <notebook-id> --confirm

# Step 5: Sync specific sources only
nlm source sync <notebook-id> --source-ids <id1>,<id2> --confirm

# Step 6: Verify all fresh
nlm source stale <notebook-id>
# Should show no stale sources
```

---

## Workflow 7: Multi-Account Management

### Goal: Work with multiple Google accounts

```bash
# Step 1: Login to work account
nlm login --profile work

# Step 2: Login to personal account
nlm login --profile personal

# Step 3: List all profiles
nlm login profile list

# Step 4: Switch default profile
nlm login switch work

# Step 5: Use specific profile for commands
nlm notebook list --profile work
nlm notebook list --profile personal

# Step 6: Create notebook in specific account
nlm notebook create "Work Project" --profile work
```

---

## Workflow 8: Content Export

### Goal: Extract and export source content

```bash
# Step 1: List sources
nlm source list <notebook-id>

# Step 2: Get AI summary of a source
nlm source describe <source-id>

# Step 3: Get raw text content
nlm source content <source-id>

# Step 4: Export to file
nlm source content <source-id> --output ./export/source_content.txt

# Step 5: Export multiple sources (script pattern)
for id in $(nlm source list <notebook-id> --quiet); do
    nlm source content $id --output "./export/${id}.txt"
    sleep 1
done
```

---

## Workflow 9: Presentation Preparation

### Goal: Generate presentation materials

```bash
# Step 1: Create focused notebook
nlm notebook create "Q4 Presentation Prep"
nlm alias set pres <notebook-id>

# Step 2: Add relevant sources
nlm source add pres --url "https://company.com/q4-results"
nlm source add pres --drive <slides-doc-id> --type slides
nlm source add pres --text "Key talking points: ..." --title "Talking Points"

# Step 3: Generate slide deck
nlm slides create pres --format detailed --confirm
sleep 5

# Step 4: Generate briefing doc
nlm report create pres --format "Briefing Doc" --confirm
sleep 5

# Step 5: Generate infographic for visual summary
nlm infographic create pres --orientation landscape --detail standard --confirm

# Step 6: Check outputs
nlm studio status pres
```

---

## Workflow 10: Notebook Sharing and Collaboration

### Goal: Share a notebook with collaborators

```bash
# Step 1: Check current sharing status
nlm share status <notebook-id>

# Step 2: Enable public link sharing
nlm share public <notebook-id>
# Output includes the public URL

# Step 3: Invite specific collaborators
nlm share invite <notebook-id> colleague@example.com --role viewer
nlm share invite <notebook-id> editor@example.com --role editor

# Step 4: Disable public link when done
nlm share public <notebook-id> --off

# Step 5: Verify sharing settings
nlm share status <notebook-id>
```

---

## Workflow 11: Working with Notes

### Goal: Add and manage personal notes in a notebook

```bash
# Step 1: Create a note
nlm note create <notebook-id> --content "My key observations about this topic..." --title "Key Insights"

# Step 2: List all notes
nlm note list <notebook-id>

# Step 3: Update a note
nlm note update <notebook-id> <note-id> --content "Updated observations..."

# Step 4: Notes are included in queries
nlm notebook query <notebook-id> "What are my personal notes about?"

# Step 5: Delete a note (after user confirms)
nlm note delete <notebook-id> <note-id> --confirm
```

---

## Workflow 12: Downloading and Exporting Artifacts

### Goal: Download generated content locally or export to Google Docs/Sheets

```bash
# Step 1: Check available artifacts
nlm studio status <notebook-id>

# Step 2: Download audio podcast
nlm download audio <notebook-id> --output ./downloads/podcast.mp3

# Step 3: Download report
nlm download report <notebook-id> --output ./downloads/report.md

# Step 4: Download quiz in different formats
nlm download quiz <notebook-id> --output quiz.json --format json
nlm download quiz <notebook-id> --output quiz.html --format html
nlm download flashcards <notebook-id> --output cards.html --format html

# Step 5: Export data table to Google Sheets
nlm export sheets <notebook-id> <artifact-id> --title "Extracted Data"

# Step 6: Export report to Google Docs
nlm export docs <notebook-id> <artifact-id> --title "My Report"
```

---

## Workflow 13: Cleanup and Deletion

### Goal: Clean up notebooks and artifacts

**⚠️ IMPORTANT: Always confirm with user before executing delete commands!**

```bash
# Step 1: List existing notebooks
nlm notebook list

# Step 2: Get notebook details before deletion
nlm notebook get <notebook-id>
nlm source list <notebook-id>
nlm studio status <notebook-id>

# Step 3: Delete specific artifact (after user confirms)
# AI: "Are you sure you want to delete artifact X from notebook Y?"
nlm studio delete <notebook-id> <artifact-id> --confirm

# Step 4: Delete specific source (after user confirms)
# AI: "Are you sure you want to delete source X?"
nlm source delete <source-id> --confirm

# Step 5: Delete entire notebook (after user confirms)
# AI: "This will permanently delete notebook X and ALL its contents. Proceed?"
nlm notebook delete <notebook-id> --confirm

# Step 6: Clean up aliases
nlm alias delete <alias-name>
```

---

## Workflow 14: Scripting and Automation

### Goal: Automate repetitive tasks

```bash
#!/bin/bash
# Example: Daily research automation

# Configuration
NOTEBOOK_ID="abc123..."
QUERY="latest AI news $(date +%Y-%m-%d)"

# Ensure authenticated
nlm login --check || nlm login

# Start fast research
nlm research start "$QUERY" --notebook-id $NOTEBOOK_ID --mode fast

# Wait for completion
nlm research status $NOTEBOOK_ID --max-wait 60

# Get task ID from status
TASK_ID=$(nlm research status $NOTEBOOK_ID --max-wait 0 2>&1 | grep -oE 'task_id=[^ ]+' | cut -d= -f2)

# Import all sources
nlm research import $NOTEBOOK_ID $TASK_ID

# Generate brief audio summary
nlm audio create $NOTEBOOK_ID --format brief --length short --confirm

# Check status
nlm studio status $NOTEBOOK_ID
```

---

## Rate Limiting Guidelines

To avoid hitting API rate limits:

| Operation Type | Recommended Delay |
|---------------|-------------------|
| Source add | 2 seconds |
| Content generation | 5 seconds |
| Research operations | 2 seconds |
| Query operations | 2 seconds |
| Batch operations | 10 seconds |

**Daily limits (free tier):** ~50 queries/operations per day.

---

## Error Recovery Patterns

### Pattern: Re-authentication on failure

```bash
# Try command, re-auth if fails
nlm notebook list || (nlm login && nlm notebook list)
```

### Pattern: Retry with backoff

```bash
retry_command() {
    local max=3 delay=5
    for ((i=1; i<=max; i++)); do
        "$@" && return 0
        sleep $delay
        delay=$((delay * 2))
    done
    return 1
}

retry_command nlm audio create $NOTEBOOK_ID --confirm
```

### Pattern: Check before generate

```bash
# Ensure sources exist before generating
SOURCE_COUNT=$(nlm source list $NOTEBOOK_ID --quiet | wc -l)
if [ "$SOURCE_COUNT" -gt 0 ]; then
    nlm audio create $NOTEBOOK_ID --confirm
else
    echo "Error: No sources in notebook"
fi
```
