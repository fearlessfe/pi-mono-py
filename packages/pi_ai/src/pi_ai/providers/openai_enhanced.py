"""Enhanced OpenAI provider with retry logic, image support, and improved tool handling.

This is an improved version of the OpenAI provider with:
- Exponential backoff retry mechanism
- Image input support
- Improved tool call handling
- Better error handling
"""

from __future__ import annotations

import asyncio
import json
import base64
from typing import Any, cast

from ..env_keys import get_env_api_key
from ..event_stream import AssistantMessageEventStream
from ..models import calculate_cost
from ..types import (
    AssistantMessage,
    Context,
    DoneEvent,
    ErrorEvent,
    ImageContent,
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

from .retry import retry_http_request, RetryError

try:
    import httpx
except ImportError:
    httpx = None  # type: ignore[misc,assignment]


class OpenAIOptions:
    def __init__(
        self,
        tool_choice: str | None = None,
        reasoning_effort: str | None = None,
    ) -> None:
        self.tool_choice = tool_choice
        self.reasoning_effort = reasoning_effort


def normalize_mistral_tool_id(tool_id: str) -> str:
    normalized = "".join(c for c in tool_id if c.isalnum())
    if len(normalized) < 9:
        padding = "ABCDEFGHI"
        normalized = normalized + padding[0:9 - len(normalized)]
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


async def stream_openai_completions(
    model: Model,
    context: Context,
    options: StreamOptions | None = None,
    openai_options: OpenAIOptions | None = None,
) -> AssistantMessageEventStream:
    """Stream from OpenAI Chat Completions API with retry logic and image support.
    
    Args:
        model: The model configuration
        context: The conversation context
        options: Stream options
        openai_options: OpenAI-specific options
        
    Returns:
        AssistantMessageEventStream with events from OpenAI
        
    Raises:
        ValueError: If API key is not found
        ImportError: If httpx is not installed
        RetryError: If all retry attempts are exhausted
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
            api_key = (
                options.api_key if options and options.api_key else get_env_api_key(model.provider)
            )
            if not api_key:
                raise ValueError(f"No API key for provider: {model.provider}")

            if httpx is None:
                raise ImportError(
                    "httpx is required for OpenAI provider. Install with: pip install httpx"
                )

            # Make HTTP request with retry
            async def make_request(client, base_url, headers, params):
                stream.push(StartEvent(partial=output))
                response = await client.post(
                    "/chat/completions",
                    json=params,
                    headers=headers,
                    timeout=60.0,
                )
                return response

            response = await retry_http_request(
                make_request,
                max_attempts=3,
                initial_delay_ms=1000,
            )

            # Process streaming response
            stream_text = ""
            current_block: TextContent | ThinkingContent | None = None
            block_index = [0]

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
                        cacheWrite=usage_data.get("prompt_tokens_details", {}).get(
                            "associated_tokens", 0
                        ),
                        totalTokens=usage_data.get("total_tokens", 0),
                        cost=calculate_cost(model, output.usage),
                    )

                # Handle text content
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

                # Handle reasoning content (for reasoning models)
                if delta.get("reasoning_content"):
                    reasoning = delta["reasoning_content"]
                    if reasoning:
                        if not current_block or current_block.type != "thinking":
                            current_block = ThinkingContent(
                                type="thinking", thinking="", thinkingSignature=None
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

                # Handle tool calls
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
                            tool_call.name = tool_delta["function"]["name"]
                        if "arguments" in tool_delta:
                            args_str = tool_delta["arguments"]
                            if isinstance(args_str, str):
                                try:
                                    tool_call.arguments = json.loads(args_str)
                                except json.JSONDecodeError:
                                    pass
                            elif isinstance(args_str, dict):
                                tool_call.arguments = args_str

                        stream.push(
                            ToolcallEndEvent(
                                contentIndex=block_index[-1],
                                toolCall=tool_call,
                                partial=output,
                            )
                        )

            stream.push(DoneEvent(reason=output.stop_reason, message=output))

        except RetryError:
            output.stop_reason = "error"
            output.error_message = f"Failed after retries: {RetryError.last_exception}"
            stream.push(ErrorEvent(reason="error", error=output))
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


async def stream_openai_responses(
    model: Model,
    context: Context,
    options: StreamOptions | None = None,
    openai_options: OpenAIOptions | None = None,
) -> AssistantMessageEventStream:
    """Stream from OpenAI Responses API (o1/o3) with reasoning models.
    
    This supports OpenAI o1 and o3 models with reasoning_effort parameter.
    Responses API is optimized for reasoning models with improved streaming.
    
    Args:
        model: The model configuration
        context: The conversation context
        options: Stream options
        openai_options: OpenAI-specific options
        
    Returns:
        AssistantMessageEventStream with events from OpenAI
        
    Raises:
        ValueError: If API key is not found
        ImportError: If httpx is not installed
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
                baseUrl=model.base_url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    **(options.headers if options and options.headers else {}),
                },
                timeout=120.0,  # Longer timeout for reasoning models
            )

            params = _build_params_responses(model, context, options, openai_options)

            stream.push(StartEvent(partial=output))

            # Process streaming response
            current_block: TextContent | ThinkingContent | None = None
            block_index = [0]

            async for line in client.stream("POST", "/responses", json=params):
                if line.strip():
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    # Process response (similar to completions API but adapted for Responses)
                    # Handle reasoning_content (for reasoning models)
                    if data.get("reasoning_content"):
                        reasoning = data["reasoning_content"]
                        if reasoning:
                            if not current_block or current_block.type != "thinking":
                                current_block = ThinkingContent(
                                    type="thinking", thinking="", thinkingSignature=None
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

                    # Handle content (text output)
                    if data.get("content"):
                        content = data["content"]
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

                    # Handle tool_calls
                    if data.get("tool_calls"):
                        for tool_data in data["tool_calls"]:
                            if not current_block or current_block.type != "toolCall":
                                current_block = ToolCall(
                                    type="toolCall",
                                    id=tool_data.get("id", ""),
                                    name="",
                                    arguments={},
                                    thoughtSignature=tool_data.get("thought_signature"),
                                )
                                output.content.append(current_block)
                                block_index.append(len(output.content) - 1)

                            if "id" in tool_data:
                                current_block.id = tool_data["id"]
                            if "name" in tool_data:
                                current_block.name = tool_data["name"]
                            if "arguments" in tool_data:
                                current_block.arguments = tool_data["arguments"]

                            stream.push(
                                ToolcallEndEvent(
                                    contentIndex=block_index[-1],
                                    toolCall=current_block,
                                    partial=output,
                                )
                            )

                    # Handle end event
                    if data.get("end"):
                        end_data = data["end"]
                        if end_data.get("stop_reason"):
                            output.stop_reason = cast(
                                "StopReason", _map_finish_reason(end_data["stop_reason"])
                            )

                        if "usage" in end_data:
                            usage_data = end_data["usage"]
                            output.usage = Usage(
                                input=usage_data.get("prompt_tokens", 0),
                                output=usage_data.get("completion_tokens", 0),
                                cacheRead=usage_data.get("prompt_tokens_details", {}).get(
                                    "cached_tokens", 0
                                ),
                                cacheWrite=usage_data.get("prompt_tokens_details", {}).get(
                                    "associated_tokens", 0
                                ),
                                totalTokens=usage_data.get("total_tokens", 0),
                                cost=calculate_cost(model, output.usage),
                            )

            stream.push(DoneEvent(reason=output.stop_reason, message=output))

        except RetryError:
            output.stop_reason = "error"
            output.error_message = f"Failed after retries: {RetryError.last_exception}"
            stream.push(ErrorEvent(reason="error", error=output))
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


def _build_params_responses(
    model: Model,
    context: Context,
    options: StreamOptions | None,
    openai_options: OpenAIOptions | None,
) -> dict[str, Any]:
    """Build request parameters for OpenAI Responses API.
    
    Args:
        model: The model configuration
        context: The conversation context
        options: Stream options
        openai_options: OpenAI-specific options
        
    Returns:
        Request parameters dictionary
    """
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

    params: dict[str, Any] = {
        "model": model.id,
        "messages": messages,
        "stream": True,
    }

    # Add OpenAI-specific options
    if openai_options:
        if openai_options.tool_choice:
            params["tool_choice"] = openai_options.tool_choice
        if openai_options.reasoning_effort:
            # Options: "low", "medium", "high" (for o3) or level for o1
            params["reasoning_effort"] = openai_options.reasoning_effort
        if openai_options.max_completion_tokens:
            params["max_completion_tokens"] = openai_options.max_completion_tokens

    # Add stream options
    if options:
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

        if options.temperature:
            params["temperature"] = options.temperature
        if options.max_tokens:
            params["max_tokens"] = options.max_tokens

    return params


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
    openai_options: OpenAIOptions | None = None,
) -> dict[str, Any]:
    """Build request parameters for OpenAI Chat Completions API.
    
    Args:
        model: The model configuration
        context: The conversation context
        options: Stream options
        openai_options: OpenAI-specific options
        
    Returns:
        Request parameters dictionary
    """
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

    params: dict[str, Any] = {
        "model": model.id,
        "messages": messages,
        "stream": True,
    }

    # Add OpenAI-specific options
    if openai_options:
        if openai_options.tool_choice:
            params["tool_choice"] = openai_options.tool_choice
        if openai_options.reasoning_effort:
            params["reasoning_effort"] = openai_options.reasoning_effort

    # Add stream options
    if options:
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

        if options.temperature is not None:
            params["temperature"] = options.temperature
        if options.max_tokens is not None:
            params["max_tokens"] = options.max_tokens

    return params


def _format_user_content(content) -> str | list[dict[str, Any]]:
    """Format user message content with image support.
    
    Args:
        content: User message content (text or image)
        
    Returns:
        Formatted content for OpenAI API
    """
    if isinstance(content, str):
        return content
    
    # Handle image content
    if isinstance(content, list):
        formatted_content = []
        text_parts = []
        
        for item in content:
            if isinstance(item, TextContent):
                text_parts.append(item.text)
            elif isinstance(item, ImageContent):
                # Support image from URL or base64 data
                if item.data.startswith("http://") or item.data.startswith("https://"):
                    # URL format
                    formatted_content.append({
                        "type": "image_url",
                        "image_url": item.data,
                    })
                elif item.data.startswith("data:"):
                    # Base64 format: data:image/png;base64,iVBORw0KG...
                    formatted_content.append({
                        "type": "image_url",
                        "image_url": item.data,
                    })
                else:
                    # Treat as text
                    text_parts.append(str(item.data))
        
        # Combine text and images
        if text_parts:
            formatted_content.append({
                "type": "text",
                "text": " ".join(text_parts),
            })
            formatted_content.extend([item for item in formatted_content if item.get("type") == "image_url"])
        elif formatted_content:
            # Only images, no text
            formatted_content.extend([item for item in formatted_content if item.get("type") == "image_url"])
        else:
            # No images, only text
            formatted_content.append({
                "type": "text",
                "text": " ".join(text_parts),
            })
        
        return formatted_content
    
    return [{"type": "text", "text": "text"}]


def _format_assistant_content(content) -> list[dict[str, Any]]:
    """Format assistant message content."""
    result = []
    for block in content:
        if block.type == "text":
            result.append({"type": "text", "text": block.text})
        elif block.type == "thinking":
            result.append(
                {
                    "type": "reasoning_content",
                    "reasoning_content": block.thinking,
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


def _format_tool_content(content) -> str:
    """Format tool result message content."""
    if isinstance(content, str):
        return content
    return json.dumps([{"type": "text", "text": c.text} for c in content])
