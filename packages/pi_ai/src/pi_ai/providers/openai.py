"""OpenAI provider - OpenAI-compatible API."""

from __future__ import annotations

import asyncio
import json
from typing import Any, cast

from ..env_keys import get_env_api_key
from ..event_stream import AssistantMessageEventStream
from ..models import calculate_cost
from ..types import (
    AssistantMessage,
    Context,
    DoneEvent,
    ErrorEvent,
    Message,
    Model,
    StartEvent,
    StopReason,
    StreamOptions,
    TextContent,
    TextDeltaEvent,
    ThinkingContent,
    ThinkingDeltaEvent,
    ToolCall,
    ToolcallDeltaEvent,
    ToolcallEndEvent,
    Usage,
    UsageCost,
)

try:
    import httpx
except ImportError:
    httpx = None  # type: ignore[misc,assignment]


def normalize_mistral_tool_id(tool_id: str) -> str:
    normalized = "".join(c for c in tool_id if c.isalnum())
    if len(normalized) < 9:
        padding = "ABCDEFGHI"
        normalized = normalized + padding[0 : 9 - len(normalized)]
    elif len(normalized) > 9:
        normalized = normalized[0:9]
    return normalized


def has_tool_history(messages: list[Message]) -> bool:
    for msg in messages:
        if msg.role == "toolResult":
            return True
        if msg.role == "assistant":
            for block in msg.content:
                if isinstance(block, ToolCall):
                    return True
    return False


class OpenAICompletionsOptions:
    def __init__(
        self,
        tool_choice: str | None = None,
        reasoning_effort: str | None = None,
    ) -> None:
        self.tool_choice = tool_choice
        self.reasoning_effort = reasoning_effort


def stream_openai_completions(
    model: Model,
    context: Context,
    options: StreamOptions | None = None,
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
            api_key = (
                options.api_key if options and options.api_key else get_env_api_key(model.provider)
            )
            if not api_key:
                raise ValueError(f"No API key for provider: {model.provider}")

            if httpx is None:
                raise ImportError(
                    "httpx is required for OpenAI provider. Install with: pip install httpx"
                )

            client = httpx.AsyncClient(
                base_url=model.base_url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    **(options.headers if options and options.headers else {}),
                },
                timeout=60.0,
            )

            params = _build_params(model, context, options)

            headers: dict[str, str] = {}
            if options and options.headers:
                headers.update(options.headers)

            stream.push(StartEvent(partial=output))

            response = await client.post(
                "/chat/completions",
                json=params,
                headers=headers,
                timeout=60.0,
            )

            stream_text = ""
            current_block: TextContent | ThinkingContent | ToolCall | None = None
            block_index = [0]

            async for line in response.aiter_lines():
                if line.strip():
                    data = json.loads(line)

                    if "choices" not in data or len(data["choices"]) == 0:
                        continue

                    choice = data["choices"][0]
                    delta = choice.get("delta", {})

                    if delta.get("finish_reason"):
                        output.stop_reason = cast(
                            "StopReason", _map_finish_reason(delta["finish_reason"])
                        )

                    if "usage" in data:
                        usage_data = data["usage"]
                        output.usage = Usage(
                            input=usage_data.get("prompt_tokens", 0),
                            output=usage_data.get("completion_tokens", 0),
                            cacheRead=usage_data.get("prompt_tokens_details", {}).get(
                                "cached_tokens", 0
                            ),
                            cacheWrite=0,
                            totalTokens=usage_data.get("total_tokens", 0),
                            cost=calculate_cost(model, output.usage),
                        )
                        calculate_cost(model, output.usage)

                    if delta.get("content"):
                        content = delta["content"]
                        if content:
                            if not current_block or current_block.type != "text":
                                current_block = TextContent(type="text", text="")
                                output.content.append(current_block)
                                block_index.append(len(output.content) - 1)

                            current_block.text += content
                            stream.push(
                                TextDeltaEvent(
                                    contentIndex=block_index[-1],
                                    delta=content,
                                    partial=output,
                                )
                            )

                    if delta.get("reasoning_content"):
                        reasoning = delta["reasoning_content"]
                        if reasoning:
                            if not current_block or current_block.type != "thinking":
                                current_block = ThinkingContent(
                                    type="thinking", thinking="", thinking_signature=None
                                )
                                output.content.append(current_block)
                                block_index.append(len(output.content) - 1)

                            current_block.thinking += reasoning
                            stream.push(
                                ThinkingDeltaEvent(
                                    contentIndex=block_index[-1],
                                    delta=reasoning,
                                    partial=output,
                                )
                            )

                    if delta.get("tool_calls"):
                        for tool_delta in delta["tool_calls"]:
                            if not current_block or current_block.type != "toolCall":
                                current_block = ToolCall(
                                    type="toolCall",
                                    id="",
                                    name="",
                                    arguments={},
                                    thoughtSignature=None,
                                )
                                output.content.append(current_block)
                                block_index.append(len(output.content) - 1)

                            if "index" in tool_delta:
                                tool_call = current_block
                            else:
                                tool_call = current_block  # use current_block as default
                            if "id" in tool_delta:
                                tool_call.id = normalize_mistral_tool_id(tool_delta["id"])
                            if "function" in tool_delta:
                                tool_call.name = tool_delta["function"]

                            if "arguments" in tool_delta and isinstance(
                                tool_delta["arguments"], str
                            ):
                                args_str = tool_delta["arguments"]
                                if tool_call.arguments:
                                    tool_call.arguments = json.loads(tool_call.arguments + args_str)
                                else:
                                    tool_call.arguments = json.loads(args_str)
                            elif "arguments" in tool_delta:
                                tool_call.arguments = tool_delta["arguments"]

                            if "index" not in tool_delta:
                                stream.push(
                                    ToolcallEndEvent(
                                        contentIndex=block_index[-1],
                                        toolCall=tool_call,
                                        partial=output,
                                    )
                                )
                            else:
                                stream.push(
                                    ToolcallDeltaEvent(
                                        contentIndex=block_index[-1],
                                        delta=json.dumps(tool_delta["arguments"]),
                                        partial=output,
                                    )
                                )

            stream.push(DoneEvent(reason=output.stop_reason, message=output))

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


def _map_finish_reason(reason: str) -> str:
    mapping = {
        "stop": "stop",
        "length": "length",
        "tool_calls": "toolUse",
        "content_filter": "stop",
    }
    return mapping.get(reason, "stop")


def _build_params(
    model: Model,
    context: Context,
    options: StreamOptions | None,
) -> dict[str, Any]:
    messages = []

    for msg in context.messages:
        if msg.role == "user":
            messages.append({"role": "user", "content": _format_user_content(msg.content)})
        elif msg.role == "assistant":
            messages.append(
                {"role": "assistant", "content": _format_assistant_content(msg.content)}
            )
        elif msg.role == "toolResult":
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": msg.tool_call_id,
                    "tool_name": msg.tool_name,
                    "content": _format_tool_content(msg.content),
                }
            )

    params = {
        "model": model.id,
        "messages": messages,
        "stream": True,
    }

    if context.system_prompt:
        params["system_prompt"] = context.system_prompt

    if context.tools:
        tools = []
        for tool in context.tools:
            tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters,
                    },
                }
            )
        params["tools"] = tools

    if options:
        if options.temperature is not None:
            params["temperature"] = options.temperature
        if options.max_tokens is not None:
            params["max_tokens"] = options.max_tokens

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
            result.append(
                {
                    "type": "thinking",
                    "thinking": block.thinking,
                    "reasoning_signature": block.thinking_signature,
                }
            )
        elif block.type == "toolCall":
            result.append(
                {
                    "type": "tool_call",
                    "id": block.id,
                    "name": block.name,
                    "arguments": block.arguments,
                }
            )
    return result


def _format_tool_content(content: list) -> str | list[dict[str, Any]]:
    if isinstance(content, str):
        return content
    return [{"type": c.type, "text": c.text if c.type == "text" else ""} for c in content]
