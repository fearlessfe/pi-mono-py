"""
Input component - single-line text input with horizontal scrolling.

TypeScript Reference: _ts_reference/components/input.ts
"""

from __future__ import annotations

from typing import Callable

from pi_tui.component import Component
from pi_tui.keys import matches_key, Key
from pi_tui.utils import visible_width


CURSOR_MARKER = "\x1b_pi:c\x07"


class Input(Component):
    """
    Input component - single-line text input with horizontal scrolling.
    
    TypeScript Reference: _ts_reference/components/input.ts:Input
    """

    def __init__(
        self,
        value: str = "",
        prompt: str = "> ",
        on_submit: Callable[[str], None] | None = None,
        on_escape: Callable[[], None] | None = None,
    ) -> None:
        self._value = value
        self._cursor = len(value)
        self._prompt = prompt
        self._on_submit = on_submit
        self._on_escape = on_escape
        self.focused = False

        self._paste_buffer = ""
        self._is_in_paste = False

        self._undo_stack: list[tuple[str, int]] = []

    def get_value(self) -> str:
        """Get the current input value."""
        return self._value

    def set_value(self, value: str) -> None:
        """Set the input value."""
        self._value = value
        self._cursor = min(self._cursor, len(value))

    def _push_undo(self) -> None:
        """Push current state to undo stack."""
        self._undo_stack.append((self._value, self._cursor))

    def _undo(self) -> None:
        """Undo last change."""
        if not self._undo_stack:
            return
        self._value, self._cursor = self._undo_stack.pop()

    def handle_input(self, data: str) -> None:
        """Handle input data."""
        if "\x1b[200~" in data:
            self._is_in_paste = True
            self._paste_buffer = ""
            data = data.replace("\x1b[200~", "")

        if self._is_in_paste:
            self._paste_buffer += data
            end_index = self._paste_buffer.find("\x1b[201~")
            if end_index != -1:
                paste_content = self._paste_buffer[:end_index]
                self._handle_paste(paste_content)
                self._is_in_paste = False
                remaining = self._paste_buffer[end_index + 6:]
                self._paste_buffer = ""
                if remaining:
                    self.handle_input(remaining)
            return

        if matches_key(data, Key.escape):
            if self._on_escape:
                self._on_escape()
            return

        if matches_key(data, Key.ctrl("z")):
            self._undo()
            return

        if matches_key(data, Key.enter):
            if self._on_submit:
                self._on_submit(self._value)
            return

        if matches_key(data, Key.backspace):
            self._handle_backspace()
            return

        if matches_key(data, Key.delete):
            self._handle_forward_delete()
            return

        if matches_key(data, Key.left):
            if self._cursor > 0:
                self._cursor -= 1
            return

        if matches_key(data, Key.right):
            if self._cursor < len(self._value):
                self._cursor += 1
            return

        if matches_key(data, Key.ctrl("a")):
            self._cursor = 0
            return

        if matches_key(data, Key.ctrl("e")):
            self._cursor = len(self._value)
            return

        if matches_key(data, Key.ctrl("u")):
            if self._cursor > 0:
                self._push_undo()
                self._value = self._value[self._cursor:]
                self._cursor = 0
            return

        if matches_key(data, Key.ctrl("k")):
            if self._cursor < len(self._value):
                self._push_undo()
                self._value = self._value[:self._cursor]
            return

        if matches_key(data, Key.ctrl("w")):
            self._delete_word_backward()
            return

        code = ord(data[0]) if data else 0
        if code >= 32 and code != 127:
            self._insert_character(data)

    def _insert_character(self, char: str) -> None:
        """Insert a character at cursor position."""
        self._push_undo()
        self._value = self._value[:self._cursor] + char + self._value[self._cursor:]
        self._cursor += len(char)

    def _handle_backspace(self) -> None:
        """Handle backspace key."""
        if self._cursor > 0:
            self._push_undo()
            self._value = self._value[:self._cursor - 1] + self._value[self._cursor:]
            self._cursor -= 1

    def _handle_forward_delete(self) -> None:
        """Handle delete key."""
        if self._cursor < len(self._value):
            self._push_undo()
            self._value = self._value[:self._cursor] + self._value[self._cursor + 1:]

    def _delete_word_backward(self) -> None:
        """Delete word before cursor."""
        if self._cursor == 0:
            return
        self._push_undo()
        new_cursor = self._cursor
        while new_cursor > 0 and self._value[new_cursor - 1].isspace():
            new_cursor -= 1
        while new_cursor > 0 and not self._value[new_cursor - 1].isspace():
            new_cursor -= 1
        self._value = self._value[:new_cursor] + self._value[self._cursor:]
        self._cursor = new_cursor

    def _handle_paste(self, text: str) -> None:
        """Handle pasted text."""
        self._push_undo()
        clean_text = text.replace("\r\n", "").replace("\r", "").replace("\n", "")
        self._value = self._value[:self._cursor] + clean_text + self._value[self._cursor:]
        self._cursor += len(clean_text)

    def invalidate(self) -> None:
        pass

    def render(self, width: int) -> list[str]:
        """Render the input component."""
        prompt = self._prompt
        available_width = width - len(prompt)

        if available_width <= 0:
            return [prompt]

        visible_text = ""
        cursor_display = self._cursor

        if len(self._value) < available_width:
            visible_text = self._value
        else:
            scroll_width = available_width - 1 if self._cursor == len(self._value) else available_width
            half_width = scroll_width // 2

            if self._cursor < half_width:
                visible_text = self._value[:scroll_width]
                cursor_display = self._cursor
            elif self._cursor > len(self._value) - half_width:
                start = len(self._value) - scroll_width
                visible_text = self._value[start:]
                cursor_display = self._cursor - start
            else:
                start = self._cursor - half_width
                visible_text = self._value[start:start + scroll_width]
                cursor_display = half_width

        before_cursor = visible_text[:cursor_display]
        at_cursor = visible_text[cursor_display:cursor_display + 1] if cursor_display < len(visible_text) else " "
        after_cursor = visible_text[cursor_display + 1:] if cursor_display + 1 < len(visible_text) else ""

        marker = CURSOR_MARKER if self.focused else ""
        cursor_char = f"\x1b[7m{at_cursor}\x1b[27m"
        text_with_cursor = before_cursor + marker + cursor_char + after_cursor

        visual_length = visible_width(text_with_cursor)
        padding = " " * max(0, available_width - visual_length)
        line = prompt + text_with_cursor + padding

        return [line]
