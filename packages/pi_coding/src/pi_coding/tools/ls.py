"""Ls tool - lists directory contents with type indicators and truncation."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from pi_agent.types import AgentToolUpdateCallback
from typing import Any

from pi_agent import AgentTool, AgentToolResult
from pi_ai.types import TextContent

from pi_coding.utils import DEFAULT_MAX_BYTES, format_size, resolve_to_cwd, truncate_head

DEFAULT_LIMIT = 500

_LS_TOOL_PARAMETERS = {
    "type": "object",
    "properties": {
        "path": {
            "type": "string",
            "description": "Directory to list (default: current directory)",
        },
        "limit": {
            "type": "number",
            "description": "Maximum number of entries to return (default: 500)",
        },
    },
    "required": [],
}


async def _execute_ls(
    tool_call_id: str,
    params: dict[str, Any],
    cwd: str,
    cancel_event: asyncio.Event | None,
    on_update: AgentToolUpdateCallback | None,
) -> AgentToolResult:
    path = params.get("path", ".")
    limit = params.get("limit", DEFAULT_LIMIT)

    if cancel_event and cancel_event.is_set():
        return AgentToolResult(
            content=[TextContent(type="text", text="Operation aborted")],
            details={"error": "aborted"},
        )

    dir_path = resolve_to_cwd(path, cwd)

    if not os.path.exists(dir_path):
        return AgentToolResult(
            content=[TextContent(type="text", text=f"Error: Path not found: {dir_path}")],
            details={"error": "path_not_found", "path": dir_path},
        )

    if not os.path.isdir(dir_path):
        return AgentToolResult(
            content=[TextContent(type="text", text=f"Error: Not a directory: {dir_path}")],
            details={"error": "not_a_directory", "path": dir_path},
        )

    try:
        entries = sorted(os.listdir(dir_path), key=lambda s: s.lower())
    except PermissionError as e:
        return AgentToolResult(
            content=[TextContent(type="text", text=f"Error: Cannot read directory: {e}")],
            details={"error": "permission_denied", "path": dir_path},
        )

    results: list[str] = []
    entry_limit_reached = False

    for entry in entries:
        if len(results) >= limit:
            entry_limit_reached = True
            break

        full_path = os.path.join(dir_path, entry)
        suffix = "/" if os.path.isdir(full_path) else ""
        results.append(entry + suffix)

    if not results:
        return AgentToolResult(
            content=[TextContent(type="text", text="(empty directory)")],
            details={"path": dir_path},
        )

    raw_output = "\n".join(results)
    truncation = truncate_head(raw_output)

    output = truncation.content
    details: dict[str, Any] = {}
    notices: list[str] = []

    if entry_limit_reached:
        notices.append(f"{limit} entries limit reached. Use limit={limit * 2} for more")
        details["entry_limit_reached"] = limit

    if truncation.truncated:
        notices.append(f"{format_size(DEFAULT_MAX_BYTES)} limit reached")
        details["truncation"] = truncation.__dict__

    if notices:
        output += f"\n\n[{'. '.join(notices)}]"

    return AgentToolResult(
        content=[TextContent(type="text", text=output)],
        details=details if details else None,
    )


def create_ls_tool(cwd: str, options: dict[str, Any] | None = None) -> AgentTool:
    return AgentTool(
        name="ls",
        label="List",
        description=f"List directory contents. Returns entries sorted alphabetically, with '/' suffix for directories. Includes dotfiles. Output is truncated to {DEFAULT_LIMIT} entries or {DEFAULT_MAX_BYTES // 1024}KB (whichever is hit first).",
        parameters=_LS_TOOL_PARAMETERS,
        execute=lambda tool_call_id, params, cancel_event, on_update: _execute_ls(
            tool_call_id, params, cwd, cancel_event, on_update
        ),
    )


ls_tool = create_ls_tool(os.getcwd())
