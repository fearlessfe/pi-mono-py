"""Edit tool - edits files by replacing exact text matches with fuzzy matching support."""

from __future__ import annotations

import asyncio
import os
from pi_agent.types import AgentToolUpdateCallback
from typing import Any

from pi_agent import AgentTool, AgentToolResult
from pi_ai.types import TextContent

from pi_coding.utils import (
    detect_line_ending,
    fuzzy_find_text,
    generate_diff_string,
    normalize_for_fuzzy_match,
    normalize_to_lf,
    resolve_to_cwd,
    restore_line_endings,
    strip_bom,
)

_EDIT_TOOL_PARAMETERS = {
    "type": "object",
    "properties": {
        "path": {
            "type": "string",
            "description": "Path to the file to edit (relative or absolute)",
        },
        "old_text": {
            "type": "string",
            "description": "Exact text to find and replace (must match exactly)",
        },
        "new_text": {
            "type": "string",
            "description": "New text to replace the old text with",
        },
    },
    "required": ["path", "old_text", "new_text"],
}


async def _execute_edit(
    tool_call_id: str,
    params: dict[str, Any],
    cwd: str,
    cancel_event: asyncio.Event | None,
    on_update: AgentToolUpdateCallback | None,
) -> AgentToolResult:
    path: str = params.get("path", "")
    old_text: str = params.get("old_text", "")
    new_text: str = params.get("new_text", "")

    if not all([path, old_text, new_text]):
        return AgentToolResult(
            content=[
                TextContent(
                    type="text", text="Error: 'path', 'old_text', and 'new_text' parameters are required"
                )
            ],
            details={"error": "missing_parameters"},
        )

    absolute_path = resolve_to_cwd(path, cwd)

    if cancel_event and cancel_event.is_set():
        return AgentToolResult(
            content=[TextContent(type="text", text="Operation aborted")],
            details={"error": "aborted"},
        )

    try:
        if not os.path.exists(absolute_path):
            return AgentToolResult(
                content=[TextContent(type="text", text=f"Error: File not found: {path}")],
                details={"error": "file_not_found", "path": absolute_path},
            )

        with open(absolute_path, encoding="utf-8") as f:
            raw_content = f.read()

        if cancel_event and cancel_event.is_set():
            return AgentToolResult(
                content=[TextContent(type="text", text="Operation aborted")],
                details={"error": "aborted"},
            )

        bom, content = strip_bom(raw_content)
        original_ending = detect_line_ending(content)
        normalized_content = normalize_to_lf(content)
        normalized_old_text = normalize_to_lf(old_text)
        normalized_new_text = normalize_to_lf(new_text)

        match_result = fuzzy_find_text(normalized_content, normalized_old_text)

        if not match_result.found:
            return AgentToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=f"Could not find the exact text in {path}. The old text must match exactly including all whitespace and newlines.",
                    )
                ],
                details={"error": "text_not_found", "path": absolute_path},
            )

        fuzzy_content = normalize_for_fuzzy_match(normalized_content)
        fuzzy_old_text = normalize_for_fuzzy_match(normalized_old_text)
        occurrences = fuzzy_content.count(fuzzy_old_text)

        if occurrences > 1:
            return AgentToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=f"Found {occurrences} occurrences of the text in {path}. The text must be unique. Please provide more context to make it unique.",
                    )
                ],
                details={"error": "multiple_occurrences", "occurrences": occurrences, "path": absolute_path},
            )

        if cancel_event and cancel_event.is_set():
            return AgentToolResult(
                content=[TextContent(type="text", text="Operation aborted")],
                details={"error": "aborted"},
            )

        base_content = match_result.content_for_replacement
        new_content = (
            base_content[: match_result.index]
            + normalized_new_text
            + base_content[match_result.index + match_result.match_length :]
        )

        if base_content == new_content:
            return AgentToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=f"No changes made to {path}. The replacement produced identical content.",
                    )
                ],
                details={"error": "no_changes", "path": absolute_path},
            )

        final_content = bom + restore_line_endings(new_content, original_ending)
        with open(absolute_path, "w", encoding="utf-8") as f:
            f.write(final_content)

        diff_result = generate_diff_string(base_content, new_content)
        return AgentToolResult(
            content=[TextContent(type="text", text=f"Successfully replaced text in {path}.")],
            details={"diff": diff_result["diff"], "first_changed_line": diff_result["first_changed_line"]},
        )

    except Exception as e:
        return AgentToolResult(
            content=[TextContent(type="text", text=f"Error editing file: {e}")],
            details={"error": str(e), "path": absolute_path},
        )


def create_edit_tool(cwd: str, options: dict[str, Any] | None = None) -> AgentTool:
    return AgentTool(
        name="edit",
        label="Edit",
        description="Edit a file by replacing exact text. The old_text must match exactly (including whitespace). Use this for precise, surgical edits.",
        parameters=_EDIT_TOOL_PARAMETERS,
        execute=lambda tool_call_id, params, cancel_event, on_update: _execute_edit(
            tool_call_id, params, cwd, cancel_event, on_update
        ),
    )


edit_tool = create_edit_tool(os.getcwd())
