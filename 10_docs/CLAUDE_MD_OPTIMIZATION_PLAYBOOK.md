# CLAUDE.md Optimization Playbook

**Purpose**: Guide for maintaining consistent, token-efficient CLAUDE.md files across machines (Mac/PC).

**Created**: 2026-01-03 (Mac optimization session)
**Target Audience**: Claude Code instances on any machine

---

## Overview

Claude Code reads CLAUDE.md files at multiple levels, concatenating them into context. Each level adds tokens. Bloated files waste 10-30k+ tokens on every message.

**Goal**: Keep total CLAUDE.md overhead under 3k tokens while preserving essential guidance.

---

## The CLAUDE.md Hierarchy

Files are loaded in this order (later files can override earlier):

```
1. ~/.claude/CLAUDE.md          # Global (all projects, all machines)
2. ~/CLAUDE.md                  # Home directory level
3. ~/SyncedProjects/CLAUDE.md   # Workspace level
4. <project>/CLAUDE.md          # Project-specific
```

**Key Insight**: Information should live at the LOWEST level where it's actually needed.

---

## Optimization Principles

### 1. Eliminate Duplication
If something is in the project CLAUDE.md, don't repeat it at workspace level.

### 2. Remove Stale Content
- Old project references that no longer exist
- One-time troubleshooting notes (fix it, then delete the note)
- Warnings about tools you no longer use
- Historical context that's no longer relevant

### 3. Use Pointers, Not Content
Instead of embedding detailed docs, point to files:
```markdown
# Bad (wastes tokens every message)
## Detailed Troubleshooting
[500 lines of troubleshooting content]

# Good (only loads when needed)
**For troubleshooting**, see `docs/TROUBLESHOOTING.md`
```

### 4. Defer to README
Project README.md is already in the repo. Don't duplicate its content in CLAUDE.md.

### 5. Tables Over Prose
```markdown
# Bad
The `notebook_delete` tool requires confirmation. The `source_delete` tool also requires confirmation. The `source_sync_drive` tool requires confirmation too...

# Good
| Tool | Requires Confirmation |
|------|----------------------|
| notebook_delete | Yes |
| source_delete | Yes |
| source_sync_drive | Yes |
```

---

## Optimized Templates

### Level 1: Global (~/.claude/CLAUDE.md)

**Purpose**: Instructions that apply to ALL projects everywhere.
**Target size**: < 10 lines

```markdown
# Claude Code Global Settings

This file is for truly global instructions that apply across ALL projects.

For project-specific guidance, see:
- `~/SyncedProjects/CLAUDE.md` - Workspace-level guide
- Project-specific `CLAUDE.md` files within each repo
```

**What belongs here**: Almost nothing. Most instructions are project or workspace specific.

### Level 2: Home Directory (~/CLAUDE.md)

**Purpose**: Machine-level resources (credentials, services).
**Target size**: < 25 lines

```markdown
# CLAUDE.md - Home Directory

For workspace guidance, see `~/SyncedProjects/CLAUDE.md`.

## Credential Vault Quick Reference

**Location**: `~/SyncedProjects/C001_mission-control/`

```bash
# Check if vault is running
curl http://localhost:8820/health

# Start vault
cd ~/SyncedProjects/C001_mission-control && npm run dev
```

**Common credentials**: `openai-api-key`, `anthropic-api-key`, `github-token`

- Port 8820 (localhost only)
- Encrypted with AES-256-GCM
- Claude sessions pre-approved for access
```

**What belongs here**: Machine-specific services, ports, paths that differ by machine.

### Level 3: Workspace (~/SyncedProjects/CLAUDE.md)

**Purpose**: Multi-project conventions, Betty Protocol, project discovery.
**Target size**: < 100 lines

```markdown
# CLAUDE.md - SyncedProjects Workspace

## Overview

SyncedProjects contains 40+ independent projects. Each subdirectory has its own git repo and follows Betty Protocol structure.

**Critical**: Identify target project first, then `cd` into it. Never run git commands from workspace root.

## Project Naming

- **P###_name**: Active development projects
- **C###_name**: Core infrastructure
- **W###_name**: Work/business analytics
- **U##_name**: Utility projects (external tools, no GitHub)
- **_SharedData/**, **_Archive/**, **_scripts/**: Meta-folders

## Standard Project Layout (Betty Protocol)

```
P###_projectname/
├── 00_admin/       # Snapshots, receipts
├── 10_docs/        # Documentation
├── 20_receipts/    # Change receipts
├── 30_config/      # Configuration
├── 40_src/         # Source code
├── 70_evidence/    # Evidence/artifacts
├── 90_archive/     # Archived items
├── META.yaml       # Project metadata
└── README.md       # Canonical docs
```

## Finding Projects

Check `KNOWN_PROJECTS.md` or search: `ls -d *keyword*`

**Common purposes**:
- **Credentials/vault**: C001_mission-control
- **Knowledge pipeline**: C003_sadb_canonical (primary), C002_sadb (legacy)
- **MCP servers**: C021_notebooklm-mcp, P051_mcp-servers
- **Context/prompts**: C017_brain-on-tap
- **Collaboration**: C018_terminal-insights

## Betty Protocol (MANDATORY)

1. **Receipts first** - Evidence in `20_receipts/` or `70_evidence/`
2. **No self-certification** - Work pending until human approval
3. **Keep README accurate** - Update when behavior changes
4. **Verify before done** - Run tests, provide outputs
5. **Honesty over impressiveness** - Report blockers transparently

## Key Environment

```bash
export SADB_DATA_DIR="$HOME/SADB_Data"  # Artifact storage
```

**Shared locations**:
- `_SharedData/ChromaDB/` - Vector stores
- `_SharedData/registry/` - Project registry
- `$SADB_DATA_DIR` - Large artifacts (kept outside sync)

## Guardrails

- Activate project venv before running Python
- Use Read/Edit/Write tools over bash for file operations
- Create receipts for non-trivial operations
- Never commit secrets (use C001_mission-control vault)
- Check project-specific CLAUDE.md first - it overrides this file

## .gitignore Baseline

All projects should include:
```
.DS_Store
.venv/
venv/
node_modules/
data/
.env
```

## When in Doubt

1. Check project-specific CLAUDE.md
2. Read project README.md
3. Ask before making workspace-level changes
```

**What belongs here**:
- Project naming conventions
- Betty Protocol rules (universal)
- Environment variables
- Common project locations
- Workspace-level guardrails

**What does NOT belong here**:
- Project-specific instructions
- Tool-specific troubleshooting
- One-time fixes
- Outdated project references

### Level 4: Project-Specific (<project>/CLAUDE.md)

**Purpose**: Everything Claude needs to work in THIS project.
**Target size**: Varies, but use pointers to docs/

Project CLAUDE.md can be longer because it only loads when working in that project. But still apply optimization principles:

- Point to detailed docs instead of embedding them
- Use tables for reference info
- Put troubleshooting in a separate file
- Include session recovery at the top (most urgent info first)

---

## MCP Server Optimization

Beyond CLAUDE.md, MCP servers add significant tokens. Disable unused servers:

```bash
# Check current MCP usage
# In Claude Code, run: /mcp

# Disable a server (updates ~/.claude.json)
claude mcp disable <server-name>

# Re-enable when needed
claude mcp enable <server-name>
```

**Common token costs**:
- `claude-in-chrome`: ~14k tokens (disable if not using browser automation)
- `sadb-mac`: ~10k tokens (disable if not using knowledge pipeline)

---

## PC-Specific Considerations

When applying this playbook on Windows:

1. **Paths differ**:
   - Mac: `~/SyncedProjects/`
   - PC: Likely `C:\Users\<name>\SyncedProjects\` or similar

2. **Update path references** in ~/CLAUDE.md for credential vault location

3. **MCP servers may differ**: PC might have different servers enabled

4. **Sync the workspace CLAUDE.md**: This file should be identical since it's inside SyncedProjects (synced between machines)

5. **Project CLAUDE.md files sync automatically**: They're in the repos

---

## Optimization Checklist

Run through this when optimizing CLAUDE.md on a new machine:

### Step 1: Audit Current State
```bash
# Find all CLAUDE.md files
find ~ -maxdepth 4 -name "CLAUDE.md" 2>/dev/null

# Check line counts
wc -l ~/.claude/CLAUDE.md ~/CLAUDE.md ~/SyncedProjects/CLAUDE.md
```

### Step 2: Check for Red Flags
- [ ] Files over 100 lines (except project-specific)
- [ ] Duplicate content across levels
- [ ] References to projects that don't exist
- [ ] Embedded troubleshooting that should be in docs/
- [ ] One-time fixes that were never cleaned up
- [ ] Tool warnings for tools you don't use anymore

### Step 3: Apply Templates
Compare each file against the templates above. Trim to match.

### Step 4: Audit MCP Servers
```bash
# In Claude Code
/mcp
```
Disable servers not needed for current work.

### Step 5: Verify
Start a new Claude Code session and check context usage is reasonable.

---

## Before/After Example (Mac Session)

| File | Before | After | Saved |
|------|--------|-------|-------|
| `~/.claude/CLAUDE.md` | 136 lines | 8 lines | 128 lines |
| `~/CLAUDE.md` | 283 lines | 22 lines | 261 lines |
| `~/SyncedProjects/CLAUDE.md` | 575 lines | 87 lines | 488 lines |
| **Total** | 994 lines | 117 lines | **877 lines** |

Plus disabled MCP servers saved ~24k tokens.

**Total savings**: ~33k tokens (~16% of context window)

---

## Maintenance

- After any significant project changes, review if CLAUDE.md needs updating
- Periodically audit for stale content (quarterly)
- When adding new MCP servers, check if others can be disabled
- Sync this playbook to other machines via the repo

---

## Quick Reference Card

| Level | Location | Max Lines | Contains |
|-------|----------|-----------|----------|
| Global | `~/.claude/CLAUDE.md` | 10 | Pointers only |
| Home | `~/CLAUDE.md` | 25 | Machine-specific services |
| Workspace | `~/SyncedProjects/CLAUDE.md` | 100 | Betty Protocol, conventions |
| Project | `<project>/CLAUDE.md` | Varies | Project-specific guidance |

**Golden Rule**: If you're adding content, ask "What level does this belong at?" and "Can I point to a doc instead?"
