"""
Spacer component - renders empty lines.

TypeScript Reference: _ts_reference/components/spacer.ts
"""

from __future__ import annotations

from pi_tui.component import Component


class Spacer(Component):
    """
    Spacer component that renders empty lines.
    
    TypeScript Reference: _ts_reference/components/spacer.ts:Spacer
    """

    def __init__(self, lines: int = 1) -> None:
        self._lines = lines

    def set_lines(self, lines: int) -> None:
        """Set the number of empty lines."""
        self._lines = lines

    def invalidate(self) -> None:
        pass

    def render(self, width: int) -> list[str]:
        result: list[str] = []
        for _ in range(self._lines):
            result.append("")
        return result
