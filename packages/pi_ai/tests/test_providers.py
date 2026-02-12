import pytest
import respx

from pi_ai.types import Model, ModelCost, Context, UserMessage, TextContent, Usage, UsageCost
from pi_ai.providers.openai import stream_openai_completions


@pytest.fixture
def test_model():
    return Model(
        id="gpt-4o",
        name="GPT-4o",
        api="openai-completions",
        provider="openai",
        base_url="https://api.openai.com/v1",
        reasoning=False,
        input=["text", "image"],
        cost=ModelCost(input=2.50, output=10.00, cache_read=1.25, cache_write=1.25),
        context_window=128000,
        max_tokens=16384,
    )


@pytest.fixture
def test_context():
    return Context(
        system_prompt="You are a helpful assistant.",
        messages=[
            UserMessage(
                role="user",
                content=[TextContent(type="text", text="Hello!")],
                timestamp=1234567890,
            )
        ],
    )


class TestOpenAIProvider:
    @pytest.mark.skip(reason="Mock setup needs more work for async streaming")
    @respx.mock
    @pytest.mark.asyncio
    async def test_stream_openai_completions_mocked(self, test_model, test_context, mock_openai_stream):
        import json
        
        mock_openai_stream(respx.mock)
        
        events = []
        stream = stream_openai_completions(test_model, test_context)
        
        async for event in stream:
            events.append(event)
        
        assert len(events) > 0
        
        event_types = [e.type for e in events]
        assert "start" in event_types
        assert "text_delta" in event_types or "done" in event_types

    def test_normalize_mistral_tool_id(self):
        from pi_ai.providers.openai import normalize_mistral_tool_id
        
        assert normalize_mistral_tool_id("abc123ABC") == "abc123ABC"
        assert normalize_mistral_tool_id("short") == "shortABCD"
        assert normalize_mistral_tool_id("verylongid123456789") == "verylongi"

    def test_has_tool_history(self):
        from pi_ai.providers.openai import has_tool_history
        from pi_ai.types import AssistantMessage, ToolResultMessage, ToolCall, Usage, UsageCost
        
        user_msgs = [UserMessage(role="user", content=[TextContent(type="text", text="Hi")], timestamp=0)]
        assert has_tool_history(user_msgs) is False
        
        assistant_with_tool = [
            AssistantMessage(
                role="assistant",
                content=[
                    ToolCall(type="toolCall", id="1", name="test", arguments={}, thought_signature=None)
                ],
                api="test",
                provider="test",
                model="test",
                usage=Usage(input=0, output=0, cache_read=0, cache_write=0, total_tokens=0, cost=UsageCost()),
                stopReason="stop",
                timestamp=0,
            )
        ]
        assert has_tool_history(assistant_with_tool) is True
