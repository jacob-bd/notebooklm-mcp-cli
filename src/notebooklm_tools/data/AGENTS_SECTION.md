<!-- nlm-skill-start -->
<!-- nlm-version: 0.5.26 -->
## NLM - NotebookLM CLI Expert

**Triggers:** "nlm", "notebooklm", "notebook lm", "podcast", "audio overview", "research"

Expert assistant for Google NotebookLM automation via CLI. Use when users want to create/manage notebooks, add sources (URLs, YouTube, text, Google Drive), generate AI content (podcasts, reports, quizzes, flashcards, mind maps, slides, infographics, videos, data tables), conduct research, or chat with sources.

### Quick Reference

```bash
nlm login                    # Authenticate with NotebookLM
nlm notebook create "Title"  # Create notebook
nlm source add <id> --url "https://..."  # Add web source
nlm audio create <id> --confirm          # Generate podcast
nlm research start "query" --notebook-id <id>  # Discover sources
```

### Critical Rules

1. **Always authenticate first**: `nlm login` before operations
2. **Sessions expire in ~20 minutes**: Re-run `nlm login` if auth fails
3. **`--confirm` required** for generation/delete commands
4. **Capture IDs from output** for subsequent operations
5. **Use `nlm alias set`** to simplify UUIDs
6. **⚠️ NEVER auto-delete**: Always ask user before `nlm delete`
7. **⚠️ NEVER use `nlm chat start`**: It's an interactive REPL. Use `nlm notebook query` instead

### Common Workflows

**Research → Podcast Pipeline:**
```bash
nlm notebook create "AI Research"
nlm alias set ai <notebook-id>
nlm research start "AI trends" --notebook-id ai --mode deep
nlm research status ai
nlm research import ai <task-id>
nlm audio create ai --confirm
nlm studio status ai
```

**Quick Content Ingestion:**
```bash
nlm source add <id> --url "https://example.com"
nlm source add <id> --text "Notes..." --title "My Notes"
nlm source add <id> --drive <doc-id>
```

**Study Materials:**
```bash
nlm report create <id> --format "Study Guide" --confirm
nlm quiz create <id> --count 10 --focus "Key Concepts" --confirm
nlm flashcards create <id> --focus "Vocabulary" --confirm
```

**Multi-Notebook Operations:**
```bash
nlm tag add <id> --tags "ai,research"                     # Tag notebooks
nlm batch query "Summarize" --tags "ai"                   # Batch query by tag
nlm cross query "Compare approaches" --notebooks "id1,id2"  # Cross-notebook query
nlm pipeline run <id> ingest-and-podcast --url "https://..."  # Run pipeline
```

### Full Documentation

For complete command reference, troubleshooting, and workflows, install the full skill:

```bash
# Install via uv
uv tool install notebooklm-mcp-cli

# Then install/update skill for your AI tool
nlm skill install <tool>  # Install (claude-code, agents, opencode, etc)
nlm skill update <tool>   # Update existing skill
```

Or view inline: `nlm --ai`

<!-- nlm-skill-end -->
