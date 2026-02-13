"""Tool utilities for pi-agent: validation, built-in tools."""
from __future__ import annotations

import asyncio
import json
from typing import Any

try:
    import jsonschema
    from jsonschema import validate, ValidationError as JsonSchemaValidationError
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False
    JsonSchemaValidationError = Exception  # type: ignore

from pi_agent.types import AgentTool, AgentToolResult, AgentToolUpdateCallback
from pi_ai.types import TextContent


class ToolValidationError(Exception):
    """Raised when tool parameter validation fails."""
    def __init__(self, tool_name: str, errors: list[str]):
        self.tool_name = tool_name
        self.errors = errors
        super().__init__(f"Tool '{tool_name}' parameter validation failed: {', '.join(errors)}")


def validate_tool_params(
    schema: dict[str, Any],
    params: dict[str, Any],
) -> list[str]:
    """
    Validate parameters against a JSON Schema.
    
    Returns a list of validation errors (empty if valid).
    """
    if not HAS_JSONSCHEMA:
        return []
    
    errors = []
    try:
        validate(instance=params, schema=schema)
    except JsonSchemaValidationError as e:
        errors.append(str(e.message))
    
    return errors


def validate_tool_call(
    tool: AgentTool,
    args: dict[str, Any],
) -> list[str]:
    """
    Validate tool call arguments against the tool's parameter schema.
    
    Returns a list of validation errors (empty if valid).
    """
    if not tool.parameters:
        return []
    
    return validate_tool_params(tool.parameters, args)


def create_tool(
    name: str,
    description: str,
    parameters: dict[str, Any] | None,
    execute_fn,
    label: str | None = None,
) -> AgentTool:
    """
    Create an AgentTool with automatic parameter validation.
    
    Args:
        name: Tool name
        description: Tool description
        parameters: JSON Schema for parameters
        execute_fn: Async function(tool_call_id, args, cancel_event, on_update) -> AgentToolResult
        label: Human-readable label
    
    Returns:
        AgentTool instance
    """
    async def validated_execute(
        tool_call_id: str,
        args: dict[str, Any],
        cancel_event: asyncio.Event | None,
        on_update: AgentToolUpdateCallback | None,
    ) -> AgentToolResult:
        # Validate parameters
        if parameters:
            errors = validate_tool_params(parameters, args)
            if errors:
                return AgentToolResult(
                    content=[TextContent(type="text", text=f"Parameter validation failed: {', '.join(errors)}")],
                    details={"validation_errors": errors},
                )
        
        return await execute_fn(tool_call_id, args, cancel_event, on_update)
    
    return AgentTool(
        name=name,
        description=description,
        parameters=parameters or {},
        label=label or name,
        execute=validated_execute,
    )


# ============================================================================
# Built-in Tools
# ============================================================================


async def _execute_read_file(
    tool_call_id: str,
    args: dict[str, Any],
    cancel_event: asyncio.Event | None,
    on_update: AgentToolUpdateCallback | None,
) -> AgentToolResult:
    """Execute read_file tool."""
    file_path = args.get("file_path", "")
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        return AgentToolResult(
            content=[TextContent(type="text", text=content)],
            details={"file_path": file_path, "size": len(content)},
        )
    except FileNotFoundError:
        return AgentToolResult(
            content=[TextContent(type="text", text=f"File not found: {file_path}")],
            details={"error": "file_not_found", "file_path": file_path},
        )
    except Exception as e:
        return AgentToolResult(
            content=[TextContent(type="text", text=f"Error reading file: {e}")],
            details={"error": str(e), "file_path": file_path},
        )


async def _execute_write_file(
    tool_call_id: str,
    args: dict[str, Any],
    cancel_event: asyncio.Event | None,
    on_update: AgentToolUpdateCallback | None,
) -> AgentToolResult:
    """Execute write_file tool."""
    file_path = args.get("file_path", "")
    content = args.get("content", "")
    
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        return AgentToolResult(
            content=[TextContent(type="text", text=f"Successfully wrote {len(content)} bytes to {file_path}")],
            details={"file_path": file_path, "bytes_written": len(content)},
        )
    except Exception as e:
        return AgentToolResult(
            content=[TextContent(type="text", text=f"Error writing file: {e}")],
            details={"error": str(e), "file_path": file_path},
        )


async def _execute_bash(
    tool_call_id: str,
    args: dict[str, Any],
    cancel_event: asyncio.Event | None,
    on_update: AgentToolUpdateCallback | None,
) -> AgentToolResult:
    """Execute bash tool."""
    import subprocess
    
    command = args.get("command", "")
    timeout = args.get("timeout", 60)
    cwd = args.get("cwd", None)
    
    try:
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            process.kill()
            return AgentToolResult(
                content=[TextContent(type="text", text=f"Command timed out after {timeout}s")],
                details={"error": "timeout", "timeout": timeout},
            )
        
        output = stdout.decode("utf-8", errors="replace")
        error_output = stderr.decode("utf-8", errors="replace")
        
        result_text = output
        if error_output:
            result_text += f"\n[stderr]\n{error_output}"
        
        return AgentToolResult(
            content=[TextContent(type="text", text=result_text)],
            details={
                "exit_code": process.returncode,
                "stdout_length": len(output),
                "stderr_length": len(error_output),
            },
        )
    except Exception as e:
        return AgentToolResult(
            content=[TextContent(type="text", text=f"Error executing command: {e}")],
            details={"error": str(e)},
        )


async def _execute_grep(
    tool_call_id: str,
    args: dict[str, Any],
    cancel_event: asyncio.Event | None,
    on_update: AgentToolUpdateCallback | None,
) -> AgentToolResult:
    """Execute grep tool."""
    import subprocess
    
    pattern = args.get("pattern", "")
    path = args.get("path", ".")
    ignore_case = args.get("ignore_case", False)
    
    cmd = ["grep", "-r", "-n"]
    if ignore_case:
        cmd.append("-i")
    cmd.extend([pattern, path])
    
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        
        stdout, stderr = await process.communicate()
        
        output = stdout.decode("utf-8", errors="replace")
        
        return AgentToolResult(
            content=[TextContent(type="text", text=output or "No matches found")],
            details={"pattern": pattern, "path": path, "exit_code": process.returncode},
        )
    except Exception as e:
        return AgentToolResult(
            content=[TextContent(type="text", text=f"Error executing grep: {e}")],
            details={"error": str(e)},
        )


# Tool schemas
READ_FILE_SCHEMA = {
    "type": "object",
    "properties": {
        "file_path": {
            "type": "string",
            "description": "The path to the file to read",
        },
    },
    "required": ["file_path"],
}

WRITE_FILE_SCHEMA = {
    "type": "object",
    "properties": {
        "file_path": {
            "type": "string",
            "description": "The path to the file to write",
        },
        "content": {
            "type": "string",
            "description": "The content to write to the file",
        },
    },
    "required": ["file_path", "content"],
}

BASH_SCHEMA = {
    "type": "object",
    "properties": {
        "command": {
            "type": "string",
            "description": "The bash command to execute",
        },
        "timeout": {
            "type": "number",
            "description": "Timeout in seconds (default 60)",
            "default": 60,
        },
        "cwd": {
            "type": "string",
            "description": "Working directory for the command",
        },
    },
    "required": ["command"],
}

GREP_SCHEMA = {
    "type": "object",
    "properties": {
        "pattern": {
            "type": "string",
            "description": "The pattern to search for",
        },
        "path": {
            "type": "string",
            "description": "The path to search in (default: current directory)",
            "default": ".",
        },
        "ignore_case": {
            "type": "boolean",
            "description": "Whether to ignore case (default: false)",
            "default": False,
        },
    },
    "required": ["pattern"],
}


def create_read_file_tool() -> AgentTool:
    """Create a read_file tool."""
    return create_tool(
        name="read_file",
        description="Read the contents of a file",
        parameters=READ_FILE_SCHEMA,
        execute_fn=_execute_read_file,
        label="Read File",
    )


def create_write_file_tool() -> AgentTool:
    """Create a write_file tool."""
    return create_tool(
        name="write_file",
        description="Write content to a file",
        parameters=WRITE_FILE_SCHEMA,
        execute_fn=_execute_write_file,
        label="Write File",
    )


def create_bash_tool() -> AgentTool:
    """Create a bash tool."""
    return create_tool(
        name="bash",
        description="Execute a bash command",
        parameters=BASH_SCHEMA,
        execute_fn=_execute_bash,
        label="Bash",
    )


def create_grep_tool() -> AgentTool:
    """Create a grep tool."""
    return create_tool(
        name="grep",
        description="Search for a pattern in files",
        parameters=GREP_SCHEMA,
        execute_fn=_execute_grep,
        label="Grep",
    )


def get_builtin_tools() -> list[AgentTool]:
    """Get all built-in tools."""
    return [
        create_read_file_tool(),
        create_write_file_tool(),
        create_edit_file_tool(),
        create_bash_tool(),
        create_grep_tool(),
    ]


# ============================================================================
# Edit File Tool
# ============================================================================


async def _execute_edit_file(
    tool_call_id: str,
    args: dict[str, Any],
    cancel_event: asyncio.Event | None,
    on_update: AgentToolUpdateCallback | None,
) -> AgentToolResult:
    """Execute edit_file tool.
    
    Performs a precise string replacement in a file.
    The old_string must exist exactly as provided for the edit to succeed.
    """
    file_path = args.get("file_path", "")
    old_string = args.get("old_string", "")
    new_string = args.get("new_string", "")
    replace_all = args.get("replace_all", False)
    
    # Validate required parameters
    if not file_path:
        return AgentToolResult(
            content=[TextContent(type="text", text="Error: file_path is required")],
            details={"error": "missing_file_path"},
        )
    
    if not old_string:
        return AgentToolResult(
            content=[TextContent(type="text", text="Error: old_string is required")],
            details={"error": "missing_old_string"},
        )
    
    try:
        # Read the file
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Count occurrences
        occurrences = content.count(old_string)
        
        if occurrences == 0:
            return AgentToolResult(
                content=[TextContent(type="text", text=f"Error: old_string not found in {file_path}")],
                details={
                    "error": "old_string_not_found",
                    "file_path": file_path,
                    "old_string_length": len(old_string),
                },
            )
        
        # Perform replacement
        if replace_all:
            new_content = content.replace(old_string, new_string)
            replacements = occurrences
        else:
            if occurrences > 1:
                return AgentToolResult(
                    content=[TextContent(type="text", text=f"Error: old_string found {occurrences} times in {file_path}. Use replace_all=true to replace all occurrences, or provide a more specific old_string.")],
                    details={
                        "error": "multiple_matches",
                        "file_path": file_path,
                        "occurrences": occurrences,
                    },
                )
            new_content = content.replace(old_string, new_string, 1)
            replacements = 1
        
        # Write back
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        
        return AgentToolResult(
            content=[TextContent(type="text", text=f"Successfully edited {file_path}: replaced {replacements} occurrence(s)")],
            details={
                "file_path": file_path,
                "replacements": replacements,
                "old_length": len(old_string),
                "new_length": len(new_string),
            },
        )
    
    except FileNotFoundError:
        return AgentToolResult(
            content=[TextContent(type="text", text=f"Error: File not found: {file_path}")],
            details={"error": "file_not_found", "file_path": file_path},
        )
    except PermissionError:
        return AgentToolResult(
            content=[TextContent(type="text", text=f"Error: Permission denied: {file_path}")],
            details={"error": "permission_denied", "file_path": file_path},
        )
    except Exception as e:
        return AgentToolResult(
            content=[TextContent(type="text", text=f"Error editing file: {e}")],
            details={"error": str(e), "file_path": file_path},
        )


EDIT_FILE_SCHEMA = {
    "type": "object",
    "properties": {
        "file_path": {
            "type": "string",
            "description": "The path to the file to edit",
        },
        "old_string": {
            "type": "string",
            "description": "The text to search for and replace",
        },
        "new_string": {
            "type": "string",
            "description": "The text to replace old_string with",
        },
        "replace_all": {
            "type": "boolean",
            "description": "If true, replace all occurrences. If false (default), only replace the first occurrence and error if multiple matches found.",
            "default": False,
        },
    },
    "required": ["file_path", "old_string", "new_string"],
}


def create_edit_file_tool() -> AgentTool:
    """Create an edit_file tool for precise string replacement."""
    return create_tool(
        name="edit_file",
        description="Perform a precise string replacement in a file. The old_string must match exactly for the edit to succeed. Use this for surgical edits rather than rewriting entire files.",
        parameters=EDIT_FILE_SCHEMA,
        execute_fn=_execute_edit_file,
        label="Edit File",
    )
