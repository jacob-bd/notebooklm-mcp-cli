---
description: How to post GitHub issue/PR comments with markdown formatting
---

# GitHub Issue/PR Comments

**NEVER use inline `-b` with markdown content** — backticks get interpreted by the shell.

## Steps

1. Write the comment body to a temp file:
   ```
   /tmp/gh-reply.md
   ```

// turbo
2. Post using `--body-file`:
   ```bash
   gh issue comment <NUMBER> --body-file /tmp/gh-reply.md
   ```

// turbo
3. Clean up:
   ```bash
   rm /tmp/gh-reply.md
   ```
