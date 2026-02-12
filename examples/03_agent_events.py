"""
Agent Events Example - Event Handling

This example demonstrates how to subscribe to and handle agent events.
Events are emitted for various lifecycle stages and actions.
"""
import asyncio

from pi_agent import Agent
from pi_ai import Model, ModelCost


def on_event(event):
    """Handle agent events with detailed logging."""
    print(f"\n{'=' * 60}")
    print(f"Event: {event.type}")
    print(f"{'=' * 60}")

    # Agent lifecycle events
    if event.type == "agent_start":
        print("Agent started processing a prompt")
        if hasattr(event, "timestamp"):
            print(f"Timestamp: {event.timestamp}")

    elif event.type == "turn_start":
        print("New conversation turn started")
        if hasattr(event, "timestamp"):
            print(f"Timestamp: {event.timestamp}")

    elif event.type == "agent_end":
        print("Agent finished processing")
        if hasattr(event, "messages"):
            print(f"Total messages in conversation: {len(event.messages)}")
        if hasattr(event, "timestamp"):
            print(f"Timestamp: {event.timestamp}")

    # Tool-related events
    elif event.type == "tool_start":
        print("Tool execution started")
        if hasattr(event, "tool_name"):
            print(f"Tool: {event.tool_name}")
        if hasattr(event, "tool_call_id"):
            print(f"Call ID: {event.tool_call_id}")
        if hasattr(event, "params"):
            print(f"Parameters: {event.params}")

    elif event.type == "tool_delta":
        print("Tool execution update")
        if hasattr(event, "tool_call_id"):
            print(f"Call ID: {event.tool_call_id}")
        if hasattr(event, "content"):
            print(f"Content delta: {event.content}")

    elif event.type == "tool_end":
        print("Tool execution completed")
        if hasattr(event, "tool_call_id"):
            print(f"Call ID: {event.tool_call_id}")
        if hasattr(event, "result"):
            print(f"Result: {event.result}")

    # Streaming events
    elif event.type == "text_start":
        print("Text content started")
        if hasattr(event, "content_index"):
            print(f"Content index: {event.content_index}")

    elif event.type == "text_delta":
        # Print delta for streaming effect
        if hasattr(event, "delta"):
            print(event.delta, end="", flush=True)

    elif event.type == "text_end":
        print()  # New line after streaming
        print("Text content completed")
        if hasattr(event, "content"):
            print(f"Final text: {event.content}")

    # Error events
    elif event.type == "error":
        print("An error occurred!")
        if hasattr(event, "error"):
            print(f"Error: {event.error}")
        if hasattr(event, "reason"):
            print(f"Reason: {event.reason}")


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

    # Subscribe to events
    print("Subscribing to agent events...")
    unsubscribe = agent.subscribe(on_event)

    # Set system prompt
    agent.set_system_prompt("You are a helpful assistant. Be concise and friendly.")

    # Example 1: Simple conversation
    print("\n" + "=" * 60)
    print("Test 1: Simple greeting")
    print("=" * 60)
    print("\nUser: Hello!")
    print("-" * 60)

    try:
        await agent.prompt("Hello!")
    except Exception as e:
        print(f"\nError: {e}")

    # Example 2: Question requiring thought
    print("\n\n" + "=" * 60)
    print("Test 2: Complex question")
    print("=" * 60)
    print("\nUser: What's the capital of France?")
    print("-" * 60)

    try:
        await agent.prompt("What's the capital of France?")
    except Exception as e:
        print(f"\nError: {e}")

    # Show conversation history
    print("\n\n" + "=" * 60)
    print("Conversation History")
    print("=" * 60)
    for i, msg in enumerate(agent.state.messages, 1):
        print(f"\n[{i}] {msg.role}")
        if hasattr(msg, "content") and msg.content:
            for content_item in msg.content:
                if hasattr(content_item, "text"):
                    print(f"    {content_item.text[:100]}...")  # Truncate for readability

    # Unsubscribe
    print("\n" + "=" * 60)
    print("Unsubscribing from events...")
    print("=" * 60)
    unsubscribe()


if __name__ == "__main__":
    asyncio.run(main())
