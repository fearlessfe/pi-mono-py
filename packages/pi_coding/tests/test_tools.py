"""Tests for pi_coding tools."""

import asyncio
import os
import tempfile

import pytest

from pi_coding import (
    bash_tool,
    create_bash_tool,
    create_edit_tool,
    create_find_tool,
    create_grep_tool,
    create_ls_tool,
    create_read_tool,
    create_write_tool,
    edit_tool,
    find_tool,
    grep_tool,
    ls_tool,
    read_tool,
    write_tool,
)


class TestToolCreation:
    def test_read_tool_creation(self):
        tool = create_read_tool("/tmp")
        assert tool.name == "read"
        assert "parameters" in dir(tool)

    def test_write_tool_creation(self):
        tool = create_write_tool("/tmp")
        assert tool.name == "write"

    def test_edit_tool_creation(self):
        tool = create_edit_tool("/tmp")
        assert tool.name == "edit"

    def test_bash_tool_creation(self):
        tool = create_bash_tool("/tmp")
        assert tool.name == "bash"

    def test_ls_tool_creation(self):
        tool = create_ls_tool("/tmp")
        assert tool.name == "ls"

    def test_grep_tool_creation(self):
        tool = create_grep_tool("/tmp")
        assert tool.name == "grep"

    def test_find_tool_creation(self):
        tool = create_find_tool("/tmp")
        assert tool.name == "find"


class TestReadTool:
    @pytest.mark.asyncio
    async def test_read_nonexistent_file(self):
        tool = create_read_tool("/tmp")
        result = await tool.execute(
            "test-id",
            {"path": "/nonexistent/file.txt"},
            None,
            None,
        )
        assert "Error" in result.content[0].text or "not found" in result.content[0].text.lower()

    @pytest.mark.asyncio
    async def test_read_existing_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("test content\nline 2")
            temp_path = f.name

        try:
            tool = create_read_tool(os.path.dirname(temp_path))
            result = await tool.execute(
                "test-id",
                {"path": os.path.basename(temp_path)},
                None,
                None,
            )
            assert "test content" in result.content[0].text
        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_read_with_offset(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("line1\nline2\nline3\nline4\nline5")
            temp_path = f.name

        try:
            tool = create_read_tool(os.path.dirname(temp_path))
            result = await tool.execute(
                "test-id",
                {"path": os.path.basename(temp_path), "offset": 3},
                None,
                None,
            )
            assert "line3" in result.content[0].text
            assert "line1" not in result.content[0].text
        finally:
            os.unlink(temp_path)


class TestWriteTool:
    @pytest.mark.asyncio
    async def test_write_file(self):
        with tempfile.TemporaryDirectory() as d:
            tool = create_write_tool(d)
            result = await tool.execute(
                "test-id",
                {"path": "test.txt", "content": "hello world"},
                None,
                None,
            )
            assert "Successfully" in result.content[0].text or "wrote" in result.content[0].text.lower()

            with open(os.path.join(d, "test.txt")) as f:
                assert f.read() == "hello world"

    @pytest.mark.asyncio
    async def test_write_creates_directories(self):
        with tempfile.TemporaryDirectory() as d:
            tool = create_write_tool(d)
            result = await tool.execute(
                "test-id",
                {"path": "subdir/nested/test.txt", "content": "nested content"},
                None,
                None,
            )
            assert "Successfully" in result.content[0].text or "wrote" in result.content[0].text.lower()

            with open(os.path.join(d, "subdir", "nested", "test.txt")) as f:
                assert f.read() == "nested content"


class TestEditTool:
    @pytest.mark.asyncio
    async def test_edit_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("hello world")
            temp_path = f.name

        try:
            tool = create_edit_tool(os.path.dirname(temp_path))
            result = await tool.execute(
                "test-id",
                {
                    "path": os.path.basename(temp_path),
                    "old_text": "world",
                    "new_text": "universe",
                },
                None,
                None,
            )
            assert "Successfully" in result.content[0].text or "replaced" in result.content[0].text.lower()

            with open(temp_path) as f:
                assert f.read() == "hello universe"
        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_edit_text_not_found(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("hello world")
            temp_path = f.name

        try:
            tool = create_edit_tool(os.path.dirname(temp_path))
            result = await tool.execute(
                "test-id",
                {
                    "path": os.path.basename(temp_path),
                    "old_text": "nonexistent",
                    "new_text": "replacement",
                },
                None,
                None,
            )
            assert "Could not find" in result.content[0].text or "not find" in result.content[0].text.lower() or "error" in result.content[0].text.lower()
        finally:
            os.unlink(temp_path)


class TestBashTool:
    @pytest.mark.asyncio
    async def test_echo_command(self):
        tool = create_bash_tool("/tmp")
        result = await tool.execute(
            "test-id",
            {"command": "echo 'hello world'"},
            None,
            None,
        )
        assert "hello world" in result.content[0].text

    @pytest.mark.asyncio
    async def test_command_with_exit_code(self):
        tool = create_bash_tool("/tmp")
        result = await tool.execute(
            "test-id",
            {"command": "exit 1"},
            None,
            None,
        )
        assert "1" in result.content[0].text or "error" in result.content[0].text.lower()


class TestLsTool:
    @pytest.mark.asyncio
    async def test_list_directory(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "subdir"))
            with open(os.path.join(d, "file.txt"), "w") as f:
                f.write("test")

            tool = create_ls_tool(d)
            result = await tool.execute(
                "test-id",
                {},
                None,
                None,
            )
            assert "subdir/" in result.content[0].text
            assert "file.txt" in result.content[0].text

    @pytest.mark.asyncio
    async def test_list_empty_directory(self):
        with tempfile.TemporaryDirectory() as d:
            tool = create_ls_tool(d)
            result = await tool.execute(
                "test-id",
                {},
                None,
                None,
            )
            assert "empty" in result.content[0].text.lower()


class TestGrepTool:
    @pytest.mark.asyncio
    async def test_grep_search(self):
        import shutil
        if not shutil.which("rg"):
            pytest.skip("ripgrep (rg) not available")
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "test.txt"), "w") as f:
                f.write("hello world\nfoo bar\nhello again")

            tool = create_grep_tool(d)
            result = await tool.execute(
                "test-id",
                {"pattern": "hello"},
                None,
                None,
            )
            assert "hello" in result.content[0].text


class TestFindTool:
    @pytest.mark.asyncio
    async def test_find_by_pattern(self):
        import shutil
        if not shutil.which("fd"):
            pytest.skip("fd not available")
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "test.txt"), "w") as f:
                f.write("test")
            with open(os.path.join(d, "other.py"), "w") as f:
                f.write("print('test')")

            tool = create_find_tool(d)
            result = await tool.execute(
                "test-id",
                {"pattern": "*.py"},
                None,
                None,
            )
            assert "other.py" in result.content[0].text
            assert "test.txt" not in result.content[0].text
