"""
Simple Agent Example - Basic Usage

This example shows the simplest way to use the agent.
"""
import asyncio

from pi_agent import Agent
from pi_ai import Model, ModelCost
from pi_ai.types import UserMessage, TextContent


def create_test_model() -> Model:
    """Create a simple test model configuration."""
    return Model(
        id="test-model",
        name="Test Model",
        api="openai-completions",
        provider="openai",
        base_url="https://api.openai.com/v1",
        reasoning=False,
        input=["text"],
        cost=ModelCost(input=0.5, output=1.5, cache_read=0.0, cache_write=0.0),
        context_window=128000,
        max_tokens=4096,
    )


def on_event(event):
    """Handle agent events."""
    print(f"[{event.type}]")
    if hasattr(event, "message"):
        print(f"  Message: {event.message}")
    if hasattr(event, "messages"):
        print(f"  Messages: {event.messages}")


async def main():
    # Create an agent with a model
    agent = Agent(options={"model": create_test_model()})

    # Subscribe to events
    unsubscribe = agent.subscribe(on_event)

    # Set system prompt
    agent.set_system_prompt("You are a helpful assistant. Be concise and friendly.")

    # Send a prompt
    print("=" * 60)
    print("User: Hello! Can you help me?")
    print("=" * 60)

    await agent.prompt("Hello! Can you help me?")

    # Check the response
    print("\n" + "=" * 60)
    print("Conversation so far:")
    print("=" * 60)
    for msg in agent.state.messages:
        if isinstance(msg, UserMessage):
            content = (
                msg.content if isinstance(msg.content, str)
                else msg.content[0].text if isinstance(msg.content, list) and msg.content
                else str(msg.content)
            )
            print(f"User: {content}")
        elif msg.role == "assistant":
            if msg.content:
                text_parts = [
                    c.text
                    for c in msg.content
                    if hasattr(c, "text")
                ]
                if text_parts:
                    print(f"Assistant: {''.join(text_parts)}")

    # Unsubscribe from events
    unsubscribe()


if __name__ == "__main__":
    asyncio.run(main())
