"""Stream proxy for routing LLM requests through a proxy server."""

from __future__ import annotations

import asyncio
import json
from typing import Any, cast

from .event_stream import AssistantMessageEventStream
from .models import calculate_cost
from .types import (
    AssistantMessage,
    Context,
    DoneEvent,
    ErrorEvent,
    Model,
    StartEvent,
    StopReason,
    StreamOptions,
    TextContent,
    TextDeltaEvent,
    ThinkingContent,
    ThinkingDeltaEvent,
    ToolCall,
    ToolcallEndEvent,
    Usage,
    UsageCost,
)

try:
    import httpx
except ImportError:
    httpx = None  # type: ignore[misc,assignment]


class ProxyConfig:
    """Configuration for the proxy server."""

    def __init__(
        self,
        proxy_url: str,
        auth_token: str | None = None,
        headers: dict[str, str] | None = None,
        timeout: float = 120.0,
    ):
        self.proxy_url = proxy_url.rstrip("/")
        self.auth_token = auth_token
        self.headers = headers or {}
        self.timeout = timeout


def stream_proxy(
    model: Model,
    context: Context,
    options: StreamOptions | None = None,
    *,
    proxy_config: ProxyConfig,
) -> AssistantMessageEventStream:
    """Stream from a proxy server instead of directly from the LLM provider.

    This is useful for:
    - Centralized API key management
    - Request logging and auditing
    - Rate limiting and quota management
    - Custom model routing logic

    Args:
        model: The model configuration
        context: The conversation context
        options: Stream options
        proxy_config: Proxy server configuration

    Returns:
        AssistantMessageEventStream with events from the proxy

    Example:
        from pi_ai.stream_proxy import stream_proxy, ProxyConfig

        config = ProxyConfig(
            proxy_url="https://your-proxy.example.com",
            auth_token="your-auth-token",
        )

        stream = stream_proxy(model, context, proxy_config=config)
        async for event in stream:
            print(event.type)
    """
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
            if httpx is None:
                raise ImportError(
                    "httpx is required for stream_proxy. Install with: pip install httpx"
                )

            params = _build_proxy_request(model, context, options)

            headers = {
                "Content-Type": "application/json",
                **proxy_config.headers,
            }
            if proxy_config.auth_token:
                headers["Authorization"] = f"Bearer {proxy_config.auth_token}"

            stream.push(StartEvent(partial=output))

            current_block: TextContent | ThinkingContent | None = None
            block_index = [0]

            async with httpx.AsyncClient(timeout=proxy_config.timeout) as client:
                url = f"{proxy_config.proxy_url}/v1/chat/completions"

                async with client.stream("POST", url, json=params, headers=headers) as response:
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
                            output.stop_reason = cast(
                                "StopReason", _map_finish_reason(choice["finish_reason"])
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

                                if "id" in tool_delta:
                                    current_block.id = tool_delta["id"]
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
                                        contentIndex=block_index[-1],
                                        toolCall=cast(ToolCall, current_block),
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


def _build_proxy_request(
    model: Model,
    context: Context,
    options: StreamOptions | None,
) -> dict[str, Any]:
    """Build the request payload for the proxy server."""
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
                    "content": _format_tool_content(msg.content),
                }
            )

    params: dict[str, Any] = {
        "model": model.id,
        "messages": messages,
        "stream": True,
    }

    if context.system_prompt:
        params["messages"] = [{"role": "system", "content": context.system_prompt}] + params[
            "messages"
        ]

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
        if options.api_key is not None:
            params["api_key"] = options.api_key

    return params


def _format_user_content(content) -> str | list[dict[str, Any]]:
    if isinstance(content, str):
        return content
    result = []
    for c in content:
        if c.type == "text":
            result.append({"type": "text", "text": c.text})
        elif c.type == "image":
            result.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{c.mime_type};base64,{c.data}"},
                }
            )
    return result


def _format_assistant_content(content: list) -> str | list[dict[str, Any]]:
    result = []
    for block in content:
        if block.type == "text":
            result.append({"type": "text", "text": block.text})
        elif block.type == "thinking":
            result.append(
                {
                    "type": "text",
                    "text": f"<thinking>{block.thinking}</thinking>",
                }
            )
        elif block.type == "toolCall":
            result.append(
                {
                    "type": "function",
                    "id": block.id,
                    "function": {
                        "name": block.name,
                        "arguments": json.dumps(block.arguments),
                    },
                }
            )
    return result if len(result) > 1 else (result[0] if result else "")


def _format_tool_content(content) -> str:
    if isinstance(content, str):
        return content
    return "\n".join(c.text for c in content if c.type == "text")
