# NotebookLM MCP Open Questions

**Last Updated**: 2026-01-10
**Version**: 0.1.0

Unresolved decisions, known limitations, and future considerations.

## Architecture Questions

### Official API Support

**Current State**: Using reverse-engineered internal APIs

**Question**: Should we switch when/if Google releases an official NotebookLM API?

| Option | Pros | Cons |
|--------|------|------|
| Wait for official API | Stable, supported | Unknown timeline |
| Continue reverse-engineering | Works now | May break anytime |
| Hybrid approach | Best of both | More complexity |

**Current Approach**: Continue with reverse-engineered APIs, monitor for official API announcements.

### MCP Protocol Evolution

**Current State**: Using FastMCP framework

**Question**: How should we handle MCP protocol updates?

**Considerations**:
- FastMCP may update independently
- MCP spec may evolve
- Tool schemas may need updates

**Resolution**: Track FastMCP releases, update as needed.

### Multi-Account Support

**Current State**: Single Google account at a time

**Question**: Should we support multiple NotebookLM accounts?

**Options**:
- Multiple auth.json files with switching
- Account parameter per tool call
- Keep single account focus

**Resolution**: Single account for simplicity. Users can re-auth to switch.

## Known Limitations

### API Limitations

| Limitation | Impact | Workaround |
|------------|--------|------------|
| Rate limits (~50/day free) | Restricts heavy usage | Batch operations, upgrade to Plus |
| Cookie rotation | Auth dies mid-session | Keep auth CLI ready |
| No official API | May break anytime | Monitor for changes |
| 31 tools = large context | Consumes context window | Toggle MCP on/off |

### Feature Limitations

| Limitation | Impact | Workaround |
|------------|--------|------------|
| No Notes support | Can't save chat responses | Manual copy |
| No Sharing | Can't share via MCP | Use web UI |
| No Export | Can't download content | Use web UI |
| No audio playback | URL only | Open URL in browser |

### Studio Limitations

| Limitation | Impact | Workaround |
|------------|--------|------------|
| Video sometimes fails | "No sources" error | Retry request |
| Mind maps separate | Not in studio_status | Use mind_map_list |
| Quiz shows as flashcards | Type field misleading | Track by ID |
| Generation time varies | Long waits | Poll status |

## Security Considerations

### Cookie Security

**Question**: Is local cookie storage secure enough?

**Current Approach**:
- User-only file permissions (0600)
- Dedicated Chrome profile isolation
- No logging of credentials

**Potential Improvements**:
- System keychain integration
- Encrypted storage
- Shorter cookie lifetimes

**Resolution**: Current approach sufficient for personal use.

### API Key Alternative

**Question**: Should we support API keys if Google adds them?

**Options**:
- Environment variable
- Config file
- MCP tool for setting key

**Resolution**: Implement when/if Google provides API keys.

## Feature Roadmap Questions

### Notes Feature

**Current State**: Not implemented

**Question**: Should we add Notes support?

**Considerations**:
- Would enable saving chat responses
- Requires discovering RPC ID
- May increase complexity

**Resolution**: Low priority until user demand.

### Sharing Feature

**Current State**: Not implemented

**Question**: Should we add notebook sharing?

**Considerations**:
- Enterprise use case
- Requires collaboration RPC discovery
- Security implications

**Resolution**: Out of scope for personal use focus.

### Export Feature

**Current State**: Not implemented

**Question**: Should we add content export?

**Options**:
- Direct download via API (if available)
- Screen scraping
- Manual web UI

**Resolution**: Investigate API options when time permits.

## Integration Questions

### Doc-Refresh Loop

**Current State**: Implemented in `src/notebooklm_mcp/doc_refresh/`

**Question**: Should artifact refresh be automatic?

**Options**:
- Automatic on doc change (>15% delta)
- Manual trigger only
- User-configurable threshold

**Current Approach**: Threshold-based with manual override flags.

### Cross-Platform Support

**Current State**: macOS focused

**Question**: How well does it work on Linux/Windows?

**Tested**:
- macOS: Full support
- Linux: Should work (untested)
- Windows: Unknown

**Resolution**: Accept issues, improve as reports come in.

## Performance Questions

### Context Window Optimization

**Current State**: 31 tools consume significant context

**Question**: Can we reduce tool count or consolidate?

**Options**:
- Consolidate similar tools
- Dynamic tool loading
- Tool categories with sub-menus

**Resolution**: Keep current structure, rely on toggle feature.

### Response Size

**Current State**: Compact mode for token efficiency

**Question**: Is compact mode sufficient?

**Measurements**:
- Full response: ~2-5KB per notebook
- Compact response: ~200-500 bytes per notebook

**Resolution**: Compact mode default, full details on request.

## Resolved Questions

| Question | Resolution | Date |
|----------|------------|------|
| Auth token format | JSON file with cookies | 2025-12 |
| CSRF extraction | Auto-extracted from page | 2025-12 |
| Confirmation pattern | `confirm=True` required | 2025-12 |
| Tool count | 31 tools sufficient | 2026-01 |
| Compact mode | Default for efficiency | 2026-01 |

## Contributing Questions

If you encounter an unresolved question:

1. Check existing issues on GitHub
2. Add question to this document with context
3. Propose options if you have ideas
4. Reference related code or API behavior

## Related Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) - System design context
- [SECURITY_AND_PRIVACY.md](SECURITY_AND_PRIVACY.md) - Security decisions
- [../KNOWN_ISSUES.md](../KNOWN_ISSUES.md) - Known bugs
- [../API_REFERENCE.md](../API_REFERENCE.md) - API details
