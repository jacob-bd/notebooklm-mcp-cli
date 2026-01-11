# NotebookLM MCP Security & Privacy

**Last Updated**: 2026-01-10
**Version**: 0.1.0

Security model and data protection for the NotebookLM MCP Server.

## Security Principles

1. **Local credential storage** - Auth tokens stored locally, not transmitted
2. **No credential logging** - Cookies never written to logs
3. **Dedicated Chrome profile** - Isolated from main browser profile
4. **Confirmation patterns** - Destructive operations require explicit confirmation

## Authentication Security

### Token Storage

| Token | Location | Permissions |
|-------|----------|-------------|
| Cookies | `~/.notebooklm-mcp/auth.json` | User-only (0600) |
| Chrome profile | `~/.notebooklm-mcp/chrome-profile/` | User-only (0700) |

### What Gets Stored

```json
// ~/.notebooklm-mcp/auth.json
{
  "cookies": "SID=...; HSID=...; ...",
  "csrf_token": "...",
  "session_id": "...",
  "extracted_at": "2026-01-10T12:00:00Z"
}
```

### What Stays Local

| Data | Stored Where | Synced Externally? |
|------|--------------|-------------------|
| Google cookies | `auth.json` | No |
| CSRF token | `auth.json` | No |
| Session ID | `auth.json` | No |
| Chrome profile | `chrome-profile/` | No |

## Network Security

### Connections Made

| Endpoint | Purpose | Auth Required |
|----------|---------|---------------|
| `notebooklm.google.com` | NotebookLM API | Yes (cookies) |
| `accounts.google.com` | OAuth (auth CLI only) | Interactive |

### No Proxy Support

Current implementation connects directly to Google services. Corporate proxies may require additional configuration.

## Data Privacy

### What Data is Sent to NotebookLM

| Data Type | When Sent |
|-----------|-----------|
| Notebook content | When adding sources |
| Queries | When using `notebook_query` |
| Studio requests | When generating content |

### What Data is Returned

| Data Type | Storage |
|-----------|---------|
| Notebook metadata | In-memory only |
| Source content | In-memory only |
| Generated content URLs | In-memory only |

**No MCP data is persisted locally** except auth tokens.

### Google's Data Handling

All notebook data is stored and processed by Google NotebookLM. Refer to:
- [NotebookLM Terms of Service](https://notebooklm.google.com/terms)
- [Google Privacy Policy](https://policies.google.com/privacy)

## Confirmation Pattern

Destructive operations require explicit `confirm=True`:

```python
# Without confirmation - safe preview
notebook_delete(notebook_id, confirm=False)
# Returns: {"status": "confirm_required", ...}

# With confirmation - executes delete
notebook_delete(notebook_id, confirm=True)
# Returns: {"status": "success", ...}
```

### Operations Requiring Confirmation

| Operation | Risk Level | Notes |
|-----------|------------|-------|
| `notebook_delete` | High | IRREVERSIBLE |
| `source_delete` | High | IRREVERSIBLE |
| `studio_delete` | High | IRREVERSIBLE |
| `source_sync_drive` | Medium | May update content |
| All studio creation | Medium | Uses API quota |

## Threat Model

### Mitigated Threats

| Threat | Mitigation |
|--------|------------|
| Credential theft | Local storage with user-only permissions |
| Accidental deletion | Confirmation pattern |
| Cookie leakage | Not logged, not synced |
| Profile contamination | Dedicated Chrome profile |

### Accepted Risks

| Risk | Acceptance Rationale |
|------|---------------------|
| Local file access | OS-level protection |
| Google sees data | Inherent to using NotebookLM |
| Cookie expiration | Auto-detection and user notification |
| API changes | Reverse-engineered API may break |

### Out of Scope

| Risk | Notes |
|------|-------|
| Google account security | User's responsibility |
| Network interception | HTTPS handled by Google |
| Memory inspection | Requires system access |

## Security Checklist

### Initial Setup

- [ ] Run `notebooklm-mcp-auth` to create dedicated profile
- [ ] Verify `~/.notebooklm-mcp/` has correct permissions (0700)
- [ ] Verify `auth.json` has correct permissions (0600)
- [ ] Ensure `auth.json` is not committed to version control

### Ongoing

- [ ] Don't share `auth.json` file
- [ ] Don't commit cookies to version control
- [ ] Re-authenticate when cookies expire
- [ ] Use separate Google account if needed for isolation

## Incident Response

### Suspected Credential Compromise

1. **Revoke Google session**: [Google Security Checkup](https://myaccount.google.com/security-checkup)
2. **Delete local tokens**: `rm -rf ~/.notebooklm-mcp/`
3. **Re-authenticate**: `notebooklm-mcp-auth`
4. **Monitor account**: Check for unauthorized notebook access

### Auth Token Leaked

1. **Invalidate session**: Sign out of all Google sessions
2. **Delete local tokens**: `rm ~/.notebooklm-mcp/auth.json`
3. **Change Google password** if concerned
4. **Re-authenticate**: `notebooklm-mcp-auth`

## Configuration

### File Permissions

```bash
# Verify permissions
ls -la ~/.notebooklm-mcp/

# Fix if needed
chmod 700 ~/.notebooklm-mcp/
chmod 600 ~/.notebooklm-mcp/auth.json
```

### Gitignore

The following should be in `.gitignore`:
```
auth.json
.notebooklm-mcp/
chrome-profile/
cookies.txt
```

## Related Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) - System design
- [OPERATIONS.md](OPERATIONS.md) - Day-to-day operation
- [../AUTHENTICATION.md](../AUTHENTICATION.md) - Auth details
