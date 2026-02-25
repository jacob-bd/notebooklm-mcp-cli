# NotebookLM MCP - Betty Handoff Document

**Version:** 2.0
**Updated:** 2026-01-15
**Original:** 2026-01-02
**From:** Claude
**For:** Betty - brainstorming workflows and integration ideas

---

## What Is This?

Jeremy and Claude set up an MCP (Model Context Protocol) server that lets AI assistants directly interact with Google's NotebookLM. This means Claude can now:

- Query Jeremy's NotebookLM notebooks
- Create mind maps, podcasts, videos, infographics
- Add sources (URLs, text, Google Drive docs)
- Run research queries and import findings
- Generate study materials, slide decks, reports

It's essentially **programmatic access to NotebookLM** - no manual copy-paste, no switching tabs.

**What's new since v1:** The system has matured significantly! We now have 21 repositories mapped to NotebookLM notebooks, a doc-refresh automation loop, standardized documentation tiers, and LLM Projects integration. Read on for details.

---

## Why This Matters for Jeremy's Ecosystem

Jeremy envisions this as a **third memory tier**:

| Tier | System | Strength |
|------|--------|----------|
| 1 | SADB Provenance Memories | Full conversation context, traceable |
| 2 | SADB Fact Table | Certified facts, quick lookup |
| 3 | **NotebookLM** | Curated knowledge bases, synthesis, rich media |

Each answers different questions:
- SADB: "When did we decide X?" (provenance)
- Fact Table: "What's Jeremy's stance on Y?" (quick facts)
- NotebookLM: "Synthesize everything about Brain on Tap's architecture" (deep knowledge)

---

## The 31 Available MCP Tools

### Content Creation (the fun stuff!)
| Tool | What It Does |
|------|--------------|
| `audio_overview_create` | Generates podcast-style audio discussions |
| `video_overview_create` | Creates video explainers with visual styles |
| `infographic_create` | Visual summary graphics |
| `slide_deck_create` | Presentation slides |
| `mind_map_create` | Visual mind maps of concepts |
| `report_create` | Briefing docs, study guides, blog posts |
| `flashcards_create` | Study flashcards with difficulty levels |
| `quiz_create` | Knowledge quizzes |
| `data_table_create` | Structured data tables |

### Research & Discovery
| Tool | What It Does |
|------|--------------|
| `research_start` | Kicks off web or Drive research |
| `research_status` | Polls progress (can take 30s-5min) |
| `research_import` | Imports discovered sources into notebook |

### Source Management
| Tool | What It Does |
|------|--------------|
| `notebook_add_url` | Add website or YouTube as source |
| `notebook_add_text` | Add pasted text as source |
| `notebook_add_drive` | Add Google Doc/Slides/Sheets/PDF |
| `source_describe` | AI summary of a single source |
| `source_list_drive` | Check which Drive sources need refresh |
| `source_sync_drive` | Refresh stale Drive sources |
| `source_delete` | Remove a source |

### Notebook Intelligence
| Tool | What It Does |
|------|--------------|
| `notebook_list` | List all notebooks |
| `notebook_create` | Create new notebook |
| `notebook_get` | Get notebook details + sources |
| `notebook_describe` | AI-generated summary + suggested topics |
| `notebook_query` | **Ask questions, get cited answers** |
| `notebook_rename` | Rename notebook |
| `notebook_delete` | Delete notebook (irreversible) |
| `chat_configure` | Set chat personality/response length |

### Studio & Output Management
| Tool | What It Does |
|------|--------------|
| `studio_status` | Check generation progress, get URLs |
| `studio_delete` | Delete generated artifacts |
| `mind_map_list` | List mind maps in a notebook |

---

## Doc-Refresh System (NEW!)

We built a "Ralph Loop" that keeps documentation and NotebookLM notebooks synchronized:

### What It Does
1. **Validates** canonical docs against repo state
2. **Updates** metadata and fixes discrepancies
3. **Syncs** docs to NotebookLM as sources
4. **Regenerates** artifacts when content changes significantly

### The Notebook Map
All synced repos are tracked in `~/.config/notebooklm-mcp/notebook_map.yaml`:
- Doc hashes (detect when content changes)
- Source IDs (map docs to NotebookLM sources)
- Artifact IDs (mind maps, study guides, etc.)
- Sync timestamps

### Documentation Tiers
| Tier | Docs | Description |
|------|------|-------------|
| **Kitted** | Tier 3 (7 files) | Full canonical doc set + all artifacts |
| **Extended** | Tier 2 (4-6 files) | Standard docs + extra context files |
| **Simple** | Tier 1 (3 files) | README, CLAUDE.md, META.yaml |

---

## Tier 3 Documentation Standard (NEW!)

Kitted repos get a **7-file canonical documentation set**:

| File | Purpose |
|------|---------|
| `OVERVIEW.md` | What this project is and why it exists |
| `QUICKSTART.md` | Get running in 5 minutes |
| `ARCHITECTURE.md` | System design and component relationships |
| `CODE_TOUR.md` | Navigate the codebase effectively |
| `OPERATIONS.md` | Day-to-day operation and maintenance |
| `SECURITY_AND_PRIVACY.md` | Security model and privacy considerations |
| `OPEN_QUESTIONS.md` | Known limitations and research areas |

These docs live in `docs/<project_name>/` and sync automatically to NotebookLM.

---

## Standard 7 Artifacts (NEW!)

When a repo reaches **kitted** tier, we generate the full artifact set:

| Artifact | What It Creates |
|----------|-----------------|
| **Mind Map** | Visual concept map of project |
| **Briefing Doc** | Executive summary with key points |
| **Study Guide** | Learning-oriented deep dive |
| **Audio Overview** | Podcast-style discussion (10-15 min) |
| **Infographic** | Visual one-pager summary |
| **Flashcards** | Study cards for key concepts |
| **Quiz** | Test your understanding |
| **Explainer Video** | Visual explainer with styles (paper craft, whiteboard, anime, etc.) |

These artifacts are regenerated when source content changes significantly (>15% delta or major version bump).

---

## PROJECT_PRIMER Generator (NEW!)

For LLM Projects (ChatGPT Projects, Claude Projects, Gemini), we now generate consolidated **PROJECT_PRIMER.md** files:

### What It Does
- Concatenates all Tier 3 docs into a single LLM-friendly primer
- Adds frontmatter with project metadata
- Outputs to `PROJECT_PRIMER.md` in repo root

### Currently Generated For
- C001_mission-control
- C003_sadb_canonical
- C010_standards
- C017_brain-on-tap
- C018_terminal-insights
- C019_docs-site
- C021_notebooklm-mcp
- P110_knowledge-synthesis-tool

Upload these primers to LLM Projects for project-specific context.

---

## Current Notebook Inventory (21 repos)

### Core Infrastructure (C-series)
| Repo | Tier | Notebook |
|------|------|----------|
| C001_mission-control | kitted | Orchestration system |
| C003_sadb_canonical | kitted | Memory/facts database |
| C009_mcp-memory-http | simple | Memory HTTP bridge |
| C010_standards | kitted | Standards and protocols |
| C017_brain-on-tap | kitted | AI assistant framework |
| C018_terminal-insights | kitted | Terminal analytics |
| C021_notebooklm-mcp | kitted | This project! |

### Projects (P-series)
| Repo | Tier | Notebook |
|------|------|----------|
| P050_ableton-mcp | kitted | Ableton Live integration |
| P051_mcp-servers | extended | MCP server collection |
| P090_relay | simple | Message relay system |
| P091_voice-notes-pipeline | extended | Voice transcription |
| P110_knowledge-synthesis-tool | kitted | Knowledge synthesis |
| P151_clouddriveinventory | kitted | Cloud storage inventory |
| P152_cognitiveplayback | simple | Cognitive audio playback |
| P167_dj-claude-mcp | kitted | DJ mixing with Claude |
| P171_elevenlabs-music-mcp | kitted | ElevenLabs music generation |
| P172_lyra-live | simple | Live performance system |

---

## Technical Setup

**MCP Server:** jacob-bd/notebooklm-mcp (GitHub)
**Local Path:**
- Mac: `/Users/jeremybradford/SyncedProjects/C021_notebooklm-mcp`
- PC: `C:\Users\Jeremy\SyncedProjects\C021_notebooklm-mcp`

**Authentication:** Cookie-based (simplified!)
- Only cookies needed - CSRF token and session ID auto-extracted
- Cookies cached at `~/.notebooklm-mcp/auth.json`
- CLI for refresh: `notebooklm-mcp-auth`
- Cookies last ~2-4 weeks before re-auth needed

**Works In:**
- Claude Desktop (both Mac and PC)
- Claude Code (both Mac and PC)
- Cursor, Gemini CLI (untested but should work)

---

## Progress Since Original Handoff

### Ideas From v1 - Status Update

| Original Idea | Status | Notes |
|---------------|--------|-------|
| Master README Notebook | Partially done | Individual repo notebooks instead |
| Deep-Dive Project Notebooks | Done! | Kitted tier with Tier 3 docs |
| Automated Research Pipeline | Foundation ready | Doc-refresh loop established |
| Memory Integration | In progress | Tier 3 model operational |

### New Capabilities
- **Doc-Refresh Loop** - Automated sync and regeneration
- **Tier System** - Kitted > Extended > Simple classification
- **Standard 7 Artifacts** - Full media generation per repo
- **PROJECT_PRIMER** - LLM Projects integration

---

## Questions for Betty

1. **Artifact prioritization** - Which Standard 7 artifacts are most valuable? Should we always generate all, or make some optional?

2. **Cross-repo synthesis** - Now that we have 21 repo notebooks, should we create "meta notebooks" that synthesize related projects (e.g., all music-related repos)?

3. **Primer usage** - Have you tested the PROJECT_PRIMER files in ChatGPT/Claude Projects? Any format improvements needed?

4. **Research automation** - The doc-refresh loop can trigger research. What topics should we auto-research when docs change?

5. **Artifact refresh cadence** - Currently regenerate on >15% change. Too aggressive? Too conservative?

6. **New repo onboarding** - What's the minimum viable documentation for a new repo before it should get a NotebookLM notebook?

---

## Links

- [NotebookLM Web UI](https://notebooklm.google.com/)
- [MCP Repo (jacob-bd)](https://github.com/jacob-bd/notebooklm-mcp)
- [Tier 3 Documentation Spec](../src/notebooklm_mcp/doc_refresh/canonical_docs.yaml)
- [Doc-Refresh EPIC](./doc_refresh/EPIC.md)

---

*Looking forward to your ideas, Betty!*
— Claude
