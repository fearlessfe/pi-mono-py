import pytest


def test_user_message_creation():
    from pi_ai.types import UserMessage, TextContent

    msg = UserMessage(
        role="user",
        content=[TextContent(type="text", text="Hello")],
        timestamp=1234567890,
    )
    assert msg.role == "user"
    assert msg.content[0].text == "Hello"


def test_model_cost_calculation():
    from pi_ai.types import Model, ModelCost, Usage, UsageCost, StopReason
    from pi_ai.models import calculate_cost

    model = Model(
        id="test-model",
        name="Test Model",
        api="openai-completions",
        provider="openai",
        base_url="https://api.openai.com",
        reasoning=False,
        input=["text"],
        cost=ModelCost(input=0.5, output=1.5, cache_read=0.1, cache_write=0.05),
        context_window=128000,
        max_tokens=4096,
    )

    usage = Usage(
        input=1000,
        output=500,
        cache_read=200,
        cache_write=50,
        total_tokens=1500,
        cost=UsageCost(input=0, output=0, cache_read=0, cache_write=0, total=0),
    )

    cost = calculate_cost(model, usage)
    assert cost.input == pytest.approx(0.0005, rel=1e-6)
    assert cost.output == pytest.approx(0.00075, rel=1e-6)
    assert cost.cache_read == pytest.approx(0.00002, rel=1e-6)
    assert cost.cache_write == pytest.approx(0.0000025, rel=1e-6)


def test_env_api_key():
    from pi_ai.env_keys import get_env_api_key
    import os

    result = get_env_api_key("openai")
    assert result is None or result == os.environ.get("OPENAI_API_KEY")


def test_event_stream_basic():
    from pi_ai.event_stream import EventStream
    import asyncio

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
