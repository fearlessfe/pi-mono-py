import sys

sys.path.insert(0, "packages/pi_ai/src")
sys.path.insert(0, "packages/pi_agent/src")

from pi_ai.types import UserMessage, TextContent, Model, ModelCost, StopReason
from pi_ai.models import calculate_cost, register_model
from pi_agent.types import AgentState
from pi_agent.agent import Agent

print("Testing basic types...")

msg = UserMessage(
    role="user",
    content=[TextContent(type="text", text="Hello")],
    timestamp=1234567890,
)
print(f"UserMessage created: {msg.role}, {msg.content[0].text}")

model = Model(
    id="test-model",
    name="Test Model",
    api="openai-completions",
    provider="openai",
    base_url="https://api.openai.com",
    reasoning=False,
    input=["text"],
    cost=ModelCost(input=0.5, output=1.5, cache_read=0.1, cache_write=0.05),
    context_window=128000,
    max_tokens=4096,
)
print(f"Model created: {model.id}")

from pi_ai.types import Usage, UsageCost

usage = Usage(
    input=1000,
    output=500,
    cache_read=200,
    cache_write=50,
    total_tokens=1500,
    cost=UsageCost(),
)
cost = calculate_cost(model, usage)
print(f"Cost calculated: {cost.total}")

print("Testing Agent...")
register_model(model)
agent = Agent(options={"model": model})
print(f"Agent created with model: {agent.state.model.id}")
print(f"Agent thinking level: {agent.state.thinking_level}")

print("All basic tests passed!")
