# Security Policy

## Reporting a vulnerability

Please report security issues privately through GitHub's advisory form:

**https://github.com/jacob-bd/gemini-notebook-mcp-cli/security/advisories/new**

Please do not open a public issue for anything that looks exploitable. If you
are not sure whether something qualifies, report it privately and we will sort
it out together.

Helpful things to include, though none of them are required:

1. The version or commit you reviewed
2. The affected file and line
3. What an attacker gains, stated as narrowly as you can
4. A proof of concept, if you have one
5. A suggested fix, if you have one

## What to expect

| Stage | Target |
|---|---|
| First response | 3 business days |
| Triage and severity decision | 7 business days |
| Fix released for High or Critical | 14 days from triage |
| Fix released for Low or Medium | Next scheduled release |

This is a personal open source project, not a funded product, so these are
targets rather than guarantees. If a report goes quiet, please ping the
advisory thread.

## Supported versions

Only the latest released version gets security fixes. Please upgrade before
reporting an issue against an older release.

| Version | Supported |
|---|---|
| 0.11.x | Yes |
| < 0.11 | No |

## Scope

In scope:

- The `notebooklm-mcp` MCP server and its tools
- The `nlm` CLI
- Credential handling, file writes, and the authentication flows
- Setup instructions in `docs/` that create a security boundary

Out of scope:

- Vulnerabilities in Google's services. Please report those to Google.
- Chrome DevTools Protocol having no authentication. That is Chrome's design.
- Anything that requires an attacker to already have your Google session
  cookies.

## Credit

Reporters get credited in `CHANGELOG.md` and in the published advisory unless
they ask not to be. Please say so in the report if you would rather stay
anonymous.

## No bounty

There is no bug bounty program and no payment. Reports are welcome anyway, and
they get taken seriously.
