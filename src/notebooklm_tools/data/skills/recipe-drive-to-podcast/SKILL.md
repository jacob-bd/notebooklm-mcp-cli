---
name: recipe-drive-to-podcast
description: "Turn Google Drive documents into a NotebookLM audio podcast. Adds Drive sources to a notebook, generates a deep-dive audio overview, and downloads the MP3."
metadata:
  openclaw:
    category: "recipe"
    domain: "content-creation"
    requires:
      bins: ["nlm"]
      skills: ["nlm-notebook", "nlm-source", "nlm-studio"]
---

# Recipe: Google Drive → Podcast

Turn one or more Google Drive documents into a NotebookLM audio podcast.

## Prerequisites

- `nlm` installed and authenticated (`nlm login`)
- Google Drive document IDs ready (from the URL: `docs.google.com/document/d/<ID>/`)

## Steps

### 1. Create (or select) a notebook

```bash
# Create new
NB_ID=$(nlm notebook create "Podcast: Topic Name" --quiet)

# Or use existing
NB_ID=$(nlm notebook list --quiet | head -1)  # First notebook
nlm alias set podcast $NB_ID                  # Optional: set alias
```

### 2. Add Google Drive sources

```bash
# Add a Google Doc
nlm source add $NB_ID --drive 1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms --type doc

# Add multiple sources (pause between to avoid rate limits)
for DOC_ID in "1abc..." "1def..." "1ghi..."; do
    nlm source add $NB_ID --drive "$DOC_ID"
    sleep 2
done

# Verify sources were added
nlm source list $NB_ID
```

### 3. Review sources and generate podcast

```bash
# Show what's in the notebook
nlm notebook describe $NB_ID

# Generate deep-dive podcast
nlm audio create $NB_ID --format deep_dive --length default --confirm
```

### 4. Monitor progress

```bash
# Poll until complete (~5-10 minutes for audio)
watch -n 30 "nlm studio status $NB_ID"
# Or manual polls:
nlm studio status $NB_ID
```

### 5. Download

```bash
nlm download audio $NB_ID --output podcast.mp3
echo "Podcast saved to podcast.mp3"
```

## Variations

### Brief format (2-3 minutes)

```bash
nlm audio create $NB_ID --format brief --length short --confirm
```

### Focused on specific topic

```bash
nlm audio create $NB_ID --format deep_dive --focus "focus on the Q4 results" --confirm
```

### Specific language

```bash
nlm audio create $NB_ID --format deep_dive --language es --confirm  # Spanish
```

### Use only selected sources

```bash
# Get source IDs
nlm source list $NB_ID --quiet

# Generate from specific sources only
nlm audio create $NB_ID --source-ids <id1>,<id2> --confirm
```

## MCP Version

```python
# Step 1: Create notebook
nb = notebook_create(title="Podcast: Topic Name")
nb_id = nb["notebook_id"]

# Step 2: Add Drive source
source_add(notebook_id=nb_id, source_type="drive",
           document_id="1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms",
           doc_type="doc")

# Step 3: Generate
studio_create(notebook_id=nb_id, artifact_type="audio",
              audio_format="deep_dive", audio_length="default",
              confirm=True)

# Step 4: Poll
studio_status(notebook_id=nb_id)  # Repeat until state == "completed"

# Step 5: Download
download_artifact(notebook_id=nb_id, artifact_type="audio",
                  output_path="/tmp/podcast.mp3")
```

## Syncing Updated Drive Documents

If the Drive documents are edited after adding them:

```bash
# Check freshness
nlm source stale $NB_ID

# Sync stale sources
nlm source sync $NB_ID --confirm

# Regenerate podcast
nlm audio create $NB_ID --format deep_dive --confirm
```
