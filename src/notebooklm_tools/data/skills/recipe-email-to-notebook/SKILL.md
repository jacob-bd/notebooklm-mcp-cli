---
name: recipe-email-to-notebook
description: "Save email content to NotebookLM for AI-powered synthesis. Works with gws gmail read to extract email text, add as a source, and query the notebook."
metadata:
  openclaw:
    category: "recipe"
    domain: "productivity"
    requires:
      bins: ["nlm"]
      skills: ["nlm-notebook", "nlm-source", "gws-gmail-read"]
---

# Recipe: Email → NotebookLM

Save emails to NotebookLM for AI synthesis, research, and Q&A.

## Prerequisites

- `nlm` installed and authenticated (`nlm login`)
- `gws` CLI installed and authenticated (for email reading)
- OR: email content already available as text

## Pattern A: From gws gmail (with gws CLI)

### 1. Read email(s) with gws

```bash
# List recent emails matching a filter
gws gmail list --query "subject:quarterly report" --max 10

# Read a specific email
gws gmail read <message-id> --format text > email.txt

# Or pipe directly
gws gmail read <message-id> --format text | \
    nlm source add <nb-id> --text "$(cat)" --title "Email: Subject"
```

### 2. Add email to notebook

```bash
# From file
nlm source add <nb-id> --text "$(cat email.txt)" --title "Q4 Report Email"

# From inline text
nlm source add <nb-id> \
    --text "From: ceo@company.com
Subject: Q4 Results

The Q4 results show 30% growth..." \
    --title "CEO Q4 Email"
```

### 3. Query the notebook

```bash
nlm notebook query <nb-id> "What are the key decisions from these emails?"
nlm notebook query <nb-id> "Summarize the action items"
nlm notebook query <nb-id> "What metrics were mentioned?"
```

## Pattern B: Forward Thread to Notebook

```bash
# Save a whole email thread
gws gmail read <thread-id> --format text --thread > thread.txt
nlm source add <nb-id> --text "$(cat thread.txt)" --title "Thread: Decision on X"

# Synthesize
nlm notebook query <nb-id> "What was decided and by whom?"
```

## Pattern C: Bulk Email Ingestion

```bash
NB_ID="your-notebook-id"

# Add multiple emails as separate sources
while IFS= read -r msg_id; do
    subject=$(gws gmail get "$msg_id" --field subject)
    body=$(gws gmail read "$msg_id" --format text)
    nlm source add "$NB_ID" --text "$body" --title "Email: $subject"
    sleep 2
done < message_ids.txt

echo "Added $(nlm source list $NB_ID --quiet | wc -l) sources"
```

## Pattern D: Generate Report from Emails

```bash
NB_ID="emails-notebook"

# After adding email sources...
nlm report create "$NB_ID" --format "Briefing Doc" \
    --custom-prompt "Summarize key decisions, action items, and follow-ups from these emails" \
    --confirm

nlm studio status "$NB_ID"
nlm download report "$NB_ID" --output email-summary.md
```

## Pattern E: No gws CLI (Manual)

If `gws` is not available, paste email content manually:

```bash
# Inline paste
nlm source add <nb-id> \
    --text "PASTE EMAIL CONTENT HERE" \
    --title "Email: <Subject>"
```

Or use the MCP tool:
```python
source_add(
    notebook_id="...",
    source_type="text",
    text="<email content>",
    title="Email: <subject>"
)
```

## Use Cases

| Use Case | Command |
|----------|---------|
| Summarize thread | `nlm notebook query <nb-id> "Summarize this thread"` |
| Extract action items | `nlm notebook query <nb-id> "What are the action items?"` |
| Find decisions | `nlm notebook query <nb-id> "What decisions were made?"` |
| Create briefing | `nlm report create <nb-id> --format "Briefing Doc" --confirm` |
| Generate follow-up notes | `nlm note create <nb-id> "$(nlm notebook query <nb-id> 'Key points')"` |

## gws Gmail → NotebookLM → gws Chat (Full Loop)

```bash
# 1. Read email
gws gmail read <msg-id> --format text > email.txt

# 2. Add to notebook
nlm source add <nb-id> --text "$(cat email.txt)" --title "Email Thread"

# 3. Query and summarize
SUMMARY=$(nlm notebook query <nb-id> "Summarize key points in 3 bullets")

# 4. Send summary to Google Chat
gws chat send --space <space-id> --text "$SUMMARY"
```
