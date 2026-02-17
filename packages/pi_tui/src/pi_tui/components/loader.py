"""
Loader component - spinning animation loader.

TypeScript Reference: _ts_reference/components/loader.ts
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from pi_tui.tui import TUI

from pi_tui.components.text import Text


class Loader(Text):
    """
    Loader component that updates with spinning animation.
    
    TypeScript Reference: _ts_reference/components/loader.ts:Loader
    """

    FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def __init__(
        self,
        tui: TUI,
        spinner_color_fn: Callable[[str], str],
        message_color_fn: Callable[[str], str],
        message: str = "Loading...",
    ) -> None:
        super().__init__("", padding_x=1, padding_y=0)
        self._tui = tui
        self._spinner_color_fn = spinner_color_fn
        self._message_color_fn = message_color_fn
        self._message = message
        self._current_frame = 0
        self._task: asyncio.Task | None = None
        self._running = False

    def render(self, width: int) -> list[str]:
        return ["", *super().render(width)]

    def start(self) -> None:
        """Start the loader animation."""
        if self._running:
            return
        self._running = True
        self._update_display()
        self._task = asyncio.create_task(self._animate())

    async def _animate(self) -> None:
        """Animation loop."""
        while self._running:
            await asyncio.sleep(0.08)
            self._current_frame = (self._current_frame + 1) % len(self.FRAMES)
            self._update_display()

    def stop(self) -> None:
        """Stop the loader animation."""
        self._running = False
        if self._task:
            self._task.cancel()
            self._task = None

    def set_message(self, message: str) -> None:
        """Set the loader message."""
        self._message = message
        self._update_display()

    def _update_display(self) -> None:
        """Update the display text."""
        frame = self.FRAMES[self._current_frame]
        self.set_text(f"{self._spinner_color_fn(frame)} {self._message_color_fn(self._message)}")
        if self._tui:
            self._tui.request_render()
