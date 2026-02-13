from __future__ import annotations

import asyncio
import json
from typing import Any

from pi_ai.types import (
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
    ThinkingContent,
    ThinkingDeltaEvent,
    Tool,
    ToolCall,
    ToolcallDeltaEvent,
    ToolcallEndEvent,
    Usage,
    UsageCost,
)
from pi_ai.event_stream import AssistantMessageEventStream
from pi_ai.env_keys import get_env_api_key
from pi_ai.models import calculate_cost
from pi_ai.stream import stream_simple

try:
    import httpx
except ImportError:
    httpx = None


def normalize_zhipu_tool_id(tool_id: str) -> str:
    normalized = "".join(c for c in tool_id if c.isalnum())
    if len(normalized) < 9:
        padding = "ABCDEFGHI"
        normalized = normalized + padding[0: 9 - len(normalized)]
    elif len(normalized) > 9:
        normalized = normalized[0:9]
    return normalized


class ZhipuOptions:
    def __init__(
        self,
        tool_choice: str | None = None,
    ) -> None:
        self.tool_choice = tool_choice


def stream_zhipu(
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
                cache_read=0,
                cache_write=0,
                total_tokens=0,
                cost=UsageCost(),
            ),
            stop_reason=StopReason.stop,
            timestamp=0,
        )

        try:
            api_key = options.api_key if options and options.api_key else get_env_api_key(model.provider)
            if not api_key:
                raise ValueError(f"No API key for provider: {model.provider}")

            if httpx is None:
                raise ImportError("httpx is required for Zhipu provider. Install with: pip install httpx")

            opts = ZhipuOptions() if options is None else ZhipuOptions(
                tool_choice=options.tool_choice,
            )

            params = _build_params(model, context, opts)

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            if options and options.headers:
                headers.update(options.headers)

            stream.push(StartEvent(partial=output))

            current_block: TextContent | ThinkingContent | None = None
            block_index = [0]

            async with httpx.AsyncClient(
                base_url=model.base_url,
                headers=headers,
                timeout=120.0,
            ) as client:
                async with client.stream("POST", "/chat/completions", json=params) as response:
                    async for line in response.aiter_lines():
                        if not line.strip() or not line.startswith("data: "):
                            continue

                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break

                        try:
                            data = json.loads(data_str)
                        except json.JSONDecodeError:
                            continue

                        if "choices" not in data or len(data["choices"]) == 0:
                            continue

                        choice = data["choices"][0]
                        delta = choice.get("delta", {})

                        if choice.get("finish_reason"):
                            output.stop_reason = _map_finish_reason(choice["finish_reason"])

                        if "usage" in data:
                            usage_data = data["usage"]
                            output.usage = Usage(
                                input=usage_data.get("prompt_tokens", 0),
                                output=usage_data.get("completion_tokens", 0),
                                cache_read=0,
                                cache_write=0,
                                total_tokens=usage_data.get("total_tokens", 0),
                                cost=calculate_cost(model, output.usage),
                            )

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
                                        content_index=block_index[-1],
                                        delta=content,
                                        partial=output,
                                    )
                                )

                        if delta.get("reasoning_content"):
                            reasoning = delta["reasoning_content"]
                            if reasoning:
                                if not current_block or current_block.type != "thinking":
                                    current_block = ThinkingContent(type="thinking", thinking="", thinking_signature=None)
                                    output.content.append(current_block)
                                    block_index.append(len(output.content) - 1)

                                current_block.thinking += reasoning
                                stream.push(
                                    ThinkingDeltaEvent(
                                        content_index=block_index[-1],
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
                                        thought_signature=None,
                                    )
                                    output.content.append(current_block)
                                    block_index.append(len(output.content) - 1)

                                if "id" in tool_delta:
                                    current_block.id = normalize_zhipu_tool_id(tool_delta["id"])
                                if "function" in tool_delta:
                                    func = tool_delta["function"]
                                    if "name" in func:
                                        current_block.name = func["name"]
                                    if "arguments" in func:
                                        args_str = func["arguments"]
                                        if isinstance(args_str, str):
                                            try:
                                                current_block.arguments = json.loads(args_str)
                                            except json.JSONDecodeError:
                                                pass
                                        elif isinstance(args_str, dict):
                                            current_block.arguments = args_str

                                stream.push(
                                    ToolcallEndEvent(
                                        content_index=block_index[-1],
                                        tool_call=current_block,
                                        partial=output,
                                    )
                                )

            stream.push(DoneEvent(reason=output.stop_reason, message=output))

        except asyncio.CancelledError:
            output.stop_reason = StopReason.aborted
            output.error_message = "Request was aborted"
            stream.push(ErrorEvent(reason=StopReason.aborted, error=output))
        except Exception as e:
            output.stop_reason = StopReason.error
            output.error_message = str(e)
            stream.push(ErrorEvent(reason=StopReason.error, error=output))
        finally:
            stream.end()

    asyncio.create_task(_run())
    return stream


def _map_finish_reason(reason: str) -> StopReason:
    mapping = {
        "stop": StopReason.stop,
        "length": StopReason.length,
        "tool_calls": StopReason.toolUse,
        "content_filter": StopReason.stop,
    }
    return mapping.get(reason, StopReason.stop)


def _build_params(
    model: Model,
    context: Context,
    options: ZhipuOptions,
) -> dict[str, Any]:
    messages = []

    for msg in context.messages:
        if msg.role == "user":
            messages.append({"role": "user", "content": _format_user_content(msg.content)})
        elif msg.role == "assistant":
            messages.append({"role": "assistant", "content": _format_assistant_content(msg.content)})
        elif msg.role == "toolResult":
            messages.append({
                "role": "tool",
                "tool_call_id": msg.tool_call_id,
                "content": _format_tool_content(msg.content),
            })

    params: dict[str, Any] = {
        "model": model.id,
        "messages": messages,
        "stream": True,
    }

    if context.system_prompt:
        params.insert(0, {"role": "system", "content": context.system_prompt})
        params["messages"] = [{"role": "system", "content": context.system_prompt}] + params["messages"]

    if context.tools:
        tools = []
        for tool in context.tools:
            tools.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            })
        params["tools"] = tools

    if options.tool_choice:
        params["tool_choice"] = options.tool_choice

    return params


def _format_user_content(content) -> str | list[dict[str, Any]]:
    if isinstance(content, str):
        return content
    result = []
    for c in content:
        if c.type == "text":
            result.append({"type": "text", "text": c.text})
        elif c.type == "image":
            result.append({
                "type": "image_url",
                "image_url": {"url": f"data:{c.mime_type};base64,{c.data}"},
            })
    return result


def _format_assistant_content(content: list) -> str | list[dict[str, Any]]:
    result = []
    for block in content:
        if block.type == "text":
            result.append({"type": "text", "text": block.text})
        elif block.type == "thinking":
            result.append({
                "type": "text",
                "text": f"<thinking>{block.thinking}</thinking>",
            })
        elif block.type == "toolCall":
            result.append({
                "type": "function",
                "id": block.id,
                "function": {
                    "name": block.name,
                    "arguments": json.dumps(block.arguments),
                },
            })
    return result if len(result) > 1 else (result[0] if result else "")


def _format_tool_content(content) -> str:
    if isinstance(content, str):
        return content
    return "\n".join(c.text for c in content if c.type == "text")
