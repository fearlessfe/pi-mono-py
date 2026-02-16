"""Tests for agent_loop and related types."""

from time import time

import pytest
from pi_agent.loop import agent_loop_continue
from pi_agent.types import AgentContext, AgentLoopConfig, AgentTool, AgentToolResult
from pi_ai.types import (
    AssistantMessage,
    Model,
    ModelCost,
    TextContent,
    Usage,
)


def create_mock_model():
    return Model(
        id="test-model",
        name="Test Model",
        api="openai-completions",
        provider="openai",
        baseUrl="https://api.test.com",
        reasoning=False,
        input=["text"],
        cost=ModelCost(),
        contextWindow=128000,
        maxTokens=4096,
    )


class TestAgentLoopConfig:
    """Tests for AgentLoopConfig."""

    def test_config_defaults(self):
        """Test AgentLoopConfig default values."""
        model = create_mock_model()

        config = AgentLoopConfig(
            model=model,
            convertToLlm=lambda msgs: [],
        )

        assert config.max_retries == 3
        assert config.retry_delay_ms == 1000
        assert config.retry_on_rate_limit is True
        assert config.tool_timeout_ms == 60000
        assert config.llm_timeout_ms == 120000

    def test_config_custom_values(self):
        """Test AgentLoopConfig with custom values."""
        model = create_mock_model()

        async def get_steering():
            return []

        config = AgentLoopConfig(
            model=model,
            convertToLlm=lambda msgs: [],
            maxRetries=5,
            retryDelayMs=2000,
            toolTimeoutMs=30000,
            llmTimeoutMs=60000,
            getSteeringMessages=get_steering,
        )

        assert config.max_retries == 5
        assert config.retry_delay_ms == 2000
        assert config.tool_timeout_ms == 30000
        assert config.llm_timeout_ms == 60000
        assert config.get_steering_messages == get_steering


class TestAgentLoopContinueValidation:
    """Tests for agent_loop_continue validation."""

    @pytest.mark.asyncio
    async def test_continue_from_assistant_message_raises(self):
        """Test that continuing from an assistant message raises an error."""
        model = create_mock_model()

        assistant_message = AssistantMessage(
            role="assistant",
            content=[TextContent(type="text", text="Previous response")],
            api=model.api,
            provider=model.provider,
            model=model.id,
            usage=Usage(),
            stopReason="stop",
            timestamp=int(time() * 1000),
        )

        context = AgentContext(
            systemPrompt="",
            messages=[assistant_message],
            tools=[],
        )

        config = AgentLoopConfig(
            model=model,
            convertToLlm=lambda msgs: [],
        )

        with pytest.raises(ValueError, match="Cannot continue from message role: assistant"):
            agent_loop_continue(context, config)

    @pytest.mark.asyncio
    async def test_continue_with_no_messages_raises(self):
        """Test that continuing with no messages raises an error."""
        model = create_mock_model()

        context = AgentContext(
            systemPrompt="",
            messages=[],
            tools=[],
        )

        config = AgentLoopConfig(
            model=model,
            convertToLlm=lambda msgs: [],
        )

        with pytest.raises(ValueError, match="Cannot continue: no messages"):
            agent_loop_continue(context, config)


class TestToolExecution:
    """Tests for tool execution logic."""

    @pytest.mark.asyncio
    async def test_tool_execution_success(self):
        """Test successful tool execution."""

        async def mock_execute(tool_call_id, args, cancel_event, on_update):
            return AgentToolResult(
                content=[TextContent(type="text", text="Tool result")],
                details={},
            )

        test_tool = AgentTool(
            name="test_tool",
            description="A test tool",
            parameters={"type": "object", "properties": {"arg1": {"type": "string"}}},
            label="Test Tool",
            execute=mock_execute,
        )

        result = await test_tool.execute("call_123", {"arg1": "value"}, None, None)

        assert result is not None
        assert result.content[0].text == "Tool result"

    @pytest.mark.asyncio
    async def test_tool_execution_with_error(self):
        """Test tool execution that returns an error."""

        async def mock_execute(tool_call_id, args, cancel_event, on_update):
            return AgentToolResult(
                content=[TextContent(type="text", text="Error: Something went wrong")],
                details={"error": "execution_failed"},
            )

        test_tool = AgentTool(
            name="error_tool",
            description="A tool that errors",
            parameters={},
            label="Error Tool",
            execute=mock_execute,
        )

        result = await test_tool.execute("call_456", {}, None, None)

        assert result is not None
        assert "error" in result.details
