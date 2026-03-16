#!/bin/bash
# YGGDRASIL — Install git hooks (Linux/Mac/Git Bash)
# Usage: bash hooks/install.sh

HOOK_SRC="$(dirname "$0")/pre-commit"
HOOK_DST="$(git rev-parse --git-dir)/hooks/pre-commit"

cp "$HOOK_SRC" "$HOOK_DST"
chmod +x "$HOOK_DST"
echo "[winter-tree] Hook installed: $HOOK_DST"
echo "[winter-tree] Auto-updates: winter-tree.json, CHANGELOG.md, TODO.md, SOL.md"
