"""Find tool - searches for files by glob pattern using fd."""

from __future__ import annotations

import asyncio
import os
import shutil
from pi_agent.types import AgentToolUpdateCallback
from typing import Any

from pi_agent import AgentTool, AgentToolResult
from pi_ai.types import TextContent

from pi_coding.utils import DEFAULT_MAX_BYTES, format_size, resolve_to_cwd, truncate_head

DEFAULT_LIMIT = 1000

_FIND_TOOL_PARAMETERS = {
    "type": "object",
    "properties": {
        "pattern": {
            "type": "string",
            "description": "Glob pattern to match files, e.g. '*.ts', '**/*.json', or 'src/**/*.spec.ts'",
        },
        "path": {
            "type": "string",
            "description": "Directory to search in (default: current directory)",
        },
        "limit": {
            "type": "number",
            "description": "Maximum number of results (default: 1000)",
        },
    },
    "required": ["pattern"],
}


async def _execute_find(
    tool_call_id: str,
    params: dict[str, Any],
    cwd: str,
    cancel_event: asyncio.Event | None,
    on_update: AgentToolUpdateCallback | None,
) -> AgentToolResult:
    pattern = params.get("pattern")
    search_dir = params.get("path", ".")
    limit = params.get("limit", DEFAULT_LIMIT)

    if not pattern:
        return AgentToolResult(
            content=[TextContent(type="text", text="Error: 'pattern' parameter is required")],
            details={"error": "missing_parameter"},
        )

    fd_path = shutil.which("fd")
    if not fd_path:
        return AgentToolResult(
            content=[TextContent(type="text", text="Error: fd is not available")],
            details={"error": "fd_not_found"},
        )

    search_path = resolve_to_cwd(search_dir, cwd)

    if not os.path.exists(search_path):
        return AgentToolResult(
            content=[TextContent(type="text", text=f"Error: Path not found: {search_path}")],
            details={"error": "path_not_found", "path": search_path},
        )

    if cancel_event and cancel_event.is_set():
        return AgentToolResult(
            content=[TextContent(type="text", text="Operation aborted")],
            details={"error": "aborted"},
        )

    args = [
        fd_path,
        "--glob",
        "--color=never",
        "--hidden",
        "--max-results",
        str(limit),
        pattern,
        search_path,
    ]

    try:
        process = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        if cancel_event and cancel_event.is_set():
            return AgentToolResult(
                content=[TextContent(type="text", text="Operation aborted")],
                details={"error": "aborted"},
            )

        output = stdout.decode("utf-8", errors="replace").strip()

        if process.returncode is not None and process.returncode != 0 and not output:
            error_msg = stderr.decode("utf-8", errors="replace").strip() or f"fd exited with code {process.returncode}"
            return AgentToolResult(
                content=[TextContent(type="text", text=f"Error: {error_msg}")],
                details={"error": "fd_error", "exit_code": process.returncode},
            )

        if not output:
            return AgentToolResult(
                content=[TextContent(type="text", text="No files found matching pattern")],
                details={"pattern": pattern, "results": 0},
            )

        lines = output.split("\n")
        relativized: list[str] = []

        for raw_line in lines:
            line = raw_line.rstrip("\r").strip()
            if not line:
                continue

            had_trailing_slash = line.endswith("/") or line.endswith("\\")
            if line.startswith(search_path):
                relative_path = line[len(search_path) + 1 :]
            else:
                try:
                    relative_path = os.path.relpath(line, search_path)
                except ValueError:
                    relative_path = line

            if had_trailing_slash and not relative_path.endswith("/"):
                relative_path += "/"

            relativized.append(relative_path)

        result_limit_reached = len(relativized) >= limit
        raw_output = "\n".join(relativized)
        truncation = truncate_head(raw_output)

        result_output = truncation.content
        details: dict[str, Any] = {}
        notices: list[str] = []

        if result_limit_reached:
            notices.append(f"{limit} results limit reached. Use limit={limit * 2} for more, or refine pattern")
            details["result_limit_reached"] = limit

        if truncation.truncated:
            notices.append(f"{format_size(DEFAULT_MAX_BYTES)} limit reached")
            details["truncation"] = truncation.__dict__

        if notices:
            result_output += f"\n\n[{'. '.join(notices)}]"

        return AgentToolResult(
            content=[TextContent(type="text", text=result_output)],
            details=details if details else None,
        )

    except Exception as e:
        return AgentToolResult(
            content=[TextContent(type="text", text=f"Error running find: {e}")],
            details={"error": str(e)},
        )


def create_find_tool(cwd: str, options: dict[str, Any] | None = None) -> AgentTool:
    return AgentTool(
        name="find",
        label="Find",
        description=f"Search for files by glob pattern. Returns matching file paths relative to the search directory. Respects .gitignore. Output is truncated to {DEFAULT_LIMIT} results or {DEFAULT_MAX_BYTES // 1024}KB (whichever is hit first).",
        parameters=_FIND_TOOL_PARAMETERS,
        execute=lambda tool_call_id, params, cancel_event, on_update: _execute_find(
            tool_call_id, params, cwd, cancel_event, on_update
        ),
    )


find_tool = create_find_tool(os.getcwd())
