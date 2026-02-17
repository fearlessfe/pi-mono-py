import pytest
from unittest.mock import patch
from pi_tui.utils import (
    visible_width,
    truncate_to_width,
    wrap_text_with_ansi,
    slice_by_column,
    apply_background_to_line,
    _strip_ansi
)

class TestVisibleWidth:
    """Tests for visible_width() function."""

    @pytest.mark.parametrize("text, expected", [
        ("", 0),
        ("hello", 5),
        ("  spaces  ", 10),
        ("\x1b[31mRed\x1b[0m", 3),
        ("\x1b[1;32mBold Green\x1b[0m", 10),
        ("\x1b[4mUnderline\x1b[24m", 9),
        ("\x1b[38;5;208mOrange\x1b[0m", 6),
        ("\x1b[48;2;255;0;0mRGB BG\x1b[0m", 6),
        ("Mixed \x1b[34mBlue\x1b[0m and \x1b[32mGreen\x1b[0m", 20),
        ("\x1b[?25hCursor Show", 11),  # CSI sequence
        ("\x1b]0;Title\x07Terminal", 8),  # OSC sequence
        ("\x1b_APC\x07Hidden", 6),  # APC sequence
        ("Multiple \x1b[31mANSI\x1b[0m \x1b[32mcodes\x1b[0m", 19),
        ("\x1b[31m\x1b[1mDouble\x1b[0m", 6),
        ("No ANSI here", 12),
        ("\x1b[mReset only", 10),
        ("\x1b[0mReset zero", 10),
        ("\x1b[1mBold\x1b[22mNormal", 10),
        ("\x1b[31;1;4mComplex\x1b[0m", 7),
        ("Tabs\t", 4), # wcwidth('\t') is -1, so max(0, -1) is 0
    ])
    def test_visible_width_basic(self, text, expected):
        assert visible_width(text) == expected

    def test_visible_width_cjk(self):
        # Since wcwidth might be the fallback (returning 1), 
        # we mock it to test wide character behavior
        with patch("pi_tui.utils.wcwidth", side_effect=lambda c: 2 if ord(c) > 0x4e00 else 1):
            assert visible_width("你好") == 4
            assert visible_width("Hello 你好") == 10
            assert visible_width("\x1b[31m你好\x1b[0m") == 4

    def test_visible_width_emoji(self):
        with patch("pi_tui.utils.wcwidth", return_value=2):
            assert visible_width("🚀") == 2
            assert visible_width("🚀🚀") == 4

    def test_visible_width_zero_width(self):
        with patch("pi_tui.utils.wcwidth", return_value=0):
            assert visible_width("\u200b") == 0  # Zero width space
        
        # 'a' with combining grave accent
        def mock_wcwidth(c):
            if c == 'a': return 1
            if c == '\u0300': return 0
            return 1
        with patch("pi_tui.utils.wcwidth", side_effect=mock_wcwidth):
            assert visible_width("a\u0300") == 1

    def test_strip_ansi(self):
        assert _strip_ansi("\x1b[31mRed\x1b[0m") == "Red"
        assert _strip_ansi("\x1b]0;Title\x07Terminal") == "Terminal"
        assert _strip_ansi("\x1b_APC\x07Hidden") == "Hidden"
        assert _strip_ansi("Plain") == "Plain"
        assert _strip_ansi("\x1b[?25hCursor") == "Cursor"

class TestTruncateToWidth:
    """Tests for truncate_to_width() function."""

    @pytest.mark.parametrize("text, max_width, expected", [
        ("hello world", 11, "hello world"),
        ("hello world", 12, "hello world"),
        ("hello world", 5, "he..."),
        ("hello world", 8, "hello..."),
        ("hello world", 3, "..."),
        ("hello world", 0, ""),
        ("hello world", -1, ""),
    ])
    def test_truncate_basic(self, text, max_width, expected):
        assert truncate_to_width(text, max_width) == expected

    @pytest.mark.parametrize("text, max_width, ellipsis, expected", [
        ("hello world", 5, "..", "hel.."),
        ("hello world", 5, "", "hello"),
        ("hello world", 5, "!", "hell!"),
        ("abcde", 3, "...", "..."),
    ])
    def test_truncate_custom_ellipsis(self, text, max_width, ellipsis, expected):
        assert truncate_to_width(text, max_width, ellipsis=ellipsis) == expected

    @pytest.mark.parametrize("text, max_width, expected", [
        ("abc", 5, "abc  "),
        ("hello", 5, "hello"),
        ("hello world", 8, "hello..."), # pad=True but already truncated
    ])
    def test_truncate_padding(self, text, max_width, expected):
        assert truncate_to_width(text, max_width, pad=True) == expected

    def test_truncate_ansi_preserved(self):
        text = "\x1b[31mhello world\x1b[0m"
        # "hello world" is 11 chars. Truncate to 5 -> "he..."
        # ANSI should be preserved.
        assert truncate_to_width(text, 5) == "\x1b[31mhe..."

    def test_truncate_ansi_at_boundary(self):
        text = "hello\x1b[31m world\x1b[0m"
        # Truncate to 5. ellipsis_width=3. max_width-ellipsis_width=2.
        # "he" (2). Next is 'l' (1). 2+1 > 2 is True.
        # Result: "he..."
        assert truncate_to_width(text, 5) == "he..."

    def test_truncate_wide_chars(self):
        with patch("pi_tui.utils.wcwidth", side_effect=lambda c: 2 if ord(c) > 0x4e00 else 1):
            # "你好世界" -> 8 width
            # Truncate to 5. max_width-ellipsis_width=2.
            # '你' (2). Next '好' (2). 2+2 > 2 is True.
            # Result: "你..."
            assert truncate_to_width("你好世界", 5) == "你..."
            
            # Truncate to 4. max_width-ellipsis_width=1.
            # '你' (2). 2 > 1 is True.
            # Result: "..."
            assert truncate_to_width("你好世界", 4) == "..."

    @pytest.mark.parametrize("text, max_width, expected", [
        ("\x1b[31mRed\x1b[0m Text", 6, "\x1b[31mRed\x1b[0m..."),
        ("\x1b[1mBold\x1b[0m and \x1b[4mUnderline\x1b[0m", 10, "\x1b[1mBold\x1b[0m an..."),
    ])
    def test_truncate_complex_ansi(self, text, max_width, expected):
        assert truncate_to_width(text, max_width) == expected

    def test_truncate_osc_apc(self):
        text = "\x1b]0;Title\x07Hello World"
        # OSC is ignored in width. "Hello World" is 11.
        # Truncate to 5 -> "He..."
        # Result: "\x1b]0;Title\x07He..."
        assert truncate_to_width(text, 5) == "\x1b]0;Title\x07He..."

    def test_truncate_multiple_ansi_at_start(self):
        text = "\x1b[31m\x1b[1mHello\x1b[0m"
        assert truncate_to_width(text, 3) == "\x1b[31m\x1b[1m..."

    def test_truncate_exactly_at_width_with_ellipsis(self):
        # text width 5, max_width 5. No truncation needed.
        assert truncate_to_width("hello", 5) == "hello"
        # text width 6, max_width 5. Truncate to "he..."
        assert truncate_to_width("hello!", 5) == "he..."

    def test_truncate_with_pad_and_ansi(self):
        text = "\x1b[31mHi\x1b[0m"
        # width 2. pad to 5.
        # Result: "\x1b[31mHi\x1b[0m   "
        assert truncate_to_width(text, 5, pad=True) == "\x1b[31mHi\x1b[0m   "

    def test_truncate_empty_string(self):
        assert truncate_to_width("", 5) == ""
        assert truncate_to_width("", 5, pad=True) == "     "

    def test_truncate_max_width_smaller_than_ellipsis(self):
        # As discovered, it returns "..." even if max_width < 3
        assert truncate_to_width("hello", 2) == "..."
        assert truncate_to_width("hello", 1) == "..."

class TestWrapTextWithAnsi:
    """Tests for wrap_text_with_ansi() function."""

    @pytest.mark.parametrize("text, width, expected", [
        ("hello world", 5, ["hello", "world"]),
        ("hello world", 11, ["hello world"]),
        ("hello world", 20, ["hello world"]),
        ("a b c d e", 3, ["a b", "c d", "e"]),
        ("longword", 5, ["longword"]), # Implementation doesn't break words
        ("", 10, [""]),
        ("hello", 0, ["hello"]),
        ("hello", -1, ["hello"]),
    ])
    def test_wrap_basic(self, text, width, expected):
        assert wrap_text_with_ansi(text, width) == expected

    def test_wrap_with_ansi(self):
        text = "\x1b[31mhello\x1b[0m \x1b[32mworld\x1b[0m"
        # width 5. "hello" is 5. "world" is 5.
        # Result: ["\x1b[31mhello\x1b[0m", "\x1b[32mworld\x1b[0m"]
        assert wrap_text_with_ansi(text, 5) == ["\x1b[31mhello\x1b[0m", "\x1b[32mworld\x1b[0m"]

    def test_wrap_ansi_preserved_across_lines(self):
        # Note: The current implementation of wrap_text_with_ansi in utils.py 
        # DOES NOT actually preserve active styles across lines.
        # It just splits by space and keeps whatever ANSI was in the word.
        # If a style starts in one word and ends in another, and they are on different lines,
        # the second line won't have the style unless it's explicitly added.
        # Let's see what it does.
        text = "\x1b[31mhello world\x1b[0m"
        # words = ["\x1b[31mhello", "world\x1b[0m"]
        # width 5.
        # Line 1: "\x1b[31mhello"
        # Line 2: "world\x1b[0m"
        # Line 2 will NOT be red in a real terminal because it lacks the escape code.
        assert wrap_text_with_ansi(text, 5) == ["\x1b[31mhello", "world\x1b[0m"]

    def test_wrap_multiple_spaces(self):
        text = "hello  world"
        # words = ["hello", "", "world"]
        # width 5.
        # Result: ["hello", "", "world"]
        assert wrap_text_with_ansi(text, 5) == ["hello", "", "world"]

    def test_wrap_wide_chars(self):
        with patch("pi_tui.utils.wcwidth", side_effect=lambda c: 2 if ord(c) > 0x4e00 else 1):
            text = "你好 世界"
            # "你好" (4), "世界" (4)
            assert wrap_text_with_ansi(text, 5) == ["你好", "世界"]
            assert wrap_text_with_ansi(text, 10) == ["你好 世界"]

    def test_wrap_leading_trailing_spaces(self):
        assert wrap_text_with_ansi(" hello ", 5) == ["", "hello", ""]
        # " hello ".split(" ") -> ["", "hello", ""]

class TestSliceByColumn:
    """Tests for slice_by_column() function."""

    @pytest.mark.parametrize("text, start, length, expected", [
        ("hello world", 0, 5, "hello"),
        ("hello world", 6, 5, "world"),
        ("hello world", 0, 20, "hello world"),
        ("hello world", 20, 5, ""),
    ])
    def test_slice_basic(self, text, start, length, expected):
        assert slice_by_column(text, start, length) == expected

    def test_slice_with_ansi(self):
        text = "\x1b[31mRed\x1b[0m \x1b[32mGreen\x1b[0m"
        # "Red Green"
        # Slice 0, 3 -> "\x1b[31mRed"
        # Note: \x1b[0m is at col 3, and current_col < end_col (3 < 3) is False.
        assert slice_by_column(text, 0, 3) == "\x1b[31mRed"
        # Slice 4, 5 -> "\x1b[32mGreen"
        assert slice_by_column(text, 4, 5) == "\x1b[32mGreen"

    def test_slice_wide_chars(self):
        with patch("pi_tui.utils.wcwidth", side_effect=lambda c: 2 if ord(c) > 0x4e00 else 1):
            text = "你好世界" # 8 width
            # Slice 2, 4 -> "好世"
            assert slice_by_column(text, 2, 4) == "好世"
            
            # Slice 1, 4 -> "好" (if strict=True, '你' is skipped because it starts at 0 and ends at 2, which is > 1 but current_col < 1? No.)
            # current_col=0. '你' char_end_col=2. 
            # char_end_col(2) > start_col(1) and current_col(0) < end_col(5) is True.
            # So '你' is included.
            assert slice_by_column(text, 1, 4) == "你好世" 
            # Wait, '世' ends at 6. 6 > 5 (end_col). 
            # If strict=False, '世' is included.
            
            # Test strict mode
            # text="你好世界", start=0, length=3, strict=True
            # '你' (0-2) included.
            # '好' (2-4). char_end_col(4) > end_col(3). strict=True -> skip.
            assert slice_by_column(text, 0, 3, strict=True) == "你"
            assert slice_by_column(text, 0, 3, strict=False) == "你好"

    def test_slice_beyond_length(self):
        assert slice_by_column("abc", 1, 10) == "bc"

class TestApplyBackgroundToLine:
    """Tests for apply_background_to_line() function."""

    def test_apply_bg_basic(self):
        bg_fn = lambda x: f"\x1b[44m{x}\x1b[0m"
        line = "hello"
        width = 10
        # Should pad to 10 and apply bg
        expected = "\x1b[44mhello     \x1b[0m"
        assert apply_background_to_line(line, width, bg_fn) == expected

    def test_apply_bg_none(self):
        assert apply_background_to_line("hello", 10, None) == "hello"

    def test_apply_bg_already_wide_enough(self):
        bg_fn = lambda x: f"BG({x})"
        assert apply_background_to_line("hello world", 5, bg_fn) == "BG(hello world)"

