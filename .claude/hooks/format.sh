#!/bin/bash

# Post-tool-use hook for Claude Code
# Auto-formats files after Edit/Write: Prettier for frontend files, Ruff for Python.
# Never blocks tool execution.

FILE=$(jq -r '.tool_input.file_path // empty')

[ -z "$FILE" ] && exit 0
[ -f "$FILE" ] || exit 0

cd "$CLAUDE_PROJECT_DIR" 2>/dev/null || exit 0
git check-ignore -q "$FILE" && exit 0

case "${FILE##*.}" in
    vue|js|json|css|html)
        npx --yes prettier --write "$FILE" >&2 || true
        ;;
    py)
        uvx ruff format "$FILE" >&2 || true
        ;;
esac

exit 0
