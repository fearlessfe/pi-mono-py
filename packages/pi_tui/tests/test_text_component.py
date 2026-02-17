import pytest
from pi_tui.components.text import Text

def test_render_plain_text():
    """Test render plain text."""
    text = Text("Hello World", padding_x=0, padding_y=0)
    # width 20, "Hello World" is 11 chars.
    # wrap_text_with_ansi will return ["Hello World"]
    # render will pad it to 20
    rendered = text.render(20)
    assert rendered == ["Hello World         "]

def test_render_with_padding_x():
    """Test render with padding_x."""
    text = Text("Hello", padding_x=2, padding_y=0)
    # width 10, content_width = 10 - 2*2 = 6
    # "Hello" fits in 6.
    # line_with_margins = "  " + "Hello" + "  " = "    Hello  " (wait, 2+5+2 = 9)
    # visible_width is 9. padding_needed = 10 - 9 = 1.
    # result = "    Hello   " (10 chars)
    # Wait, left_margin = " " * 2, right_margin = " " * 2.
    # "  " + "Hello" + "  " = "  Hello  " (7 chars)
    # visible_width("  Hello  ") is 9? No, 2 + 5 + 2 = 9.
    # Let's re-calculate: "  " (2) + "Hello" (5) + "  " (2) = 9.
    # width 10. 10 - 9 = 1 space padding.
    # Total: "  Hello   "
    rendered = text.render(10)
    assert rendered == ["  Hello   "]
    assert len(rendered[0]) == 10

def test_render_with_padding_y():
    """Test render with padding_y."""
    text = Text("Hello", padding_x=0, padding_y=1)
    # width 10.
    # empty_line = "          " (10 spaces)
    # content_line = "Hello     " (10 spaces)
    # result = [empty_line, content_line, empty_line]
    rendered = text.render(10)
    assert rendered == ["          ", "Hello     ", "          "]

def test_render_empty_text_returns_empty_list():
    """Test empty text returns empty list."""
    text = Text("", padding_x=1, padding_y=1)
    rendered = text.render(10)
    assert rendered == []

def test_render_whitespace_text_returns_empty_list():
    """Test text with only whitespace returns empty list."""
    text = Text("   ", padding_x=1, padding_y=1)
    rendered = text.render(10)
    assert rendered == []

def test_tab_replacement():
    """Test tab replacement with 3 spaces."""
    text = Text("A\tB", padding_x=0, padding_y=0)
    rendered = text.render(10)
    assert rendered[0] == "A   B     "
    assert len(rendered[0]) == 10

def test_render_word_wrap():
    """Test render with word wrapping."""
    text = Text("Hello World", padding_x=0, padding_y=0)
    # width 5. "Hello" (5), "World" (5).
    # wrap_text_with_ansi("Hello World", 5) -> ["Hello", "World"]
    rendered = text.render(5)
    assert rendered == ["Hello", "World"]

def test_render_long_word():
    """Test render with a word longer than width."""
    text = Text("Supercalifragilistic", padding_x=0, padding_y=0)
    # width 5. Word is longer than 5.
    # wrap_text_with_ansi will put it on its own line.
    rendered = text.render(5)
    assert rendered == ["Supercalifragilistic"]

def test_render_multiple_words_wrap():
    """Test multiple words wrapping."""
    text = Text("one two three", padding_x=0, padding_y=0)
    # width 7. "one two" (7), "three" (5)
    rendered = text.render(7)
    assert rendered == ["one two", "three  "]

def test_render_padding_and_wrap():
    """Test combined padding and wrapping."""
    text = Text("Hello World", padding_x=1, padding_y=0)
    # width 7. content_width = 7 - 2 = 5.
    # "Hello" (5), "World" (5).
    # line_with_margins = " " + "Hello" + " " = " Hello " (7 chars)
    rendered = text.render(7)
    assert rendered == [" Hello ", " World "]

# B. Caching Tests

def test_cache_hit():
    """Test cache hit when text and width unchanged."""
    text = Text("Hello", padding_x=0, padding_y=0)
    rendered1 = text.render(10)
    rendered2 = text.render(10)
    assert rendered1 is rendered2

def test_cache_invalidated_on_set_text():
    """Test cache invalidated on set_text()."""
    text = Text("Hello", padding_x=0, padding_y=0)
    rendered1 = text.render(10)
    text.set_text("World")
    rendered2 = text.render(10)
    assert rendered1 is not rendered2
    assert rendered2 == ["World     "]

def test_cache_invalidated_on_invalidate():
    """Test cache invalidated on invalidate()."""
    text = Text("Hello", padding_x=0, padding_y=0)
    rendered1 = text.render(10)
    text.invalidate()
    rendered2 = text.render(10)
    assert rendered1 is not rendered2

def test_cache_invalidated_on_width_change():
    """Test cache invalidated on width change."""
    text = Text("Hello", padding_x=0, padding_y=0)
    rendered1 = text.render(10)
    rendered2 = text.render(20)
    assert rendered1 is not rendered2
    assert len(rendered2[0]) == 20

def test_cache_invalidated_on_bg_fn_change():
    """Test cache invalidated on set_custom_bg_fn()."""
    text = Text("Hello", padding_x=0, padding_y=0)
    rendered1 = text.render(10)
    text.set_custom_bg_fn(lambda x: f"[{x}]")
    rendered2 = text.render(10)
    assert rendered1 is not rendered2
    assert rendered2 == ["[Hello     ]"]

# C. Background Function Tests

def test_render_with_custom_bg_fn():
    """Test render with custom_bg_fn applied."""
    def bg_fn(s):
        return f"BG({s})"
    text = Text("Hello", padding_x=0, padding_y=0, custom_bg_fn=bg_fn)
    rendered = text.render(10)
    # apply_background_to_line will pad "Hello" to 10 then call bg_fn
    assert rendered == ["BG(Hello     )"]

def test_no_background_when_bg_fn_none():
    """Test no background when bg_fn=None."""
    text = Text("Hello", padding_x=0, padding_y=0, custom_bg_fn=None)
    rendered = text.render(10)
    assert rendered == ["Hello     "]

def test_render_padding_y_with_bg_fn():
    """Test vertical padding also gets background."""
    def bg_fn(s):
        return f"BG({s})"
    text = Text("Hello", padding_x=0, padding_y=1, custom_bg_fn=bg_fn)
    rendered = text.render(10)
    assert rendered == [
        "BG(          )",
        "BG(Hello     )",
        "BG(          )"
    ]

def test_render_empty_text_no_bg():
    """Test empty text returns empty list even with bg_fn."""
    def bg_fn(s):
        return f"BG({s})"
    text = Text("", padding_x=0, padding_y=0, custom_bg_fn=bg_fn)
    rendered = text.render(10)
    assert rendered == []

def test_render_with_bg_fn_and_padding_x():
    """Test horizontal padding is included in what's passed to bg_fn."""
    def bg_fn(s):
        return f"BG({s})"
    text = Text("Hi", padding_x=1, padding_y=0, custom_bg_fn=bg_fn)
    # width 6. content_width = 6 - 2 = 4.
    # "Hi" fits in 4.
    # line_with_margins = " " + "Hi" + " " = " Hi " (4 chars)
    # apply_background_to_line pads " Hi " to 6 -> " Hi   "
    # then calls bg_fn(" Hi   ") -> "BG( Hi   )"
    rendered = text.render(6)
    assert rendered == ["BG( Hi   )"]
