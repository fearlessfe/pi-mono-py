"""
Quick Start Example - No API Required

This example demonstrates agent concepts without making API calls.
Perfect for understanding the agent structure and behavior.
"""
import asyncio

from pi_agent import Agent
from pi_agent.types import AgentMessage
from pi_ai.types import TextContent, UserMessage, AssistantMessage, Usage, StopReason, ToolCall


def on_event(event):
    """Simple event handler."""
    print(f"\n[{event.type}]")
    if hasattr(event, "timestamp"):
        print(f"  Time: {event.timestamp}")


async def main():
    print("=" * 60)
    print("Quick Start - Agent Concepts")
    print("=" * 60)

    # Create an agent without a model (for testing structure)
    agent = Agent(options={})

    # Set system prompt
    agent.set_system_prompt("You are a helpful assistant.")
    print(f"\nSystem Prompt: {agent.state.system_prompt}")

    # Subscribe to events
    unsubscribe = agent.subscribe(on_event)

    # Demonstrate state management
    print("\n" + "-" * 60)
    print("State Management")
    print("-" * 60)
    print(f"Initial messages: {len(agent.state.messages)}")

    # Add messages manually
    user_msg = UserMessage(
        role="user",
        content=[TextContent(type="text", text="Hello!")],
        timestamp=0
    )

    agent.append_message(user_msg)
    print(f"After adding message: {len(agent.state.messages)}")

    # Show message
    print(f"\nMessage details:")
    print(f"  Role: {user_msg.role}")
    print(f"  Content: {user_msg.content[0].text}")

    # Demonstrate queue management
    print("\n" + "-" * 60)
    print("Queue Management")
    print("-" * 60)

    # Add steering messages
    agent.steer({"role": "user", "content": "First steering message"})
    agent.steer({"role": "user", "content": "Second steering message"})

    print(f"Steering queue size: {len(agent._steering_queue)}")
    print(f"Steering mode: {agent.get_steering_mode()}")

    # Dequeue one message (one-at-a-time mode)
    dequeued = agent._dequeue_steering_messages()
    print(f"Dequeued: {len(dequeued)} message(s)")
    print(f"Remaining in queue: {len(agent._steering_queue)}")

    # Clear all queues
    agent.clear_all_queues()
    print(f"\nAfter clearing all queues:")
    print(f"  Steering queue: {len(agent._steering_queue)}")
    print(f"  Follow-up queue: {len(agent._follow_up_queue)}")

    # Demonstrate thinking levels
    print("\n" + "-" * 60)
    print("Thinking Levels")
    print("-" * 60)
    print(f"Current thinking level: {agent.state.thinking_level}")

    levels = ["off", "minimal", "low", "medium", "high", "xhigh"]
    print(f"Available levels: {', '.join(levels)}")

    for level in levels[:3]:
        agent.set_thinking_level(level)
        print(f"Set to: {level}")

    # Demonstrate tool structure
    print("\n" + "-" * 60)
    print("Tool Structure")
    print("-" * 60)

    from pi_agent import AgentTool

    # Mock tool structure
    tool_params = {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "A name"},
            "count": {"type": "number", "description": "A number"}
        },
        "required": ["name", "count"]
    }

    print("Tool parameters (JSON Schema):")
    import json
    print(json.dumps(tool_params, indent=2))

    # Unsubscribe
    unsubscribe()

    print("\n" + "=" * 60)
    print("Demo Complete!")
    print("=" * 60)
    print("\nKey takeaways:")
    print("  1. Agent maintains state (messages, tools, etc.)")
    print("  2. Events are emitted for lifecycle actions")
    print("  3. Steering allows injecting messages mid-conversation")
    print("  4. Queue management controls message flow")
    print("  5. Tools use JSON Schema for parameter validation")
    print("\nNext: Try the other examples with actual API calls!")


if __name__ == "__main__":
    asyncio.run(main())
