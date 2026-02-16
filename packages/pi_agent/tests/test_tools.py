import os
import tempfile

import pytest
from pi_agent.tools import (
    create_bash_tool,
    create_edit_file_tool,
    create_grep_tool,
    create_read_file_tool,
    create_tool,
    create_write_file_tool,
    get_builtin_tools,
    validate_tool_params,
)
from pi_agent.types import AgentToolResult
from pi_ai.types import TextContent


class TestValidateToolParams:
    def test_validate_valid_params(self):
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        }
        params = {"name": "test"}

        errors = validate_tool_params(schema, params)
        assert errors == []

    def test_validate_missing_required(self):
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        }
        params = {}

        errors = validate_tool_params(schema, params)
        assert len(errors) > 0

    def test_validate_wrong_type(self):
        schema = {
            "type": "object",
            "properties": {"count": {"type": "number"}},
            "required": ["count"],
        }
        params = {"count": "not a number"}

        errors = validate_tool_params(schema, params)
        assert len(errors) > 0


class TestCreateTool:
    @pytest.mark.asyncio
    async def test_create_tool_with_validation(self):
        async def execute_fn(tool_call_id, args, cancel_event, on_update):
            return AgentToolResult(
                content=[TextContent(type="text", text=f"Executed with {args}")],
                details={},
            )

        tool = create_tool(
            name="test_tool",
            description="A test tool",
            parameters={"type": "object", "properties": {"input": {"type": "string"}}},
            execute_fn=execute_fn,
        )

        assert tool.name == "test_tool"
        assert tool.description == "A test tool"

    @pytest.mark.asyncio
    async def test_tool_validates_params(self):
        async def execute_fn(tool_call_id, args, cancel_event, on_update):
            return AgentToolResult(
                content=[TextContent(type="text", text="Success")],
                details={},
            )

        schema = {
            "type": "object",
            "properties": {"required_field": {"type": "string"}},
            "required": ["required_field"],
        }

        tool = create_tool(
            name="validated_tool",
            description="Tool with validation",
            parameters=schema,
            execute_fn=execute_fn,
        )

        result = await tool.execute("call-1", {"required_field": "value"}, None, None)
        assert "Success" in result.content[0].text  # type: ignore[union-attr]


class TestBuiltinTools:
    def test_get_builtin_tools(self):
        tools = get_builtin_tools()

        assert len(tools) == 5
        names = [t.name for t in tools]
        assert "read_file" in names
        assert "write_file" in names
        assert "edit_file" in names
        assert "bash" in names
        assert "grep" in names

    def test_create_read_file_tool(self):
        tool = create_read_file_tool()

        assert tool.name == "read_file"
        assert "file_path" in tool.parameters.get("properties", {})

    def test_create_write_file_tool(self):
        tool = create_write_file_tool()

        assert tool.name == "write_file"
        assert "file_path" in tool.parameters.get("properties", {})
        assert "content" in tool.parameters.get("properties", {})

    def test_create_bash_tool(self):
        tool = create_bash_tool()

        assert tool.name == "bash"
        assert "command" in tool.parameters.get("properties", {})

    def test_create_grep_tool(self):
        tool = create_grep_tool()

        assert tool.name == "grep"
        assert "pattern" in tool.parameters.get("properties", {})

    def test_create_edit_file_tool(self):
        tool = create_edit_file_tool()

        assert tool.name == "edit_file"
        params = tool.parameters.get("properties", {})
        assert "file_path" in params
        assert "old_string" in params
        assert "new_string" in params
        assert "replace_all" in params


class TestToolExecution:
    @pytest.mark.asyncio
    async def test_bash_tool_echo(self):
        tool = create_bash_tool()

        result = await tool.execute(
            "call-1",
            {"command": "echo 'Hello World'"},
            None,
            None,
        )

        assert "Hello World" in result.content[0].text  # type: ignore[union-attr]

    @pytest.mark.asyncio
    async def test_read_file_not_found(self):
        tool = create_read_file_tool()

        result = await tool.execute(
            "call-1",
            {"file_path": "/nonexistent/path/file.txt"},
            None,
            None,
        )

        assert (
            "not found" in result.content[0].text  # type: ignore[union-attr].lower()
            or "error" in result.content[0].text  # type: ignore[union-attr].lower()
        )

    @pytest.mark.asyncio
    async def test_edit_file_single_replacement(self):
        """Test edit_file with a single occurrence."""
        tool = create_edit_file_tool()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Hello World\nThis is a test\n")
            temp_file = f.name

        try:
            result = await tool.execute(
                "call-1",
                {
                    "file_path": temp_file,
                    "old_string": "Hello World",
                    "new_string": "Hi World",
                },
                None,
                None,
            )

            assert "Successfully edited" in result.content[0].text  # type: ignore[union-attr]
            assert result.details.get("replacements") == 1

            with open(temp_file) as f:
                content = f.read()
            assert "Hi World" in content
            assert "Hello World" not in content
        finally:
            os.unlink(temp_file)

    @pytest.mark.asyncio
    async def test_edit_file_multiple_matches_error(self):
        """Test edit_file errors on multiple matches without replace_all."""
        tool = create_edit_file_tool()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Hello World\nHello Again\n")
            temp_file = f.name

        try:
            result = await tool.execute(
                "call-1",
                {
                    "file_path": temp_file,
                    "old_string": "Hello",
                    "new_string": "Hi",
                },
                None,
                None,
            )

            assert (
                "error" in result.content[0].text  # type: ignore[union-attr].lower()
                or "found 2 times" in result.content[0].text  # type: ignore[union-attr]
            )
            assert result.details.get("error") == "multiple_matches"
        finally:
            os.unlink(temp_file)

    @pytest.mark.asyncio
    async def test_edit_file_replace_all(self):
        """Test edit_file with replace_all=true."""
        tool = create_edit_file_tool()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Hello World\nHello Again\n")
            temp_file = f.name

        try:
            result = await tool.execute(
                "call-1",
                {
                    "file_path": temp_file,
                    "old_string": "Hello",
                    "new_string": "Hi",
                    "replace_all": True,
                },
                None,
                None,
            )

            assert "Successfully edited" in result.content[0].text  # type: ignore[union-attr]
            assert result.details.get("replacements") == 2

            with open(temp_file) as f:
                content = f.read()
            assert content.count("Hi") == 2
            assert "Hello" not in content
        finally:
            os.unlink(temp_file)

    @pytest.mark.asyncio
    async def test_edit_file_string_not_found(self):
        """Test edit_file when old_string is not found."""
        tool = create_edit_file_tool()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Some content\n")
            temp_file = f.name

        try:
            result = await tool.execute(
                "call-1",
                {
                    "file_path": temp_file,
                    "old_string": "NonExistentString",
                    "new_string": "NewString",
                },
                None,
                None,
            )

            assert "not found" in result.content[0].text  # type: ignore[union-attr].lower()
            assert result.details.get("error") == "old_string_not_found"
        finally:
            os.unlink(temp_file)
