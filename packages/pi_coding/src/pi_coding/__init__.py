from __future__ import annotations

import os
from typing import Any

from pi_agent import Agent

from pi_coding.config import (
    ENV_AGENT_DIR,
    VERSION,
    get_agent_dir,
    get_bin_dir,
    get_sessions_dir,
    get_settings_path,
)
from pi_coding.core.defaults import DEFAULT_THINKING_LEVEL
from pi_coding.tools import (
    all_tools,
    bash_tool,
    coding_tools,
    create_all_tools,
    create_bash_tool,
    create_coding_tools,
    create_edit_tool,
    create_find_tool,
    create_grep_tool,
    create_ls_tool,
    create_read_only_tools,
    create_read_tool,
    create_write_tool,
    edit_tool,
    find_tool,
    grep_tool,
    ls_tool,
    read_only_tools,
    read_tool,
    write_tool,
)
from pi_coding.utils import (
    DEFAULT_MAX_BYTES,
    DEFAULT_MAX_LINES,
    EditDiffError,
    EditDiffResult,
    FuzzyMatchResult,
    GREP_MAX_LINE_LENGTH,
    TruncationOptions,
    TruncationResult,
    compute_edit_diff,
    detect_line_ending,
    expand_path,
    file_exists,
    format_size,
    fuzzy_find_text,
    generate_diff_string,
    normalize_for_fuzzy_match,
    normalize_to_lf,
    resolve_read_path,
    resolve_to_cwd,
    restore_line_endings,
    strip_bom,
    truncate_head,
    truncate_line,
    truncate_tail,
)

__all__ = [
    "get_coding_tools",
    "get_read_only_tools",
    "get_all_tools",
    "create_coding_agent",
    "CodingAgentConfig",
    "read_tool",
    "write_tool",
    "edit_tool",
    "bash_tool",
    "ls_tool",
    "grep_tool",
    "find_tool",
    "create_read_tool",
    "create_write_tool",
    "create_edit_tool",
    "create_bash_tool",
    "create_ls_tool",
    "create_grep_tool",
    "create_find_tool",
    "coding_tools",
    "read_only_tools",
    "all_tools",
    "create_coding_tools",
    "create_read_only_tools",
    "create_all_tools",
    "DEFAULT_MAX_BYTES",
    "DEFAULT_MAX_LINES",
    "GREP_MAX_LINE_LENGTH",
    "TruncationOptions",
    "TruncationResult",
    "format_size",
    "truncate_head",
    "truncate_tail",
    "truncate_line",
    "expand_path",
    "resolve_to_cwd",
    "resolve_read_path",
    "file_exists",
    "detect_line_ending",
    "normalize_to_lf",
    "restore_line_endings",
    "normalize_for_fuzzy_match",
    "fuzzy_find_text",
    "FuzzyMatchResult",
    "strip_bom",
    "generate_diff_string",
    "compute_edit_diff",
    "EditDiffResult",
    "EditDiffError",
    # Configuration
    "VERSION",
    "ENV_AGENT_DIR",
    "get_agent_dir",
    "get_bin_dir",
    "get_sessions_dir",
    "get_settings_path",
    # Defaults
    "DEFAULT_THINKING_LEVEL",
]


def get_coding_tools(cwd: str | None = None) -> list:
    return create_coding_tools(cwd or os.getcwd())


def get_read_only_tools(cwd: str | None = None) -> list:
    return create_read_only_tools(cwd or os.getcwd())


def get_all_tools(cwd: str | None = None) -> list:
    return create_all_tools(cwd or os.getcwd())


class CodingAgentConfig:
    def __init__(
        self,
        model: Any = None,
        system_prompt: str | None = None,
        working_dir: str | None = None,
        tools: list | None = None,
    ):
        self.model = model
        self.system_prompt = system_prompt
        self.working_dir = working_dir
        self.tools = tools


def create_coding_agent(
    config: CodingAgentConfig | None = None,
    **kwargs: Any,
) -> Agent:
    cfg = config or CodingAgentConfig()

    cwd = cfg.working_dir or os.getcwd()

    system_prompt = cfg.system_prompt or """You are an expert coding assistant with access to file system tools.

## Core Principles

1. **Read before writing**: Always read files before suggesting changes
2. **Be precise**: Use exact string matches when editing
3. **Show context**: Display file previews before editing
4. **Explain changes**: Clearly describe what you're changing and why
5. **Handle errors**: Gracefully report errors and suggest solutions

## Available Tools

### File Operations
- **read**: Read file contents with line numbers, supports images
- **write**: Create or overwrite files (creates directories)
- **edit**: Search and replace text in files (exact match required)

### Search & Navigation
- **ls**: List directory contents with type indicators
- **grep**: Search file contents using ripgrep
- **find**: Find files by glob pattern using fd

### Execution
- **bash**: Execute shell commands with streaming output

## Workflow

When asked to make code changes:
1. Use ls to understand structure
2. Read relevant files
3. Explain what you're going to do
4. Make changes with edit or write
5. Verify changes by reading back

## Best Practices

- Use relative paths when possible
- Check if files exist before editing
- Be conservative with replacements
- Provide clear, concise explanations"""

    tools = cfg.tools or create_coding_tools(cwd)

    agent = Agent(
        options={
            "model": cfg.model,
            "tools": tools,
            **kwargs,
        }
    )

    agent.set_system_prompt(system_prompt)

    return agent
