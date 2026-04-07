# Project Standards — Master Reference

## Load order

On project start, read these files in this order:
1. `ai/MEMORY.md`   — prior decisions, architecture, known gotchas
2. `ai/BACKLOG.md`  — current tasks and status (this is the to-do list)
3. `ai/SESSION.md`  — what happened last session and next steps
4. `ai/CODING.md`   — coding style and patterns for this project
5. `ai/SECURITY.md` — security requirements (always apply, no exceptions)
6. `ai/PLANNING.md` — how to structure plans and spec documents
7. `ai/TEAM.md`     — team roster, ownership, working agreements

If this file contains an overlay section below the separator line (`---`),
that content is project-type specific and applies to this project in addition
to the base standards above. Read it as part of the same load sequence.

## Session rules

- At END of every session, update `ai/SESSION.md` — include your name and tool
- When tasks change status, update `ai/BACKLOG.md`
- When architectural or design decisions are made, update `ai/MEMORY.md`
- Never store secrets, credentials, API keys, or PHI in any `ai/` file
- If unsure where something belongs, ask before writing

## Tool behavior

All AI tools in this project follow these rules regardless of platform:
- Session logs go to: `ai/SESSION.md`
- Backlog and to-do list go to: `ai/BACKLOG.md`
- Persistent decisions and context go to: `ai/MEMORY.md`
- Specs and planning documents go to: `docs/specs/`

## Source of truth — ai/ files take precedence

The `ai/` folder is the single source of truth for this project, shared across
all tools and all machines. Some AI tools (including Claude Code) maintain their
own local memory or context systems alongside this folder. When any conflict or
overlap exists between a tool's local memory and the `ai/` files:

- `ai/BACKLOG.md` is the authoritative task list — not any tool's local memory
- `ai/MEMORY.md` is the authoritative decision log — not any tool's local memory
- `ai/SESSION.md` is the authoritative session history — not any tool's local memory

If you are Claude Code and have local memory files (e.g. under `.claude/projects/`),
read them for additional context but write all updates to the `ai/` files only.
Do not create or update local memory backlog or session files — use `ai/BACKLOG.md`
and `ai/SESSION.md` instead.

## Multi-user rules

When more than one person or tool works in this repo:
- Never commit directly to `main` — always branch and PR
- Use the PR template in `.github/PULL_REQUEST_TEMPLATE.md`
- `ai/SESSION.md` and `ai/BACKLOG.md` are append-only — on merge conflicts,
  keep all entries from both sides
- `ai/MEMORY.md` conflicts must be resolved by the project owner manually —
  never auto-merge this file
- See `ai/TEAM.md` for ownership and escalation

## Git workflow — merge only

This org uses a merge-only workflow. Rebasing is not used.

**Starting new work:**
```bash
git checkout main
git pull origin main
git checkout -b feature/your-work
```

**Committing and opening a PR:**
```bash
git add .
git commit -m "type(scope): description"
git push origin feature/your-work
# Then open a Pull Request in GitHub
```

**Keeping your branch current while the PR is open:**
```bash
git checkout feature/your-work
git fetch origin
git merge origin/main
git push origin feature/your-work
```

**After your PR is merged:**
```bash
git checkout main
git pull origin main
```

## Versioning standard

All projects and releases use this format:

    MAJOR.MINOR.PATCH.YYYYMMDD.HHMM

| Part     | Meaning                           | Example  |
|----------|-----------------------------------|----------|
| MAJOR    | Breaking changes                  | 1        |
| MINOR    | New features, backward compatible | 0        |
| PATCH    | Bug fixes only                    | 0        |
| YYYYMMDD | Build date                        | 20260406 |
| HHMM     | Build time, 24-hour format        | 1200     |

Full example: `1.0.0.20260406.1200`

---

# API Integration Overlay — Standards

_This overlay extends the base standards for projects that call external APIs._
_This project integrates with two Google API surfaces: batchexecute (personal) and_
_Discovery Engine REST (enterprise). Load base standards first, then these additions._

## Versioning

- MAJOR bump = breaking change to API contract, auth model, or config schema
- MINOR bump = new endpoint, new tool, or new integration
- PATCH bump = bug fix — no contract change

## Authentication standards

- All API credentials come from environment variables or `config.toml` — never hardcoded
- OAuth tokens (GCP) are refreshed automatically via `gcloud auth print-access-token`
- Browser cookies (personal) auto-refreshed via `nlm login`
- Document every auth mechanism in `docs/AUTHENTICATION.md`
- Never log auth headers, tokens, cookies, or credential values

| Auth type | Implementation |
|-----------|---------------|
| GCP OAuth2 (enterprise) | `gcloud auth print-access-token` subprocess call |
| Browser cookies (personal) | Chrome DevTools Protocol via `utils/cdp.py` |

## Required API documentation

Enterprise API contract lives in `docs/API_REFERENCE.md`. Keep it current when
adding new endpoints or discovering undocumented behavior (like the audio overview
empty-body requirement).

## Rate limiting and retry

- All clients handle 429/5xx gracefully — never crash on rate limits
- Personal (batchexecute): no explicit rate limiting but ~50 queries/day on free tier
- Enterprise (REST): respect HTTP 429 Retry-After headers

## Error handling

- Every API call must handle errors explicitly — no unhandled exceptions
- Distinguish 4xx (fix the request) from 5xx (retry)
- Error messages must not expose auth headers or tokens — strip them in exceptions
- Surface `ServiceError`/`ValidationError` from services layer; never raw exceptions to MCP

## Release checklist

- [ ] Version updated in `version` file and `src/notebooklm_tools/__init__.py`
- [ ] `docs/AUTHENTICATION.md` current
- [ ] All tests passing (`uv run pytest`)
- [ ] Ruff lint + format clean (`uvx ruff check . && uvx ruff format --check .`)
- [ ] No credentials in committed files
- [ ] `ai/SESSION.md` and `ai/BACKLOG.md` updated
