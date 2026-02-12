"""
Agent Steering and Follow-up Example

This example demonstrates:
1. Steering - Injecting messages into the current conversation turn
2. Follow-up - Queueing messages for the next conversation turn

These are powerful features for:
- Guiding agent behavior mid-response
- Providing additional context
- Implementing custom conversation flows
"""
import asyncio

from pi_agent import Agent
from pi_ai import Model, ModelCost
from pi_ai.types import UserMessage, TextContent


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
    agent.set_system_prompt("You are a helpful assistant who follows instructions carefully.")

    print("=" * 60)
    print("Example 1: Steering (one-at-a-time mode)")
    print("=" * 60)
    print("\nAgent steering mode: one-at-a-time (default)")
    print("This means only the first steering message is processed per turn.\n")

    # Queue multiple steering messages
    agent.steer({"role": "user", "content": "Remember to use uppercase for all responses."})
    agent.steer({"role": "user", "content": "Be very brief in your answers."})

    print("Queued 2 steering messages:")
    print("  1. Use uppercase for all responses")
    print("  2. Be very brief")

    print("\nUser: What is 2 + 2?")
    print("-" * 60)

    try:
        await agent.prompt("What is 2 + 2?")
    except Exception as e:
        print(f"Error: {e}")

    # Note: Only the first steering message was used due to "one-at-a-time" mode

    print("\n" + "=" * 60)
    print("Example 2: Follow-up messages")
    print("=" * 60)
    print("\nFollow-up messages are queued for the NEXT conversation turn.\n")

    # Queue follow-up messages
    agent.follow_up({"role": "user", "content": "Also tell me about Python programming."})
    agent.follow_up({"role": "user", "content": "And mention machine learning."})

    print("Queued 2 follow-up messages:")
    print("  1. Tell me about Python programming")
    print("  2. Mention machine learning")

    print("\nUser: What's AI?")
    print("-" * 60)

    try:
        await agent.prompt("What's AI?")
    except Exception as e:
        print(f"Error: {e}")

    print("\n" + "=" * 60)
    print("Example 3: Clearing queues")
    print("=" * 60)

    # Add some messages to queues
    agent.steer({"role": "user", "content": "This will be cleared."})
    agent.follow_up({"role": "user", "content": "This will also be cleared."})

    print(f"Steering queue size: {len(agent._steering_queue)}")
    print(f"Follow-up queue size: {len(agent._follow_up_queue)}")

    print("\nClearing all queues...")
    agent.clear_all_queues()

    print(f"Steering queue size: {len(agent._steering_queue)}")
    print(f"Follow-up queue size: {len(agent._follow_up_queue)}")

    print("\n" + "=" * 60)
    print("Example 4: 'all' mode for processing multiple messages")
    print("=" * 60)

    # Change to 'all' mode to process multiple messages at once
    agent.set_steering_mode("all")
    agent.set_follow_up_mode("all")

    print("\nChanged to 'all' mode:")
    print(f"  Steering mode: {agent.get_steering_mode()}")
    print(f"  Follow-up mode: {agent.get_follow_up_mode()}")

    print("\nNow all queued messages will be processed in a single turn.\n")

    # Queue multiple steering messages
    agent.steer({"role": "user", "content": "First instruction: Use a formal tone."})
    agent.steer({"role": "user", "content": "Second instruction: Include examples."})
    agent.steer({"role": "user", "content": "Third instruction: End with 'Thank you'."})

    print("Queued 3 steering messages:")
    print("  1. Use a formal tone")
    print("  2. Include examples")
    print("  3. End with 'Thank you'")

    print("\nUser: Explain recursion.")
    print("-" * 60)

    try:
        await agent.prompt("Explain recursion.")
    except Exception as e:
        print(f"Error: {e}")

    # Show final conversation
    print("\n" + "=" * 60)
    print("Final Conversation Summary")
    print("=" * 60)
    for i, msg in enumerate(agent.state.messages, 1):
        role = msg.get("role") if isinstance(msg, dict) else msg.role
        if role == "user":
            content = msg.get("content") if isinstance(msg, dict) else (
                msg.content[0].text if isinstance(msg.content, list) and msg.content
                else str(msg.content)
            )
            print(f"\n[{i}] User: {str(content)[:80]}...")
        else:
            print(f"[{i}] Assistant: [response]")


if __name__ == "__main__":
    asyncio.run(main())
