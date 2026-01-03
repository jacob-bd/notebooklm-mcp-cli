# NotebookLM Integration Pattern

**Created**: 2026-01-02
**Verified by**: Thin-slice receipt `notebooklm_thinslice_2026-01-02.md`

---

## Three-Tier Memory Architecture

NotebookLM serves as **Tier 3** in Jeremy's memory hierarchy:

| Tier | System | Strength | When to Use |
|------|--------|----------|-------------|
| 1 | SADB Provenance | Full context, traceable to conversations | "When did we decide X?" |
| 2 | SADB Fact Table | Certified facts, quick lookup | "What's Jeremy's stance on Y?" |
| 3 | **NotebookLM** | Curated knowledge, synthesis, rich media | "Synthesize everything about Z" |

### What Belongs in NotebookLM (Tier 3)

**Good fit:**
- Documentation aggregation (READMEs across repos)
- Research synthesis (web/Drive discovery)
- Rich media generation (audio, video, infographics)
- Curated knowledge bases by topic
- External sources (URLs, YouTube, Google Docs)

**Not a fit:**
- Ephemeral conversation context (use SADB Tier 1)
- Quick biographical facts (use SADB Tier 2)
- Real-time data (NotebookLM is static after ingest)

---

## Sync Strategy

**Current approach: Manual cadence**

NotebookLM sources are static once ingested. Keep notebooks fresh by:

1. **Weekly review** - Check `source_list_drive` for stale Drive sources
2. **On-demand sync** - After major doc updates, run `source_sync_drive`
3. **Version in title** - Use "v0", "v1" etc. for major re-builds

**Future consideration**: Automated re-ingest pipeline when source docs change.

---

## Conflict Policy

When information differs across tiers:

| Conflict Type | Resolution |
|---------------|------------|
| SADB vs NotebookLM | **SADB wins** - it has provenance |
| Fact Table vs NotebookLM | **Fact Table wins** - it's certified |
| Multiple NotebookLM notebooks | Newer modified_at wins, or ask user |

**Rationale**: SADB has attribution to original conversations. NotebookLM is synthesis which may lose nuance.

---

## Safety Notes

### Cookie Authentication
- Cookies expire every **2-4 weeks**
- Run `notebooklm-mcp-auth` when you see auth errors
- Never commit `~/.notebooklm-mcp/auth.json` (contains session data)

### Experimental Scope
- Uses **reverse-engineered APIs** - may break without notice
- Free tier has **~50 queries/day** limit
- Not suitable for production/critical workflows

### When to Disable
- **High context sessions** - 31 tools consume significant context
- Use `@notebooklm-mcp` toggle in Claude Code or `/mcp` command
- Comment out in config when not actively using

---

## Verification Checklist

Minimal tool calls to verify integration is working:

```
1. notebook_list
   - Expect: status=success, count > 0
   - If auth error: run notebooklm-mcp-auth

2. notebook_create (title="Test Notebook")
   - Capture: notebook_id

3. notebook_add_text (notebook_id, text="test content", title="Test Source")
   - Capture: source_id

4. notebook_query (notebook_id, query="What is in this notebook?")
   - Expect: answer with citations [1], [2], etc.
   - Capture: conversation_id

5. mind_map_create (notebook_id, title="Test Mind Map", confirm=true)
   - Capture: mind_map_id

6. notebook_delete (notebook_id, confirm=true)
   - Cleanup test artifacts
```

**Capture all IDs for receipt documentation.**

---

## Thin-Slice Receipt Reference

First verified integration: `docs/receipts/notebooklm_thinslice_2026-01-02.md`

| Artifact | ID |
|----------|-----|
| Notebook | `d8554b52-ed73-4503-8430-a6f4872639e1` |
| Source | `eb542cb5-dac4-4d35-b0e6-992cb24ac36e` |
| Conversation | `688304c9-de9f-4e58-826a-01543fef925d` |
| Mind Map | `0ab18908-5364-4d9a-b6d8-ef607403d210` |

---

## Related Documentation

- [API_REFERENCE.md](./API_REFERENCE.md) - Internal API details
- [MCP_TEST_PLAN.md](./MCP_TEST_PLAN.md) - Full test coverage
- [AUTHENTICATION.md](./AUTHENTICATION.md) - Auth troubleshooting
