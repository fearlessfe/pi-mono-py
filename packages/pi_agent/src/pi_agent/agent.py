from __future__ import annotations

import asyncio
from time import time
from typing import Any, Callable, Literal

from pi_ai.models import get_model
from pi_ai.stream import stream_simple
from pi_ai.types import (
    Context as AiContext,
    ImageContent,
    Message,
    Model,
    TextContent,
    AssistantMessage,
)
from collections.abc import Callable, Awaitable
from pi_agent.loop import agent_loop, agent_loop_continue
from pi_agent.types import (
    AgentContext,
    AgentEvent,
    AgentLoopConfig,
    AgentMessage,
    AgentState,
    AgentTool,
    AgentToolResult,
    StreamFn,
    ThinkingLevel,
)


def _default_convert_to_llm(messages: list[AgentMessage]) -> list[Message]:
    from pi_ai.types import UserMessage, AssistantMessage, ToolResultMessage

    return [
        m for m in messages
        if isinstance(m, (UserMessage, AssistantMessage, ToolResultMessage))
    ]


class Agent:
    def __init__(
        self,
        options: dict[str, Any] | None = None,
    ) -> None:
        opts = options or {}
        self._state = AgentState(
            model=get_model("google", "gemini-2.5-flash-lite-preview-06-17") or opts.get("model"),
            thinking_level=opts.get("thinking_level", "off"),
            messages=[],
        )
        self._convert_to_llm = opts.get("convert_to_llm", _default_convert_to_llm)
        self._transform_context = opts.get("transform_context")
        self._steering_mode: Literal["all", "one-at-a-time"] = opts.get(
            "steering_mode", "one-at-a-time"
        )
        self._follow_up_mode: Literal["all", "one-at-a-time"] = opts.get(
            "follow_up_mode", "one-at-a-time"
        )
        self._stream_fn = opts.get("stream_fn", stream_simple)
        self._session_id: str | None = opts.get("session_id")
        self._get_api_key = opts.get("get_api_key")
        self._thinking_budgets = opts.get("thinking_budgets")
        self._max_retry_delay_ms = opts.get("max_retry_delay_ms")

        self._listeners: list[Callable[[AgentEvent], None]] = []
        self._cancel_event: asyncio.Event | None = None
        self._steering_queue: list[AgentMessage] = []
        self._follow_up_queue: list[AgentMessage] = []
        self._running_prompt: asyncio.Future[None] | None = None

    @property
    def session_id(self) -> str | None:
        return self._session_id

    @session_id.setter
    def session_id(self, value: str | None) -> None:
        self._session_id = value

    @property
    def thinking_budgets(self) -> dict[str, Any] | None:
        return self._thinking_budgets

    @thinking_budgets.setter
    def thinking_budgets(self, value: dict[str, Any] | None) -> None:
        self._thinking_budgets = value

    @property
    def max_retry_delay_ms(self) -> int | None:
        return self._max_retry_delay_ms

    @max_retry_delay_ms.setter
    def max_retry_delay_ms(self, value: int | None) -> None:
        self._max_retry_delay_ms = value

    @property
    def state(self) -> AgentState:
        return self._state

    def subscribe(self, fn: Callable[[AgentEvent], None]) -> Callable[[], None]:
        self._listeners.append(fn)

        def unsubscribe() -> None:
            if fn in self._listeners:
                self._listeners.remove(fn)

        return unsubscribe

    def set_system_prompt(self, v: str) -> None:
        self._state.system_prompt = v

    def set_model(self, m: Model) -> None:
        self._state.model = m

    def set_thinking_level(self, l: ThinkingLevel) -> None:
        self._state.thinking_level = l

    def set_steering_mode(self, mode: Literal["all", "one-at-a-time"]) -> None:
        self._steering_mode = mode

    def get_steering_mode(self) -> Literal["all", "one-at-a-time"]:
        return self._steering_mode

    def set_follow_up_mode(self, mode: Literal["all", "one-at-a-time"]) -> None:
        self._follow_up_mode = mode

    def get_follow_up_mode(self) -> Literal["all", "one-at-a-time"]:
        return self._follow_up_mode

    def set_tools(self, t: list[AgentTool]) -> None:
        self._state.tools = t

    def replace_messages(self, ms: list[AgentMessage]) -> None:
        self._state.messages = list(ms)

    def append_message(self, m: AgentMessage) -> None:
        self._state.messages = [*self._state.messages, m]

    def steer(self, m: AgentMessage) -> None:
        self._steering_queue.append(m)

    def follow_up(self, m: AgentMessage) -> None:
        self._follow_up_queue.append(m)

    def clear_steering_queue(self) -> None:
        self._steering_queue = []

    def clear_follow_up_queue(self) -> None:
        self._follow_up_queue = []

    def clear_all_queues(self) -> None:
        self._steering_queue = []
        self._follow_up_queue = []

    def has_queued_messages(self) -> bool:
        return len(self._steering_queue) > 0 or len(self._follow_up_queue) > 0

    def _dequeue_steering_messages(self) -> list[AgentMessage]:
        if self._steering_mode == "one-at-a-time":
            if len(self._steering_queue) > 0:
                first = self._steering_queue[0]
                self._steering_queue = self._steering_queue[1:]
                return [first]
            return []
        steering = list(self._steering_queue)
        self._steering_queue = []
        return steering

    def _dequeue_follow_up_messages(self) -> list[AgentMessage]:
        if self._follow_up_mode == "one-at-a-time":
            if len(self._follow_up_queue) > 0:
                first = self._follow_up_queue[0]
                self._follow_up_queue = self._follow_up_queue[1:]
                return [first]
            return []
        follow_up = list(self._follow_up_queue)
        self._follow_up_queue = []
        return follow_up

    def clear_messages(self) -> None:
        self._state.messages = []

    def abort(self) -> None:
        if self._cancel_event:
            self._cancel_event.set()

    async def wait_for_idle(self) -> None:
        if self._running_prompt:
            await self._running_prompt

    def reset(self) -> None:
        self._state.messages = []
        self._state.is_streaming = False
        self._state.stream_message = None
        self._state.pending_tool_calls = set()
        self._state.error = None
        self._steering_queue = []
        self._follow_up_queue = []

    async def prompt(
        self,
        input: str | AgentMessage | list[AgentMessage],
        images: list[ImageContent] | None = None,
    ) -> None:
        if self._state.is_streaming:
            raise RuntimeError(
                "Agent is already processing a prompt. Use steer() or follow_up() to queue messages, or wait for completion."
            )

        model = self._state.model
        if model is None:
            raise ValueError("No model configured")

        msgs: list[AgentMessage]
        if isinstance(input, list):
            msgs = input
        elif isinstance(input, str):
            from pi_ai.types import UserMessage

            content: list[TextContent | ImageContent] = [
                TextContent(type="text", text=input)
            ]
            if images:
                content.extend(images)

            msgs = [UserMessage(role="user", content=content, timestamp=int(time() * 1000))]
        else:
            msgs = [input]

        await self._run_loop(msgs)

    async def continue_(self) -> None:
        if self._state.is_streaming:
            raise RuntimeError("Agent is already processing. Wait for completion before continuing.")

        messages = self._state.messages
        if len(messages) == 0:
            raise ValueError("No messages to continue from")

        last_msg = messages[-1]
        from pi_ai.types import AssistantMessage

        if isinstance(last_msg, AssistantMessage):
            queued_steering = self._dequeue_steering_messages()
            if len(queued_steering) > 0:
                await self._run_loop(queued_steering, skip_initial_steering_poll=True)
                return

            queued_follow_up = self._dequeue_follow_up_messages()
            if len(queued_follow_up) > 0:
                await self._run_loop(queued_follow_up)
                return

            raise ValueError("Cannot continue from message role: assistant")

        await self._run_loop(None)

    async def _run_loop(
        self,
        messages: list[AgentMessage] | None = None,
        skip_initial_steering_poll: bool = False,
    ) -> None:
        model = self._state.model
        if model is None:
            raise ValueError("No model configured")

        self._running_prompt = asyncio.get_event_loop().create_future()
        self._cancel_event = asyncio.Event()
        self._state.is_streaming = True
        self._state.stream_message = None
        self._state.error = None

        reasoning = None
        if self._state.thinking_level != "off":
            reasoning = self._state.thinking_level

        context = AgentContext(
            system_prompt=self._state.system_prompt,
            messages=list(self._state.messages),
            tools=self._state.tools,
        )

        from pi_ai.types import ThinkingBudgets as AiThinkingBudgets

        config = AgentLoopConfig(
            model=model,
            reasoning=reasoning,
            session_id=self._session_id,
            thinking_budgets=AiThinkingBudgets(**(self._thinking_budgets or {})),
            max_retry_delay_ms=self._max_retry_delay_ms,
            convert_to_llm=self._convert_to_llm,
            transform_context=self._transform_context,
            get_api_key=self._get_api_key,
        )

        skip_initial = skip_initial_steering_poll

        async def _get_steering() -> list[AgentMessage]:
            if skip_initial:
                skip_initial = False
                return []
            return self._dequeue_steering_messages()

        async def _get_follow_up() -> list[AgentMessage]:
            return self._dequeue_follow_up_messages()

        config.get_steering_messages = _get_steering
        config.get_follow_up_messages = _get_follow_up

        partial: AgentMessage | None = None

        try:
            stream = (
                agent_loop(messages, context, config, self._cancel_event, self._stream_fn)
                if messages
                else agent_loop_continue(
                    context, config, self._cancel_event, self._stream_fn
                )
            )

            async for event in stream:
                match event.type:
                    case "message_start":
                        partial = event.message
                        self._state.stream_message = event.message

                    case "message_update":
                        partial = event.message
                        self._state.stream_message = event.message

                    case "message_end":
                        partial = None
                        self._state.stream_message = None
                        self.append_message(event.message)

                    case "tool_execution_start":
                        s = set(self._state.pending_tool_calls)
                        s.add(event.tool_call_id)
                        self._state.pending_tool_calls = s

                    case "tool_execution_end":
                        s = set(self._state.pending_tool_calls)
                        s.discard(event.tool_call_id)
                        self._state.pending_tool_calls = s

                    case "turn_end":
                        if (
                            event.message.role == "assistant"
                            and hasattr(event.message, "error_message")
                            and event.message.error_message
                        ):
                            self._state.error = event.message.error_message  # type: ignore[assignment]

                    case "agent_end":
                        self._state.is_streaming = False
                        self._state.stream_message = None

                self._emit(event)

            if partial and partial.role == "assistant" and len(partial.content) > 0:
                from pi_ai.types import TextContent, ThinkingContent, ToolCall

                only_empty = not any(
                    (
                        isinstance(c, ThinkingContent) and c.thinking.strip()
                        or isinstance(c, TextContent) and c.text.strip()
                        or isinstance(c, ToolCall) and c.name.strip()
                    )
                    for c in partial.content
                )
                if not only_empty:
                    self.append_message(partial)
                else:
                    if self._cancel_event.is_set():
                        raise RuntimeError("Request was aborted")

        except Exception as err:
            from pi_ai.types import AssistantMessage, Usage, UsageCost, StopReason

            error_message = AssistantMessage(
                role="assistant",
                content=[TextContent(type="text", text="")],
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
                stop_reason=StopReason.aborted if self._cancel_event.is_set() else StopReason.error,
                error_message=str(err),
                timestamp=int(time() * 1000),
            )
            self.append_message(error_message)
            self._state.error = str(err)
            self._emit(AgentEndEvent(messages=[error_message]))

        finally:
            self._state.is_streaming = False
            self._state.stream_message = None
            self._state.pending_tool_calls = set()
            self._cancel_event = None
            if self._running_prompt and not self._running_prompt.done():
                self._running_prompt.set_result(None)

    def _emit(self, event: AgentEvent) -> None:
        for listener in self._listeners:
            listener(event)
