from __future__ import annotations

import asyncio
from typing import Any
from time import time

from pi_ai.stream import stream_simple
from pi_ai.types import Context as AiContext, Message, StopReason, Usage, ToolResultMessage, ToolCall, TextContent, AssistantMessage
from pi_agent.types import (
    AgentContext,
    AgentEvent,
    AgentLoopConfig,
    AgentMessage,
    AgentTool,
    AgentToolResult,
    StreamFn,
)
from pi_agent.types import (
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
from pi_ai.event_stream import EventStream


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
                )
                tool_results.extend(tool_execution.tool_results)
                steering_after_tools = tool_execution.steering_messages
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

    llm_messages = await config.convert_to_llm(messages)

    llm_context = AiContext(
        system_prompt=context.system_prompt,
        messages=llm_messages,
        tools=context.tools,
    )

    stream_function = stream_fn or stream_simple

    resolved_api_key = None
    if config.get_api_key:
        resolved_api_key = await config.get_api_key(config.model.provider)
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

    response = await stream_function(config.model, llm_context, options)

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
    from collections.abc import Callable, Awaitable

    async for event in response:
        if isinstance(event, StartEvent):
            partial_message = event.partial
            context.messages.append(partial_message)
            added_partial = True
            stream.push(MessageStartEvent(message=partial_message.model_copy(deep=True)))
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
                        message=partial_message.model_copy(deep=True),
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

            result = await tool.execute(
                tool_call.id, tool_call.arguments, cancel_event, on_update
            )
        except Exception as e:
            from pi_agent.types import AgentToolResult, TextContent

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
    from pi_agent.types import AgentToolResult, TextContent

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
