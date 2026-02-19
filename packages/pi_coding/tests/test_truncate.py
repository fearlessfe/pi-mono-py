"""Tests for truncation utilities."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from pi_coding.utils.truncate import (
    DEFAULT_MAX_BYTES,
    DEFAULT_MAX_LINES,
    GREP_MAX_LINE_LENGTH,
    TruncationOptions,
    TruncationResult,
    format_size,
    truncate_head,
    truncate_line,
    truncate_tail,
)


class TestFormatSize:
    def test_bytes(self):
        assert format_size(0) == "0B"
        assert format_size(100) == "100B"
        assert format_size(1023) == "1023B"

    def test_kilobytes(self):
        assert format_size(1024) == "1.0KB"
        assert format_size(2048) == "2.0KB"
        assert format_size(1536) == "1.5KB"

    def test_megabytes(self):
        assert format_size(1024 * 1024) == "1.0MB"
        assert format_size(2.5 * 1024 * 1024) == "2.5MB"


class TestTruncateLine:
    def test_short_line(self):
        text, truncated = truncate_line("short line")
        assert text == "short line"
        assert not truncated

    def test_exact_limit(self):
        line = "x" * GREP_MAX_LINE_LENGTH
        text, truncated = truncate_line(line)
        assert text == line
        assert not truncated

    def test_long_line(self):
        line = "x" * (GREP_MAX_LINE_LENGTH + 100)
        text, truncated = truncate_line(line)
        assert truncated
        assert text.endswith("... [truncated]")
        assert len(text) < len(line)


class TestTruncateHead:
    def test_no_truncation_needed(self):
        content = "line1\nline2\nline3"
        result = truncate_head(content)
        assert not result.truncated
        assert result.content == content
        assert result.total_lines == 3

    def test_truncate_by_lines(self):
        content = "\n".join([f"line{i}" for i in range(3000)])
        result = truncate_head(content, TruncationOptions(max_lines=100))
        assert result.truncated
        assert result.truncated_by == "lines"
        assert result.output_lines == 100

    def test_truncate_by_bytes(self):
        line = "x" * 1000
        content = "\n".join([line for _ in range(100)])
        result = truncate_head(content, TruncationOptions(max_bytes=5000))
        assert result.truncated
        assert result.truncated_by == "bytes"

    def test_first_line_exceeds_limit(self):
        content = "x" * 100000
        result = truncate_head(content, TruncationOptions(max_bytes=1000))
        assert result.truncated
        assert result.first_line_exceeds_limit
        assert result.content == ""

    def test_empty_content(self):
        result = truncate_head("")
        assert not result.truncated
        assert result.content == ""


class TestTruncateTail:
    def test_no_truncation_needed(self):
        content = "line1\nline2\nline3"
        result = truncate_tail(content)
        assert not result.truncated
        assert result.content == content

    def test_truncate_by_lines(self):
        content = "\n".join([f"line{i}" for i in range(3000)])
        result = truncate_tail(content, TruncationOptions(max_lines=100))
        assert result.truncated
        assert result.truncated_by == "lines"
        assert result.output_lines == 100
        assert "line2999" in result.content

    def test_keeps_last_lines(self):
        content = "\n".join([f"line{i}" for i in range(10)])
        result = truncate_tail(content, TruncationOptions(max_lines=3))
        assert "line7" in result.content
        assert "line8" in result.content
        assert "line9" in result.content
        assert "line0" not in result.content
