"""Coding agent tools - read, write, edit, bash, ls, grep, find."""

from __future__ import annotations

from pi_coding.tools.bash import bash_tool, create_bash_tool
from pi_coding.tools.edit import edit_tool, create_edit_tool
from pi_coding.tools.find import find_tool, create_find_tool
from pi_coding.tools.grep import grep_tool, create_grep_tool
from pi_coding.tools.ls import ls_tool, create_ls_tool
from pi_coding.tools.read import read_tool, create_read_tool
from pi_coding.tools.write import write_tool, create_write_tool

coding_tools = [read_tool, bash_tool, edit_tool, write_tool]
read_only_tools = [read_tool, bash_tool, ls_tool, grep_tool, find_tool]
all_tools = [read_tool, write_tool, edit_tool, bash_tool, ls_tool, grep_tool, find_tool]


def create_coding_tools(cwd: str) -> list:
    return [
        create_read_tool(cwd),
        create_bash_tool(cwd),
        create_edit_tool(cwd),
        create_write_tool(cwd),
    ]


def create_read_only_tools(cwd: str) -> list:
    return [
        create_read_tool(cwd),
        create_bash_tool(cwd),
        create_ls_tool(cwd),
        create_grep_tool(cwd),
        create_find_tool(cwd),
    ]


def create_all_tools(cwd: str) -> list:
    return [
        create_read_tool(cwd),
        create_write_tool(cwd),
        create_edit_tool(cwd),
        create_bash_tool(cwd),
        create_ls_tool(cwd),
        create_grep_tool(cwd),
        create_find_tool(cwd),
    ]


__all__ = [
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
]
