#!/bin/bash

# AI Project Scaffold — Sync Check
# Run before starting work to verify your ai/ files are current with remote.
# Usage: ./sync-check.sh

set -euo pipefail

BRANCH=$(git branch --show-current 2>/dev/null)
if [ -z "$BRANCH" ]; then
  echo "ERROR: Not in a git repository or no branch checked out."
  exit 1
fi

echo "[..] Fetching latest from origin..."
git fetch origin 2>/dev/null

if ! git rev-parse --verify "origin/$BRANCH" >/dev/null 2>&1; then
  echo "[OK] No remote branch 'origin/$BRANCH' — nothing to compare."
  exit 0
fi

BEHIND=$(git rev-list HEAD..origin/"$BRANCH" -- ai/ | wc -l | tr -d ' ')

if [ "$BEHIND" -gt 0 ]; then
  echo ""
  echo "WARNING: ai/ files are $BEHIND commit(s) behind origin/$BRANCH"
  echo ""
  echo "Run this before starting work:"
  echo "  git pull origin $BRANCH"
  echo ""
  exit 1
else
  echo "[OK] ai/ files are current with origin/$BRANCH"
fi

DIRTY=$(git status --porcelain ai/ 2>/dev/null | wc -l | tr -d ' ')
if [ "$DIRTY" -gt 0 ]; then
  echo "[!]  You have uncommitted changes in ai/:"
  git status --short ai/
fi
