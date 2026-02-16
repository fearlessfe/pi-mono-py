from __future__ import annotations

import asyncio
import random
from collections.abc import Callable, Awaitable
from typing import Any
from time import time

from pi_ai.stream import stream_simple
from pi_ai.types import Context as AiContext, Message, StopReason, Usage, UsageCost, ToolResultMessage, ToolCall, TextContent, AssistantMessage
from pi_ai.event_stream import EventStream

from .types import (
    AgentContext,
    AgentEvent,
    AgentLoopConfig,
    AgentMessage,
    AgentTool,
    AgentToolResult,
    StreamFn,
    AgentStartEvent,
    AgentEndEvent,
    TurnStartEvent,
    TurnEndEvent,
    MessageStartEvent,
    MessageUpdateEvent,
    MessageEndEvent,
    ToolExecutionStartEvent,
    ToolExecutionUpdateEvent,
    ToolExecutionEndEvent,
)


class RateLimitError(Exception):
    """Raised when API rate limit is hit."""
    def __init__(self, retry_after_ms: int | None = None):
        self.retry_after_ms = retry_after_ms
        super().__init__(f"Rate limit hit, retry after {retry_after_ms}ms")


class LLMTimeoutError(Exception):
    """Raised when LLM call times out."""
    pass


class ToolTimeoutError(Exception):
    """Raised when tool execution times out."""
    def __init__(self, tool_name: str, timeout_ms: int):
        self.tool_name = tool_name
        self.timeout_ms = timeout_ms
        super().__init__(f"Tool '{tool_name}' timed out after {timeout_ms}ms")


def agent_loop(
    prompts: list[AgentMessage],
    context: AgentContext,
    config: AgentLoopConfig,
    cancel_event: asyncio.Event | None = None,
    stream_fn: StreamFn | None = None,
) -> EventStream[AgentEvent, list[AgentMessage]]:
    stream = _create_agent_stream()

    async def _run():
        new_messages = list(prompts)
        current_context = AgentContext(
            system_prompt=context.system_prompt,
            messages=[*context.messages, *prompts],
            tools=context.tools,
        )
        stream.push(AgentStartEvent())
        stream.push(TurnStartEvent())
        for prompt in prompts:
            stream.push(MessageStartEvent(message=prompt))
            stream.push(MessageEndEvent(message=prompt))

        await _run_loop(current_context, new_messages, config, cancel_event, stream, stream_fn)

    asyncio.create_task(_run())
    return stream


def agent_loop_continue(
    context: AgentContext,
    config: AgentLoopConfig,
    cancel_event: asyncio.Event | None = None,
    stream_fn: StreamFn | None = None,
) -> EventStream[AgentEvent, list[AgentMessage]]:
    if len(context.messages) == 0:
        raise ValueError("Cannot continue: no messages in context")

    last_msg = context.messages[-1]
    if isinstance(last_msg, AssistantMessage):
        raise ValueError("Cannot continue from message role: assistant")

    stream = _create_agent_stream()

    async def _run():
        new_messages: list[AgentMessage] = []
        current_context = AgentContext(
            system_prompt=context.system_prompt,
            messages=list(context.messages),
            tools=context.tools,
        )
        stream.push(AgentStartEvent())
        stream.push(TurnStartEvent())
        await _run_loop(current_context, new_messages, config, cancel_event, stream, stream_fn)

    asyncio.create_task(_run())
    return stream


def _create_agent_stream() -> EventStream[AgentEvent, list[AgentMessage]]:
    return EventStream(
        is_complete=lambda event: event.type == "agent_end",
        extract_result=lambda event: (
            event.messages if isinstance(event, AgentEndEvent) else []  # type: ignore[return-value]
        ),
    )


async def _run_loop(
    current_context: AgentContext,
    new_messages: list[AgentMessage],
    config: AgentLoopConfig,
    cancel_event: asyncio.Event | None,
    stream: EventStream[AgentEvent, list[AgentMessage]],
    stream_fn: StreamFn | None,
) -> None:
    first_turn = True
    pending_messages = (await config.get_steering_messages() if config.get_steering_messages else [])

    while True:
        has_more_tool_calls = True
        steering_after_tools: list[AgentMessage] | None = None

        while has_more_tool_calls or len(pending_messages) > 0:
            if not first_turn:
                stream.push(TurnStartEvent())
            else:
                first_turn = False

            if len(pending_messages) > 0:
                for message in pending_messages:
                    stream.push(MessageStartEvent(message=message))
                    stream.push(MessageEndEvent(message=message))
                    current_context.messages.append(message)
                    new_messages.append(message)
                pending_messages = []

            message = await _stream_assistant_response(
                current_context, config, cancel_event, stream, stream_fn
            )
            new_messages.append(message)

            if message.stop_reason in (StopReason.error, StopReason.aborted):
                stream.push(TurnEndEvent(message=message, tool_results=[]))
                stream.push(AgentEndEvent(messages=new_messages))
                stream.end(new_messages)
                return

            tool_calls = [c for c in message.content if isinstance(c, ToolCall)]
            has_more_tool_calls = len(tool_calls) > 0

            tool_results = []
            if has_more_tool_calls:
                tool_execution = await _execute_tool_calls(
                    current_context.tools,
                    message,
                    cancel_event,
                    stream,
                    config.get_steering_messages,
                    config.tool_timeout_ms,
                )
                tool_results.extend(tool_execution["tool_results"])
                steering_after_tools = tool_execution["steering_messages"]
                for result in tool_results:
                    current_context.messages.append(result)
                    new_messages.append(result)

            stream.push(TurnEndEvent(message=message, tool_results=tool_results))

            if steering_after_tools and len(steering_after_tools) > 0:
                pending_messages = steering_after_tools
                steering_after_tools = None
            else:
                pending_messages = (
                    await config.get_steering_messages() if config.get_steering_messages else []
                )

        follow_up_messages = (
            await config.get_follow_up_messages() if config.get_follow_up_messages else []
        )
        if len(follow_up_messages) > 0:
            pending_messages = follow_up_messages
            continue

        break

    stream.push(AgentEndEvent(messages=new_messages))
    stream.end(new_messages)


async def _stream_assistant_response(
    context: AgentContext,
    config: AgentLoopConfig,
    cancel_event: asyncio.Event | None,
    stream: EventStream[AgentEvent, list[AgentMessage]],
    stream_fn: StreamFn | None,
) -> AssistantMessage:
    messages = context.messages
    if config.transform_context:
        messages = await config.transform_context(messages, cancel_event)

    llm_messages_raw = config.convert_to_llm(messages)
    if asyncio.iscoroutine(llm_messages_raw):
        llm_messages = await llm_messages_raw
    else:
        llm_messages = llm_messages_raw

    llm_context = AiContext(
        system_prompt=context.system_prompt,
        messages=llm_messages,
        tools=context.tools,
    )

    stream_function = stream_fn or stream_simple

    resolved_api_key = None
    if config.get_api_key:
        result = config.get_api_key(config.model.provider)
        if asyncio.iscoroutine(result):
            resolved_api_key = await result
        else:
            resolved_api_key = result
    resolved_api_key = resolved_api_key or config.api_key

    options = {
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
        "api_key": resolved_api_key,
        "cache_retention": config.cache_retention,
        "session_id": config.session_id,
        "headers": config.headers,
        "max_retry_delay_ms": config.max_retry_delay_ms,
    }

    # Retry logic
    max_retries = config.max_retries
    retry_delay_ms = config.retry_delay_ms
    last_error: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            if cancel_event and cancel_event.is_set():
                return _create_error_message("Request cancelled")

            # LLM timeout handling
            if config.llm_timeout_ms:
                response = await asyncio.wait_for(
                    stream_function(config.model, llm_context, options),
                    timeout=config.llm_timeout_ms / 1000
                )
            else:
                response = await stream_function(config.model, llm_context, options)

            return await _process_llm_response(response, context, stream)

        except asyncio.TimeoutError:
            last_error = LLMTimeoutError(f"LLM call timed out after {config.llm_timeout_ms}ms")
            if attempt < max_retries:
                await _exponential_backoff(attempt, retry_delay_ms, cancel_event)
                continue
        except Exception as e:
            error_str = str(e).lower()
            is_rate_limit = "rate" in error_str or "limit" in error_str or "429" in error_str

            if is_rate_limit and config.retry_on_rate_limit and attempt < max_retries:
                last_error = e
                await _exponential_backoff(attempt, retry_delay_ms, cancel_event)
                continue
            else:
                raise

    # All retries exhausted
    return _create_error_message(str(last_error) if last_error else "Unknown error after retries")


async def _process_llm_response(
    response,
    context: AgentContext,
    stream: EventStream[AgentEvent, list[AgentMessage]],
) -> AssistantMessage:
    partial_message: AssistantMessage | None = None
    added_partial = False

    from pi_ai.types import (
        AssistantMessageEvent,
        StartEvent,
        TextStartEvent,
        TextDeltaEvent,
        TextEndEvent,
        ThinkingStartEvent,
        ThinkingDeltaEvent,
        ThinkingEndEvent,
        ToolcallStartEvent,
        ToolcallDeltaEvent,
        ToolcallEndEvent,
        DoneEvent,
        ErrorEvent,
    )

    async for event in response:
        if isinstance(event, StartEvent):
            partial_message = event.partial
            context.messages.append(partial_message)
            added_partial = True
            stream.push(MessageStartEvent(message=event.partial.model_copy(deep=True)))
        elif isinstance(
            event,
            (
                TextStartEvent,
                TextDeltaEvent,
                TextEndEvent,
                ThinkingStartEvent,
                ThinkingDeltaEvent,
                ThinkingEndEvent,
                ToolcallStartEvent,
                ToolcallDeltaEvent,
                ToolcallEndEvent,
            ),
        ):
            if partial_message:
                partial_message = event.partial
                context.messages[-1] = partial_message
                stream.push(
                    MessageUpdateEvent(
                        message=event.partial.model_copy(deep=True),
                        assistant_message_event=event,  # type: ignore[arg-type]
                    )
                )
        elif isinstance(event, (DoneEvent, ErrorEvent)):
            final_message = await response.result()
            if added_partial:
                context.messages[-1] = final_message
            else:
                context.messages.append(final_message)

            if not added_partial:
                stream.push(MessageStartEvent(message=final_message.model_copy(deep=True)))
            stream.push(MessageEndEvent(message=final_message))
            return final_message

    return await response.result()


async def _execute_tool_calls(
    tools: list[AgentTool] | None,
    assistant_message: AssistantMessage,
    cancel_event: asyncio.Event | None,
    stream: EventStream[AgentEvent, list[AgentMessage]],
    get_steering_messages: (
        Callable[[], Awaitable[list[AgentMessage]]] | None
    ) = None,
    tool_timeout_ms: int | None = None,
) -> dict[str, Any]:
    tool_calls = [c for c in assistant_message.content if isinstance(c, ToolCall)]
    results = []
    steering_messages: list[AgentMessage] | None = None

    for index in range(len(tool_calls)):
        if cancel_event and cancel_event.is_set():
            break

        tool_call = tool_calls[index]
        tool = None
        if tools:
            for t in tools:
                if t.name == tool_call.name:
                    tool = t
                    break

        stream.push(
            ToolExecutionStartEvent(
                tool_call_id=tool_call.id,
                tool_name=tool_call.name,
                args=tool_call.arguments,
            )
        )

        result: AgentToolResult | None = None
        is_error = False

        try:
            if tool is None:
                raise ValueError(f"Tool {tool_call.name} not found")

            async def on_update(partial_result: AgentToolResult) -> None:
                stream.push(
                    ToolExecutionUpdateEvent(
                        tool_call_id=tool_call.id,
                        tool_name=tool_call.name,
                        args=tool_call.arguments,
                        partial_result=partial_result,
                    )
                )

            # Execute with optional timeout
            if tool_timeout_ms:
                result = await asyncio.wait_for(
                    tool.execute(tool_call.id, tool_call.arguments, cancel_event, on_update),
                    timeout=tool_timeout_ms / 1000
                )
            else:
                result = await tool.execute(
                    tool_call.id, tool_call.arguments, cancel_event, on_update
                )
        except asyncio.TimeoutError:
            from .types import AgentToolResult
            result = AgentToolResult(
                content=[TextContent(type="text", text=f"Tool '{tool_call.name}' timed out after {tool_timeout_ms}ms")],
                details={"timeout_ms": tool_timeout_ms},
            )
            is_error = True
        except asyncio.CancelledError:
            from .types import AgentToolResult
            result = AgentToolResult(
                content=[TextContent(type="text", text="Tool execution was cancelled")],
                details={"cancelled": True},
            )
            is_error = True
        except Exception as e:
            from .types import AgentToolResult

            result = AgentToolResult(
                content=[TextContent(type="text", text=str(e))], details={}
            )
            is_error = True

        stream.push(
            ToolExecutionEndEvent(
                tool_call_id=tool_call.id,
                tool_name=tool_call.name,
                result=result.model_dump() if result else {},  # type: ignore[arg-type]
                is_error=is_error,
            )
        )

        tool_result_message = ToolResultMessage(
            role="toolResult",
            tool_call_id=tool_call.id,
            tool_name=tool_call.name,
            content=result.content if result else [],
            details=result.details if result else None,
            is_error=is_error,
            timestamp=int(time() * 1000),
        )
        results.append(tool_result_message)
        stream.push(MessageStartEvent(message=tool_result_message))
        stream.push(MessageEndEvent(message=tool_result_message))

        if get_steering_messages:
            steering = await get_steering_messages()
            if len(steering) > 0:
                steering_messages = steering
                remaining_calls = tool_calls[index + 1 :]
                for skipped in remaining_calls:
                    results.append(_skip_tool_call(skipped, stream))
                break

    return {"tool_results": results, "steering_messages": steering_messages}


def _skip_tool_call(
    tool_call: ToolCall, stream: EventStream[AgentEvent, list[AgentMessage]]
) -> ToolResultMessage:
    from .types import AgentToolResult

    result = AgentToolResult(
        content=[TextContent(type="text", text="Skipped due to queued user message.")],
        details={},
    )

    stream.push(
        ToolExecutionStartEvent(
            tool_call_id=tool_call.id,
            tool_name=tool_call.name,
            args=tool_call.arguments,
        )
    )
    stream.push(
        ToolExecutionEndEvent(
            tool_call_id=tool_call.id,
            tool_name=tool_call.name,
            result=result.model_dump(),
            is_error=True,
        )
    )

    tool_result_message = ToolResultMessage(
        role="toolResult",
        tool_call_id=tool_call.id,
        tool_name=tool_call.name,
        content=result.content,
        details={},
        is_error=True,
        timestamp=int(time() * 1000),
    )

    stream.push(MessageStartEvent(message=tool_result_message))
    stream.push(MessageEndEvent(message=tool_result_message))

    return tool_result_message


async def _exponential_backoff(
    attempt: int,
    base_delay_ms: int,
    cancel_event: asyncio.Event | None = None,
) -> None:
    """Wait with exponential backoff before retry."""
    delay_ms = base_delay_ms * (2 ** attempt) + random.randint(0, 1000)
    delay_s = delay_ms / 1000

    if cancel_event:
        try:
            await asyncio.wait_for(cancel_event.wait(), timeout=delay_s)
        except asyncio.TimeoutError:
            pass  # Cancel not triggered, continue with retry
    else:
        await asyncio.sleep(delay_s)


def _create_error_message(error_text: str) -> AssistantMessage:
    """Create an error assistant message."""
    return AssistantMessage(
        role="assistant",
        content=[TextContent(type="text", text=f"Error: {error_text}")],
        api="error",
        provider="error",
        model="error",
        usage=Usage(
            input=0,
            output=0,
            cacheRead=0,
            cacheWrite=0,
            totalTokens=0,
            cost=UsageCost(),
        ),
        stopReason=StopReason.error,
        errorMessage=error_text,
        timestamp=int(time() * 1000),
    )
