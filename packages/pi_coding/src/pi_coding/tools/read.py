"""Read tool - reads file contents with line numbers and truncation."""

from __future__ import annotations

import asyncio
import base64
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

from pi_agent import AgentTool, AgentToolResult
from pi_agent.types import AgentToolUpdateCallback
from pi_ai.types import ImageContent, TextContent

from pi_coding.utils import (
    DEFAULT_MAX_BYTES,
    DEFAULT_MAX_LINES,
    TruncationResult,
    format_size,
    resolve_read_path,
    truncate_head,
)

if TYPE_CHECKING:
    from pi_coding.utils import TruncationOptions

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
IMAGE_MIME_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
}


def _detect_image_mime_type(path: str) -> str | None:
    ext = Path(path).suffix.lower()
    return IMAGE_MIME_TYPES.get(ext)


_READ_TOOL_PARAMETERS = {
    "type": "object",
    "properties": {
        "path": {
            "type": "string",
            "description": "Path to the file to read (relative or absolute)",
        },
        "offset": {
            "type": "number",
            "description": "Line number to start reading from (1-indexed)",
        },
        "limit": {
            "type": "number",
            "description": "Maximum number of lines to read",
        },
    },
    "required": ["path"],
}


async def _execute_read(
    tool_call_id: str,
    params: dict[str, Any],
    cwd: str,
    cancel_event: asyncio.Event | None,
    on_update: AgentToolUpdateCallback | None,
) -> AgentToolResult:
    path = params.get("path")
    offset = params.get("offset")
    limit = params.get("limit")

    if not path:
        return AgentToolResult(
            content=[TextContent(type="text", text="Error: 'path' parameter is required")],
            details={"error": "missing_parameter"},
        )

    absolute_path = resolve_read_path(path, cwd)

    if cancel_event and cancel_event.is_set():
        return AgentToolResult(
            content=[TextContent(type="text", text="Operation aborted")],
            details={"error": "aborted"},
        )

    if not os.path.exists(absolute_path):
        return AgentToolResult(
            content=[TextContent(type="text", text=f"Error: File not found: {path}")],
            details={"error": "file_not_found", "path": absolute_path},
        )

    if not os.path.isfile(absolute_path):
        return AgentToolResult(
            content=[TextContent(type="text", text=f"Error: Not a file: {path}")],
            details={"error": "not_a_file", "path": absolute_path},
        )

    mime_type = _detect_image_mime_type(absolute_path)

    if mime_type:
        try:
            with open(absolute_path, "rb") as f:
                data = base64.standard_b64encode(f.read()).decode("utf-8")
            return AgentToolResult(
                content=[
                    TextContent(type="text", text=f"Read image file [{mime_type}]"),
                    ImageContent(type="image", data=data, mimeType=mime_type),
                ],
                details={"path": absolute_path, "mime_type": mime_type},
            )
        except Exception as e:
            return AgentToolResult(
                content=[TextContent(type="text", text=f"Error reading image: {e}")],
                details={"error": str(e), "path": absolute_path},
            )

    try:
        with open(absolute_path, encoding="utf-8") as f:
            content = f.read()

        if cancel_event and cancel_event.is_set():
            return AgentToolResult(
                content=[TextContent(type="text", text="Operation aborted")],
                details={"error": "aborted"},
            )

        all_lines = content.split("\n")
        total_file_lines = len(all_lines)

        start_line = max(0, (offset or 1) - 1)
        start_line_display = start_line + 1

        if start_line >= total_file_lines:
            return AgentToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=f"Error: Offset {offset} is beyond end of file ({total_file_lines} lines total)",
                    )
                ],
                details={"error": "offset_out_of_bounds", "total_lines": total_file_lines},
            )

        if limit is not None:
            end_line = min(start_line + limit, total_file_lines)
            selected_content = "\n".join(all_lines[start_line:end_line])
            user_limited_lines = end_line - start_line
        else:
            selected_content = "\n".join(all_lines[start_line:])
            user_limited_lines = None

        truncation = truncate_head(selected_content)

        if truncation.first_line_exceeds_limit:
            first_line_size = format_size(len(all_lines[start_line].encode("utf-8")))
            output_text = f"[Line {start_line_display} is {first_line_size}, exceeds {format_size(DEFAULT_MAX_BYTES)} limit. Use bash: sed -n '{start_line_display}p' {path} | head -c {DEFAULT_MAX_BYTES}]"
            return AgentToolResult(
                content=[TextContent(type="text", text=output_text)],
                details={"truncation": truncation.__dict__},
            )

        if truncation.truncated:
            end_line_display = start_line_display + truncation.output_lines - 1
            next_offset = end_line_display + 1
            output_text = truncation.content
            if truncation.truncated_by == "lines":
                output_text += f"\n\n[Showing lines {start_line_display}-{end_line_display} of {total_file_lines}. Use offset={next_offset} to continue.]"
            else:
                output_text += f"\n\n[Showing lines {start_line_display}-{end_line_display} of {total_file_lines} ({format_size(DEFAULT_MAX_BYTES)} limit). Use offset={next_offset} to continue.]"
            return AgentToolResult(
                content=[TextContent(type="text", text=output_text)],
                details={"truncation": truncation.__dict__},
            )

        if user_limited_lines is not None and start_line + user_limited_lines < total_file_lines:
            remaining = total_file_lines - (start_line + user_limited_lines)
            next_offset = start_line + user_limited_lines + 1
            output_text = truncation.content
            output_text += f"\n\n[{remaining} more lines in file. Use offset={next_offset} to continue.]"
            return AgentToolResult(
                content=[TextContent(type="text", text=output_text)],
                details={"total_lines": total_file_lines},
            )

        return AgentToolResult(
            content=[TextContent(type="text", text=truncation.content)],
            details={"path": absolute_path, "total_lines": total_file_lines},
        )

    except Exception as e:
        return AgentToolResult(
            content=[TextContent(type="text", text=f"Error reading file: {e}")],
            details={"error": str(e), "path": absolute_path},
        )


def create_read_tool(cwd: str, options: dict[str, Any] | None = None) -> AgentTool:
    return AgentTool(
        name="read",
        label="Read",
        description=f"Read the contents of a file. Supports text files and images (jpg, png, gif, webp). Images are sent as attachments. For text files, output is truncated to {DEFAULT_MAX_LINES} lines or {DEFAULT_MAX_BYTES // 1024}KB (whichever is hit first). Use offset/limit for large files.",
        parameters=_READ_TOOL_PARAMETERS,
        execute=lambda tool_call_id, params, cancel_event, on_update: _execute_read(
            tool_call_id, params, cwd, cancel_event, on_update
        ),
    )


read_tool = create_read_tool(os.getcwd())
