"""
Tests for pi_tui/stdin_buffer.py - input buffering.
"""

import pytest
from pi_tui.stdin_buffer import (
    is_complete_sequence,
    extract_complete_sequences,
    StdinBuffer,
    StdinBufferOptions,
)


class TestIsCompleteSequence:
    """Tests for is_complete_sequence function."""

    def test_single_esc_incomplete(self):
        assert is_complete_sequence("\x1b") == "incomplete"

    def test_esc_with_letter_complete(self):
        assert is_complete_sequence("\x1ba") == "complete"

    def test_csi_sequence_complete(self):
        assert is_complete_sequence("\x1b[A") == "complete"
        assert is_complete_sequence("\x1b[B") == "complete"
        assert is_complete_sequence("\x1b[5~") == "complete"

    def test_csi_sequence_incomplete(self):
        assert is_complete_sequence("\x1b[") == "incomplete"
        assert is_complete_sequence("\x1b[1") == "incomplete"

    def test_osc_sequence_with_bel_complete(self):
        assert is_complete_sequence("\x1b]0;Title\x07") == "complete"

    def test_osc_sequence_with_st_complete(self):
        assert is_complete_sequence("\x1b]0;Title\x1b\\") == "complete"

    def test_osc_sequence_incomplete(self):
        assert is_complete_sequence("\x1b]0;Title") == "incomplete"

    def test_dcs_sequence_complete(self):
        assert is_complete_sequence("\x1bPdata\x1b\\") == "complete"

    def test_dcs_sequence_incomplete(self):
        assert is_complete_sequence("\x1bPdata") == "incomplete"

    def test_apc_sequence_complete(self):
        assert is_complete_sequence("\x1b_G\x1b\\") == "complete"

    def test_apc_sequence_incomplete(self):
        assert is_complete_sequence("\x1b_G") == "incomplete"

    def test_ss3_sequence_complete(self):
        assert is_complete_sequence("\x1bOA") == "complete"
        assert is_complete_sequence("\x1bOP") == "complete"

    def test_ss3_sequence_incomplete(self):
        assert is_complete_sequence("\x1bO") == "incomplete"

    def test_non_escape_not_escape(self):
        assert is_complete_sequence("a") == "not-escape"
        assert is_complete_sequence("hello") == "not-escape"


class TestExtractCompleteSequences:
    """Tests for extract_complete_sequences function."""

    def test_single_complete_sequence(self):
        result = extract_complete_sequences("\x1b[A")
        assert result.sequences == ["\x1b[A"]
        assert result.remainder == ""

    def test_multiple_complete_sequences(self):
        result = extract_complete_sequences("\x1b[A\x1b[B")
        assert result.sequences == ["\x1b[A", "\x1b[B"]
        assert result.remainder == ""

    def test_with_trailing_incomplete(self):
        result = extract_complete_sequences("\x1b[A\x1b")
        assert result.sequences == ["\x1b[A"]
        assert result.remainder == "\x1b"

    def test_non_escape_chars(self):
        result = extract_complete_sequences("ab\x1b[A")
        assert result.sequences == ["a", "b", "\x1b[A"]
        assert result.remainder == ""

    def test_empty_buffer(self):
        result = extract_complete_sequences("")
        assert result.sequences == []
        assert result.remainder == ""

    def test_only_incomplete(self):
        result = extract_complete_sequences("\x1b[")
        assert result.sequences == []
        assert result.remainder == "\x1b["


class TestStdinBufferProcess:
    """Tests for StdinBuffer.process method."""

    def test_complete_sequence_emits(self, data_callback):
        buffer = StdinBuffer()
        buffer.on_data = data_callback

        buffer.process("\x1b[A")

        data_callback.assert_called_once_with("\x1b[A")

    def test_partial_sequence_waits(self, data_callback):
        buffer = StdinBuffer()
        buffer.on_data = data_callback

        buffer.process("\x1b")
        data_callback.assert_not_called()

        buffer.process("[")
        data_callback.assert_not_called()

        buffer.process("A")
        data_callback.assert_called_once_with("\x1b[A")

    def test_multiple_chunks_one_sequence(self, data_callback):
        buffer = StdinBuffer()
        buffer.on_data = data_callback

        buffer.process("\x1b")
        buffer.process("[")
        buffer.process("A")

        data_callback.assert_called_once_with("\x1b[A")

    def test_bytes_input(self, data_callback):
        buffer = StdinBuffer()
        buffer.on_data = data_callback

        buffer.process(b"a")

        data_callback.assert_called_once_with("a")

    def test_empty_input(self, data_callback):
        buffer = StdinBuffer()
        buffer.on_data = data_callback

        buffer.process("")

        data_callback.assert_called_once_with("")


class TestBracketedPaste:
    """Tests for bracketed paste handling."""

    def test_bracketed_paste(self, paste_callback):
        buffer = StdinBuffer()
        buffer.on_paste = paste_callback

        buffer.process("\x1b[200~Hello World\x1b[201~")

        paste_callback.assert_called_once_with("Hello World")

    def test_bracketed_paste_multiple_chunks(self, paste_callback):
        buffer = StdinBuffer()
        buffer.on_paste = paste_callback

        buffer.process("\x1b[200~Hello")
        buffer.process(" World\x1b[201~")

        paste_callback.assert_called_once_with("Hello World")

    def test_content_after_paste_processed(self, data_callback, paste_callback):
        buffer = StdinBuffer()
        buffer.on_data = data_callback
        buffer.on_paste = paste_callback

        buffer.process("\x1b[200~paste\x1b[201~\x1b[A")

        paste_callback.assert_called_once_with("paste")
        data_callback.assert_called_with("\x1b[A")


class TestBufferState:
    """Tests for buffer state management."""

    def test_clear_resets_state(self, data_callback):
        buffer = StdinBuffer()
        buffer.on_data = data_callback

        buffer.process("\x1b")
        buffer.clear()

        assert buffer.get_buffer() == ""

    def test_get_buffer(self, data_callback):
        buffer = StdinBuffer()
        buffer.on_data = data_callback

        buffer.process("\x1b")

        assert buffer.get_buffer() == "\x1b"

    def test_flush(self, data_callback):
        buffer = StdinBuffer()
        buffer.on_data = data_callback

        buffer.process("\x1b")
        result = buffer.flush()

        assert result == ["\x1b"]
        assert buffer.get_buffer() == ""

    def test_flush_empty(self):
        buffer = StdinBuffer()
        result = buffer.flush()
        assert result == []

    def test_destroy(self, data_callback):
        buffer = StdinBuffer()
        buffer.on_data = data_callback

        buffer.process("\x1b")
        buffer.destroy()

        assert buffer.get_buffer() == ""


class TestStdinBufferOptions:
    """Tests for StdinBufferOptions."""

    def test_default_timeout(self):
        options = StdinBufferOptions()
        assert options.timeout == 10.0

    def test_custom_timeout(self):
        options = StdinBufferOptions(timeout=50.0)
        assert options.timeout == 50.0
