"""
Box component - a container that applies padding and background to all children.

TypeScript Reference: _ts_reference/components/box.ts
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from pi_tui.component import Component
from pi_tui.utils import apply_background_to_line, visible_width


@dataclass
class _RenderCache:
    """Cache for rendered output."""
    child_lines: list[str]
    width: int
    bg_sample: str | None
    lines: list[str]


class Box(Component):
    """
    Box component - a container that applies padding and background to all children.

    TypeScript Reference: _ts_reference/components/box.ts:Box
    """

    def __init__(
        self,
        padding_x: int = 1,
        padding_y: int = 1,
        bg_fn: Callable[[str], str] | None = None,
    ) -> None:
        self._padding_x = padding_x
        self._padding_y = padding_y
        self._bg_fn = bg_fn
        self._cache: _RenderCache | None = None
        self.children: list[Component] = []

    def add_child(self, component: Component) -> None:
        """Add a child component."""
        self.children.append(component)
        self._invalidate_cache()

    def remove_child(self, component: Component) -> None:
        """Remove a child component."""
        try:
            self.children.remove(component)
            self._invalidate_cache()
        except ValueError:
            pass

    def clear(self) -> None:
        """Remove all child components."""
        self.children.clear()
        self._invalidate_cache()

    def set_bg_fn(self, bg_fn: Callable[[str], str] | None) -> None:
        """Set the background function."""
        self._bg_fn = bg_fn

    def _invalidate_cache(self) -> None:
        """Clear the render cache."""
        self._cache = None

    def _match_cache(
        self, width: int, child_lines: list[str], bg_sample: str | None
    ) -> bool:
        """Check if cache is still valid."""
        if self._cache is None:
            return False
        return (
            self._cache.width == width
            and self._cache.bg_sample == bg_sample
            and len(self._cache.child_lines) == len(child_lines)
            and all(
                self._cache.child_lines[i] == child_lines[i]
                for i in range(len(child_lines))
            )
        )

    def invalidate(self) -> None:
        """Invalidate this component and all children."""
        self._invalidate_cache()
        for child in self.children:
            child.invalidate()

    def _apply_bg(self, line: str, width: int) -> str:
        """Apply background to a line."""
        vis_len = visible_width(line)
        pad_needed = max(0, width - vis_len)
        padded = line + " " * pad_needed

        if self._bg_fn:
            return apply_background_to_line(padded, width, self._bg_fn)
        return padded

    def render(self, width: int) -> list[str]:
        """Render the box component."""
        if not self.children:
            return []

        content_width = max(1, width - self._padding_x * 2)
        left_pad = " " * self._padding_x

        child_lines: list[str] = []
        for child in self.children:
            lines = child.render(content_width)
            for line in lines:
                child_lines.append(left_pad + line)

        if not child_lines:
            return []

        bg_sample = self._bg_fn("test") if self._bg_fn else None

        if self._match_cache(width, child_lines, bg_sample):
            assert self._cache is not None
            return self._cache.lines

        result: list[str] = []

        for _ in range(self._padding_y):
            result.append(self._apply_bg("", width))

        for line in child_lines:
            result.append(self._apply_bg(line, width))

        for _ in range(self._padding_y):
            result.append(self._apply_bg("", width))

        self._cache = _RenderCache(
            child_lines=child_lines,
            width=width,
            bg_sample=bg_sample,
            lines=result,
        )

        return result
