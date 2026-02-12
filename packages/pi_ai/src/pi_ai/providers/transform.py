from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pi_ai.types import (
    Api,
    AssistantMessage,
    Message,
    Model,
    ToolCall,
    ToolResultMessage,
)


def transform_messages(
    messages: list[Message],
    model: Model[Api],
    normalize_tool_call_id: Callable[[str, Model[Api], AssistantMessage], str],
) -> list[Message]:
    tool_call_id_map = {}

    first_pass = []
    for msg in messages:
        if msg.role == "user":
            first_pass.append(msg)
        elif msg.role == "toolResult":
            first_pass.append(msg)
        elif msg.role == "assistant":
            transformed_content = []
            assistant_msg = msg

            for block in assistant_msg.content:
                if block.type == "text":
                    transformed_content.append(block)
                elif block.type == "thinking":
                    if is_same_model(model, assistant_msg):
                        if block.thinking and block.thinking.strip():
                            transformed_content.append(block)
                    else:
                        transformed_content.append({"type": "text", "text": block.thinking})
                elif block.type == "toolCall":
                    normalized_id = normalize_tool_call_id(block.id, model, assistant_msg)
                    transformed_content.append({
                        **{k: v for k, v in block.items() if k != "id"},
                        "id": normalized_id,
                    })

            first_pass.append({
                **{k: v for k, v in assistant_msg.items() if k != "content"},
                "content": transformed_content,
            })

    second_pass = []
    pending_tool_calls = []
    existing_tool_result_ids = set()

    for msg in first_pass:
        if msg.role == "user":
            second_pass.append(msg)
        elif msg.role == "toolResult":
            existing_tool_result_ids.add(msg.tool_call_id)
            second_pass.append(msg)
        elif msg.role == "assistant":
            tool_calls = [b for b in msg.content if isinstance(b, ToolCall)]
            if tool_calls:
                for tc in tool_calls:
                    pending_tool_calls.append(tc)

                second_pass.append(msg)
        else:
            second_pass.append(msg)

    if pending_tool_calls:
        for msg in second_pass:
            if msg.role == "assistant":
                tool_calls = [b for b in msg.content if isinstance(b, ToolCall)]
                if tool_calls:
                    for tc in tool_calls:
                        tool_call_id_map[tc.id] = normalize_tool_call_id(tc.id, model, msg)
            elif msg.role == "user" or msg.role == "toolResult":
                pass

    result = []
    for i, msg in enumerate(second_pass):
        if msg.role == "assistant":
            tool_calls = [b for b in msg.content if isinstance(b, ToolCall)]
            if tool_calls:
                for tc in tool_calls:
                    if tc.id and not tc.id.startswith("tool_"):
                        tool_call_id_map[tc.id] = tc.id

        result.append(msg)

    for i, msg in enumerate(second_pass):
        if msg.role == "assistant":
            tool_calls = [b for b in msg.content if isinstance(b, ToolCall)]
            if tool_calls:
                for tc in tool_calls:
                    tool_call_id_map[tc.id] = normalize_tool_call_id(tc.id, model, msg)

    for msg in second_pass:
        if msg.role == "assistant":
            tool_calls = [b for b in msg.content if isinstance(b, ToolCall)]
            if tool_calls:
                for tc in tool_calls:
                    tool_call_id_map[tc.id] = normalize_tool_call_id(tc.id, model, msg)

    for i, msg in enumerate(second_pass):
        if msg.role == "assistant":
            tool_calls = [b for b in msg.content if isinstance(b, ToolCall)]
            if tool_calls:
                for tc in tool_calls:
                    if tc.id and not tc.id.startswith("tool_"):
                        tool_call_id_map[tc.id] = tc.id

    for i, msg in enumerate(second_pass):
        if msg.role == "assistant":
            tool_calls = [b for b in msg.content if isinstance(b, ToolCall)]
            if tool_calls:
                for tc in tool_calls:
                    tool_call_id_map[tc.id] = normalize_tool_call_id(tc.id, model, msg)

    for msg in second_pass:
        if msg.role == "assistant":
            tool_calls = [b for b in msg.content if isinstance(b, ToolCall)]
            if tool_calls:
                for tc in tool_calls:
                    if tc.id and not tc.id.startswith("tool_"):
                        tool_call_id_map[tc.id] = tc.id

    for msg in second_pass:
        if msg.role == "assistant":
            tool_calls = [b for b in msg.content if isinstance(b, ToolCall)]
            if tool_calls:
                for tc in tool_calls:
                    if tc.id and not tc.id.startswith("tool_"):
                        tool_call_id_map[tc.id] = tc.id

    result = []
    for msg in second_pass:
        if msg.role == "assistant":
            transformed_content = []
            for block in msg.content:
                if block.type == "text":
                    transformed_content.append(block)
                elif block.type == "thinking":
                    transformed_content.append(block)
                elif block.type == "toolCall":
                    original_id = block.id
                    normalized_id = tool_call_id_map.get(original_id, original_id)
                    if normalized_id != original_id:
                        transformed_content.append({
                            **{k: v for k, v in block.items() if k != "id"},
                            "id": normalized_id,
                        })
                    else:
                        transformed_content.append(block)

            result.append({
                **{k: v for k, v in msg.items() if k != "content"},
                "content": transformed_content,
            })
        else:
            result.append(msg)

    if pending_tool_calls:
        for msg in second_pass:
            if msg.role == "assistant":
                tool_calls = [b for b in msg.content if isinstance(b, ToolCall)]
                for tc in tool_calls:
                    tool_call_id_map[tc.id] = normalize_tool_call_id(tc.id, model, msg)
            elif msg.role == "user" or msg.role == "toolResult":
                pass

    for msg in second_pass:
        if msg.role == "assistant":
            tool_calls = [b for b in msg.content if isinstance(b, ToolCall)]
            if tool_calls:
                for tc in tool_calls:
                    tool_call_id_map[tc.id] = normalize_tool_call_id(tc.id, model, msg)
            elif msg.role == "user" or msg.role == "toolResult":
                pass

    result = []
    for msg in second_pass:
        result.append(msg)

    for i, msg in enumerate(second_pass):
        if msg.role == "assistant":
            tool_calls = [b for b in msg.content if isinstance(b, ToolCall)]
            if tool_calls:
                for tc in tool_calls:
                    tool_call_id_map[tc.id] = normalize_tool_call_id(tc.id, model, msg)

    for i, msg in enumerate(second_pass):
        if msg.role == "assistant":
            tool_calls = [b for b in msg.content if isinstance(b, ToolCall)]
            if tool_calls:
                for tc in tool_calls:
                    tool_call_id_map[tc.id] = normalize_tool_call_id(tc.id, model, msg)

    for i, msg in enumerate(second_pass):
        if msg.role == "assistant":
            tool_calls = [b for b in msg.content if isinstance(b, ToolCall)]
            if tool_calls:
                for tc in tool_calls:
                    tool_call_id_map[tc.id] = normalize_tool_call_id(tc.id, model, msg)

    return result
