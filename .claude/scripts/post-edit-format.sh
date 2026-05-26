#!/usr/bin/env bash
# PostToolUse hook for Edit|Write — auto-formats Python files after edits.
#
# Runs ruff format + ruff check --fix on .py files via the project venv.

set -euo pipefail

FILE=$(cat | jq -r '.tool_input.file_path // empty')
RUFF="$(dirname "$0")/../../.venv/bin/ruff"

if [[ "$FILE" == *.py && -x "$RUFF" ]]; then
  "$RUFF" format "$FILE"
  "$RUFF" check --fix "$FILE"
fi
