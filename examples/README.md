# Agent Examples

This directory contains examples demonstrating how to use the `pi-agent` agent runtime.

## Running Examples

### From Workspace Root (Recommended)

```bash
cd /Users/pengzhen/work/ideas/pi-mono-py

# Run an example
uv run --directory examples python 01_simple_agent.py
```

### From Examples Directory

```bash
cd /Users/pengzhen/work/ideas/pi-mono-py/examples

# Using helper script
../uv-run.sh run python 01_simple_agent.py
```

## Example Files

| File | Description | Topics |
|------|-------------|---------|
| `00_quick_start.py` | Quick start (no API required) | |
| `01_simple_agent.py` | Basic agent usage | |
| `02_agent_with_tools.py` | Using tools with agent | Custom tools, tool execution, parameters |
| `03_agent_events.py` | Event handling | Lifecycle events, streaming, error handling |
| `04_steering_followup.py` | Advanced conversation control | Steering, follow-up, queue management |
| `05_streaming_response.py` | Streaming responses | Real-time output, multi-turn conversations |
| `providers_config.py` | Provider configurations | Pre-configured models, base URLs |
| `06_provider_config.py` | Provider config usage | Registering providers, getting URLs |
| `PROVIDER_CONFIG.md` | Provider documentation | Complete provider guide |

## Quick Start

### Example 1: Simple Agent

```python
import asyncio
from pi_agent import Agent
from pi_ai import Model, ModelCost

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

agent.set_system_prompt("You are a helpful assistant.")
await agent.prompt("Hello!")
```

### Example 2: Using Tools

```python
import asyncio
from pi_agent import Agent, AgentTool, AgentToolResult
from pi_ai import Model, ModelCost
from pi_ai.types import TextContent

async def my_tool(tool_call_id, params, signal, on_update):
    return AgentToolResult(
        content=[TextContent(type="text", text="Tool executed!")],
        details={"params": params}
    )

tool = AgentTool(
    name="my_tool",
    label="My Tool",
    description="A simple tool",
    parameters={"type": "object", "properties": {}},
    execute=my_tool
)

agent = Agent(options={
    "model": <your model>,
    "tools": [tool]
})

await agent.prompt("Use my_tool!")
```

## Key Concepts

### Agent State

The agent maintains state including:
- **System prompt**: Instructions for the agent's behavior
- **Model**: The LLM model being used
- **Messages**: Conversation history
- **Tools**: Available tools for the agent to use
- **Thinking level**: Level of reasoning/reasoning budget

### Event Subscription

Subscribe to agent events to monitor behavior:

```python
def on_event(event):
    print(f"Event: {event.type}")

unsubscribe = agent.subscribe(on_event)

# Later, unsubscribe
unsubscribe()
```

### Steering and Follow-up

**Steering**: Inject messages into the current conversation turn
- Use to guide the agent mid-response
- Modes: `one-at-a-time` (default) or `all`

**Follow-up**: Queue messages for the next conversation turn
- Use to provide additional context for next prompt
- Modes: `one-at-a-time` (default) or `all`

```python
# Steering
agent.steer({"role": "user", "content": "Remember this instruction."})

# Follow-up
agent.follow_up({"role": "user", "content": "Ask about this next."})

# Clear queues
agent.clear_all_queues()
```

### Streaming

Responses are streamed by default. Handle streaming events:

```python
def on_event(event):
    if event.type == "text_delta":
        print(event.delta, end="", flush=True)
    elif event.type == "text_end":
        print()
```

## Common Patterns

### Multi-turn Conversation

```python
questions = [
    "What's the capital of France?",
    "What's famous about it?",
    "Can you recommend visiting there?"
]

for question in questions:
    print(f"User: {question}")
    await agent.prompt(question)
```

### Tool Execution

```python
async def data_fetcher(tool_call_id, params, signal, on_update):
    url = params["url"]
    # Fetch data...
    return AgentToolResult(
        content=[TextContent(type="text", text=f"Data from {url}")],
        details={"url": url}
    )

tool = AgentTool(
    name="fetch_data",
    label="Fetch Data",
    description="Fetch data from a URL",
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "URL to fetch"}
        },
        "required": ["url"]
    },
    execute=data_fetcher
)
```

### Error Handling

```python
def on_event(event):
    if event.type == "error":
        print(f"Error: {event.error}")
        print(f"Reason: {event.reason}")

agent.subscribe(on_event)

try:
    await agent.prompt("Hello!")
except Exception as e:
    print(f"Caught exception: {e}")
```

## Notes

- All examples use asyncio and must be run in an async context
- The model configuration in examples is a placeholder - replace with your actual API credentials
- Tools can be asynchronous and can be cancelled via the `signal` parameter
- Use `agent.abort()` to cancel an in-progress prompt

## Troubleshooting

### Module Not Found Errors

If you see import errors:
```bash
cd /Users/pengzhen/work/ideas/pi-mono-py
uv sync
# Then run from workspace root
uv run --directory examples python 01_simple_agent.py
```

### API Errors

Make sure you've configured your API keys:
```bash
export OPENAI_API_KEY="your-key"
export ANTHROPIC_API_KEY="your-key"
export GOOGLE_API_KEY="your-key"
```

## Further Reading

- [pi-mono-py README](../README.md)
- [Workspace Guide](../WORKSPACE.md)
- [pi-ai Documentation](../packages/pi_ai/README.md)
