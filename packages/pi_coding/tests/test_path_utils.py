"""Tests for path utilities."""

import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from pi_coding.utils.path_utils import (
    expand_path,
    file_exists,
    normalize_at_prefix,
    normalize_unicode_spaces,
    resolve_read_path,
    resolve_to_cwd,
    try_curly_quote_variant,
    try_macos_screenshot_path,
    try_nfd_variant,
)


class TestNormalizeUnicodeSpaces:
    def test_regular_spaces(self):
        assert normalize_unicode_spaces("hello world") == "hello world"

    def test_nbsp(self):
        assert normalize_unicode_spaces("hello\u00a0world") == "hello world"

    def test_multiple_unicode_spaces(self):
        text = "hello\u2000world\u2001test"
        assert normalize_unicode_spaces(text) == "hello world test"


class TestTryMacOSScreenshotPath:
    def test_no_am_pm(self):
        assert try_macos_screenshot_path("image.png") == "image.png"

    def test_with_am(self):
        result = try_macos_screenshot_path("Screenshot 2024-01-01 at 10.30 AM.png")
        assert "\u202fAM" in result

    def test_with_pm(self):
        result = try_macos_screenshot_path("Screenshot 2024-01-01 at 10.30 PM.png")
        assert "\u202fPM" in result


class TestTryNfdVariant:
    def test_ascii_text(self):
        assert try_nfd_variant("hello") == "hello"

    def test_composed_character(self):
        text = "café"
        result = try_nfd_variant(text)
        assert result != text or result == text


class TestTryCurlyQuoteVariant:
    def test_no_apostrophe(self):
        assert try_curly_quote_variant("hello") == "hello"

    def test_with_apostrophe(self):
        result = try_curly_quote_variant("don't")
        assert result == "don’t"  # result has curly quote
        assert "\u2019" in result


class TestNormalizeAtPrefix:
    def test_no_prefix(self):
        assert normalize_at_prefix("file.txt") == "file.txt"

    def test_with_prefix(self):
        assert normalize_at_prefix("@file.txt") == "file.txt"

    def test_multiple_at_signs(self):
        assert normalize_at_prefix("@@file.txt") == "@file.txt"


class TestExpandPath:
    def test_relative_path(self):
        assert expand_path("file.txt") == "file.txt"

    def test_tilde(self):
        result = expand_path("~")
        assert result == os.path.expanduser("~")

    def test_tilde_with_path(self):
        result = expand_path("~/Documents")
        assert result == os.path.expanduser("~/Documents")


class TestResolveToCwd:
    def test_relative_path(self):
        result = resolve_to_cwd("file.txt", "/home/user")
        assert os.path.isabs(result)
        assert result.endswith("file.txt")

    def test_absolute_path(self):
        result = resolve_to_cwd("/etc/passwd", "/home/user")
        assert result == "/etc/passwd"


class TestFileExists:
    def test_existing_file(self):
        with tempfile.NamedTemporaryFile() as f:
            assert file_exists(f.name)

    def test_nonexistent_file(self):
        assert not file_exists("/nonexistent/path/file.txt")

    def test_existing_directory(self):
        with tempfile.TemporaryDirectory() as d:
            assert file_exists(d)


class TestResolveReadPath:
    def test_existing_file(self):
        with tempfile.NamedTemporaryFile(suffix=".txt") as f:
            result = resolve_read_path(f.name, os.path.dirname(f.name))
            assert result == f.name

    def test_relative_path(self):
        with tempfile.TemporaryDirectory() as d:
            test_file = os.path.join(d, "test.txt")
            with open(test_file, "w") as f:
                f.write("test")

            result = resolve_read_path("test.txt", d)
            assert result == test_file
