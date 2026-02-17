"""
TUI - Main class for managing terminal UI with differential rendering

TypeScript Reference: _ts_reference/tui.ts (entire file, ~600 lines)
See MAPPING.md for detailed mapping.

This is the core of pi-tui. Key sections in the TypeScript source:
- Lines 20-50: Component and Focusable interfaces
- Lines 100-130: Container class
- Lines 130-280: Overlay system
- Lines 280-450: Rendering pipeline
- Lines 450-600: Input handling
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, TypedDict, Callable

if TYPE_CHECKING:
    from pi_tui.component import Component
    from pi_tui.terminal import Terminal

from pi_tui.container import Container

# =============================================================================
# Constants
# =============================================================================

CURSOR_MARKER = "\x1b_pi:c\x07"
"""
Cursor position marker - APC sequence.
This is a zero-width escape sequence that terminals ignore.
Components emit this at the cursor position when focused.
TUI finds and strips this marker, then positions the hardware cursor there.

TypeScript Reference: _ts_reference/tui.ts:CURSOR_MARKER
"""

# =============================================================================
# Type Definitions
# =============================================================================

OverlayAnchor = Literal[
    "center",
    "top-left",
    "top-right",
    "bottom-left",
    "bottom-right",
    "top-center",
    "bottom-center",
    "left-center",
    "right-center",
]
"""Anchor position for overlays. TypeScript Reference: _ts_reference/tui.ts:OverlayAnchor"""


class OverlayMargin(TypedDict, total=False):
    """Margin configuration for overlays. TypeScript Reference: _ts_reference/tui.ts:OverlayMargin"""
    top: int
    right: int
    bottom: int
    left: int


SizeValue = int | str
"""Value that can be absolute (number) or percentage (string like "50%"). TypeScript Reference: _ts_reference/tui.ts:SizeValue"""


class OverlayOptions(TypedDict, total=False):
    """
    Options for overlay positioning and sizing.
    
    TypeScript Reference: _ts_reference/tui.ts:OverlayOptions
    """
    width: SizeValue
    minWidth: int
    maxHeight: SizeValue
    anchor: OverlayAnchor
    offsetX: int
    offsetY: int
    row: SizeValue
    col: SizeValue
    margin: OverlayMargin | int
    visible: Callable[[int, int], bool]


class OverlayHandle:
    """
    Handle returned by showOverlay for controlling the overlay.
    
    TypeScript Reference: _ts_reference/tui.ts:OverlayHandle
    """
    
    def __init__(
        self,
        hide: Callable[[], None],
        set_hidden: Callable[[bool], None],
        is_hidden: Callable[[], bool],
    ) -> None:
        self._hide = hide
        self._set_hidden = set_hidden
        self._is_hidden = is_hidden
    
    def hide(self) -> None:
        """Permanently remove the overlay (cannot be shown again)."""
        self._hide()
    
    def set_hidden(self, hidden: bool) -> None:
        """Temporarily hide or show the overlay."""
        self._set_hidden(hidden)
    
    def is_hidden(self) -> bool:
        """Check if overlay is temporarily hidden."""
        return self._is_hidden()


# =============================================================================
# TUI Class
# =============================================================================

class TUI(Container):
    """
    TUI - Main class for managing terminal UI with differential rendering.
    
    TypeScript Reference: _ts_reference/tui.ts:TUI class (lines 130+)
    
    Features:
    - Differential rendering (3 strategies)
    - CSI 2026 synchronized output
    - Overlay system
    - Focus management
    - Input handling
    """
    
    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------
    
    def __init__(
        self,
        terminal: Terminal,
        show_hardware_cursor: bool = False,
    ) -> None:
        """
        Initialize TUI.
        
        Args:
            terminal: Terminal implementation
            show_hardware_cursor: Whether to show hardware cursor for IME
        """
        super().__init__()
        
        self.terminal = terminal
        self._show_hardware_cursor = show_hardware_cursor
        
        # Rendering state
        self._previous_lines: list[str] = []
        self._previous_width = 0
        self._render_requested = False
        self._stopped = False
        self._full_redraw_count = 0
        
        # Focus state
        self._focused_component: Component | None = None
        
        # Overlay stack
        self._overlay_stack: list[dict] = []
        
        # Input listeners
        self._input_listeners: set[Callable[[str], dict | None]] = set()
        
        # Debug callback
        self.on_debug: Callable[[], None] | None = None
    
    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------
    
    @property
    def full_redraws(self) -> int:
        """Number of full redraws performed."""
        return self._full_redraw_count
    
    # -------------------------------------------------------------------------
    # Cursor Management
    # -------------------------------------------------------------------------
    
    def get_show_hardware_cursor(self) -> bool:
        return self._show_hardware_cursor
    
    def set_show_hardware_cursor(self, enabled: bool) -> None:
        if self._show_hardware_cursor == enabled:
            return
        self._show_hardware_cursor = enabled
        if not enabled:
            self.terminal.hide_cursor()
        self.request_render()
    
    # -------------------------------------------------------------------------
    # Focus Management
    # -------------------------------------------------------------------------
    
    def set_focus(self, component: Component | None) -> None:
        """
        Set focus to a component.
        
        TypeScript Reference: _ts_reference/tui.ts:setFocus
        """
        from pi_tui.component import Focusable, is_focusable
        
        # Clear focused flag on old component
        if self._focused_component is not None and is_focusable(self._focused_component):
            focusable: Focusable = self._focused_component  # type: ignore[assignment]
            focusable.focused = False
        
        self._focused_component = component
        
        # Set focused flag on new component
        if component is not None and is_focusable(component):
            focusable = component  # type: ignore[assignment]
            focusable.focused = True
    
    # -------------------------------------------------------------------------
    # Overlay System
    # -------------------------------------------------------------------------
    
    def show_overlay(
        self,
        component: Component,
        options: OverlayOptions | None = None,
    ) -> OverlayHandle:
        """
        Show an overlay component.
        
        TypeScript Reference: _ts_reference/tui.ts:showOverlay
        
        Args:
            component: Component to show as overlay
            options: Overlay positioning options
            
        Returns:
            Handle to control the overlay
        """
        entry = {
            "component": component,
            "options": options,
            "pre_focus": self._focused_component,
            "hidden": False,
        }
        self._overlay_stack.append(entry)
        
        # Focus the overlay if visible
        if self._is_overlay_visible(entry):
            self.set_focus(component)
        
        self.terminal.hide_cursor()
        self.request_render()
        
        def hide() -> None:
            try:
                idx = self._overlay_stack.index(entry)
                self._overlay_stack.pop(idx)
                # Restore focus
                if self._focused_component == component:
                    top_visible = self._get_topmost_visible_overlay()
                    self.set_focus(top_visible["component"] if top_visible else entry["pre_focus"])
                if not self._overlay_stack:
                    self.terminal.hide_cursor()
                self.request_render()
            except ValueError:
                pass
        
        def set_hidden(hidden: bool) -> None:
            if entry["hidden"] == hidden:
                return
            entry["hidden"] = hidden
            if hidden:
                if self._focused_component == component:
                    top_visible = self._get_topmost_visible_overlay()
                    self.set_focus(top_visible["component"] if top_visible else entry["pre_focus"])
            else:
                if self._is_overlay_visible(entry):
                    self.set_focus(component)
            self.request_render()
        
        def is_hidden() -> bool:
            return entry["hidden"]
        
        return OverlayHandle(hide, set_hidden, is_hidden)
    
    def hide_overlay(self) -> None:
        """Hide the topmost overlay. TypeScript Reference: _ts_reference/tui.ts:hideOverlay"""
        if not self._overlay_stack:
            return
        entry = self._overlay_stack.pop()
        top_visible = self._get_topmost_visible_overlay()
        self.set_focus(top_visible["component"] if top_visible else entry["pre_focus"])
        if not self._overlay_stack:
            self.terminal.hide_cursor()
        self.request_render()
    
    def has_overlay(self) -> bool:
        """Check if there are any visible overlays."""
        return any(self._is_overlay_visible(e) for e in self._overlay_stack)
    
    def _is_overlay_visible(self, entry: dict) -> bool:
        """Check if an overlay entry is visible."""
        if entry["hidden"]:
            return False
        options = entry.get("options")
        if options and "visible" in options:
            return options["visible"](self.terminal.columns, self.terminal.rows)
        return True
    
    def _get_topmost_visible_overlay(self) -> dict | None:
        """Find the topmost visible overlay."""
        for i in range(len(self._overlay_stack) - 1, -1, -1):
            if self._is_overlay_visible(self._overlay_stack[i]):
                return self._overlay_stack[i]
        return None
    
    # -------------------------------------------------------------------------
    # Lifecycle
    # -------------------------------------------------------------------------
    
    def start(self) -> None:
        """Start the TUI. TypeScript Reference: _ts_reference/tui.ts:start"""
        self._stopped = False
        self.terminal.start(
            lambda data: self._handle_input(data),
            lambda: self.request_render(),
        )
        self.terminal.hide_cursor()
        self.request_render()
    
    def stop(self) -> None:
        """Stop the TUI. TypeScript Reference: _ts_reference/tui.ts:stop"""
        self._stopped = True
        self.terminal.show_cursor()
        self.terminal.stop()
    
    # -------------------------------------------------------------------------
    # Rendering
    # -------------------------------------------------------------------------
    
    def request_render(self, force: bool = False) -> None:
        """Request a render. TypeScript Reference: _ts_reference/tui.ts:requestRender"""
        if force:
            self._previous_lines = []
            self._previous_width = -1
        if self._render_requested:
            return
        self._render_requested = True
        # Schedule render on next tick
        # TODO: Use asyncio or similar
        self._do_render()
    
    def _do_render(self) -> None:
        """Perform the actual rendering. TypeScript Reference: _ts_reference/tui.ts:doRender"""
        if self._stopped:
            return
        
        width = self.terminal.columns
        # height = self.terminal.rows
        
        # Render all components
        new_lines = self.render(width)
        
        # Composite overlays
        if self._overlay_stack:
            new_lines = self._composite_overlays(new_lines, width)
        
        # Detect width change
        width_changed = self._previous_width != 0 and self._previous_width != width
        
        # First render
        if not self._previous_lines and not width_changed:
            self._full_render(new_lines, clear=False)
            return
        
        # Width changed - full re-render
        if width_changed:
            self._full_render(new_lines, clear=True)
            return
        
        # Partial update
        self._partial_render(new_lines)
    
    def _full_render(self, lines: list[str], clear: bool) -> None:
        """Full render with optional clear. TypeScript Reference: _ts_reference/tui.ts:fullRender"""
        buffer = "\x1b[?2026h"  # Begin synchronized output
        if clear:
            buffer += "\x1b[3J\x1b[2J\x1b[H"  # Clear scrollback, screen, home
        buffer += "\r\n".join(lines)
        buffer += "\x1b[?2026l"  # End synchronized output
        self.terminal.write(buffer)
        
        self._previous_lines = lines
        self._previous_width = self.terminal.columns
        self._full_redraw_count = getattr(self, "_full_redraw_count", 0) + 1
    
    def _partial_render(self, new_lines: list[str]) -> None:
        """Partial render with differential update. TypeScript Reference: _ts_reference/tui.ts:partialRender"""
        # Find changed lines
        first_changed = -1
        last_changed = -1
        max_lines = max(len(new_lines), len(self._previous_lines))
        
        for i in range(max_lines):
            old_line = self._previous_lines[i] if i < len(self._previous_lines) else ""
            new_line = new_lines[i] if i < len(new_lines) else ""
            if old_line != new_line:
                if first_changed == -1:
                    first_changed = i
                last_changed = i
        
        # No changes
        if first_changed == -1:
            self._previous_lines = new_lines
            return
        
        # Render only changed lines
        buffer = "\x1b[?2026h"
        # TODO: Move cursor to first_changed and render
        for i in range(first_changed, last_changed + 1):
            if i > first_changed:
                buffer += "\r\n"
            buffer += new_lines[i] if i < len(new_lines) else ""
        buffer += "\x1b[?2026l"
        
        self.terminal.write(buffer)
        self._previous_lines = new_lines
    
    def _composite_overlays(self, lines: list[str], width: int) -> list[str]:
        """Composite overlays onto base lines. TypeScript Reference: _ts_reference/tui.ts:compositeOverlays"""
        if not self._overlay_stack:
            return lines

        result = list(lines)
        term_height = self.terminal.rows

        for entry in self._overlay_stack:
            if not self._is_overlay_visible(entry):
                continue

            component = entry["component"]
            options: OverlayOptions = entry.get("options") or {}

            overlay_width = self._resolve_overlay_width(options, width)
            overlay_lines = component.render(overlay_width)

            max_height = self._resolve_max_height(options, term_height)
            if max_height is not None and len(overlay_lines) > max_height:
                overlay_lines = overlay_lines[:max_height]

            row, col = self._resolve_overlay_position(
                options, overlay_width, len(overlay_lines), width, term_height
            )

            for i, overlay_line in enumerate(overlay_lines):
                idx = row + i
                if 0 <= idx < len(result):
                    result[idx] = self._composite_line_at(
                        result[idx], overlay_line, col, overlay_width, width
                    )
                elif idx >= len(result):
                    while len(result) < idx:
                        result.append("")
                    base_line = ""
                    result.append(self._composite_line_at(
                        base_line, overlay_line, col, overlay_width, width
                    ))

        return result

    def _resolve_overlay_width(self, options: OverlayOptions, term_width: int) -> int:
        width_opt = options.get("width", 80)
        if isinstance(width_opt, str) and width_opt.endswith("%"):
            pct = int(width_opt[:-1])
            width = term_width * pct // 100
        else:
            width = int(width_opt)
        min_width = options.get("minWidth", 1)
        return max(min_width, min(width, term_width))

    def _resolve_max_height(self, options: OverlayOptions, term_height: int) -> int | None:
        max_h = options.get("maxHeight")
        if max_h is None:
            return None
        if isinstance(max_h, str) and max_h.endswith("%"):
            pct = int(max_h[:-1])
            return term_height * pct // 100
        return int(max_h)

    def _resolve_overlay_position(
        self,
        options: OverlayOptions,
        overlay_width: int,
        overlay_height: int,
        term_width: int,
        term_height: int,
    ) -> tuple[int, int]:
        anchor = options.get("anchor", "center")

        margin = options.get("margin", 0)
        if isinstance(margin, int):
            margin_top = margin_right = margin_bottom = margin_left = margin
        else:
            margin_top = margin.get("top", 0)
            margin_right = margin.get("right", 0)
            margin_bottom = margin.get("bottom", 0)
            margin_left = margin.get("left", 0)

        avail_width = term_width - margin_left - margin_right
        avail_height = term_height - margin_top - margin_bottom

        if "row" in options:
            row_opt = options["row"]
            if isinstance(row_opt, str) and row_opt.endswith("%"):
                pct = int(row_opt[:-1])
                row = margin_top + avail_height * pct // 100
            else:
                row = int(row_opt)
        else:
            if anchor in ("top-left", "top-center", "top-right"):
                row = margin_top
            elif anchor in ("bottom-left", "bottom-center", "bottom-right"):
                row = margin_top + avail_height - overlay_height
            else:
                row = margin_top + (avail_height - overlay_height) // 2

        if "col" in options:
            col_opt = options["col"]
            if isinstance(col_opt, str) and col_opt.endswith("%"):
                pct = int(col_opt[:-1])
                col = margin_left + avail_width * pct // 100
            else:
                col = int(col_opt)
        else:
            if anchor in ("top-left", "left-center", "bottom-left"):
                col = margin_left
            elif anchor in ("top-right", "right-center", "bottom-right"):
                col = margin_left + avail_width - overlay_width
            else:
                col = margin_left + (avail_width - overlay_width) // 2

        row += options.get("offsetY", 0)
        col += options.get("offsetX", 0)

        row = max(margin_top, min(row, term_height - margin_bottom - overlay_height))
        col = max(margin_left, min(col, term_width - margin_right - overlay_width))

        return row, col

    def _composite_line_at(
        self,
        base_line: str,
        overlay_line: str,
        start_col: int,
        overlay_width: int,
        total_width: int,
    ) -> str:
        from pi_tui.utils import visible_width

        before = " " * start_col

        overlay_vis_width = visible_width(overlay_line)
        if overlay_vis_width < overlay_width:
            overlay_line += " " * (overlay_width - overlay_vis_width)

        after_width = total_width - start_col - overlay_width
        after = " " * max(0, after_width)

        return before + overlay_line + after
    
    # -------------------------------------------------------------------------
    # Input Handling
    # -------------------------------------------------------------------------
    
    def add_input_listener(
        self,
        listener: Callable[[str], dict | None],
    ) -> Callable[[], None]:
        """Add an input listener. Returns removal function."""
        self._input_listeners.add(listener)
        return lambda: self._input_listeners.discard(listener)
    
    def _handle_input(self, data: str) -> None:
        """Handle input data. TypeScript Reference: _ts_reference/tui.ts:handleInput"""
        # Process input listeners
        current = data
        for listener in self._input_listeners:
            result = listener(current)
            if result and result.get("consume"):
                return
            if result and "data" in result:
                current = result["data"]
        
        if not current:
            return
        
        # Pass to focused component
        if self._focused_component and hasattr(self._focused_component, "handle_input"):
            self._focused_component.handle_input(current)
            self.request_render()
