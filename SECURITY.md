# Security Policy

## Overview

This document outlines the security measures, threat model, and best practices for the NotebookLM MCP CLI tool.

## Security Features

### 1. Credential Protection

**File Permissions**
- Auth cache files: `0o600` (owner read/write only)
- Profile directories: `0o700` (owner access only)
- Cookie files: `0o600` (owner read/write only)
- Metadata files: `0o600` (owner read/write only)

**Storage Location**
- Credentials stored in `~/.notebooklm-mcp-cli/` (Unix) or `%USERPROFILE%\.notebooklm-mcp-cli\` (Windows)
- Never stored in project directories or version control

**No Hardcoded Secrets**
- All authentication tokens loaded from secure cache files
- No API keys, passwords, or tokens in source code
- Environment variables used for configuration, not secrets

### 2. Input Validation

**File Path Validation**
- All file paths resolved with `Path.resolve()` to prevent traversal attacks
- Files validated for existence and type before operations
- Size limits enforced on cookie files (1MB max)

**Download URL Validation**
- Downloads restricted to trusted Google domains:
  - `*.google.com`
  - `*.googleusercontent.com`
  - `*.ggpht.com`
- URL domain validation before streaming begins
- Prevents SSRF and credential exfiltration attacks

**File Upload Validation**
- Supported file types whitelist enforced
- Empty files rejected
- File type detection based on extension

### 3. Network Security

**HTTP Transport Warnings**
- Non-loopback binding requires explicit opt-in via `NOTEBOOKLM_ALLOW_EXTERNAL_BIND=1`
- Clear security warnings displayed before binding to external addresses
- Default binding to `127.0.0.1` (localhost only)

**Request Authentication**
- All API requests include proper CSRF tokens
- Cookies scoped to appropriate domains
- Session management with automatic token refresh

**Download Security**
- OSID cookies stripped before download requests (prevents session hijacking)
- HTML content type check to detect auth redirects
- Per-chunk timeouts to detect stalled/malicious connections

### 4. Resource Protection

**Rate Limiting**
- Token bucket algorithm limits API request rate
- Default: 10 requests/second sustained, 20 burst
- Prevents accidental DoS of Google's API
- Configurable via `RateLimitConfig`

**Memory Management**
- Conversation cache limited to 100 conversations (LRU eviction)
- Streaming downloads (64KB chunks) prevent memory exhaustion
- Cookie object caching reduces duplication overhead

**Timeout Configuration**
- Connect timeout: 10s
- Read/write timeout: 30s per chunk
- Overall query timeout: 120s (configurable)
- Prevents resource exhaustion from hanging requests

### 5. Subprocess Safety

**No Shell Injection**
- All `subprocess` calls use list-based arguments (no `shell=True`)
- User input never passed to shell commands
- Command construction uses safe parameter passing

### 6. Authentication Flow

**Multi-Layer Auth Recovery**
1. Fast: Refresh CSRF/session tokens from current session
2. Medium: Reload cookies from disk cache
3. Slow: Headless browser re-authentication (if Chrome profile available)

**Browser-Based Authentication**
- Uses Chrome DevTools Protocol for secure cookie extraction
- No credential storage in intermediate formats
- Validates required Google auth cookies present

## Threat Model

### In Scope

1. **Credential Theft**
   - Local file system access by malicious processes
   - Network interception of authentication tokens
   - Accidental credential exposure in logs/debug output

2. **API Abuse**
   - Rate limit exhaustion
   - Resource exhaustion (memory, connections)
   - Denial of service via malformed inputs

3. **Code Injection**
   - Command injection via subprocess
   - Path traversal in file operations
   - URL injection in download operations

4. **Data Exfiltration**
   - Unauthorized file downloads
   - SSRF via malicious URLs
   - Credential leakage via HTTP headers

### Out of Scope

1. **Physical Access Attacks**
   - Direct memory access while running
   - Hardware keyloggers
   - Screen capture of browser login

2. **Google Account Compromise**
   - Phishing attacks on Google account
   - Weak password on Google account
   - Compromised 2FA device

3. **Supply Chain Attacks**
   - Compromised PyPI packages (not controlled by this project)
   - Malicious browser extensions
   - OS-level malware

## Security Best Practices

### For Users

1. **Credential Management**
   ```bash
   # Verify file permissions after login
   ls -la ~/.notebooklm-mcp-cli/
   # Should show: drwx------ (700) for directories
   #              -rw------- (600) for files
   ```

2. **Network Deployment**
   ```bash
   # SAFE: Local development
   notebooklm-mcp --transport http --host 127.0.0.1 --port 8000
   
   # UNSAFE: External access without authentication
   # Don't do this unless you know what you're doing
   NOTEBOOKLM_ALLOW_EXTERNAL_BIND=1 notebooklm-mcp --transport http --host 0.0.0.0 --port 8000
   ```

3. **Rate Limiting**
   - Default limits are conservative to protect Google's API
   - Adjust only if you have explicit permission for higher rates
   - Monitor for 429 (rate limit) errors in production

4. **Credential Rotation**
   ```bash
   # Re-authenticate periodically (cookies expire ~7 days)
   nlm login
   
   # Revoke all sessions from Google Account settings if compromised
   # https://myaccount.google.com/permissions
   ```

### For Developers

1. **Never Log Credentials**
   ```python
   # BAD
   logger.debug(f"Cookie: {cookie_header}")
   
   # GOOD
   logger.debug("Cookie: [REDACTED]")
   ```

2. **Validate All External Input**
   ```python
   # BAD
   file_path = Path(user_input)
   
   # GOOD
   file_path = Path(user_input).resolve()
   if not file_path.exists():
       raise ValueError(f"File not found: {file_path}")
   ```

3. **Use Safe Subprocess Calls**
   ```python
   # BAD
   subprocess.run(f"command {user_input}", shell=True)
   
   # GOOD
   subprocess.run(["command", user_input], shell=False)
   ```

4. **Respect Rate Limits**
   ```python
   from notebooklm_tools.core.rate_limiter import rate_limit
   
   # Apply rate limiting before API calls
   rate_limit(tokens=1)
   result = client._call_rpc(rpc_id, params)
   ```

## Reporting Security Issues

**DO NOT** open public GitHub issues for security vulnerabilities.

Instead:
1. Email security concerns to the maintainers (check repository for contact)
2. Provide detailed reproduction steps
3. Include impact assessment
4. Suggest remediation if possible

Response timeline:
- Initial acknowledgment: 48 hours
- Fix development: 1-2 weeks for critical issues
- Public disclosure: After patch is released

## Security Changelog

### 2025-05-25 - Security Hardening Update

**Added:**
- Rate limiting (token bucket, 10 req/s sustained, 20 burst)
- Conversation cache size limit (100 conversations, LRU eviction)
- Download URL domain validation (Google domains only)
- Cookie file size limit (1MB max)
- File path traversal protection
- HTTP binding warnings with opt-in requirement
- Exponential backoff for source reconciliation polling
- Cookie object caching optimization

**Improved:**
- OSID cookie stripping for downloads
- Timeout configuration for all network operations
- Memory efficiency for large file downloads
- Thread safety for concurrent MCP requests

## Compliance

This tool:
- Does NOT store Google passwords or 2FA codes
- Uses official Google cookie-based authentication
- Respects Google's API rate limits
- Does not bypass any Google security controls
- Requires valid Google account credentials

Users are responsible for:
- Securing their Google account
- Complying with Google's Terms of Service
- Protecting their local credential cache
- Using appropriate network security when deploying MCP server

## References

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Google OAuth 2.0 Security Best Practices](https://developers.google.com/identity/protocols/oauth2/security-best-practices)
- [MCP Protocol Security](https://modelcontextprotocol.io/docs/security)
- [Python Security Best Practices](https://python.readthedocs.io/en/stable/library/security_warnings.html)
