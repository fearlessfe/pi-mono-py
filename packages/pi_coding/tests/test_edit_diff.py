"""Tests for edit diff utilities."""

import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from pi_coding.utils.edit_diff import (
    EditDiffError,
    EditDiffResult,
    FuzzyMatchResult,
    compute_edit_diff,
    detect_line_ending,
    fuzzy_find_text,
    generate_diff_string,
    normalize_for_fuzzy_match,
    normalize_to_lf,
    restore_line_endings,
    strip_bom,
)


class TestDetectLineEnding:
    def test_lf(self):
        assert detect_line_ending("line1\nline2") == "\n"

    def test_crlf(self):
        assert detect_line_ending("line1\r\nline2") == "\r\n"

    def test_no_newlines(self):
        assert detect_line_ending("no newlines") == "\n"

    def test_mixed(self):
        assert detect_line_ending("line1\r\nline2\nline3") == "\r\n"


class TestNormalizeToLf:
    def test_lf_text(self):
        assert normalize_to_lf("line1\nline2") == "line1\nline2"

    def test_crlf_text(self):
        assert normalize_to_lf("line1\r\nline2") == "line1\nline2"

    def test_cr_only(self):
        assert normalize_to_lf("line1\rline2") == "line1\nline2"


class TestRestoreLineEndings:
    def test_restore_lf(self):
        assert restore_line_endings("line1\nline2", "\n") == "line1\nline2"

    def test_restore_crlf(self):
        assert restore_line_endings("line1\nline2", "\r\n") == "line1\r\nline2"


class TestNormalizeForFuzzyMatch:
    def test_trailing_whitespace(self):
        assert normalize_for_fuzzy_match("line  \nline2  ") == "line\nline2"

    def test_smart_quotes(self):
        result = normalize_for_fuzzy_match("don't say \u201chello\u201d")
        assert "'" in result
        assert '"' in result

    def test_dashes(self):
        text = "hello—world"
        result = normalize_for_fuzzy_match(text)
        assert "-" in result


class TestFuzzyFindText:
    def test_exact_match(self):
        content = "hello world"
        result = fuzzy_find_text(content, "world")
        assert result.found
        assert not result.used_fuzzy_match
        assert result.index == 6

    def test_no_match(self):
        content = "hello world"
        result = fuzzy_find_text(content, "xyz")
        assert not result.found

    def test_fuzzy_match_whitespace(self):
        content = "line1  \nline2  "
        result = fuzzy_find_text(content, "line1\nline2")
        assert result.found
        assert result.used_fuzzy_match


class TestStripBom:
    def test_no_bom(self):
        bom, text = strip_bom("hello")
        assert bom == ""
        assert text == "hello"

    def test_with_bom(self):
        bom, text = strip_bom("\ufeffhello")
        assert bom == "\ufeff"
        assert text == "hello"


class TestGenerateDiffString:
    def test_no_changes(self):
        old = "line1\nline2"
        new = "line1\nline2"
        result = generate_diff_string(old, new)
        assert result["diff"] == ""
        assert result["first_changed_line"] is None

    def test_add_line(self):
        old = "line1"
        new = "line1\nline2"
        result = generate_diff_string(old, new)
        assert "+" in result["diff"]
        assert "line2" in result["diff"]

    def test_remove_line(self):
        old = "line1\nline2"
        new = "line1"
        result = generate_diff_string(old, new)
        assert "-" in result["diff"]

    def test_modify_line(self):
        old = "line1\nline2"
        new = "line1\nmodified"
        result = generate_diff_string(old, new)
        assert "+" in result["diff"]
        assert "-" in result["diff"]


class TestComputeEditDiff:
    def test_file_not_found(self):
        result = compute_edit_diff("/nonexistent/file.txt", "old", "new", "/tmp")
        assert isinstance(result, EditDiffError)
        assert "not found" in result.error.lower()

    def test_text_not_found(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("hello world")
            f.flush()
            temp_path = f.name

        try:
            result = compute_edit_diff(temp_path, "xyz", "new", os.path.dirname(temp_path))
            assert isinstance(result, EditDiffError)
            assert "not find" in result.error.lower()
        finally:
            os.unlink(temp_path)

    def test_successful_diff(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("hello world")
            f.flush()
            temp_path = f.name

        try:
            result = compute_edit_diff(temp_path, "world", "universe", os.path.dirname(temp_path))
            assert isinstance(result, EditDiffResult)
            assert "universe" in result.diff
        finally:
            os.unlink(temp_path)

    def test_multiple_occurrences(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("test test test")
            f.flush()
            temp_path = f.name

        try:
            result = compute_edit_diff(temp_path, "test", "new", os.path.dirname(temp_path))
            assert isinstance(result, EditDiffError)
            assert "occurrences" in result.error.lower()
        finally:
            os.unlink(temp_path)
