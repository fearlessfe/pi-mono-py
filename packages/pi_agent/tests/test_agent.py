import pytest


def test_agent_state_default():
    from pi_agent.types import AgentState
    from pi_ai.types import Model, ModelCost, StopReason

    model = Model(
        id="test-model",
        name="Test Model",
        api="openai-completions",
        provider="openai",
        base_url="https://api.openai.com",
        reasoning=False,
        input=["text"],
        cost=ModelCost(),
        context_window=128000,
        max_tokens=4096,
    )

    state = AgentState(
        system_prompt="You are helpful.",
        model=model,
        thinking_level="off",
        tools=[],
        messages=[],
    )
    assert state.system_prompt == "You are helpful."
    assert state.thinking_level == "off"
    assert len(state.tools) == 0
    assert len(state.messages) == 0
    assert state.is_streaming is False
    assert state.stream_message is None
    assert len(state.pending_tool_calls) == 0


def test_agent_tool_result():
    from pi_agent.types import AgentToolResult, TextContent

    result = AgentToolResult(
        content=[TextContent(type="text", text="Tool output")],
        details={"path": "/tmp/file.txt"},
    )
    assert result.content[0].text == "Tool output"
    assert result.details == {"path": "/tmp/file.txt"}


def test_agent_events():
    from pi_agent.types import AgentStartEvent, AgentEndEvent, TurnStartEvent

    start = AgentStartEvent()
    assert start.type == "agent_start"

    turn_start = TurnStartEvent()
    assert turn_start.type == "turn_start"

    end = AgentEndEvent(messages=[])
    assert end.type == "agent_end"
    assert end.messages == []


def test_steering_queue_one_at_a_time():
    from pi_agent.types import AgentToolResult, TextContent

    from pi_agent.agent import Agent

    agent = Agent()

    agent.steer({"role": "user", "content": "Hello"})
    agent.steer({"role": "user", "content": "World"})

    assert len(agent._steering_queue) == 2

    dequeued = agent._dequeue_steering_messages()
    assert len(dequeued) == 1
    assert len(agent._steering_queue) == 1

    dequeued2 = agent._dequeue_steering_messages()
    assert len(dequeued2) == 1
    assert len(agent._steering_queue) == 0
