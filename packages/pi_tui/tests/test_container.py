"""
Tests for the Container component.
"""

from pi_tui.container import Container

class TestContainer:
    # =========================================================================
    # A. Child Management Tests
    # =========================================================================

    def test_add_child_appends_to_list(self, mock_component):
        container = Container()
        container.add_child(mock_component)
        assert container.children[-1] == mock_component

    def test_add_child_increases_count(self, mock_component):
        container = Container()
        assert len(container.children) == 0
        container.add_child(mock_component)
        assert len(container.children) == 1

    def test_remove_child_removes_specific_child(self, mock_component):
        container = Container()
        container.add_child(mock_component)
        container.remove_child(mock_component)
        assert mock_component not in container.children

    def test_remove_child_non_existent_no_error(self, mock_component):
        container = Container()
        # Should not raise any error
        container.remove_child(mock_component)

    def test_remove_child_decreases_count(self, mock_component):
        container = Container()
        container.add_child(mock_component)
        assert len(container.children) == 1
        container.remove_child(mock_component)
        assert len(container.children) == 0

    def test_clear_removes_all_children(self, mock_component_factory):
        container = Container()
        container.add_child(mock_component_factory())
        container.add_child(mock_component_factory())
        container.clear()
        assert len(container.children) == 0

    def test_clear_results_in_empty_list(self, mock_component_factory):
        container = Container()
        container.add_child(mock_component_factory())
        container.clear()
        assert container.children == []

    def test_children_list_is_accessible(self):
        container = Container()
        assert isinstance(container.children, list)

    def test_multiple_add_child_calls(self, mock_component_factory):
        container = Container()
        c1 = mock_component_factory()
        c2 = mock_component_factory()
        container.add_child(c1)
        container.add_child(c2)
        assert container.children == [c1, c2]

    def test_add_child_different_components(self, mock_component_factory):
        container = Container()
        c1 = mock_component_factory()
        c2 = mock_component_factory()
        container.add_child(c1)
        container.add_child(c2)
        assert len(container.children) == 2
        assert container.children[0] is c1
        assert container.children[1] is c2

    def test_remove_child_only_removes_specified(self, mock_component_factory):
        container = Container()
        c1 = mock_component_factory()
        c2 = mock_component_factory()
        container.add_child(c1)
        container.add_child(c2)
        container.remove_child(c1)
        assert container.children == [c2]

    def test_clear_on_empty_container(self):
        container = Container()
        container.clear()
        assert len(container.children) == 0

    # =========================================================================
    # B. Invalidation Tests
    # =========================================================================

    def test_invalidate_calls_children_invalidate(self, mock_component):
        container = Container()
        container.add_child(mock_component)
        container.invalidate()
        assert mock_component.invalidate_calls == 1

    def test_invalidate_no_children_no_error(self):
        container = Container()
        # Should not raise any error
        container.invalidate()

    def test_invalidate_propagates_to_all_children(self, mock_component_factory):
        container = Container()
        children = [mock_component_factory() for _ in range(3)]
        for child in children:
            container.add_child(child)
        
        container.invalidate()
        for child in children:
            assert child.invalidate_calls == 1

    # =========================================================================
    # C. Render Tests
    # =========================================================================

    def test_render_concatenates_children_output(self, mock_component_factory):
        container = Container()
        container.add_child(mock_component_factory(["line 1"]))
        container.add_child(mock_component_factory(["line 2", "line 3"]))
        
        output = container.render(80)
        assert output == ["line 1", "line 2", "line 3"]

    def test_render_single_child(self, mock_component_factory):
        container = Container()
        container.add_child(mock_component_factory(["only line"]))
        assert container.render(80) == ["only line"]

    def test_render_multiple_children(self, mock_component_factory):
        container = Container()
        container.add_child(mock_component_factory(["c1"]))
        container.add_child(mock_component_factory(["c2"]))
        container.add_child(mock_component_factory(["c3"]))
        assert container.render(80) == ["c1", "c2", "c3"]

    def test_render_no_children_returns_empty_list(self):
        container = Container()
        assert container.render(80) == []

    def test_render_width_passed_to_children(self, mock_component):
        container = Container()
        container.add_child(mock_component)
        width = 123
        container.render(width)
        assert mock_component.render_calls == [width]
