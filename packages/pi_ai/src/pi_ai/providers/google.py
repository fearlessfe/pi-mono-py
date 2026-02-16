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
    from google.generativeai import GenerativeModel, Part  # type: ignore[import-untyped]
except ImportError:
    GenerativeModel = None  # type: ignore[misc,assignment]
    Part = None  # type: ignore[misc,assignment]

try:
    import httpx
except ImportError:
    httpx = None  # type: ignore[misc,assignment]


def is_gemini_3_pro_model(model: Model) -> bool:
    return "3-pro" in model.id


def is_gemini_3_flash_model(model: Model) -> bool:
    return "3-flash" in model.id


def get_gemini_3_thinking_level(level: str) -> str:
    mapping = {
        "minimal": "MINIMAL",
        "low": "LOW",
        "medium": "MEDIUM",
        "high": "HIGH",
    }
    return mapping.get(level, "MINIMAL")


def get_thinking_budget(model: Model, level: str | None) -> int | None:
    if not level or not is_gemini_3_pro_model(model) and not is_gemini_3_flash_model(model):
        return None

    budgets: dict[str, int] = {}
    if is_gemini_3_pro_model(model):
        budgets = {"minimal": 128, "low": 2048, "medium": 8192, "high": 32768}
    elif is_gemini_3_flash_model(model):
        budgets = {"minimal": 128, "low": 2048, "medium": 8192, "high": 24576}

    return budgets.get(level)


tool_call_counter = 0


async def _parse_sse_chunks(response: Any):
    """Parse SSE response chunks."""
    async for line in response:
        if line.strip():
            yield line


class GoogleOptions:
    def __init__(
        self,
        tool_choice: str | None = None,
        thinking_enabled: bool = False,
        thinking_budget_tokens: int | None = None,
        thinking_level: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> None:
        self.tool_choice = tool_choice
        self.thinking_enabled = thinking_enabled
        self.thinking_budget_tokens = thinking_budget_tokens
        self.thinking_level = thinking_level
        self.temperature = temperature
        self.max_tokens = max_tokens


def stream_google(
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
                    "httpx is required for Google provider. Install with: pip install httpx"
                )

            opts = (
                GoogleOptions()
                if options is None
                else GoogleOptions(
                    tool_choice=options.tool_choice,
                    thinking_enabled=options.reasoning if options.reasoning else False,
                    thinking_budget_tokens=options.thinking_budgets.get("high")
                    if options.thinking_budgets
                    else None,
                )
            )

            params = _build_params(model, context, opts)

            headers = {}
            if options and options.headers:
                headers.update(options.headers)

            stream.push(StartEvent(partial=output))

            current_block: TextContent | ThinkingContent | ToolCall | None = None
            block_index = [0]

            response = await http_client_stream(model, params, headers)

            async for chunk in _parse_sse_chunks(response):
                data = json.loads(chunk)

                if "candidates" not in data or len(data["candidates"]) == 0:
                    continue

                candidate = data["candidates"][0]
                delta = candidate.get("content", {}).get("parts", [])

                if not delta:
                    continue

                for part in delta:
                    part_type = part.get("type", "")
                    part_text = part.get("text", "")

                    if part_type == "text":
                        if part_text:
                            if not current_block or current_block.type != "text":
                                current_block = TextContent(type="text", text="")
                                output.content.append(current_block)
                                block_index.append(len(output.content) - 1)

                            current_block.text += part_text
                            stream.push(
                                TextDeltaEvent(
                                    contentIndex=block_index[-1],
                                    delta=part_text,
                                    partial=output,
                                )
                            )

                    elif part_type == "thinking":
                        if part_text:
                            if not current_block or current_block.type != "thinking":
                                current_block = ThinkingContent(
                                    type="thinking",
                                    thinking="",
                                    thinkingSignature=None,
                                )
                                output.content.append(current_block)
                                block_index.append(len(output.content) - 1)

                            current_block.thinking += part_text
                            stream.push(
                                ThinkingDeltaEvent(
                                    contentIndex=block_index[-1],
                                    delta=part_text,
                                    partial=output,
                                )
                            )

                    elif part_type == "function_call":
                        function_call = part.get("functionCall", {})
                        function_name = function_call.get("name", "")
                        function_args = function_call.get("args", {})

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

                        current_block.name = function_name
                        global tool_call_counter
                        current_block.id = f"{function_name}_{tool_call_counter}"
                        tool_call_counter += 1
                        current_block.arguments.update(
                            json.loads(function_args)
                            if isinstance(function_args, str)
                            else function_args
                        )

                        stream.push(
                            ToolcallEndEvent(
                                contentIndex=block_index[-1],
                                toolCall=current_block,
                                partial=output,
                            )
                        )

                    elif part_type == "function_response":
                        if "response" in part and current_block:
                            function_response = part["response"]
                            for part_response_item in function_response:
                                part_response_type = part_response_item.get("type", "")
                                part_response_text = part_response_item.get("text", "")
                                part_response_name = part_response_item.get("name", "")

                                if part_response_type == "text" and current_block.type == "text":
                                    current_block.text += part_response_text
                                    stream.push(
                                        TextDeltaEvent(
                                            contentIndex=block_index[-1],
                                            delta=part_response_text,
                                            partial=output,
                                        )
                                    )

                finish_reason = candidate.get("finishReason")
                if finish_reason:
                    output.stop_reason = cast("StopReason", _map_google_stop_reason(finish_reason))

                usage_metadata = candidate.get("usageMetadata", {})
                if usage_metadata:
                    output.usage = Usage(
                        input=usage_metadata.get("promptTokenCount", 0),
                        output=usage_metadata.get("candidatesTokenCount", 0)
                        + usage_metadata.get("thoughtsTokenCount", 0),
                        cacheRead=0,
                        cacheWrite=0,
                        totalTokens=usage_metadata.get("totalTokenCount", 0),
                        cost=calculate_cost(model, output.usage),
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


def _map_google_stop_reason(reason: str) -> str:
    mapping = {
        "STOP": "stop",
        "MAX_TOKENS": "length",
        "SAFETY": "toolUse",
        "RECITATION": "stop",
    }
    return mapping.get(reason, "stop")


def _build_params(
    model: Model,
    context: Context,
    options: GoogleOptions,
) -> dict[str, Any]:
    messages = []

    for msg in context.messages:
        if msg.role == "user":
            messages.append({"role": "user", "parts": _format_user_parts(msg.content)})
        elif msg.role == "assistant":
            messages.append({"role": "model", "parts": _format_assistant_parts(msg.content)})
        elif msg.role == "toolResult":
            messages.append(
                {
                    "role": "user",
                    "parts": _format_user_parts(msg.content),
                }
            )

    params: dict[str, Any] = {"model": model.id, "contents": messages}

    if context.system_prompt:
        params["systemInstruction"] = context.system_prompt

    if context.tools:
        tools = []
        for tool in context.tools:
            tools.append(
                {
                    "functionDeclarations": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters,
                    },
                }
            )
        params["tools"] = tools

    if options.temperature is not None:
        params["generationConfig"] = {"temperature": options.temperature}

    if options.max_tokens is not None:
        params["generationConfig"] = {"maxOutputTokens": options.max_tokens}

    return params


def _format_user_parts(content) -> list[dict[str, Any]]:
    if isinstance(content, str):
        return [{"text": content}]
    return [{"text": block.text} for block in content]


def _format_assistant_parts(content: list) -> list[dict[str, Any]]:
    result = []
    for block in content:
        if block.type == "text":
            result.append({"text": block.text})
        elif block.type == "thinking":
            result.append({"thought": block.thinking})
        elif block.type == "toolCall":
            result.append(
                {
                    "functionResponse": {
                        "name": block.name,
                        "response": {},
                    },
                }
            )
    return result


async def http_client_stream(
    model: Model,
    params: dict[str, Any],
    headers: dict[str, str],
) -> Any:
    if httpx is None:
        raise ImportError("httpx is required for Google provider. Install with: pip install httpx")

    url = f"{model.base_url}/v1beta/models/{model.id}:streamGenerateContent"

    async with httpx.AsyncClient(
        baseUrl=model.base_url,
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": headers.get("Authorization", "").replace("Bearer ", ""),
            **headers,
        },
        timeout=60.0,
    ) as client, client.stream("POST", url, json=params) as response:
        async for line in response.aiter_lines():
            yield line
