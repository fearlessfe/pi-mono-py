from pi_tui.components.box import Box
from unittest.mock import MagicMock

# =============================================================================
# A. Basic Rendering Tests (10 tests)
# =============================================================================

def test_render_no_children():
    """Render with no children returns empty list."""
    box = Box()
    assert box.render(10) == []

def test_render_single_child(mock_component_factory):
    """Render with single child."""
    child = mock_component_factory(["hello"])
    box = Box(padding_x=0, padding_y=0)
    box.add_child(child)
    assert box.render(10) == ["hello     "]

def test_render_multiple_children(mock_component_factory):
    """Render with multiple children."""
    child1 = mock_component_factory(["line1"])
    child2 = mock_component_factory(["line2"])
    box = Box(padding_x=0, padding_y=0)
    box.add_child(child1)
    box.add_child(child2)
    assert box.render(10) == ["line1     ", "line2     "]

def test_padding_x(mock_component_factory):
    """Test padding_x applied."""
    child = mock_component_factory(["hello"])
    box = Box(padding_x=2, padding_y=0)
    box.add_child(child)
    # width=10, padding_x=2 -> content_width = 10 - 2*2 = 6
    # child.render(6) -> ["hello"]
    # left_pad = "  "
    # child_lines = ["  hello"]
    # _apply_bg("  hello", 10) -> "  hello   "
    assert box.render(10) == ["  hello   "]

def test_padding_y(mock_component_factory):
    """Test padding_y applied."""
    child = mock_component_factory(["hello"])
    box = Box(padding_x=0, padding_y=1)
    box.add_child(child)
    # width=10, padding_y=1
    # top padding: _apply_bg("", 10) -> "          "
    # child: _apply_bg("hello", 10) -> "hello     "
    # bottom padding: _apply_bg("", 10) -> "          "
    assert box.render(10) == ["          ", "hello     ", "          "]

def test_padding_xy(mock_component_factory):
    """Test both padding_x and padding_y applied."""
    child = mock_component_factory(["hi"])
    box = Box(padding_x=1, padding_y=1)
    box.add_child(child)
    # width=5
    # content_width = 5 - 2 = 3
    # child.render(3) -> ["hi"]
    # child_lines -> [" hi"]
    # top: "     "
    # mid: " hi  "
    # bot: "     "
    assert box.render(5) == ["     ", " hi  ", "     "]

def test_render_child_multiple_lines(mock_component_factory):
    """Render child that returns multiple lines."""
    child = mock_component_factory(["l1", "l2"])
    box = Box(padding_x=0, padding_y=0)
    box.add_child(child)
    assert box.render(10) == ["l1        ", "l2        "]

def test_render_with_bg_fn(mock_component_factory):
    """Test rendering with background function."""
    bg_fn = lambda s: f"BG({s})"
    child = mock_component_factory(["hi"])
    box = Box(padding_x=0, padding_y=0, bg_fn=bg_fn)
    box.add_child(child)
    # width=5
    # child.render(5) -> ["hi"]
    # _apply_bg("hi", 5) -> padded="hi   ", returns BG(hi   )
    assert box.render(5) == ["BG(hi   )"]

def test_render_empty_child_output():
    """Render with child that returns no lines."""
    child = MagicMock()
    child.render.return_value = []
    box = Box()
    box.add_child(child)
    assert box.render(10) == []

def test_render_min_content_width(mock_component_factory):
    """Test content width is at least 1."""
    child = mock_component_factory(["x"])
    box = Box(padding_x=10, padding_y=0)
    box.add_child(child)
    # width=5, padding_x=10
    # content_width = max(1, 5 - 20) = 1
    # child.render(1)
    # left_pad = " " * 10
    # child_lines = ["          x"]
    # _apply_bg("          x", 5) -> vis_len=11, width=5, pad_needed=0
    # returns "          x"
    assert box.render(5) == ["          x"]

# =============================================================================
# B. Child Management Tests (7 tests)
# =============================================================================

def test_add_child_appends(mock_component):
    """add_child() appends child."""
    box = Box()
    box.add_child(mock_component)
    assert len(box.children) == 1
    assert box.children[0] == mock_component

def test_remove_child_removes(mock_component):
    """remove_child() removes child."""
    box = Box()
    box.add_child(mock_component)
    box.remove_child(mock_component)
    assert len(box.children) == 0

def test_remove_child_not_found(mock_component, mock_component_factory):
    """remove_child() does nothing if child not found."""
    box = Box()
    box.add_child(mock_component)
    other = mock_component_factory()
    box.remove_child(other)
    assert len(box.children) == 1
    assert box.children[0] == mock_component

def test_clear_removes_all(mock_component_factory):
    """clear() removes all children."""
    box = Box()
    box.add_child(mock_component_factory())
    box.add_child(mock_component_factory())
    box.clear()
    assert len(box.children) == 0

def test_add_child_multiple(mock_component_factory):
    """add_child() multiple times."""
    box = Box()
    c1 = mock_component_factory()
    c2 = mock_component_factory()
    box.add_child(c1)
    box.add_child(c2)
    assert box.children == [c1, c2]

def test_remove_child_middle(mock_component_factory):
    """remove_child() from middle of list."""
    box = Box()
    c1 = mock_component_factory()
    c2 = mock_component_factory()
    c3 = mock_component_factory()
    box.add_child(c1)
    box.add_child(c2)
    box.add_child(c3)
    box.remove_child(c2)
    assert box.children == [c1, c3]

def test_clear_empty():
    """clear() on empty box."""
    box = Box()
    box.clear()
    assert len(box.children) == 0

# =============================================================================
# C. Caching Tests (5 tests)
# =============================================================================

def test_cache_used_on_second_render(mock_component_factory):
    """Verify cache is used on subsequent renders with same width."""
    child = mock_component_factory(["hello"])
    bg_fn = MagicMock(side_effect=lambda s: s)
    box = Box(padding_x=0, padding_y=0, bg_fn=bg_fn)
    box.add_child(child)
    
    # First render
    box.render(10)
    # bg_fn called for: bg_sample("test") and _apply_bg("hello", 10)
    assert bg_fn.call_count == 2
    
    # Second render
    box.render(10)
    # bg_fn called for: bg_sample("test") only. 
    # _apply_bg is NOT called again because of cache.
    assert bg_fn.call_count == 3
    # Note: child.render IS called again because Box needs to check if child output changed
    assert len(child.render_calls) == 2

def test_cache_invalidated_on_add_child(mock_component_factory):
    """Cache invalidated on add_child()."""
    box = Box(padding_x=0, padding_y=0)
    c1 = mock_component_factory(["c1"])
    box.add_child(c1)
    
    box.render(10)
    assert len(c1.render_calls) == 1
    
    c2 = mock_component_factory(["c2"])
    box.add_child(c2)
    
    box.render(10)
    assert len(c1.render_calls) == 2
    assert len(c2.render_calls) == 1

def test_cache_invalidated_on_invalidate(mock_component_factory):
    """Cache invalidated on invalidate()."""
    child = mock_component_factory(["hello"])
    box = Box(padding_x=0, padding_y=0)
    box.add_child(child)
    
    box.render(10)
    assert len(child.render_calls) == 1
    
    box.invalidate()
    assert child.invalidate_calls == 1
    
    box.render(10)
    assert len(child.render_calls) == 2

def test_cache_invalidated_on_width_change(mock_component_factory):
    """Cache invalidated when width changes."""
    child = mock_component_factory(["hello"])
    box = Box(padding_x=0, padding_y=0)
    box.add_child(child)
    
    box.render(10)
    assert len(child.render_calls) == 1
    
    box.render(20)
    assert len(child.render_calls) == 2

def test_cache_invalidated_on_remove_child(mock_component_factory):
    """Cache invalidated on remove_child()."""
    box = Box(padding_x=0, padding_y=0)
    c1 = mock_component_factory(["c1"])
    box.add_child(c1)
    
    box.render(10)
    assert len(c1.render_calls) == 1
    
    box.remove_child(c1)
    assert box.render(10) == []
