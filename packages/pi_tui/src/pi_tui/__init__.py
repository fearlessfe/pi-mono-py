"""
pi-tui: Terminal UI library with differential rendering

Python port of @mariozechner/pi-tui from the pi-mono monorepo.

TypeScript Reference: _ts_reference/tui.ts, _ts_reference/index.ts
"""

from pi_tui.component import Component, Focusable, is_focusable
from pi_tui.container import Container
from pi_tui.tui import (
    TUI,
    CURSOR_MARKER,
    OverlayAnchor,
    OverlayHandle,
    OverlayMargin,
    OverlayOptions,
    SizeValue,
)
from pi_tui.terminal import Terminal, ProcessTerminal
from pi_tui.keys import (
    Key,
    KeyId,
    KeyEventType,
    parse_key,
    matches_key,
    is_key_release,
    is_key_repeat,
)
from pi_tui.stdin_buffer import StdinBuffer, StdinBufferOptions
from pi_tui.utils import (
    visible_width,
    truncate_to_width,
    wrap_text_with_ansi,
)

from pi_tui.components import (
    Text,
    Box,
    TruncatedText,
    Spacer,
    Loader,
    CancellableLoader,
    Input,
    SelectList,
    SelectItem,
    DefaultSelectListTheme,
)

__all__ = [
    "Component",
    "Focusable",
    "is_focusable",
    "Container",
    "TUI",
    "CURSOR_MARKER",
    "Terminal",
    "ProcessTerminal",
    "Key",
    "KeyId",
    "KeyEventType",
    "parse_key",
    "matches_key",
    "is_key_release",
    "is_key_repeat",
    "StdinBuffer",
    "StdinBufferOptions",
    "visible_width",
    "truncate_to_width",
    "wrap_text_with_ansi",
    "OverlayAnchor",
    "OverlayHandle",
    "OverlayMargin",
    "OverlayOptions",
    "SizeValue",
    "Text",
    "Box",
    "TruncatedText",
    "Spacer",
    "Loader",
    "CancellableLoader",
    "Input",
    "SelectList",
    "SelectItem",
    "DefaultSelectListTheme",
]
