# Working with Subdirectories in uv Workspace

## The Issue

When you're in a subdirectory like `packages/pi_agent/` and try to run `uv run python script.py`, you might get:

```
ModuleNotFoundError: No module named 'pi_ai'
```

This happens because `pi_agent` depends on `pi-ai`, and in a uv workspace, the packages must be resolved together.

## Solutions

### Solution 1: Run from Workspace Root (Best)

Always run uv commands from the workspace root directory:

```bash
cd /Users/pengzhen/work/ideas/pi-mono-py  # Workspace root

# Run tests
uv run pytest packages/pi_agent/tests/

# Run a script
uv run --directory packages/pi_agent python your_script.py
```

### Solution 2: Use the Helper Script

From any package directory, use the `uv-run.sh` helper script:

```bash
cd /Users/pengzhen/work/ideas/pi-mono-py/packages/pi_agent

# Run tests
../uv-run.sh run pytest tests/

# Run a script
../uv-run.sh run python your_script.py
```

### Solution 3: Use VS Code/Editor Configuration

Configure your editor to use the workspace virtual environment:

**VS Code (.vscode/settings.json):**
```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["packages"]
}
```

## Why This Happens

uv workspace is designed as a **monorepo** where:
- All packages share one virtual environment
- Dependencies between packages are resolved together
- The `pyproject.toml` at the root defines the workspace

```toml
# root pyproject.toml
[tool.uv.workspace]
members = ["packages/*"]

[tool.uv.sources]
pi-ai = { workspace = true }
pi-agent = { workspace = true }
```

## Common Workflows

### Running Tests

```bash
# All tests
uv run pytest -v

# Specific package
uv run pytest packages/pi_ai/tests/
uv run pytest packages/pi_agent/tests/

# From package directory
cd packages/pi_ai && ../uv-run.sh run pytest tests/
```

### Adding Dependencies

```bash
# From workspace root only
cd /Users/pengzhen/work/ideas/pi-mono-py
uv add httpx
```

### Running Scripts

```bash
# From workspace root
uv run --directory packages/pi_agent python script.py

# From package directory
cd packages/pi_agent && ../uv-run.sh run python script.py
```

### Installing Package in Editable Mode

```bash
# From workspace root (installs all workspace packages)
uv pip install -e packages/pi_ai -e packages/pi_agent

# From workspace root (single package)
uv pip install -e packages/pi_agent
```

## Quick Reference

| Task | Command | Location |
|------|---------|----------|
| Run all tests | `uv run pytest -v` | Workspace root |
| Run pi_ai tests | `uv run pytest packages/pi_ai/tests/` | Workspace root |
| Run pi_agent tests | `uv run pytest packages/pi_agent/tests/` | Workspace root |
| Run script in pi_agent | `uv run --directory packages/pi_agent python script.py` | Workspace root |
| Add dependency | `uv add <package>` | Workspace root |
| Run tests from package dir | `../uv-run.sh run pytest tests/` | Package directory |
