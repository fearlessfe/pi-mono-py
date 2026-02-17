"""
Tests for pi_tui/keys.py - keyboard input parsing.
"""

import pytest
from pi_tui.keys import (
    Key,
    matches_key,
    parse_key,
    set_kitty_protocol_active,
    is_kitty_protocol_active,
)


class TestKeyHelper:
    """Tests for the Key helper class."""

    def test_escape_constant(self):
        assert Key.escape == "escape"

    def test_enter_constant(self):
        assert Key.enter == "enter"

    def test_tab_constant(self):
        assert Key.tab == "tab"

    def test_space_constant(self):
        assert Key.space == "space"

    def test_backspace_constant(self):
        assert Key.backspace == "backspace"

    def test_delete_constant(self):
        assert Key.delete == "delete"

    def test_up_constant(self):
        assert Key.up == "up"

    def test_down_constant(self):
        assert Key.down == "down"

    def test_left_constant(self):
        assert Key.left == "left"

    def test_right_constant(self):
        assert Key.right == "right"

    def test_ctrl_modifier(self):
        assert Key.ctrl("a") == "ctrl+a"
        assert Key.ctrl("x") == "ctrl+x"

    def test_shift_modifier(self):
        assert Key.shift("a") == "shift+a"

    def test_alt_modifier(self):
        assert Key.alt("a") == "alt+a"

    def test_ctrl_shift_modifier(self):
        assert Key.ctrl_shift("p") == "ctrl+shift+p"

    def test_ctrl_alt_modifier(self):
        assert Key.ctrl_alt("x") == "ctrl+alt+x"

    def test_symbol_keys(self):
        assert Key.backtick == "`"
        assert Key.period == "."
        assert Key.comma == ","


class TestProtocolState:
    """Tests for Kitty protocol state management."""

    def test_set_kitty_protocol_active(self, reset_kitty_protocol):
        assert is_kitty_protocol_active() is False
        set_kitty_protocol_active(True)
        assert is_kitty_protocol_active() is True

    def test_reset_kitty_protocol(self, reset_kitty_protocol):
        set_kitty_protocol_active(True)
        assert is_kitty_protocol_active() is True
        set_kitty_protocol_active(False)
        assert is_kitty_protocol_active() is False

    def test_default_state(self, reset_kitty_protocol):
        assert is_kitty_protocol_active() is False


class TestLegacySequenceMatching:
    """Tests for legacy terminal sequence matching."""

    @pytest.mark.parametrize("data,key_id", [
        ("\x1b[A", "up"),
        ("\x1b[B", "down"),
        ("\x1b[C", "right"),
        ("\x1b[D", "left"),
        ("\x1bOA", "up"),
        ("\x1bOB", "down"),
        ("\x1bOC", "right"),
        ("\x1bOD", "left"),
    ])
    def test_arrow_keys(self, data, key_id, reset_kitty_protocol):
        assert matches_key(data, key_id) is True

    @pytest.mark.parametrize("data,key_id", [
        ("\x1bOP", "f1"),
        ("\x1bOQ", "f2"),
        ("\x1bOR", "f3"),
        ("\x1bOS", "f4"),
        ("\x1b[15~", "f5"),
        ("\x1b[17~", "f6"),
        ("\x1b[18~", "f7"),
        ("\x1b[19~", "f8"),
        ("\x1b[20~", "f9"),
        ("\x1b[21~", "f10"),
        ("\x1b[23~", "f11"),
        ("\x1b[24~", "f12"),
    ])
    def test_function_keys(self, data, key_id, reset_kitty_protocol):
        assert matches_key(data, key_id) is True

    @pytest.mark.parametrize("data,key_id", [
        ("\x1b[H", "home"),
        ("\x1b[F", "end"),
        ("\x1b[2~", "insert"),
        ("\x1b[3~", "delete"),
        ("\x1b[5~", "pageUp"),
        ("\x1b[6~", "pageDown"),
    ])
    def test_navigation_keys(self, data, key_id, reset_kitty_protocol):
        assert matches_key(data, key_id) is True

    def test_shift_tab(self, reset_kitty_protocol):
        assert matches_key("\x1b[Z", "shift+tab") is True

    def test_alt_arrow_left(self, reset_kitty_protocol):
        assert matches_key("\x1bb", "alt+left") is True
        assert matches_key("\x1b[1;3D", "alt+left") is True

    def test_alt_arrow_right(self, reset_kitty_protocol):
        assert matches_key("\x1bf", "alt+right") is True
        assert matches_key("\x1b[1;3C", "alt+right") is True


class TestSingleCharacterMatching:
    """Tests for single character key matching."""

    @pytest.mark.parametrize("char", "abcdefghijklmnopqrstuvwxyz")
    def test_lowercase_letters(self, char, reset_kitty_protocol):
        assert matches_key(char, char) is True

    @pytest.mark.parametrize("char", "ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    def test_uppercase_letters(self, char, reset_kitty_protocol):
        assert matches_key(char, char.lower()) is True

    def test_space(self, reset_kitty_protocol):
        assert matches_key(" ", "space") is True

    def test_tab(self, reset_kitty_protocol):
        assert matches_key("\t", "tab") is True

    def test_enter(self, reset_kitty_protocol):
        assert matches_key("\r", "enter") is True

    def test_backspace(self, reset_kitty_protocol):
        assert matches_key("\x7f", "backspace") is True
        assert matches_key("\x08", "backspace") is True

    def test_escape(self, reset_kitty_protocol):
        assert matches_key("\x1b", "escape") is True

    @pytest.mark.parametrize("code,expected", [
        (1, "ctrl+a"),
        (2, "ctrl+b"),
        (3, "ctrl+c"),
        (24, "ctrl+x"),
        (25, "ctrl+y"),
        (26, "ctrl+z"),
    ])
    def test_ctrl_letters(self, code, expected, reset_kitty_protocol):
        assert matches_key(chr(code), expected) is True

    @pytest.mark.parametrize("char", "abcdefghijklmnopqrstuvwxyz")
    def test_alt_letters(self, char, reset_kitty_protocol):
        assert matches_key(f"\x1b{char}", f"alt+{char}") is True


class TestMatchesKeyEdgeCases:
    """Tests for matches_key edge cases."""

    def test_empty_input(self, reset_kitty_protocol):
        assert matches_key("", "a") is False

    def test_invalid_key_id(self, reset_kitty_protocol):
        assert matches_key("a", "invalid_key") is False

    def test_wrong_key(self, reset_kitty_protocol):
        assert matches_key("a", "b") is False


class TestParseKey:
    """Tests for parse_key function."""

    def test_parse_ss3_arrow_up(self, reset_kitty_protocol):
        result = parse_key("\x1bOA")
        assert result == "up"

    def test_parse_ss3_arrow_down(self, reset_kitty_protocol):
        result = parse_key("\x1bOB")
        assert result == "down"

    def test_parse_letter(self, reset_kitty_protocol):
        result = parse_key("a")
        assert result == "a"

    def test_parse_ctrl_a(self, reset_kitty_protocol):
        result = parse_key(chr(1))
        assert result == "ctrl+a"

    def test_parse_tab(self, reset_kitty_protocol):
        result = parse_key("\t")
        assert result == "tab"

    def test_parse_enter(self, reset_kitty_protocol):
        result = parse_key("\r")
        assert result == "enter"

    def test_parse_f1(self, reset_kitty_protocol):
        result = parse_key("\x1bOP")
        assert result == "f1"

    def test_parse_home(self, reset_kitty_protocol):
        result = parse_key("\x1bOH")
        assert result == "home"
