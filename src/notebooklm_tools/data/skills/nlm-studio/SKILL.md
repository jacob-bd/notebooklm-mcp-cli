---
name: nlm-studio
description: "NotebookLM Studio — generate AI content from notebook sources: podcasts, videos, reports, quizzes, flashcards, mind maps, slides, infographics, data tables. Download or export to Google Docs/Sheets."
metadata:
  openclaw:
    category: "productivity"
    requires:
      bins: ["nlm"]
    cliHelp: "nlm studio --help"
---

# nlm studio

Generate AI-powered content artifacts from NotebookLM sources.

## See Also

- **[nlm-skill](../nlm-skill/SKILL.md)** — Full reference
- **[nlm-source](../nlm-source/SKILL.md)** — Add sources first
- **[recipe-drive-to-podcast](../recipe-drive-to-podcast/SKILL.md)** — Drive → podcast workflow
- **[recipe-research-report](../recipe-research-report/SKILL.md)** — Research → report workflow

## Artifact Types

| Type | CLI command | Description |
|------|-------------|-------------|
| Audio podcast | `nlm audio create` | Deep-dive, brief, critique, or debate |
| Video | `nlm video create` | Animated explainer or brief |
| Report | `nlm report create` | Briefing doc, study guide, blog post |
| Quiz | `nlm quiz create` | Multiple-choice questions |
| Flashcards | `nlm flashcards create` | Q&A flashcard deck |
| Mind map | `nlm mindmap create` | Concept map JSON |
| Slide deck | `nlm slides create` | Presentation slides |
| Infographic | `nlm infographic create` | Visual summary image |
| Data table | `nlm data-table create` | Structured data extraction |

> All generation commands require `--confirm` / `-y`. **Always show the user the settings and ask for confirmation before generating.**

## CLI Commands

### Audio
```bash
nlm audio create <nb-id> --confirm
nlm audio create <nb-id> --format deep_dive --length long --confirm
nlm audio create <nb-id> --format brief --focus "key topic" --confirm
# Formats: deep_dive, brief, critique, debate
# Lengths: short, default, long
```

### Video
```bash
nlm video create <nb-id> --confirm
nlm video create <nb-id> --format brief --style whiteboard --confirm
# Formats: explainer, brief
# Styles: auto_select, classic, whiteboard, kawaii, anime, watercolor,
#         retro_print, heritage, paper_craft
```

### Report
```bash
nlm report create <nb-id> --confirm
nlm report create <nb-id> --format "Study Guide" --confirm
nlm report create <nb-id> --format "Create Your Own" --prompt "Custom instructions..." --confirm
# Formats: "Briefing Doc", "Study Guide", "Blog Post", "Create Your Own"
```

### Quiz & Flashcards
```bash
nlm quiz create <nb-id> --count 10 --difficulty 3 --confirm
nlm quiz create <nb-id> --focus "Focus on key concepts" --confirm
# Difficulty: 1-5 (1=easy, 5=hard)

nlm flashcards create <nb-id> --difficulty medium --confirm
nlm flashcards create <nb-id> --focus "Core definitions" --confirm
# Difficulty: easy, medium, hard
```

### Visual Content
```bash
# Mind Map
nlm mindmap create <nb-id> --confirm
nlm mindmap create <nb-id> --title "Topic Overview" --confirm

# Slides
nlm slides create <nb-id> --confirm
nlm slides create <nb-id> --format presenter --length short --confirm
# Formats: detailed, presenter | Lengths: short, default

# Revise existing slide deck (creates NEW deck, original unchanged)
nlm slides revise <artifact-id> --slide '1 Make the title larger' --confirm
nlm slides revise <artifact-id> --slide '3 Add more detail' --slide '5 Simplify' --confirm

# Infographic
nlm infographic create <nb-id> --confirm
nlm infographic create <nb-id> --orientation portrait --detail detailed --style professional --confirm
# Orientations: landscape, portrait, square
# Detail: concise, standard, detailed
# Styles: auto_select, sketch_note, professional, bento_grid, editorial,
#         instructional, bricks, clay, anime, kawaii, scientific
```

### Data Table
```bash
# Description is REQUIRED as a positional argument
nlm data-table create <nb-id> "Extract all dates and events" --confirm
nlm data-table create <nb-id> "List all people, their roles, and affiliations" --confirm
```

## Status and Download

```bash
# Check status of all artifacts
nlm studio status <nb-id>             # Summary table
nlm studio status <nb-id> --full      # Includes custom prompts
nlm studio status <nb-id> --json      # JSON output

# Status values: completed ✓, in_progress ●, failed ✗

# Download artifacts
nlm download audio <nb-id> --output podcast.mp3
nlm download video <nb-id> --output video.mp4
nlm download report <nb-id> --output report.md
nlm download slide-deck <nb-id> --output slides.pdf
nlm download slide-deck <nb-id> --output slides.pptx --format pptx
nlm download quiz <nb-id> --output quiz.json --format json

# Export to Google Workspace
nlm export sheets <nb-id> <artifact-id> --title "My Data"  # → Google Sheets
nlm export docs <nb-id> <artifact-id> --title "My Report"  # → Google Docs

# Rename artifact
nlm studio rename <artifact-id> "New Title"
nlm rename studio <artifact-id> "New Title"  # verb-first

# Delete artifact (IRREVERSIBLE)
nlm studio delete <nb-id> <artifact-id> --confirm
```

## MCP Tools

Use `studio_create` with `artifact_type` and type-specific options. All require `confirm=True`.

```python
# Audio
studio_create(notebook_id="...", artifact_type="audio",
              audio_format="deep_dive", audio_length="long", confirm=True)

# Report
studio_create(notebook_id="...", artifact_type="report",
              report_format="Study Guide", confirm=True)

# Data table (description required)
studio_create(notebook_id="...", artifact_type="data_table",
              description="Extract all dates and events", confirm=True)

# Check status / list artifacts
studio_status(notebook_id="...")

# Download
download_artifact(notebook_id="...", artifact_type="audio",
                  output_path="/tmp/podcast.mp3")

# Export
export_artifact(notebook_id="...", artifact_id="...", export_type="docs",
                title="My Report")

# Delete
studio_delete(notebook_id="...", artifact_id="...", confirm=True)

# Revise slides (creates new artifact)
studio_revise(artifact_id="...", slide_instructions={"1": "Make title larger"},
              confirm=True)
```

## Common Options (All Artifact Types)

| Option | CLI | MCP | Description |
|--------|-----|-----|-------------|
| Limit to sources | `--source-ids id1,id2` | `source_ids` | Only use these sources |
| Language | `--language en` | `language` | BCP-47 code (en, es, fr, de, ja) |
| Focus | `--focus "topic"` | `focus_prompt` | Guide generation focus |

## Generation Workflow

```bash
# 1. Generate artifact
nlm audio create <nb-id> --format deep_dive --confirm

# 2. Poll until complete (~2-10 minutes for audio)
nlm studio status <nb-id>

# 3. Download when completed
nlm download audio <nb-id> --output podcast.mp3
```

Poll `studio status` every 30s for long-running generation. Slides and infographics are fastest (< 1min); audio and video take 2-10 minutes.
