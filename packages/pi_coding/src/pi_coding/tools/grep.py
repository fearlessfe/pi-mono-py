"""Grep tool - searches file contents using ripgrep with context lines."""

from __future__ import annotations

import asyncio
import json
import os
import shutil
from pi_agent.types import AgentToolUpdateCallback
from typing import Any

from pi_agent import AgentTool, AgentToolResult
from pi_ai.types import TextContent

from pi_coding.utils import (
    DEFAULT_MAX_BYTES,
    GREP_MAX_LINE_LENGTH,
    format_size,
    resolve_to_cwd,
    truncate_head,
    truncate_line,
)

DEFAULT_LIMIT = 100

_GREP_TOOL_PARAMETERS = {
    "type": "object",
    "properties": {
        "pattern": {
            "type": "string",
            "description": "Search pattern (regex or literal string)",
        },
        "path": {
            "type": "string",
            "description": "Directory or file to search (default: current directory)",
        },
        "glob": {
            "type": "string",
            "description": "Filter files by glob pattern, e.g. '*.ts' or '**/*.spec.ts'",
        },
        "ignore_case": {
            "type": "boolean",
            "description": "Case-insensitive search (default: false)",
        },
        "literal": {
            "type": "boolean",
            "description": "Treat pattern as literal string instead of regex (default: false)",
        },
        "context": {
            "type": "number",
            "description": "Number of lines to show before and after each match (default: 0)",
        },
        "limit": {
            "type": "number",
            "description": "Maximum number of matches to return (default: 100)",
        },
    },
    "required": ["pattern"],
}


async def _execute_grep(
    tool_call_id: str,
    params: dict[str, Any],
    cwd: str,
    cancel_event: asyncio.Event | None,
    on_update: AgentToolUpdateCallback | None,
) -> AgentToolResult:
    pattern = params.get("pattern")
    search_dir = params.get("path", ".")
    glob_pattern = params.get("glob")
    ignore_case = params.get("ignore_case", False)
    literal = params.get("literal", False)
    context = params.get("context", 0)
    limit = params.get("limit", DEFAULT_LIMIT)

    if not pattern:
        return AgentToolResult(
            content=[TextContent(type="text", text="Error: 'pattern' parameter is required")],
            details={"error": "missing_parameter"},
        )

    rg_path = shutil.which("rg")
    if not rg_path:
        return AgentToolResult(
            content=[TextContent(type="text", text="Error: ripgrep (rg) is not available")],
            details={"error": "rg_not_found"},
        )

    search_path = resolve_to_cwd(search_dir, cwd)

    if not os.path.exists(search_path):
        return AgentToolResult(
            content=[TextContent(type="text", text=f"Error: Path not found: {search_path}")],
            details={"error": "path_not_found", "path": search_path},
        )

    is_directory = os.path.isdir(search_path)
    context_value = max(0, context) if context else 0
    effective_limit = max(1, limit)

    def format_path(file_path: str) -> str:
        if is_directory:
            try:
                relative = os.path.relpath(file_path, search_path)
                if not relative.startswith(".."):
                    return relative.replace("\\", "/")
            except ValueError:
                pass
        return os.path.basename(file_path)

    args = [rg_path, "--json", "--line-number", "--color=never", "--hidden"]

    if ignore_case:
        args.append("--ignore-case")

    if literal:
        args.append("--fixed-strings")

    if glob_pattern:
        args.extend(["--glob", glob_pattern])

    args.extend([pattern, search_path])

    if cancel_event and cancel_event.is_set():
        return AgentToolResult(
            content=[TextContent(type="text", text="Operation aborted")],
            details={"error": "aborted"},
        )

    try:
        process = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        matches: list[tuple[str, int]] = []
        output_lines: list[str] = []
        match_count = 0
        match_limit_reached = False
        lines_truncated = False

        file_cache: dict[str, list[str]] = {}

        def get_file_lines(file_path: str) -> list[str]:
            if file_path not in file_cache:
                try:
                    with open(file_path, encoding="utf-8", errors="replace") as f:
                        content = f.read().replace("\r\n", "\n").replace("\r", "\n")
                        file_cache[file_path] = content.split("\n")
                except Exception:
                    file_cache[file_path] = []
            return file_cache[file_path]

        def format_block(file_path: str, line_number: int) -> list[str]:
            relative_path = format_path(file_path)
            lines = get_file_lines(file_path)
            if not lines:
                return [f"{relative_path}:{line_number}: (unable to read file)"]

            block: list[str] = []
            start = max(1, line_number - context_value) if context_value > 0 else line_number
            end = min(len(lines), line_number + context_value) if context_value > 0 else line_number

            for current in range(start, end + 1):
                line_text = lines[current - 1] if current <= len(lines) else ""
                nonlocal lines_truncated
                truncated_text, was_truncated = truncate_line(line_text, GREP_MAX_LINE_LENGTH)
                if was_truncated:
                    lines_truncated = True

                if current == line_number:
                    block.append(f"{relative_path}:{current}: {truncated_text}")
                else:
                    block.append(f"{relative_path}-{current}- {truncated_text}")

            return block

        if process.stdout is None:
            return AgentToolResult(
                content=[TextContent(type="text", text="Error: Failed to read ripgrep output")],
                details={"error": "no_stdout"},
            )

        while True:
            try:
                line = await process.stdout.readline()
                if not line:
                    break

                line_text = line.decode("utf-8", errors="replace").strip()
                if not line_text or match_count >= effective_limit:
                    continue

                try:
                    event = json.loads(line_text)
                except json.JSONDecodeError:
                    continue

                if event.get("type") == "match":
                    match_count += 1
                    file_path = event.get("data", {}).get("path", {}).get("text", "")
                    line_number = event.get("data", {}).get("line_number")

                    if file_path and isinstance(line_number, int):
                        matches.append((file_path, line_number))

                    if match_count >= effective_limit:
                        match_limit_reached = True
                        process.kill()
                        break

            except asyncio.CancelledError:
                break

        await process.wait()

        if cancel_event and cancel_event.is_set():
            return AgentToolResult(
                content=[TextContent(type="text", text="Operation aborted")],
                details={"error": "aborted"},
            )

        if match_count == 0:
            return AgentToolResult(
                content=[TextContent(type="text", text="No matches found")],
                details={"pattern": pattern, "matches": 0},
            )

        for file_path, line_number in matches:
            output_lines.extend(format_block(file_path, line_number))

        raw_output = "\n".join(output_lines)
        truncation = truncate_head(raw_output)

        output = truncation.content
        details: dict[str, Any] = {}
        notices: list[str] = []

        if match_limit_reached:
            notices.append(f"{effective_limit} matches limit reached. Use limit={effective_limit * 2} for more, or refine pattern")
            details["match_limit_reached"] = effective_limit

        if truncation.truncated:
            notices.append(f"{format_size(DEFAULT_MAX_BYTES)} limit reached")
            details["truncation"] = truncation.__dict__

        if lines_truncated:
            notices.append(f"Some lines truncated to {GREP_MAX_LINE_LENGTH} chars. Use read tool to see full lines")
            details["lines_truncated"] = True

        if notices:
            output += f"\n\n[{'. '.join(notices)}]"

        return AgentToolResult(
            content=[TextContent(type="text", text=output)],
            details=details if details else None,
        )

    except Exception as e:
        return AgentToolResult(
            content=[TextContent(type="text", text=f"Error running grep: {e}")],
            details={"error": str(e)},
        )


def create_grep_tool(cwd: str, options: dict[str, Any] | None = None) -> AgentTool:
    return AgentTool(
        name="grep",
        label="Grep",
        description=f"Search file contents for a pattern. Returns matching lines with file paths and line numbers. Respects .gitignore. Output is truncated to {DEFAULT_LIMIT} matches or {DEFAULT_MAX_BYTES // 1024}KB (whichever is hit first). Long lines are truncated to {GREP_MAX_LINE_LENGTH} chars.",
        parameters=_GREP_TOOL_PARAMETERS,
        execute=lambda tool_call_id, params, cancel_event, on_update: _execute_grep(
            tool_call_id, params, cwd, cancel_event, on_update
        ),
    )


grep_tool = create_grep_tool(os.getcwd())
