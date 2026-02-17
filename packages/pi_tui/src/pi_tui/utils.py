"""
ANSI utility functions for pi-tui

TypeScript Reference: _ts_reference/utils.ts
See MAPPING.md for detailed mapping.

Key functions:
- visible_width: Calculate visible width ignoring ANSI codes
- truncate_to_width: Truncate text to width preserving ANSI
- wrap_text_with_ansi: Wrap text preserving ANSI sequences
"""

from __future__ import annotations

import re
from typing import Callable

try:
    from wcwidth import wcwidth  # type: ignore[import-untyped]
except ImportError:
    def wcwidth(c: str) -> int:
        return 1


# ANSI escape sequence patterns
ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;?]*[a-zA-Z]")
OSC_ESCAPE = re.compile(r"\x1b\][^\x07\x1b]*[\x07\x1b\\]")
APC_ESCAPE = re.compile(r"\x1b_[^\x07\x1b]*[\x07\x1b\\]")


def _strip_ansi(text: str) -> str:
    """Remove all ANSI/OSC/APC escape sequences from text."""
    text = ANSI_ESCAPE.sub("", text)
    text = OSC_ESCAPE.sub("", text)
    text = APC_ESCAPE.sub("", text)
    return text


def visible_width(text: str) -> int:
    """
    Calculate the visible width of text, ignoring ANSI codes.
    
    TypeScript Reference: _ts_reference/utils.ts:visibleWidth
    
    Args:
        text: Input text possibly containing ANSI codes
        
    Returns:
        Visible width in terminal columns
        
    Example:
        >>> visible_width("\x1b[31mHello\x1b[0m")
        5
    """
    clean = _strip_ansi(text)
    return sum(max(0, wcwidth(c)) for c in clean)


def truncate_to_width(
    text: str,
    max_width: int,
    ellipsis: str = "...",
    pad: bool = False,
) -> str:
    """
    Truncate text to max_width, preserving ANSI codes.
    
    TypeScript Reference: _ts_reference/utils.ts:truncateToWidth
    
    Args:
        text: Input text
        max_width: Maximum visible width
        ellipsis: String to append when truncated
        pad: Whether to pad with spaces if shorter
        
    Returns:
        Truncated text with ANSI codes preserved
    """
    if max_width <= 0:
        return ""
    
    total_width = visible_width(text)
    if total_width <= max_width:
        if pad and total_width < max_width:
            return text + (" " * (max_width - total_width))
        return text

    current_width = 0
    result = []
    ellipsis_width = visible_width(ellipsis)
    
    # If max_width is smaller than ellipsis, we can't really show ellipsis properly
    # but we'll follow the logic of showing it if possible.
    
    i = 0
    while i < len(text):
        # Check for ANSI sequence
        if text[i] == "\x1b":
            # Use extract_ansi_code to be consistent
            ansi_match = extract_ansi_code(text, i)
            if ansi_match:
                code, next_pos = ansi_match
                result.append(code)
                i = next_pos
                continue
        
        # Regular character
        char_width = max(0, wcwidth(text[i]))
        if current_width + char_width > max_width - ellipsis_width:
            result.append(ellipsis)
            current_width += ellipsis_width
            break
        
        result.append(text[i])
        current_width += char_width
        i += 1
    
    return "".join(result)



def wrap_text_with_ansi(text: str, width: int) -> list[str]:
    """
    Wrap text to specified width, preserving ANSI codes.
    
    TypeScript Reference: _ts_reference/utils.ts:wrapTextWithAnsi
    
    Args:
        text: Input text
        width: Maximum line width
        
    Returns:
        List of wrapped lines
    """
    if width <= 0:
        return [text]
    
    lines: list[str] = []
    current_line: list[str] = []
    current_width = 0
    active_styles: list[str] = []
    
    words = text.split(" ")
    
    for word in words:
        word_width = visible_width(word)
        
        if current_width + word_width + (1 if current_line else 0) <= width:
            if current_line:
                current_line.append(" ")
                current_width += 1
            current_line.append(word)
            current_width += word_width
        else:
            if current_line:
                lines.append("".join(current_line))
            current_line = [word]
            current_width = word_width
    
    if current_line:
        lines.append("".join(current_line))
    
    return lines if lines else [""]


def extract_ansi_code(text: str, pos: int) -> tuple[str, int] | None:
    """
    Extract ANSI code at position.
    
    TypeScript Reference: _ts_reference/utils.ts:extractAnsiCode
    
    Args:
        text: Input text
        pos: Position to check
        
    Returns:
        Tuple of (code, end_position) or None
    """
    if pos >= len(text) or text[pos] != "\x1b":
        return None
    
    i = pos + 1
    if i >= len(text):
        return None
    
    if text[i] == "[":
        # CSI sequence
        i += 1
        while i < len(text) and text[i] not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ":
            i += 1
        if i < len(text):
            return (text[pos:i+1], i + 1)
    elif text[i] == "]":
        # OSC sequence
        i += 1
        while i < len(text) and text[i] != "\x07":
            i += 1
        if i < len(text):
            return (text[pos:i+1], i + 1)
    
    return None


def slice_by_column(
    text: str,
    start_col: int,
    length: int,
    strict: bool = False,
) -> str:
    """
    Slice text by visual column position.
    
    TypeScript Reference: _ts_reference/utils.ts:sliceByColumn
    
    Args:
        text: Input text
        start_col: Starting column
        length: Number of columns to extract
        strict: Whether to exclude wide chars at boundary
        
    Returns:
        Sliced text
    """
    result: list[str] = []
    current_col = 0
    end_col = start_col + length
    
    i = 0
    while i < len(text):
        # Handle ANSI codes
        if text[i] == "\x1b":
            j = i + 1
            if j < len(text) and text[j] in "[_]":
                j += 1
                while j < len(text) and text[j] not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ\x07":
                    j += 1
                if j < len(text):
                    j += 1
                # Include ANSI codes for active regions
                if current_col >= start_col and current_col < end_col:
                    result.append(text[i:j])
            i = j
            continue
        
        char_width = wcwidth(text[i])
        char_end_col = current_col + char_width
        
        # Check if character is in range
        if char_end_col > start_col and current_col < end_col:
            if strict and char_end_col > end_col:
                # Skip wide char that crosses boundary
                pass
            else:
                result.append(text[i])
        
        current_col = char_end_col
        i += 1
    
    return "".join(result)


def apply_background_to_line(
    line: str,
    width: int,
    bg_fn: Callable[[str], str] | None,
) -> str:
    """
    Apply background color function to a line.
    
    TypeScript Reference: _ts_reference/utils.ts:applyBackgroundToLine
    
    Args:
        line: Input line
        width: Target width
        bg_fn: Function that takes text and returns styled text
        
    Returns:
        Line with background applied
    """
    if bg_fn is None:
        return line
    
    line_width = visible_width(line)
    if line_width < width:
        line += " " * (width - line_width)
    
    return bg_fn(line)
