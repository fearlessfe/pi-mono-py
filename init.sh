#!/bin/bash
# pi-mono-py initialization and verification script
# Run this at the start of each coding session

set -e

echo "=== pi-mono-py Init Script ==="
echo ""

# 1. Check working directory
echo "📁 Working directory: $(pwd)"
if [[ ! -f "pyproject.toml" ]]; then
    echo "❌ Error: Must run from pi-mono-py root directory"
    exit 1
fi
echo "✅ Correct directory"
echo ""

# 2. Check Python environment
echo "🐍 Python environment:"
if command -v uv &> /dev/null; then
    echo "   uv: $(uv --version)"
else
    echo "❌ uv not installed"
    exit 1
fi

PYTHON_VERSION=$(uv run python --version 2>&1)
echo "   $PYTHON_VERSION"
echo ""

# 3. Check dependencies
echo "📦 Checking dependencies..."
uv sync --quiet
# Install workspace packages in editable mode
uv pip install -e packages/pi_ai -e packages/pi_agent -q 2>/dev/null || true
echo "✅ Dependencies synced"
echo ""

# 4. Run basic import tests
echo "🔍 Running import tests..."

# Test pi_ai imports
echo "   Testing pi_ai imports..."
uv run python -c "
try:
    from pi_ai.types import (
        UserMessage, AssistantMessage, ToolResultMessage,
        TextContent, ImageContent, ToolCall,
        Model, ModelCost, Context
    )
    print('   ✅ pi_ai.types OK')
except ImportError as e:
    print(f'   ❌ pi_ai.types FAILED: {e}')
    exit(1)
"

uv run python -c "
try:
    from pi_ai.event_stream import AssistantMessageEventStream
    print('   ✅ pi_ai.event_stream OK')
except ImportError as e:
    print(f'   ❌ pi_ai.event_stream FAILED: {e}')
    exit(1)
"

# Test pi_agent imports
echo "   Testing pi_agent imports..."
uv run python -c "
try:
    from pi_agent.types import (
        AgentMessage, AgentState, AgentEvent,
        AgentTool, AgentToolResult
    )
    print('   ✅ pi_agent.types OK')
except ImportError as e:
    print(f'   ❌ pi_agent.types FAILED: {e}')
    exit(1)
"

uv run python -c "
try:
    from pi_agent.agent import Agent
    print('   ✅ pi_agent.agent OK')
except ImportError as e:
    print(f'   ❌ pi_agent.agent FAILED: {e}')
    exit(1)
"

echo ""

# 5. Run existing tests
echo "🧪 Running existing tests..."
uv run pytest -v --tb=short 2>&1 | tail -20
echo ""

# 6. Check provider imports (these are known to fail)
echo "⚠️  Known issues (expected to fail):"
echo "   Checking provider imports..."
uv run python -c "from pi_ai.providers.openai import stream" 2>&1 && echo "   ✅ openai OK" || echo "   ❌ openai FAILED (known issue P0-001)"
uv run python -c "from pi_ai.providers.anthropic import stream" 2>&1 && echo "   ✅ anthropic OK" || echo "   ❌ anthropic FAILED (known issue P0-002)"
uv run python -c "from pi_ai.providers.google import stream" 2>&1 && echo "   ✅ google OK" || echo "   ❌ google FAILED (known issue P0-003)"
echo ""

# 7. Summary
echo "=== Summary ==="
echo "✅ Environment ready"
echo ""
echo "📋 Next feature to work on:"
echo "   P0-001: Fix pi-ai/providers/openai.py - add missing event type imports"
echo ""
echo "📂 Key files:"
echo "   - feature_list.json  (all features to implement)"
echo "   - PROGRESS.md        (session progress log)"
echo "   - IMPLEMENTATION_PLAN.md (detailed plan)"
echo ""
echo "🚀 Ready to code!"
