# NotebookLM MCP Weekend Roadmap
**Created:** 2026-01-02 (Friday)
**Status:** Ideas captured, ready to build!

## The Vision
NotebookLM as a **third memory tier** in Jeremy's AI ecosystem:
1. **SADB Provenance Memories** - Full context, traceable to conversations
2. **Certified Fact Table** - Verified, categorized quick-lookup facts  
3. **Curated NotebookLM** - Rich queryable knowledge bases, mind maps, audio

## Weekend Project Ideas

### 1. Master README Notebook
- Aggregate READMEs from all 60+ repos
- Single queryable knowledge base for "what does project X do?"
- Could auto-update when READMEs change

### 2. Deep-Dive Notebooks (per major project)
- Brain on Tap (already has 17 sources!)
- SADB/C003 pipeline
- Mission Control
- Each gets its own curated, detailed notebook

### 3. Memory Integration Pattern
- When Claude queries, pull from multiple tiers:
  - Quick facts from SADB fact table
  - Rich context from NotebookLM notebooks
  - Provenance trail from conversation memories
- Return unified, sourced answers

### 4. Automated Research Pipeline (ambitious!)
- Each repo has a "MYSTERY.md" - the core problem being solved
- Generate research questions: "If we knew X, we could improve Y"
- Use NotebookLM's `research_start` to find answers
- Human-in-the-loop to validate and integrate findings
- Could run on schedule or on-demand

## Tools We Have (31 total!)

### Content Creation
- `audio_overview_create` - Podcasts!
- `video_overview_create` - Video explainers
- `infographic_create` - Visual summaries
- `slide_deck_create` - Presentations
- `mind_map_create` - Already tested, works great

### Research
- `research_start` - Web or Drive discovery
- `research_status` - Poll progress
- `research_import` - Bring sources into notebook

### Queries
- `notebook_query` - Ask questions, get cited answers
- `notebook_describe` - AI summary of entire notebook

## Questions for Weekend Planning
- How to keep notebooks in sync with repo changes?
- Which repos deserve their own notebook vs. aggregated?
- How to integrate NotebookLM queries into SADB retrieval?
- What's the right human-in-the-loop cadence for research?

## Next Session
Pick ONE thing to build end-to-end, then expand from there.
Candidate: Master README notebook with all 60+ repo docs.

---
*Created by Claude during the initial setup session*
