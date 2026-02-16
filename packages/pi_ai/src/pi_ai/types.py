from __future__ import annotations

from typing import Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field

ThinkingLevel = Literal["minimal", "low", "medium", "high", "xhigh"]

CacheRetention = Literal["none", "short", "long"]

StopReason = Literal["stop", "length", "toolUse", "error", "aborted"]

KnownApi = Literal[
    "openai-completions",
    "openai-responses",
    "azure-openai-responses",
    "openai-codex-responses",
    "anthropic-messages",
    "bedrock-converse-stream",
    "google-generative-ai",
    "google-gemini-cli",
    "google-vertex",
    "mistral-chat",
    "xai-chat",
    "openrouter-chat",
    "zhipu-chat",
]

KnownProvider = Literal[
    "amazon-bedrock",
    "anthropic",
    "google",
    "google-gemini-cli",
    "google-antigravity",
    "google-vertex",
    "openai",
    "azure-openai-responses",
    "openai-codex",
    "github-copilot",
    "xai",
    "groq",
    "cerebras",
    "openrouter",
    "vercel-ai-gateway",
    "zai",
    "mistral",
    "minimax",
    "minimax-cn",
    "huggingface",
    "opencode",
    "kimi-coding",
    "zhipu",
]


class ThinkingBudgets(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    minimal: int | None = None
    low: int | None = None
    medium: int | None = None
    high: int | None = None


class StreamOptions(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    temperature: float | None = None
    max_tokens: int | None = Field(default=None, alias="maxTokens")
    api_key: str | None = Field(default=None, alias="apiKey")
    cache_retention: CacheRetention | None = Field(default=None, alias="cacheRetention")
    session_id: str | None = Field(default=None, alias="sessionId")
    headers: dict[str, str] | None = None
    max_retry_delay_ms: int | None = Field(default=None, alias="maxRetryDelayMs")
    tool_choice: str | None = Field(default=None, alias="toolChoice")


class SimpleStreamOptions(StreamOptions):
    reasoning: ThinkingLevel | None = None
    thinking_budgets: ThinkingBudgets | None = Field(default=None, alias="thinkingBudgets")


class TextContent(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    type: Literal["text"] = "text"
    text: str
    text_signature: str | None = Field(default=None, alias="textSignature")


class ThinkingContent(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    type: Literal["thinking"] = "thinking"
    thinking: str
    thinking_signature: str | None = Field(default=None, alias="thinkingSignature")


class ImageContent(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    type: Literal["image"] = "image"
    data: str
    mime_type: str = Field(alias="mimeType")


class ToolCall(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    type: Literal["toolCall"] = "toolCall"
    id: str
    name: str
    arguments: dict[str, Any]
    thought_signature: str | None = Field(default=None, alias="thoughtSignature")


AssistantContent = Union[TextContent, ThinkingContent, ToolCall]
UserContent = Union[TextContent, ImageContent]
ToolResultContent = Union[TextContent, ImageContent]


class UsageCost(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    input: float = 0.0
    output: float = 0.0
    cache_read: float = Field(default=0.0, alias="cacheRead")
    cache_write: float = Field(default=0.0, alias="cacheWrite")
    total: float = 0.0


class Usage(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    input: int = 0
    output: int = 0
    cache_read: int = Field(default=0, alias="cacheRead")
    cache_write: int = Field(default=0, alias="cacheWrite")
    total_tokens: int = Field(default=0, alias="totalTokens")
    cost: UsageCost = Field(default_factory=UsageCost)


class UserMessage(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    role: Literal["user"] = "user"
    content: str | list[UserContent]
    timestamp: int


class AssistantMessage(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    role: Literal["assistant"] = "assistant"
    content: list[AssistantContent]
    api: str
    provider: str
    model: str
    usage: Usage
    stop_reason: StopReason = Field(alias="stopReason")
    error_message: str | None = Field(default=None, alias="errorMessage")
    timestamp: int


class ToolResultMessage(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    role: Literal["toolResult"] = "toolResult"
    tool_call_id: str = Field(alias="toolCallId")
    tool_name: str = Field(alias="toolName")
    content: list[ToolResultContent]
    details: Any = None
    is_error: bool = Field(alias="isError")
    timestamp: int


Message = Union[UserMessage, AssistantMessage, ToolResultMessage]


class Tool(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    name: str
    description: str
    parameters: dict[str, Any]


class Context(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    system_prompt: str | None = Field(default=None, alias="systemPrompt")
    messages: list[Message]
    tools: list[Tool] | None = None


# Api is a type alias for str representing the API name
Api = str


class ApiProvider(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    api: str
    stream: Any  # Callable or function reference
    stream_simple: Any  # Callable or function reference


class StartEvent(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    type: Literal["start"] = "start"
    partial: AssistantMessage


class TextStartEvent(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    type: Literal["text_start"] = "text_start"
    content_index: int = Field(alias="contentIndex")
    partial: AssistantMessage


class TextDeltaEvent(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    type: Literal["text_delta"] = "text_delta"
    content_index: int = Field(alias="contentIndex")
    delta: str
    partial: AssistantMessage


class TextEndEvent(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    type: Literal["text_end"] = "text_end"
    content_index: int = Field(alias="contentIndex")
    content: str
    partial: AssistantMessage


class ThinkingStartEvent(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    type: Literal["thinking_start"] = "thinking_start"
    content_index: int = Field(alias="contentIndex")
    partial: AssistantMessage


class ThinkingDeltaEvent(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    type: Literal["thinking_delta"] = "thinking_delta"
    content_index: int = Field(alias="contentIndex")
    delta: str
    partial: AssistantMessage


class ThinkingEndEvent(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    type: Literal["thinking_end"] = "thinking_end"
    content_index: int = Field(alias="contentIndex")
    content: str
    partial: AssistantMessage


class ToolcallStartEvent(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    type: Literal["toolcall_start"] = "toolcall_start"
    content_index: int = Field(alias="contentIndex")
    partial: AssistantMessage


class ToolcallDeltaEvent(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    type: Literal["toolcall_delta"] = "toolcall_delta"
    content_index: int = Field(alias="contentIndex")
    delta: str
    partial: AssistantMessage


class ToolcallEndEvent(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    type: Literal["toolcall_end"] = "toolcall_end"
    content_index: int = Field(alias="contentIndex")
    tool_call: ToolCall = Field(alias="toolCall")
    partial: AssistantMessage


class DoneEvent(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    type: Literal["done"] = "done"
    reason: Literal["stop", "length", "toolUse"]
    message: AssistantMessage


class ErrorEvent(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    type: Literal["error"] = "error"
    reason: Literal["aborted", "error"]
    error: AssistantMessage


AssistantMessageEvent = Union[
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
]


class ModelCost(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    input: float = 0.0
    output: float = 0.0
    cache_read: float = Field(default=0.0, alias="cacheRead")
    cache_write: float = Field(default=0.0, alias="cacheWrite")


class Model(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: str
    name: str
    api: str
    provider: str
    base_url: str = Field(alias="baseUrl")
    reasoning: bool
    input: list[str]
    cost: ModelCost
    context_window: int = Field(alias="contextWindow")
    max_tokens: int = Field(alias="maxTokens")
    headers: dict[str, str] | None = None
