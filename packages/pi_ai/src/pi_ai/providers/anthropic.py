from __future__ import annotations

import asyncio
import json
from typing import Any, cast

from ..types import (
    AssistantMessage,
    AssistantMessageEvent,
    Context,
    DoneEvent,
    ErrorEvent,
    Message,
    Model,
    SimpleStreamOptions,
    StartEvent,
    StreamOptions,
    StopReason,
    TextContent,
    TextDeltaEvent,
    TextEndEvent,
    TextStartEvent,
    ThinkingContent,
    ThinkingEndEvent,
    ThinkingLevel,
    ThinkingStartEvent,
    Tool,
    ToolCall,
    ToolcallDeltaEvent,
    ToolcallEndEvent,
    ToolcallStartEvent,
    Usage,
    UsageCost,
    CacheRetention,
)
from ..event_stream import AssistantMessageEventStream
from ..env_keys import get_env_api_key
from ..models import calculate_cost
from ..stream import stream_simple

try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None  # type: ignore[misc,assignment]


def normalize_mistral_tool_id(tool_id: str) -> str:
    normalized = "".join(c for c in tool_id if c.isalnum())
    if len(normalized) < 9:
        padding = "ABCDEFGHI"
        normalized = normalized + padding[0: 9 - len(normalized)]
    elif len(normalized) > 9:
        normalized = normalized[0:9]
    return normalized


CLAUDE_CODE_TOOLS = [
    "Read", "Write", "Edit", "Bash", "Grep", "Glob",
    "AskUserQuestion", "EnterPlanMode", "ExitPlanMode", "KillShell",
    "NotebookEdit", "Skill", "Task", "TaskOutput", "TodoWrite",
    "WebFetch", "WebSearch",
]

CC_TOOL_LOOKUP = {t.lower(): t for t in CLAUDE_CODE_TOOLS}


def resolve_cache_retention(cache_retention: CacheRetention | None) -> str:
    if cache_retention:
        return cache_retention
    return "short"


class AnthropicOptions:
    def __init__(
        self,
        thinking_enabled: bool = False,
        thinking_budget_tokens: int | None = None,
        thinking_level: str | None = None,
        interleaved_thinking: bool = True,
    ) -> None:
        self.thinking_enabled = thinking_enabled
        self.thinking_budget_tokens = thinking_budget_tokens
        self.thinking_level = thinking_level
        self.interleaved_thinking = interleaved_thinking


def stream_anthropic_messages(
    model: Model,
    context: Context,
    options: SimpleStreamOptions | None = None,
) -> AssistantMessageEventStream:
    stream = AssistantMessageEventStream()

    async def _run():
        output: AssistantMessage = AssistantMessage(
            role="assistant",
            content=[],
            api=model.api,
            provider=model.provider,
            model=model.id,
            usage=Usage(
                input=0,
                output=0,
                cacheRead=0,
                cacheWrite=0,
                totalTokens=0,
                cost=UsageCost(),
            ),
            stopReason="stop",
            timestamp=0,
        )

        try:
            api_key = options.api_key if options and options.api_key else get_env_api_key(model.provider)
            if not api_key:
                raise ValueError(f"No API key for provider: {model.provider}")

            if Anthropic is None:
                raise ImportError("anthropic is required for Anthropic provider. Install with: pip install anthropic")

            client = Anthropic(api_key=api_key, base_url=model.base_url)  # type: ignore[misc]

            opts = AnthropicOptions() if options is None else AnthropicOptions(
                thinking_enabled=options.reasoning is not None,
                thinking_level=options.reasoning if options.reasoning else None,
            )

            params = _build_params(model, context, opts)

            headers = {}
            if options and options.headers:
                headers.update(options.headers)

            stream.push(StartEvent(partial=output))

            current_block: TextContent | ThinkingContent | None = None
            block_index = [0]
            thinking_signature: str | None = None

            with client.messages.stream(**params) as mstream:
                for event in mstream:
                    event_type = event.type

                    if event_type == "message_start":
                        msg = event.message
                        if hasattr(msg, "usage"):
                            usage_data = msg.usage
                            output.usage = Usage(
                                input=usage_data.input_tokens,
                                output=usage_data.output_tokens,
                                cacheRead=usage_data.cache_read_input_tokens,
                                cacheWrite=usage_data.cache_creation_input_tokens,
                                totalTokens=usage_data.total_tokens,
                                cost=calculate_cost(model, output.usage),
                            )

                    elif event_type == "content_block_start":
                        block = event.content_block
                        if block.type == "text":
                            current_block = TextContent(type="text", text="")
                            output.content.append(current_block)
                            block_index.append(len(output.content) - 1)
                            stream.push(
                                TextStartEvent(contentIndex=block_index[-1], partial=output)
                            )
                        elif block.type == "thinking":
                            current_block = ThinkingContent(type="thinking", thinking="", thinking_signature=None)
                            output.content.append(current_block)
                            block_index.append(len(output.content) - 1)
                            stream.push(
                                ThinkingStartEvent(contentIndex=block_index[-1], partial=output)
                            )

                    elif event_type == "content_block_delta":
                        if current_block and current_block.type == "text":
                            delta = event.delta
                            if delta.text:
                                current_block.text += delta.text
                                stream.push(
                                    TextDeltaEvent(
                                        contentIndex=block_index[-1],
                                        delta=delta.text,
                                        partial=output,
                                    )
                                )

                    elif event_type == "content_block_stop":
                        if current_block and current_block.type == "text":
                            stream.push(
                                TextEndEvent(
                                    contentIndex=block_index[-1],
                                    content=current_block.text,
                                    partial=output,
                                )
                            )
                        elif current_block and current_block.type == "thinking":
                            stream.push(
                                ThinkingEndEvent(
                                    contentIndex=block_index[-1],
                                    content=current_block.thinking,
                                    partial=output,
                                )
                            )

                    elif event_type == "tool_use_block_start":
                        tool_call = event.content_block
                        current_block = ToolCall(
                            type="toolCall",
                            id=tool_call.id,
                            name=tool_call.name,
                            arguments=tool_call.input,
                            thoughtSignature=tool_call.thought_signature,
                        )
                        output.content.append(current_block)
                        block_index.append(len(output.content) - 1)
                        stream.push(
                            ToolcallStartEvent(contentIndex=block_index[-1], partial=output)
                        )

                    elif event_type == "input_json_delta":
                        if current_block and current_block.type == "toolCall":
                            current_block.arguments.update(json.loads(event.delta))
                            stream.push(
                                ToolcallDeltaEvent(
                                    contentIndex=block_index[-1],
                                    delta=event.delta,
                                    partial=output,
                                )
                            )

                    elif event_type == "tool_use_block_stop":
                        if current_block and current_block.type == "toolCall":
                            current_block.id = normalize_mistral_tool_id(current_block.id)
                            stream.push(
                                ToolcallEndEvent(
                                    contentIndex=block_index[-1],
                                    toolCall=current_block,
                                    partial=output,
                                )
                            )

                    elif event_type == "message_stop":
                        finish_reason = _map_anthropic_stop_reason(event.message.stop_reason)
                        output.stop_reason = cast(StopReason, finish_reason)

                        if finish_reason == "toolUse" and output.content:
                            output.stop_reason = cast(StopReason, "toolUse")

                        output.usage = Usage(
                            input=0,
                            output=0,
                            cacheRead=0,
                            cacheWrite=0,
                            totalTokens=0,
                            cost=calculate_cost(model, output.usage),
                        )

                        stream.push(DoneEvent(reason=output.stop_reason, message=output))
                        return

        except asyncio.CancelledError:
            output.stop_reason = "aborted"
            output.error_message = "Request was aborted"
            stream.push(ErrorEvent(reason="aborted", error=output))
        except Exception as e:
            output.stop_reason = "error"
            output.error_message = str(e)
            stream.push(ErrorEvent(reason="error", error=output))
        finally:
            stream.end()

    asyncio.create_task(_run())
    return stream


def _map_anthropic_stop_reason(reason: str) -> str:
    mapping = {
        "end_turn": "stop",
        "max_tokens": "length",
        "stop_sequence": "toolUse",
    }
    return mapping.get(reason, "stop")


def _build_params(
    model: Model,
    context: Context,
    options: AnthropicOptions,
) -> dict[str, Any]:
    messages = []

    for msg in context.messages:
        if msg.role == "user":
            messages.append({"role": "user", "content": _format_user_content(msg.content)})
        elif msg.role == "assistant":
            messages.append({"role": "assistant", "content": _format_assistant_content(msg.content)})
        elif msg.role == "toolResult":
            messages.append({
                "role": "user",
                "content": _format_user_content(msg.content),
            })

    params: dict[str, Any] = {
        "model": model.id,
        "messages": messages,
        "stream": True,
        "max_tokens": model.max_tokens,
    }

    if context.system_prompt:
        params["system"] = context.system_prompt

    if context.tools:
        tools = []
        for tool in context.tools:
            tools.append({
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.parameters,
            })
        params["tools"] = tools

    return params


def _format_user_content(content) -> str | list[dict[str, Any]]:
    if isinstance(content, str):
        return content
    return [{"type": c.type, "text": c.text if c.type == "text" else ""} for c in content]


def _format_assistant_content(content: list) -> list[dict[str, Any]]:
    result = []
    for block in content:
        if block.type == "text":
            result.append({"type": "text", "text": block.text})
        elif block.type == "thinking":
            if block.thinking:
                result.append({
                    "type": "thinking",
                    "thinking": block.thinking,
                    "thinking_signature": block.thinking_signature,
                })
            elif block.type == "toolCall":
                result.append({
                    "type": "tool_use",
                    "id": block.id,
                    "name": block.name,
                    "input": block.arguments,
                })
    return result
