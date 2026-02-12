#!/usr/bin/env bash
# Helper script to run commands in workspace context
# Usage: From any subdirectory, run: ../uv-run.sh run python script.py

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "$SCRIPT_DIR" && pwd)"

# Find workspace root by looking for pyproject.toml
while [ ! -f "$WORKSPACE_ROOT/pyproject.toml" ] && [ "$WORKSPACE_ROOT" != "/" ]; do
    WORKSPACE_ROOT="$(dirname "$WORKSPACE_ROOT")"
done

# Run uv command with workspace root context
cd "$WORKSPACE_ROOT" && uv "$@"
