"""
Streaming Response Example

This example shows how to handle streaming responses from the agent.
Streaming allows you to display responses as they're generated.
"""
import asyncio

from pi_agent import Agent
from pi_ai import Model, ModelCost
from pi_ai.types import UserMessage, TextContent


def on_event(event):
    """Handle agent events with special handling for streaming."""
    # Print streaming text as it arrives
    if event.type == "text_delta":
        if hasattr(event, "delta"):
            print(event.delta, end="", flush=True)
    elif event.type == "text_end":
        print()  # New line after text is complete
    elif event.type == "agent_start":
        print("\n" + "=" * 60)
        print("Assistant: ", end="", flush=True)
    elif event.type == "agent_end":
        print("=" * 60)


async def main():
    # Create an agent
    agent = Agent(options={
        "model": Model(
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
    })

    # Set system prompt
    agent.set_system_prompt("You are a helpful assistant who provides detailed answers.")

    # Subscribe to events for streaming
    unsubscribe = agent.subscribe(on_event)

    # Example 1: Simple streaming
    print("Example 1: Streaming a response")
    print("-" * 60)
    print("User: Tell me a short story about space exploration.")
    print("-" * 60)

    try:
        await agent.prompt("Tell me a short story about space exploration.")
    except Exception as e:
        print(f"\nError: {e}")

    # Example 2: Multi-turn conversation with streaming
    print("\n\n" + "=" * 60)
    print("Example 2: Multi-turn conversation")
    print("=" * 60)

    questions = [
        "What's the capital of France?",
        "And what's famous about it?",
        "Can you recommend visiting there?"
    ]

    for i, question in enumerate(questions, 1):
        print(f"\n[{i}] User: {question}")
        print("-" * 60)
        try:
            await agent.prompt(question)
        except Exception as e:
            print(f"\nError: {e}")

    # Example 3: Handling thinking/reasoning
    print("\n\n" + "=" * 60)
    print("Example 3: Question with reasoning")
    print("=" * 60)
    print("User: What's 15 * 24? Show your work.")
    print("-" * 60)

    # Enable thinking
    agent.set_thinking_level("medium")

    try:
        await agent.prompt("What's 15 * 24? Show your work.")
    except Exception as e:
        print(f"\nError: {e}")

    # Show conversation summary
    print("\n" + "=" * 60)
    print("Conversation Summary")
    print("=" * 60)
    print(f"Total turns: {len([m for m in agent.state.messages if m.role == 'user'])}")
    print(f"Total messages: {len(agent.state.messages)}")

    # Unsubscribe
    unsubscribe()


if __name__ == "__main__":
    asyncio.run(main())
