"""Write tool - writes content to files with automatic directory creation."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from pi_agent.types import AgentToolUpdateCallback
from typing import Any

from pi_agent import AgentTool, AgentToolResult
from pi_ai.types import TextContent

from pi_coding.utils import resolve_read_path

_WRITE_TOOL_PARAMETERS = {
    "type": "object",
    "properties": {
        "path": {
            "type": "string",
            "description": "Path to the file to write (relative or absolute)",
        },
        "content": {
            "type": "string",
            "description": "Content to write to the file",
        },
    },
    "required": ["path", "content"],
}


async def _execute_write(
    tool_call_id: str,
    params: dict[str, Any],
    cwd: str,
    cancel_event: asyncio.Event | None,
    on_update: AgentToolUpdateCallback | None,
) -> AgentToolResult:
    path = params.get("path")
    content = params.get("content")

    if not path or content is None:
        return AgentToolResult(
            content=[
                TextContent(type="text", text="Error: 'path' and 'content' parameters are required")
            ],
            details={"error": "missing_parameters"},
        )

    absolute_path = resolve_read_path(path, cwd)

    if cancel_event and cancel_event.is_set():
        return AgentToolResult(
            content=[TextContent(type="text", text="Operation aborted")],
            details={"error": "aborted"},
        )

    try:
        Path(absolute_path).parent.mkdir(parents=True, exist_ok=True)

        if cancel_event and cancel_event.is_set():
            return AgentToolResult(
                content=[TextContent(type="text", text="Operation aborted")],
                details={"error": "aborted"},
            )

        with open(absolute_path, "w", encoding="utf-8") as f:
            f.write(content)

        lines = content.count("\n") + 1
        chars = len(content)

        return AgentToolResult(
            content=[
                TextContent(type="text", text=f"Successfully wrote {lines} lines ({chars} chars) to {path}")
            ],
            details={"path": absolute_path, "line_count": lines, "char_count": chars},
        )

    except Exception as e:
        return AgentToolResult(
            content=[TextContent(type="text", text=f"Error writing file: {e}")],
            details={"error": str(e), "path": absolute_path},
        )


def create_write_tool(cwd: str, options: dict[str, Any] | None = None) -> AgentTool:
    return AgentTool(
        name="write",
        label="Write",
        description="Write content to a file. Creates the file if it doesn't exist, overwrites if it does. Automatically creates parent directories.",
        parameters=_WRITE_TOOL_PARAMETERS,
        execute=lambda tool_call_id, params, cancel_event, on_update: _execute_write(
            tool_call_id, params, cwd, cancel_event, on_update
        ),
    )


write_tool = create_write_tool(os.getcwd())
