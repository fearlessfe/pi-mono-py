"""Bash tool - executes shell commands with streaming output and truncation."""

from __future__ import annotations

import asyncio
import os
import tempfile
from pi_agent.types import AgentToolUpdateCallback
from typing import Any

from pi_agent import AgentTool, AgentToolResult
from pi_ai.types import TextContent

from pi_coding.utils import DEFAULT_MAX_BYTES, DEFAULT_MAX_LINES, format_size, truncate_tail

_BASH_TOOL_PARAMETERS = {
    "type": "object",
    "properties": {
        "command": {
            "type": "string",
            "description": "Bash command to execute",
        },
        "timeout": {
            "type": "number",
            "description": "Timeout in seconds (optional, no default timeout)",
        },
    },
    "required": ["command"],
}


async def _execute_bash(
    tool_call_id: str,
    params: dict[str, Any],
    cwd: str,
    cancel_event: asyncio.Event | None,
    on_update: AgentToolUpdateCallback | None,
) -> AgentToolResult:
    command = params.get("command")
    timeout = params.get("timeout")

    if not command:
        return AgentToolResult(
            content=[TextContent(type="text", text="Error: 'command' parameter is required")],
            details={"error": "missing_parameter"},
        )

    if cancel_event and cancel_event.is_set():
        return AgentToolResult(
            content=[TextContent(type="text", text="Operation aborted")],
            details={"error": "aborted"},
        )

    shell = os.environ.get("SHELL", "/bin/bash")
    temp_file: tempfile._TemporaryFileWrapper | None = None
    temp_file_path: str | None = None

    chunks: list[bytes] = []
    chunks_bytes = 0
    max_chunks_bytes = DEFAULT_MAX_BYTES * 2
    total_bytes = 0

    try:
        process = await asyncio.create_subprocess_shell(
            command,
            cwd=cwd,
            shell=True,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            executable=shell,
        )

        async def read_stream():
            nonlocal total_bytes, chunks_bytes, temp_file, temp_file_path

            if process.stdout is None:
                return

            while True:
                try:
                    chunk = await process.stdout.read(4096)
                    if not chunk:
                        break

                    total_bytes += len(chunk)

                    if total_bytes > DEFAULT_MAX_BYTES and temp_file is None:
                        temp_file = tempfile.NamedTemporaryFile(
                            mode="wb", suffix=".log", prefix="pi-bash-", delete=False
                        )
                        temp_file_path = temp_file.name
                        for c in chunks:
                            temp_file.write(c)

                    if temp_file:
                        temp_file.write(chunk)

                    chunks.append(chunk)
                    chunks_bytes += len(chunk)

                    while chunks_bytes > max_chunks_bytes and len(chunks) > 1:
                        removed = chunks.pop(0)
                        chunks_bytes -= len(removed)

                    if on_update:
                        full_buffer = b"".join(chunks)
                        full_text = full_buffer.decode("utf-8", errors="replace")
                        truncation = truncate_tail(full_text)
                        on_update(
                            AgentToolResult(
                                content=[TextContent(type="text", text=truncation.content or "")],
                                details={
                                    "truncation": truncation.__dict__ if truncation.truncated else None,
                                    "full_output_path": temp_file_path,
                                },
                            )
                        )

                except asyncio.CancelledError:
                    break

        read_task = asyncio.create_task(read_stream())

        try:
            if timeout is not None and timeout > 0:
                await asyncio.wait_for(process.wait(), timeout=timeout)
            else:
                await process.wait()
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            if temp_file:
                temp_file.close()
            full_buffer = b"".join(chunks)
            output = full_buffer.decode("utf-8", errors="replace")
            return AgentToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=f"{output}\n\nCommand timed out after {timeout} seconds",
                    )
                ],
                details={"error": "timeout", "timeout": timeout, "command": command},
            )

        await read_task

        if temp_file:
            temp_file.close()

        if cancel_event and cancel_event.is_set():
            full_buffer = b"".join(chunks)
            output = full_buffer.decode("utf-8", errors="replace")
            return AgentToolResult(
                content=[TextContent(type="text", text=f"{output}\n\nCommand aborted")],
                details={"error": "aborted", "command": command},
            )

        full_buffer = b"".join(chunks)
        full_output = full_buffer.decode("utf-8", errors="replace")
        truncation = truncate_tail(full_output)
        output_text = truncation.content or "(no output)"

        details: dict[str, Any] = {}
        if truncation.truncated:
            details["truncation"] = truncation.__dict__
            details["full_output_path"] = temp_file_path

            start_line = truncation.total_lines - truncation.output_lines + 1
            end_line = truncation.total_lines

            if truncation.last_line_partial:
                last_line_size = format_size(len(full_output.split("\n")[-1].encode("utf-8")))
                output_text += f"\n\n[Showing last {format_size(truncation.output_bytes)} of line {end_line} (line is {last_line_size}). Full output: {temp_file_path}]"
            elif truncation.truncated_by == "lines":
                output_text += f"\n\n[Showing lines {start_line}-{end_line} of {truncation.total_lines}. Full output: {temp_file_path}]"
            else:
                output_text += f"\n\n[Showing lines {start_line}-{end_line} of {truncation.total_lines} ({format_size(DEFAULT_MAX_BYTES)} limit). Full output: {temp_file_path}]"

        if process.returncode is not None and process.returncode != 0:
            output_text += f"\n\nCommand exited with code {process.returncode}"
            return AgentToolResult(
                content=[TextContent(type="text", text=output_text)],
                details={"error": "nonzero_exit", "exit_code": process.returncode, **details},
            )

        return AgentToolResult(
            content=[TextContent(type="text", text=output_text)],
            details=details if details else None,
        )

    except Exception as e:
        if temp_file:
            temp_file.close()
        return AgentToolResult(
            content=[TextContent(type="text", text=f"Error running command: {e}")],
            details={"error": str(e), "command": command},
        )


def create_bash_tool(cwd: str, options: dict[str, Any] | None = None) -> AgentTool:
    return AgentTool(
        name="bash",
        label="Bash",
        description=f"Execute a bash command in the current working directory. Returns stdout and stderr. Output is truncated to last {DEFAULT_MAX_LINES} lines or {DEFAULT_MAX_BYTES // 1024}KB (whichever is hit first). If truncated, full output is saved to a temp file. Optionally provide a timeout in seconds.",
        parameters=_BASH_TOOL_PARAMETERS,
        execute=lambda tool_call_id, params, cancel_event, on_update: _execute_bash(
            tool_call_id, params, cwd, cancel_event, on_update
        ),
    )


bash_tool = create_bash_tool(os.getcwd())
