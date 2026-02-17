"""
TruncatedText component - text that truncates to fit viewport width.

TypeScript Reference: _ts_reference/components/truncated-text.ts
"""

from __future__ import annotations

from pi_tui.component import Component
from pi_tui.utils import truncate_to_width, visible_width


class TruncatedText(Component):
    """
    Text component that truncates to fit viewport width.
    
    TypeScript Reference: _ts_reference/components/truncated-text.ts:TruncatedText
    """

    def __init__(
        self,
        text: str = "",
        padding_x: int = 0,
        padding_y: int = 0,
    ) -> None:
        self._text = text
        self._padding_x = padding_x
        self._padding_y = padding_y

    def set_text(self, text: str) -> None:
        """Set the text content."""
        self._text = text

    def invalidate(self) -> None:
        pass

    def render(self, width: int) -> list[str]:
        result: list[str] = []

        empty_line = " " * width

        for _ in range(self._padding_y):
            result.append(empty_line)

        available_width = max(1, width - self._padding_x * 2)

        single_line_text = self._text
        newline_index = self._text.find("\n")
        if newline_index != -1:
            single_line_text = self._text[:newline_index]

        display_text = truncate_to_width(single_line_text, available_width)

        left_padding = " " * self._padding_x
        right_padding = " " * self._padding_x
        line_with_padding = left_padding + display_text + right_padding

        line_visible_width = visible_width(line_with_padding)
        padding_needed = max(0, width - line_visible_width)
        final_line = line_with_padding + " " * padding_needed

        result.append(final_line)

        for _ in range(self._padding_y):
            result.append(empty_line)

        return result
