---
name: recipe-chat-send-summary
description: "Query a NotebookLM notebook and send the AI-generated summary to a Google Chat space. Requires gws-chat-send skill and correct Google Chat OAuth scopes."
metadata:
  openclaw:
    category: "recipe"
    domain: "communication"
    requires:
      bins: ["nlm", "gws"]
      skills: ["nlm-notebook", "gws-chat-send"]
---

# Recipe: NotebookLM Query → Google Chat

Query a notebook and post the answer to a Google Chat space.

## Prerequisites

- `nlm` installed and authenticated (`nlm login`)
- `gws` CLI installed and authenticated with Google Chat scopes

## Google Chat OAuth Scope Note

> **Important:** Use `chat.spaces` and `chat.messages.create` scopes — NOT `chat.bot`.
>
> `chat.bot` is for service account-based Chat Apps only. For user-delegated access (sending messages as yourself), request these scopes in your OAuth client:
> - `https://www.googleapis.com/auth/chat.spaces`
> - `https://www.googleapis.com/auth/chat.messages.create`
>
> Configure these in Google Cloud Console → APIs & Services → OAuth consent screen → Scopes.

## Steps

### 1. Query NotebookLM

```bash
# One-shot question
ANSWER=$(nlm notebook query <nb-id> "What are the key findings?" --quiet)

# Or with a specific focus
ANSWER=$(nlm notebook query <nb-id> "Summarize the action items from today's sources")
```

### 2. Send to Google Chat

```bash
# Send to a space
gws chat send --space <space-id> --text "$ANSWER"

# Or with formatting
gws chat send --space <space-id> --text "*NotebookLM Summary*\n\n$ANSWER"
```

### 3. Full workflow example

```bash
#!/usr/bin/env bash
NB_ID="${1:?Usage: $0 <notebook-id> <space-id> <question>}"
SPACE_ID="${2:?}"
QUESTION="${3:-What are the key points?}"

echo "Querying NotebookLM..."
ANSWER=$(nlm notebook query "$NB_ID" "$QUESTION")

echo "Sending to Google Chat space: $SPACE_ID"
gws chat send --space "$SPACE_ID" \
    --text "*Q: $QUESTION*\n\n$ANSWER\n\n_via NotebookLM_"

echo "Done."
```

## Scheduled Daily Digest

```bash
# cron: 0 9 * * 1-5 — run every weekday at 9am
#!/usr/bin/env bash
NB_ID="weekly-digest-notebook"
SPACE_ID="spaces/AAAAxxxxxxx"

SUMMARY=$(nlm notebook query "$NB_ID" \
    "Summarize the key updates from recent sources in 5 bullet points")

gws chat send --space "$SPACE_ID" \
    --text "*Daily Digest — $(date +%A, %B %d)*\n\n$SUMMARY"
```

## MCP + gws combined

If using MCP for NotebookLM and CLI for Chat:

```python
# Query via MCP
result = notebook_query(
    notebook_id="...",
    query="What are this week's key findings?"
)
answer = result["answer"]

# Send via gws CLI
import subprocess
subprocess.run(["gws", "chat", "send", "--space", space_id, "--text", answer])
```

## Related Recipes

- **[recipe-email-to-notebook](../recipe-email-to-notebook/SKILL.md)** — Ingest email content into a notebook first
- **[recipe-research-report](../recipe-research-report/SKILL.md)** — Research a topic and generate a report before sending
