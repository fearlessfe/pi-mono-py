"""
SelectList component - interactive item selection list.

TypeScript Reference: _ts_reference/components/select-list.ts
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol

from pi_tui.component import Component
from pi_tui.keys import matches_key, Key
from pi_tui.utils import truncate_to_width


def _normalize_to_single_line(text: str) -> str:
    return text.replace("\r\n", " ").replace("\r", " ").replace("\n", " ").strip()


@dataclass
class SelectItem:
    """Item in a SelectList."""
    value: str
    label: str
    description: str | None = None


class SelectListTheme(Protocol):
    """Theme for SelectList rendering."""

    def selected_prefix(self, text: str) -> str: ...
    def selected_text(self, text: str) -> str: ...
    def description(self, text: str) -> str: ...
    def scroll_info(self, text: str) -> str: ...
    def no_match(self, text: str) -> str: ...


class DefaultSelectListTheme:
    """Default theme for SelectList."""

    def selected_prefix(self, text: str) -> str:
        return text

    def selected_text(self, text: str) -> str:
        return f"\x1b[1m{text}\x1b[22m"

    def description(self, text: str) -> str:
        return f"\x1b[90m{text}\x1b[39m"

    def scroll_info(self, text: str) -> str:
        return f"\x1b[90m{text}\x1b[39m"

    def no_match(self, text: str) -> str:
        return f"\x1b[90m{text}\x1b[39m"


class SelectList(Component):
    """
    SelectList component - interactive item selection list.
    
    TypeScript Reference: _ts_reference/components/select-list.ts:SelectList
    """

    def __init__(
        self,
        items: list[SelectItem],
        max_visible: int = 5,
        theme: SelectListTheme | None = None,
    ) -> None:
        self._items = items
        self._filtered_items = items
        self._selected_index = 0
        self._max_visible = max_visible
        self._theme = theme or DefaultSelectListTheme()

        self.on_select: Callable[[SelectItem], None] | None = None
        self.on_cancel: Callable[[], None] | None = None
        self.on_selection_change: Callable[[SelectItem], None] | None = None

    def set_filter(self, filter_text: str) -> None:
        """Filter items by value prefix."""
        self._filtered_items = [
            item for item in self._items
            if item.value.lower().startswith(filter_text.lower())
        ]
        self._selected_index = 0

    def set_selected_index(self, index: int) -> None:
        """Set the selected index."""
        self._selected_index = max(0, min(index, len(self._filtered_items) - 1))

    def invalidate(self) -> None:
        pass

    def render(self, width: int) -> list[str]:
        lines: list[str] = []

        if not self._filtered_items:
            lines.append(self._theme.no_match("  No matching commands"))
            return lines

        start_index = max(
            0,
            min(
                self._selected_index - self._max_visible // 2,
                len(self._filtered_items) - self._max_visible,
            ),
        )
        end_index = min(start_index + self._max_visible, len(self._filtered_items))

        for i in range(start_index, end_index):
            item = self._filtered_items[i]
            if not item:
                continue

            is_selected = i == self._selected_index
            description = _normalize_to_single_line(item.description) if item.description else None

            if is_selected:
                prefix_width = 2
                display_value = item.label or item.value

                if description and width > 40:
                    max_value_width = min(30, width - prefix_width - 4)
                    truncated_value = truncate_to_width(display_value, max_value_width, "")
                    spacing = " " * max(1, 32 - len(truncated_value))

                    description_start = prefix_width + len(truncated_value) + len(spacing)
                    remaining_width = width - description_start - 2

                    if remaining_width > 10:
                        truncated_desc = truncate_to_width(description, remaining_width, "")
                        line = self._theme.selected_text(f"→ {truncated_value}{spacing}{truncated_desc}")
                    else:
                        max_width = width - prefix_width - 2
                        line = self._theme.selected_text(f"→ {truncate_to_width(display_value, max_width, '')}")
                else:
                    max_width = width - prefix_width - 2
                    line = self._theme.selected_text(f"→ {truncate_to_width(display_value, max_width, '')}")
            else:
                display_value = item.label or item.value
                prefix = "  "

                if description and width > 40:
                    max_value_width = min(30, width - len(prefix) - 4)
                    truncated_value = truncate_to_width(display_value, max_value_width, "")
                    spacing = " " * max(1, 32 - len(truncated_value))

                    description_start = len(prefix) + len(truncated_value) + len(spacing)
                    remaining_width = width - description_start - 2

                    if remaining_width > 10:
                        truncated_desc = truncate_to_width(description, remaining_width, "")
                        desc_text = self._theme.description(spacing + truncated_desc)
                        line = prefix + truncated_value + desc_text
                    else:
                        max_width = width - len(prefix) - 2
                        line = prefix + truncate_to_width(display_value, max_width, "")
                else:
                    max_width = width - len(prefix) - 2
                    line = prefix + truncate_to_width(display_value, max_width, "")

            lines.append(line)

        if start_index > 0 or end_index < len(self._filtered_items):
            scroll_text = f"  ({self._selected_index + 1}/{len(self._filtered_items)})"
            lines.append(self._theme.scroll_info(truncate_to_width(scroll_text, width - 2, "")))

        return lines

    def handle_input(self, data: str) -> None:
        if matches_key(data, Key.up):
            if self._selected_index == 0:
                self._selected_index = len(self._filtered_items) - 1
            else:
                self._selected_index -= 1
            self._notify_selection_change()
        elif matches_key(data, Key.down):
            if self._selected_index == len(self._filtered_items) - 1:
                self._selected_index = 0
            else:
                self._selected_index += 1
            self._notify_selection_change()
        elif matches_key(data, Key.enter):
            item = self._filtered_items[self._selected_index] if self._filtered_items else None
            if item and self.on_select:
                self.on_select(item)
        elif matches_key(data, Key.escape):
            if self.on_cancel:
                self.on_cancel()

    def _notify_selection_change(self) -> None:
        item = self._filtered_items[self._selected_index] if self._filtered_items else None
        if item and self.on_selection_change:
            self.on_selection_change(item)

    def get_selected_item(self) -> SelectItem | None:
        """Get the currently selected item."""
        if self._filtered_items and 0 <= self._selected_index < len(self._filtered_items):
            return self._filtered_items[self._selected_index]
        return None
