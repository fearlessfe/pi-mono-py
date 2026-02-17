"""
Tests for pi_tui.component module.
"""

import pytest
from typing import Any
from pi_tui.component import Component, Focusable, is_focusable


# =============================================================================
# Concrete Component for Testing
# =============================================================================

class ConcreteComponent(Component):
    """A concrete implementation of Component for testing."""
    def render(self, width: int) -> list[str]:
        return [f"width: {width}"]


class OverriddenComponent(Component):
    """A component that overrides all optional methods."""
    def __init__(self) -> None:
        self.handle_input_called = False
        self.invalidate_called = False
        self.wants_key_release = True

    def render(self, width: int) -> list[str]:
        return ["overridden"]

    def handle_input(self, data: str) -> None:
        self.handle_input_called = True

    def invalidate(self) -> None:
        self.invalidate_called = True


# =============================================================================
# A. Component Interface Tests (10 tests)
# =============================================================================

def test_component_is_abstract():
    """Test Component is abstract (cannot instantiate directly)."""
    with pytest.raises(TypeError, match="Can't instantiate abstract class Component"):
        Component()  # type: ignore


def test_render_is_abstract():
    """Test render() is abstract (raises TypeError if not implemented)."""
    class IncompleteComponent(Component):
        pass
    
    with pytest.raises(TypeError, match="Can't instantiate abstract class IncompleteComponent"):
        IncompleteComponent()  # type: ignore


def test_handle_input_default_implementation():
    """Test handle_input() default implementation is no-op (can be called)."""
    comp = ConcreteComponent()
    # Should not raise any error
    assert comp.handle_input("some data") is None


def test_invalidate_default_implementation():
    """Test invalidate() default implementation is no-op (can be called)."""
    comp = ConcreteComponent()
    # Should not raise any error
    assert comp.invalidate() is None


def test_wants_key_release_default_value():
    """Test wants_key_release default value is False."""
    comp = ConcreteComponent()
    assert comp.wants_key_release is False


def test_concrete_component_instantiation():
    """Test concrete subclass can be instantiated."""
    comp = ConcreteComponent()
    assert isinstance(comp, Component)


def test_concrete_component_render():
    """Test concrete subclass render() works."""
    comp = ConcreteComponent()
    assert comp.render(80) == ["width: 80"]


def test_concrete_component_handle_input_override():
    """Test concrete subclass handle_input() can be overridden."""
    comp = OverriddenComponent()
    comp.handle_input("test")
    assert comp.handle_input_called is True


def test_concrete_component_invalidate_override():
    """Test concrete subclass invalidate() can be overridden."""
    comp = OverriddenComponent()
    comp.invalidate()
    assert comp.invalidate_called is True


def test_concrete_component_wants_key_release_override():
    """Test concrete subclass wants_key_release can be overridden."""
    comp = OverriddenComponent()
    assert comp.wants_key_release is True


# =============================================================================
# B. Focusable Protocol Tests (5 tests)
# =============================================================================

class SimpleFocusable:
    def __init__(self, focused: bool = False) -> None:
        self.focused = focused


class NonFocusable:
    pass


def test_class_with_focused_attribute_implements_focusable():
    """Test class with focused attribute implements Focusable."""
    # Since Focusable is a Protocol, we check if an instance with 'focused' 
    # attribute can be treated as Focusable.
    obj: Focusable = SimpleFocusable(focused=True)
    assert obj.focused is True


def test_class_without_focused_attribute_does_not_implement_focusable():
    """Test class without focused attribute does not implement Focusable."""
    obj = NonFocusable()
    assert not hasattr(obj, "focused")


def test_focused_can_be_true():
    """Test focused can be True."""
    obj = SimpleFocusable(focused=True)
    assert obj.focused is True


def test_focused_can_be_false():
    """Test focused can be False."""
    obj = SimpleFocusable(focused=False)
    assert obj.focused is False


def test_focusable_protocol_attribute_access():
    """Test that Focusable protocol defines focused attribute."""
    # This is more of a type-checking test, but we can verify the protocol 
    # itself has the attribute in its __annotations__
    assert "focused" in Focusable.__annotations__


# =============================================================================
# C. is_focusable() Tests (10 tests)
# =============================================================================

def test_is_focusable_returns_true_for_object_with_focused_attribute():
    """Test returns True for object with focused attribute."""
    obj = SimpleFocusable()
    assert is_focusable(obj) is True


def test_is_focusable_returns_false_for_object_without_focused_attribute():
    """Test returns False for object without focused attribute."""
    obj = NonFocusable()
    assert is_focusable(obj) is False  # type: ignore


def test_is_focusable_returns_false_for_none():
    """Test returns False for None."""
    assert is_focusable(None) is False


def test_is_focusable_returns_true_for_mock_focusable_component(mock_focusable_component):
    """Test returns True for MockFocusableComponent from conftest."""
    assert is_focusable(mock_focusable_component) is True


def test_is_focusable_returns_false_for_mock_component(mock_component):
    """Test returns False for MockComponent from conftest."""
    # MockComponent in conftest does NOT have 'focused' attribute
    assert is_focusable(mock_component) is False


def test_is_focusable_returns_true_for_dynamic_object():
    """Test returns True for a dynamic object with focused attribute."""
    obj = type("Dynamic", (), {"focused": False})()
    assert is_focusable(obj) is True  # type: ignore


def test_is_focusable_returns_false_for_string():
    """Test returns False for a string."""
    assert is_focusable("not a component") is False  # type: ignore


def test_is_focusable_returns_false_for_int():
    """Test returns False for an integer."""
    assert is_focusable(123) is False  # type: ignore


def test_is_focusable_returns_false_for_list():
    """Test returns False for a list."""
    assert is_focusable([]) is False  # type: ignore


def test_is_focusable_returns_false_for_dict():
    """Test returns False for a dict."""
    assert is_focusable({}) is False  # type: ignore
