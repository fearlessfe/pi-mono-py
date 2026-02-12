"""
Agent with Tools Example

This example shows how to use tools with the agent.
Tools allow the agent to perform actions like fetching data, calling APIs, etc.
"""
import asyncio

from pi_agent import Agent, AgentTool, AgentToolResult
from pi_ai import Model, ModelCost
from pi_ai.types import TextContent, ImageContent


# Define a simple calculator tool
async def calculator_tool(
    tool_call_id: str,
    params: dict,
    signal: asyncio.Event | None,
    on_update,
) -> AgentToolResult:
    """A simple calculator tool that performs basic arithmetic."""
    operation = params.get("operation", "")
    a = params.get("a", 0)
    b = params.get("b", 0)

    result = None
    if operation == "add":
        result = a + b
    elif operation == "subtract":
        result = a - b
    elif operation == "multiply":
        result = a * b
    elif operation == "divide":
        if b != 0:
            result = a / b
        else:
            result = "Cannot divide by zero"
    else:
        result = f"Unknown operation: {operation}"

    return AgentToolResult(
        content=[
            TextContent(type="text", text=f"Result: {result}")
        ],
        details={"operation": operation, "a": a, "b": b, "result": result}
    )


# Define a weather tool (simulated)
async def weather_tool(
    tool_call_id: str,
    params: dict,
    signal: asyncio.Event | None,
    on_update,
) -> AgentToolResult:
    """A simulated weather tool."""
    city = params.get("city", "Unknown")

    # Simulate weather data
    weather_data = {
        "San Francisco": {"temp": 72, "condition": "sunny"},
        "New York": {"temp": 65, "condition": "cloudy"},
        "London": {"temp": 58, "condition": "rainy"},
        "Tokyo": {"temp": 70, "condition": "clear"},
    }

    weather = weather_data.get(city, {"temp": 70, "condition": "unknown"})

    return AgentToolResult(
        content=[
            TextContent(
                type="text",
                text=f"The weather in {city} is {weather['temp']}°F and {weather['condition']}."
            )
        ],
        details={"city": city, "weather": weather}
    )


def on_event(event):
    """Handle agent events."""
    print(f"\n[{event.type}]")

    if event.type == "agent_start":
        print("  Agent started processing")
    elif event.type == "turn_start":
        print("  New turn started")
    elif event.type == "tool_start":
        if hasattr(event, "tool_name"):
            print(f"  Tool called: {event.tool_name}")
    elif event.type == "agent_end":
        print("  Agent finished")


async def main():
    # Create tools
    calculator = AgentTool(
        name="calculator",
        label="Calculator",
        description="Perform basic arithmetic operations: add, subtract, multiply, divide",
        parameters={
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["add", "subtract", "multiply", "divide"],
                    "description": "The operation to perform"
                },
                "a": {"type": "number", "description": "First number"},
                "b": {"type": "number", "description": "Second number"}
            },
            "required": ["operation", "a", "b"]
        },
        execute=calculator_tool
    )

    weather = AgentTool(
        name="weather",
        label="Weather",
        description="Get current weather for a city",
        parameters={
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "City name",
                    "examples": ["San Francisco", "New York", "London", "Tokyo"]
                }
            },
            "required": ["city"]
        },
        execute=weather_tool
    )

    # Create agent with tools
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
        ),
        "tools": [calculator, weather]
    })

    # Set system prompt to encourage tool use
    agent.set_system_prompt(
        "You are a helpful assistant. Use the available tools when needed: "
        "calculator for math operations, weather for weather information."
    )

    # Subscribe to events
    unsubscribe = agent.subscribe(on_event)

    print("=" * 60)
    print("Example 1: Math calculation")
    print("=" * 60)

    try:
        await agent.prompt("What is 15 multiplied by 7?")
    except Exception as e:
        print(f"Error: {e}")

    print("\n" + "=" * 60)
    print("Example 2: Weather information")
    print("=" * 60)

    try:
        await agent.prompt("What's the weather in Tokyo?")
    except Exception as e:
        print(f"Error: {e}")

    # Unsubscribe
    unsubscribe()


if __name__ == "__main__":
    asyncio.run(main())
