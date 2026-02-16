import pytest


def test_user_message_creation():
    from pi_ai.types import TextContent, UserMessage

    msg = UserMessage(
        role="user",
        content=[TextContent(type="text", text="Hello")],
        timestamp=1234567890,
    )
    assert msg.role == "user"
    assert msg.content[0].text  # type: ignore[union-attr] == "Hello"


def test_model_cost_calculation():
    from pi_ai.models import calculate_cost
    from pi_ai.types import Model, ModelCost, Usage, UsageCost

    model = Model(
        id="test-model",
        name="Test Model",
        api="openai-completions",
        provider="openai",
        baseUrl="https://api.openai.com",
        reasoning=False,
        input=["text"],
        cost=ModelCost(input=0.5, output=1.5, cacheRead=0.1, cacheWrite=0.05),
        contextWindow=128000,
        maxTokens=4096,
    )

    usage = Usage(
        input=1000,
        output=500,
        cacheRead=200,
        cacheWrite=50,
        totalTokens=1500,
        cost=UsageCost(input=0, output=0, cacheRead=0, cacheWrite=0, total=0),
    )

    cost = calculate_cost(model, usage)
    assert cost.input == pytest.approx(0.0005, rel=1e-6)
    assert cost.output == pytest.approx(0.00075, rel=1e-6)
    assert cost.cache_read == pytest.approx(0.00002, rel=1e-6)
    assert cost.cache_write == pytest.approx(0.0000025, rel=1e-6)


def test_env_api_key():
    import os

    from pi_ai.env_keys import get_env_api_key

    result = get_env_api_key("openai")
    assert result is None or result == os.environ.get("OPENAI_API_KEY")


def test_event_stream_basic():
    import asyncio

    from pi_ai.event_stream import EventStream

    async def test():
        stream = EventStream[int, list[int]](
            is_complete=lambda x: x == 100,
            extract_result=lambda x: [x],
        )

        stream.push(1)
        stream.push(50)
        stream.push(100)

        results = []
        async for item in stream:
            results.append(item)

        assert results == [1, 50, 100]
        assert await stream.result() == [100]

    asyncio.run(test())


def test_message_serialization():

    from pi_ai.types import (
        AssistantMessage,
        ImageContent,
        TextContent,
        ToolCall,
        ToolResultMessage,
        Usage,
        UsageCost,
        UserMessage,
    )

    user_msg = UserMessage(
        role="user",
        content=[
            TextContent(type="text", text="Hello"),
            ImageContent(type="image", data="base64imagedata", mimeType="image/png"),
        ],
        timestamp=1234567890,
    )
    user_json = user_msg.model_dump()
    assert user_json["role"] == "user"
    assert len(user_json["content"]) == 2
    assert user_json["content"][0]["text"] == "Hello"
    assert user_json["content"][1]["data"] == "base64imagedata"

    user_restored = UserMessage.model_validate(user_json)
    assert user_restored.role == "user"
    assert user_restored.content[0].text  # type: ignore[union-attr] == "Hello"

    assistant_msg = AssistantMessage(
        role="assistant",
        content=[
            TextContent(type="text", text="Hi there!"),
            ToolCall(
                type="toolCall",
                id="call_123",
                name="get_weather",
                arguments={"location": "Tokyo"},
                thoughtSignature=None,
            ),
        ],
        api="anthropic",
        provider="anthropic",
        model="claude-3-5-sonnet",
        usage=Usage(
            input=100,
            output=50,
            cacheRead=0,
            cacheWrite=0,
            totalTokens=150,
            cost=UsageCost(),
        ),
        timestamp=1234567891,
        stopReason="toolUse",
    )
    assistant_json = assistant_msg.model_dump()
    assert assistant_json["role"] == "assistant"
    assert assistant_json["model"] == "claude-3-5-sonnet"
    assert assistant_json["content"][1]["name"] == "get_weather"

    assistant_restored = AssistantMessage.model_validate(assistant_json)
    assert assistant_restored.role == "assistant"
    content1 = assistant_restored.content[1]
    assert isinstance(content1, ToolCall)
    assert content1.name == "get_weather"

    tool_result_msg = ToolResultMessage(
        role="toolResult",
        toolCallId="call_123",
        toolName="get_weather",
        content=[TextContent(type="text", text='{"temp": 25}')],
        isError=False,
        timestamp=1234567892,
    )
    tool_result_json = tool_result_msg.model_dump()
    assert tool_result_json["tool_call_id"] == "call_123"
    assert tool_result_json["tool_name"] == "get_weather"

    tool_result_restored = ToolResultMessage.model_validate(tool_result_json)
    assert tool_result_restored.tool_call_id == "call_123"


def test_json_schema_generation():
    from pi_ai.types import AssistantMessage, TextContent, ToolResultMessage, UserMessage

    user_schema = UserMessage.model_json_schema()
    assert "role" in user_schema["properties"]
    assert "content" in user_schema["properties"]
    assert "timestamp" in user_schema["properties"]

    assistant_schema = AssistantMessage.model_json_schema()
    assert "role" in assistant_schema["properties"]
    assert "content" in assistant_schema["properties"]
    assert "model" in assistant_schema["properties"]
    assert "stopReason" in assistant_schema["properties"]

    tool_result_schema = ToolResultMessage.model_json_schema()
    assert "toolCallId" in tool_result_schema["properties"]
    assert "toolName" in tool_result_schema["properties"]

    text_content_schema = TextContent.model_json_schema()
    assert "type" in text_content_schema["properties"]
    assert "text" in text_content_schema["properties"]


def test_content_type_validation():
    import pydantic
    import pytest
    from pi_ai.types import (
        ImageContent,
        TextContent,
        ThinkingContent,
        ToolCall,
    )

    text = TextContent(type="text", text="Hello world")
    assert text.type == "text"
    assert text.text == "Hello world"

    with pytest.raises(pydantic.ValidationError):
        TextContent(type="text")  # type: ignore[call-arg]

    image = ImageContent(
        type="image",
        data="iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
        mimeType="image/png",
    )
    assert image.type == "image"
    assert image.mime_type == "image/png"

    with pytest.raises(pydantic.ValidationError):
        ImageContent(type="image")  # type: ignore[call-arg]

    thinking = ThinkingContent(
        type="thinking",
        thinking="Let me think about this...",
        thinkingSignature="sig123",
    )
    assert thinking.type == "thinking"
    assert thinking.thinking == "Let me think about this..."

    tool_call = ToolCall(
        type="toolCall",
        id="call_abc123",
        name="get_weather",
        arguments={"location": "Tokyo"},
        thoughtSignature=None,
    )
    assert tool_call.type == "toolCall"
    assert tool_call.id == "call_abc123"
    assert tool_call.name == "get_weather"
    assert tool_call.arguments == {"location": "Tokyo"}


def test_union_type_discrimination():
    from pi_ai.types import (
        AssistantContent,
        ImageContent,
        TextContent,
        ThinkingContent,
        ToolCall,
        UserContent,
    )

    text = TextContent(type="text", text="Hello")
    assert isinstance(text, TextContent)

    image = ImageContent(type="image", data="base64", mimeType="image/png")
    assert isinstance(image, ImageContent)

    user_contents: list[UserContent] = [text, image]
    assert len(user_contents) == 2

    tool_call = ToolCall(
        type="toolCall",
        id="call_1",
        name="test",
        arguments={},
        thoughtSignature=None,
    )
    thinking = ThinkingContent(type="thinking", thinking="hmm", thinkingSignature=None)

    assistant_contents: list[AssistantContent] = [text, thinking, tool_call]
    assert len(assistant_contents) == 3

    for content in assistant_contents:
        if content.type == "text":
            assert hasattr(content, "text")
        elif content.type == "thinking":
            assert hasattr(content, "thinking")
        elif content.type == "toolCall":
            assert hasattr(content, "name")
