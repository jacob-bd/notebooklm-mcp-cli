# Security Policy

## Supported Versions

1.0.x is currently supported.

## Reporting a Vulnerability

Use GitHub's private security advisory feature (`Security` tab → `Report a vulnerability`).

Do **not** open a public issue for a security report.

## Response Timeline

- Acknowledge reports within 7 days
- Provide a fix timeline within 14 days
- Fix critical issues within 30 days

## What We Will Do

- Credit reporters in CHANGELOG
- Fix confirmed issues
- Notify affected users

## Important Note

This project uses undocumented APIs, including Google `batchexecute` for personal mode. Some vulnerabilities may be inherent to the reverse-engineering approach and may not be fixable without Google's cooperation.

## Scope

In scope:

- Credential leakage
- SSRF
- Path traversal
- RCE

Out of scope:

- Issues in upstream `jacob-bd/notebooklm-mcp-cli`; report those there directly
