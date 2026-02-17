"""
CancellableLoader component - loader that can be cancelled with Escape.

TypeScript Reference: _ts_reference/components/cancellable-loader.ts
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from pi_tui.tui import TUI

from pi_tui.components.loader import Loader
from pi_tui.keys import matches_key, Key


class CancellableLoader(Loader):
    """
    Loader that can be cancelled with Escape.
    
    TypeScript Reference: _ts_reference/components/cancellable-loader.ts:CancellableLoader
    """

    def __init__(
        self,
        tui: TUI,
        spinner_color_fn: Callable[[str], str],
        message_color_fn: Callable[[str], str],
        message: str = "Loading...",
    ) -> None:
        super().__init__(tui, spinner_color_fn, message_color_fn, message)
        self._aborted = False
        self.on_abort: Callable[[], None] | None = None

    @property
    def aborted(self) -> bool:
        """Whether the loader was aborted."""
        return self._aborted

    def handle_input(self, data: str) -> None:
        """Handle input - Escape aborts the loader."""
        if matches_key(data, Key.escape):
            self._aborted = True
            if self.on_abort:
                self.on_abort()
            return

    def dispose(self) -> None:
        """Stop the loader and clean up."""
        self.stop()
