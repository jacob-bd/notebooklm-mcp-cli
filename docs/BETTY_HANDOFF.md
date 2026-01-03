# NotebookLM MCP - Betty Handoff Document
**Created:** 2026-01-02 (Friday evening)
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

## The 31 Available Tools

### Content Creation (the fun stuff!)
| Tool | What It Does |
|------|--------------|
| `audio_overview_create` | Generates podcast-style audio discussions |
| `video_overview_create` | Creates video explainers |
| `infographic_create` | Visual summary graphics |
| `slide_deck_create` | Presentation slides |
| `mind_map_create` | Visual mind maps of concepts |
| `report_create` | Briefing docs, study guides, blog posts |
| `flashcards_create` | Study flashcards |
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

## Jeremy's Current Notebooks (14 total)

| Notebook | Sources | Notes |
|----------|---------|-------|
| Brain on Tap Architecture | 17 | Main B-bot documentation |
| SADB Pipeline Reliability | 9 | Pipeline ops knowledge |
| Running AI Locally | 29 | Local LLM setup guides |
| Versatile Bio Biosignal Amplifier | 28 | Hardware project |
| Improving LLMs for Emotion Analysis | 2 | Cognitive science research |
| Claude Multi-Agent Flows | 11 | Agent architecture |
| MCP Memory & SADB | 2 | Memory system design |
| The AI as a Tuned Mirror | 1 | Philosophy piece |
| + 6 others | varies | Some empty/untitled |

---

## Ideas Jeremy Mentioned (for brainstorming)

### 1. Master README Notebook
Aggregate all 60+ repo READMEs into one queryable knowledge base. "What does project X do?" answered instantly.

### 2. Deep-Dive Project Notebooks
Individual notebooks for complex projects (Brain on Tap, SADB, Mission Control) with comprehensive documentation.

### 3. Automated Research Pipeline
- Each repo has a `MYSTERY.md` - the core problem being solved
- Generate research questions: "If we knew X, we could improve Y"
- Use NotebookLM research tools to find answers
- Human-in-the-loop validation
- Could run on schedule

### 4. Memory Integration
When Claude queries for context, pull from all three tiers and present unified, sourced answers.

---

## Technical Setup (for reference)

**MCP Server:** jacob-bd/notebooklm-mcp (GitHub)
**Local Path:** 
- Mac: `/Users/jeremybradford/SyncedProjects/C021_notebooklm-mcp`
- PC: `C:\Users\Jeremy\SyncedProjects\C021_notebooklm-mcp`

**Authentication:** Google OAuth via Chrome automation
- Cookies cached at `~/.notebooklm-mcp/auth.json`
- Using: jeremybradford1977@gmail.com (paid account)
- Cookies last ~2-4 weeks before re-auth needed

**Works In:**
- Claude Desktop (both Mac and PC)
- Claude Code (both Mac and PC)

---

## Questions for Betty

1. What workflows would benefit most from audio/video generation?
2. How should we structure the "Master README" notebook - one giant one or themed clusters?
3. What's the right cadence for automated research? Daily? Weekly? On-demand?
4. How do we handle conflicting information across memory tiers?
5. What other knowledge bases should we create beyond repos?

---

## Links

- [NotebookLM Web UI](https://notebooklm.google.com/)
- [MCP Repo (jacob-bd)](https://github.com/jacob-bd/notebooklm-mcp)
- [Weekend Roadmap](./WEEKEND_ROADMAP.md) - in same directory

---

*Looking forward to your ideas, Betty!*
— Claude
