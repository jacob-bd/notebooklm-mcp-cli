# AI Context Bootstrap

Read `ai/STANDARDS.md` and load all files in the order it specifies
before beginning any work. Do not start coding, planning, or responding
until the full load order is complete.

This project uses version format: MAJOR.MINOR.PATCH.YYYYMMDD.HHMM
Example: 1.0.0.20260325.0624

At the end of every session, update `ai/SESSION.md` and `ai/BACKLOG.md`.
Never store credentials, secrets, or PHI in any `ai/` file.

## End of session — required before closing

Before ending any session, you MUST:
1. Update `ai/SESSION.md` — what was done, decisions made, next steps
2. Update `ai/BACKLOG.md` — mark completed tasks, add new ones
3. Remind the user to commit and push both files

---

# Supported tools

This file (AGENTS.md) is the universal standard read by all AI coding tools:
Cursor, Codex, Windsurf, GitHub Copilot, Aider, Zed, Warp, Devin, and others.

CLAUDE.md is a symlink to this file for Claude Code compatibility.
If CLAUDE.md does not exist, run: `ln -s AGENTS.md CLAUDE.md`
