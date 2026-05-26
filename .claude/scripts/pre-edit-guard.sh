#!/usr/bin/env bash
# PreToolUse hook for Edit|Write — blocks edits to sensitive files.
#
# Blocks:
#   - .env files (secrets) — .env.example is allowed

set -euo pipefail

FILE=$(cat | jq -r '.tool_input.file_path // empty')

if [[ "$FILE" == *.env* && "$FILE" != *.env.example ]]; then
  echo "Blocked: .env files contain secrets" >&2
  exit 2
fi