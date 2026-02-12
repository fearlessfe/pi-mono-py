# pi-mono-py

Python port of [pi-mono](https://github.com/badlogic/pi-mono) - unified multi-provider LLM API and agent runtime.

## Project Structure

```
pi-mono-py/
├── packages/
│   ├── pi_ai/                    # Unified multi-provider LLM API
│   │   └── src/pi_ai/
│   │       ├── types.py            # Core type definitions
│   │       ├── event_stream.py     # Async event stream implementation
│   │       ├── registry.py         # API provider registry
│   │       ├── models.py           # Model registry
│   │       ├── env_keys.py         # Environment variable API key resolution
│   │       └── stream.py          # Streaming API
│   └── tests/
│       └── test_types.py         # Type and model tests
│   └── pi_agent/                  # Agent runtime
│       └── src/pi_agent/
│           ├── types.py            # Agent types
│           ├── agent.py            # Agent class
│           └── loop.py             # Agent loop implementation
│       └── tests/
│           └── test_agent.py
├── examples/                       # Usage examples
│   ├── 00_quick_start.py           # Quick start (no API required)
│   ├── 01_simple_agent.py          # Basic agent usage
│   ├── 02_agent_with_tools.py      # Using tools
│   ├── 03_agent_events.py          # Event handling
│   ├── 04_steering_followup.py    # Conversation control
│   ├── 05_streaming_response.py   # Streaming responses
│   └── README.md                  # Examples documentation
├── pyproject.toml                  # Root workspace config
├── uv.lock                        # Dependency lock
├── uv-run.sh                      # Helper script for subdirectories
├── WORKSPACE.md                    # Workspace usage guide
└── README.md                      # This file
```

## Installation

```bash
cd pi-mono-py
uv sync
```

## Usage

### pi_ai - LLM API

```python
from pi_ai import (
    UserMessage, TextContent, Context, Model,
    stream, complete, get_model, register_model,
)

# Register a model
register_model(Model(
    id="my-model",
    name="My Model",
    api="openai-completions",
    provider="openai",
    base_url="https://api.openai.com",
    reasoning=False,
    input=["text"],
    cost=ModelCost(input=0.5, output=1.5, cache_read=0.1, cache_write=0.05),
    context_window=128000,
    max_tokens=4096,
))

# Get model and stream
model = get_model("openai", "my-model")
context = Context(
    system_prompt="You are helpful.",
    messages=[UserMessage(role="user", content=[TextContent(type="text", text="Hello")], timestamp=0)],
)

async for event in stream(model, context):
    if event.type == "text_delta":
        print(event.delta)
```

### pi_agent - Agent Runtime

```python
import asyncio
from pi_agent import Agent, AgentTool, AgentToolResult
from pi_ai import Model, ModelCost
from pi_ai.types import TextContent

# Define a tool
async def my_tool(tool_call_id: str, params: dict, signal, on_update):
    return AgentToolResult(
        content=[TextContent(type="text", text="Tool executed")],
        details={"params": params},
    )

tool = AgentTool(
    name="my_tool",
    label="My Tool",
    description="A tool for testing",
    parameters={"type": "object", "properties": {}},
    execute=my_tool,
)

# Create agent
agent = Agent(options={
    "model": Model(
        id="test-model",
        name="Test Model",
        api="openai-completions",
        provider="openai",
        base_url="https://api.openai.com",
        reasoning=False,
        input=["text"],
        cost=ModelCost(input=0.5, output=1.5, cache_read=0.0, cache_write=0.0),
        context_window=128000,
        max_tokens=4096,
    ),
    "tools": [tool],
})

# Subscribe to events
def on_event(event):
    print(f"Event: {event.type}")

unsubscribe = agent.subscribe(on_event)

# Run prompt
asyncio.run(agent.prompt("Hello!"))

# Unsubscribe later
unsubscribe()
```

## Examples

See the `examples/` directory for comprehensive usage examples:

| Example | Description |
|---------|-------------|
| [00_quick_start.py](examples/00_quick_start.py) | Quick start demo (no API required) |
| [01_simple_agent.py](examples/01_simple_agent.py) | Basic agent usage |
| [02_agent_with_tools.py](examples/02_agent_with_tools.py) | Using tools with the agent |
| [03_agent_events.py](examples/03_agent_events.py) | Event handling and monitoring |
| [04_steering_followup.py](examples/04_steering_followup.py) | Advanced conversation control |
| [05_streaming_response.py](examples/05_streaming_response.py) | Handling streaming responses |

Run examples:

```bash
# From workspace root
uv run --directory examples python 00_quick_start.py

# From examples directory using helper script
cd examples && ../uv-run.sh run python 00_quick_start.py
```

See [examples/README.md](examples/README.md) for detailed documentation.

## Port Status

- pi_ai core types and streaming API
- pi-ai model registry and API registry
- pi-ai environment API key resolution
- pi-agent-core types, agent class, and loop
- Basic unit tests

## Next Steps

Provider implementations (pending):
- OpenAI completions API
- Anthropic messages API
- Google Gemini API
- Cross-provider message transforms

## Development

### Running Commands

**Important**: This is a uv workspace. All packages share the same virtual environment.

#### From Workspace Root (Recommended)

```bash
# Run all tests
uv run pytest -v

# Run tests for specific package
uv run pytest packages/pi_ai/tests/
uv run pytest packages/pi_agent/tests/

# Run Python scripts in a package
uv run --directory packages/pi_ai python your_script.py
```

#### From Package Directory

If working in a package directory, use the helper script:

```bash
cd packages/pi_agent

# Using the helper script
../uv-run.sh run pytest tests/

# Or return to workspace root
cd ../..
uv run pytest packages/pi_agent/tests/
```

#### Installing Dependencies

Always run from workspace root:

```bash
uv add <package>
```

### Troubleshooting

**"Module not found" errors in package directories:**

This happens because packages depend on each other (e.g., `pi-agent` depends on `pi-ai`), and uv workspace requires running from the workspace root to resolve these dependencies.

**Solutions:**
1. Use `uv run` from the workspace root
2. Use the helper script `../uv-run.sh` from package directories
3. Use `uv run --directory <package>` from workspace root
