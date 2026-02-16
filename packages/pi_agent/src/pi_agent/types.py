from __future__ import annotations

import asyncio
from typing import Any, Callable, Literal, Union, Awaitable

from pydantic import BaseModel, ConfigDict, Field

from pi_ai.types import (
    AssistantMessageEvent,
    AssistantMessage,
    Context as AiContext,
    ImageContent,
    Message,
    Model,
    SimpleStreamOptions,
    TextContent,
    Tool,
    ToolResultMessage,
)
from pi_ai.event_stream import AssistantMessageEventStream, EventStream

StreamFn = Callable[..., AssistantMessageEventStream | Awaitable[AssistantMessageEventStream]]

ThinkingLevel = Literal["off", "minimal", "low", "medium", "high", "xhigh"]

AgentMessage = Union[Message, dict[str, Any]]


class AgentToolResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    content: list[TextContent | ImageContent]
    details: Any = None


AgentToolUpdateCallback = Callable[[AgentToolResult], None | Awaitable[None]]


class AgentTool(Tool):
    model_config = ConfigDict(populate_by_name=True)
    label: str
    execute: Callable[
        [str, dict[str, Any], asyncio.Event | None, AgentToolUpdateCallback | None],
        Awaitable[AgentToolResult],
    ]


class AgentContext(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    system_prompt: str = Field(default="", alias="systemPrompt")
    messages: list[AgentMessage]
    tools: list[AgentTool] | None = None


class AgentLoopConfig(SimpleStreamOptions):
    model_config = ConfigDict(populate_by_name=True)
    model: Model
    convert_to_llm: Callable[
        [list[AgentMessage]], list[Message] | Awaitable[list[Message]]
    ] = Field(alias="convertToLlm")
    transform_context: Callable[
        [list[AgentMessage], asyncio.Event | None], Awaitable[list[AgentMessage]]
    ] | None = Field(default=None, alias="transformContext")
    get_api_key: Callable[
        [str], Awaitable[str | None] | str | None
    ] | None = Field(default=None, alias="getApiKey")
    get_steering_messages: Callable[
        [], Awaitable[list[AgentMessage]]
    ] | None = Field(default=None, alias="getSteeringMessages")
    get_follow_up_messages: Callable[
        [], Awaitable[list[AgentMessage]]
    ] | None = Field(default=None, alias="getFollowUpMessages")
    # Retry configuration
    max_retries: int = Field(default=3, alias="maxRetries")
    retry_delay_ms: int = Field(default=1000, alias="retryDelayMs")
    retry_on_rate_limit: bool = Field(default=True, alias="retryOnRateLimit")
    # Timeout configuration
    tool_timeout_ms: int | None = Field(default=60000, alias="toolTimeoutMs")
    llm_timeout_ms: int | None = Field(default=120000, alias="llmTimeoutMs")


class AgentState(BaseModel):
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)
    system_prompt: str = Field(default="", alias="systemPrompt")
    model: Model | None = None
    thinking_level: ThinkingLevel = Field(default="off", alias="thinkingLevel")
    tools: list[AgentTool] = Field(default_factory=list)
    messages: list[AgentMessage] = Field(default_factory=list)
    is_streaming: bool = Field(default=False, alias="isStreaming")
    stream_message: AgentMessage | None = Field(default=None, alias="streamMessage")
    pending_tool_calls: set[str] = Field(default_factory=set, alias="pendingToolCalls")
    error: str | None = None


class AgentStartEvent(BaseModel):
    type: Literal["agent_start"] = "agent_start"


class AgentEndEvent(BaseModel):
    type: Literal["agent_end"] = "agent_end"
    messages: list[AgentMessage]


class TurnStartEvent(BaseModel):
    type: Literal["turn_start"] = "turn_start"


class TurnEndEvent(BaseModel):
    type: Literal["turn_end"] = "turn_end"
    message: AgentMessage
    tool_results: list[ToolResultMessage] = Field(alias="toolResults")


class MessageStartEvent(BaseModel):
    type: Literal["message_start"] = "message_start"
    message: AgentMessage


class MessageUpdateEvent(BaseModel):
    type: Literal["message_update"] = "message_update"
    message: AgentMessage
    assistant_message_event: AssistantMessageEvent = Field(alias="assistantMessageEvent")


class MessageEndEvent(BaseModel):
    type: Literal["message_end"] = "message_end"
    message: AgentMessage


class ToolExecutionStartEvent(BaseModel):
    type: Literal["tool_execution_start"] = "tool_execution_start"
    tool_call_id: str = Field(alias="toolCallId")
    tool_name: str = Field(alias="toolName")
    args: Any


class ToolExecutionUpdateEvent(BaseModel):
    type: Literal["tool_execution_update"] = "tool_execution_update"
    tool_call_id: str = Field(alias="toolCallId")
    tool_name: str = Field(alias="toolName")
    args: Any
    partial_result: Any = Field(alias="partialResult")


class ToolExecutionEndEvent(BaseModel):
    type: Literal["tool_execution_end"] = "tool_execution_end"
    tool_call_id: str = Field(alias="toolCallId")
    tool_name: str = Field(alias="toolName")
    result: Any
    is_error: bool = Field(alias="isError")


AgentEvent = Union[
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
]
