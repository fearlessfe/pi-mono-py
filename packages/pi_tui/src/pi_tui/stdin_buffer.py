"""
StdinBuffer buffers input and emits complete sequences.

This is necessary because stdin data events can arrive in partial chunks,
especially for escape sequences like mouse events. Without buffering,
partial sequences can be misinterpreted as regular keypresses.

For example, the mouse SGR sequence `\\x1b[<35;20;5m` might arrive as:
- Event 1: `\\x1b`
- Event 2: `[<35`
- Event 3: `;20;5m`

The buffer accumulates these until a complete sequence is detected.
Call the `process()` method to feed input data.

Based on code from OpenTUI (https://github.com/anomalyco/opentui)
MIT License - Copyright (c) 2025 opentui

TypeScript Reference: _ts_reference/stdin-buffer.ts
"""

from __future__ import annotations

import asyncio
from typing import Callable, Literal
from dataclasses import dataclass, field


ESC = "\x1b"
BRACKETED_PASTE_START = "\x1b[200~"
BRACKETED_PASTE_END = "\x1b[201~"

SequenceStatus = Literal["complete", "incomplete", "not-escape"]


def _is_complete_csi_sequence(data: str) -> Literal["complete", "incomplete"]:
    """Check if CSI sequence is complete.

    CSI sequences: ESC [ ... followed by a final byte (0x40-0x7E)
    """
    if not data.startswith(f"{ESC}["):
        return "complete"

    # Need at least ESC [ and one more character
    if len(data) < 3:
        return "incomplete"

    payload = data[2:]

    # CSI sequences end with a byte in the range 0x40-0x7E (@-~)
    last_char = payload[-1]
    last_char_code = ord(last_char)

    if 0x40 <= last_char_code <= 0x7E:
        # Special handling for SGR mouse sequences
        # Format: ESC[<B;X;Ym or ESC[<B;X;YM
        if payload.startswith("<"):
            # Must have format: <digits;digits;digits[Mm]
            import re
            if re.match(r"^<\d+;\d+;\d+[Mm]$", payload):
                return "complete"
            # If it ends with M or m but doesn't match the pattern, still incomplete
            if last_char in ("M", "m"):
                parts = payload[1:-1].split(";")
                if len(parts) == 3 and all(p.isdigit() for p in parts):
                    return "complete"
            return "incomplete"

        return "complete"

    return "incomplete"


def _is_complete_osc_sequence(data: str) -> Literal["complete", "incomplete"]:
    """Check if OSC sequence is complete.

    OSC sequences: ESC ] ... ST (where ST is ESC \\ or BEL)
    """
    if not data.startswith(f"{ESC}]"):
        return "complete"

    # OSC sequences end with ST (ESC \\) or BEL (\\x07)
    if data.endswith(f"{ESC}\\") or data.endswith("\x07"):
        return "complete"

    return "incomplete"


def _is_complete_dcs_sequence(data: str) -> Literal["complete", "incomplete"]:
    """Check if DCS (Device Control String) sequence is complete.

    DCS sequences: ESC P ... ST (where ST is ESC \\)
    Used for XTVersion responses like ESC P >| ... ESC \\
    """
    if not data.startswith(f"{ESC}P"):
        return "complete"

    # DCS sequences end with ST (ESC \\)
    if data.endswith(f"{ESC}\\"):
        return "complete"

    return "incomplete"


def _is_complete_apc_sequence(data: str) -> Literal["complete", "incomplete"]:
    """Check if APC (Application Program Command) sequence is complete.

    APC sequences: ESC _ ... ST (where ST is ESC \\)
    Used for Kitty graphics responses like ESC _ G ... ESC \\
    """
    if not data.startswith(f"{ESC}_"):
        return "complete"

    # APC sequences end with ST (ESC \\)
    if data.endswith(f"{ESC}\\"):
        return "complete"

    return "incomplete"


def is_complete_sequence(data: str) -> SequenceStatus:
    """Check if a string is a complete escape sequence or needs more data."""
    if not data.startswith(ESC):
        return "not-escape"

    if len(data) == 1:
        return "incomplete"

    after_esc = data[1:]

    # CSI sequences: ESC [
    if after_esc.startswith("["):
        # Check for old-style mouse sequence: ESC[M + 3 bytes
        if after_esc.startswith("[M"):
            # Old-style mouse needs ESC[M + 3 bytes = 6 total
            return "complete" if len(data) >= 6 else "incomplete"
        return _is_complete_csi_sequence(data)

    # OSC sequences: ESC ]
    if after_esc.startswith("]"):
        return _is_complete_osc_sequence(data)

    # DCS sequences: ESC P ... ESC \\
    if after_esc.startswith("P"):
        return _is_complete_dcs_sequence(data)

    # APC sequences: ESC _ ... ESC \\
    if after_esc.startswith("_"):
        return _is_complete_apc_sequence(data)

    # SS3 sequences: ESC O
    if after_esc.startswith("O"):
        # ESC O followed by a single character
        return "complete" if len(after_esc) >= 2 else "incomplete"

    # Meta key sequences: ESC followed by a single character
    if len(after_esc) == 1:
        return "complete"

    # Unknown escape sequence - treat as complete
    return "complete"


@dataclass
class ExtractResult:
    """Result of extracting complete sequences from buffer."""
    sequences: list[str] = field(default_factory=list)
    remainder: str = ""


def extract_complete_sequences(buffer: str) -> ExtractResult:
    """Split accumulated buffer into complete sequences."""
    sequences: list[str] = []
    pos = 0

    while pos < len(buffer):
        remaining = buffer[pos:]

        # Try to extract a sequence starting at this position
        if remaining.startswith(ESC):
            # Find the end of this escape sequence
            seq_end = 1
            while seq_end <= len(remaining):
                candidate = remaining[:seq_end]
                status = is_complete_sequence(candidate)

                if status == "complete":
                    sequences.append(candidate)
                    pos += seq_end
                    break
                elif status == "incomplete":
                    seq_end += 1
                else:
                    # Should not happen when starting with ESC
                    sequences.append(candidate)
                    pos += seq_end
                    break

            if seq_end > len(remaining):
                return ExtractResult(sequences=sequences, remainder=remaining)
        else:
            # Not an escape sequence - take a single character
            sequences.append(remaining[0])
            pos += 1

    return ExtractResult(sequences=sequences, remainder="")


@dataclass
class StdinBufferOptions:
    """Options for StdinBuffer."""
    timeout: float = 10.0  # Maximum time to wait for sequence completion (ms)


class StdinBuffer:
    """
    Buffers stdin input and emits complete sequences via callbacks.

    Handles partial escape sequences that arrive across multiple chunks.

    TypeScript Reference: _ts_reference/stdin-buffer.ts:StdinBuffer

    Usage:
        buffer = StdinBuffer()
        buffer.on_data = lambda data: print(f"Got: {data!r}")
        buffer.on_paste = lambda text: print(f"Paste: {text!r}")
        buffer.process(some_input_data)
    """

    def __init__(self, options: StdinBufferOptions | None = None) -> None:
        self._buffer: str = ""
        self._timeout_handle: asyncio.TimerHandle | None = None
        self._timeout_ms = (options.timeout if options else 10.0) / 1000.0
        self._paste_mode = False
        self._paste_buffer = ""

        # Callbacks
        self.on_data: Callable[[str], None] | None = None
        self.on_paste: Callable[[str], None] | None = None

    def _emit_data(self, data: str) -> None:
        """Emit data event."""
        if self.on_data:
            self.on_data(data)

    def _emit_paste(self, text: str) -> None:
        """Emit paste event."""
        if self.on_paste:
            self.on_paste(text)

    def _clear_timeout(self) -> None:
        """Clear any pending timeout."""
        if self._timeout_handle:
            self._timeout_handle.cancel()
            self._timeout_handle = None

    def _schedule_flush(self) -> None:
        """Schedule a flush after timeout."""
        async def _do_flush() -> None:
            flushed = self.flush()
            for sequence in flushed:
                self._emit_data(sequence)

        loop = asyncio.get_event_loop()
        self._timeout_handle = loop.call_later(
            self._timeout_ms,
            lambda: asyncio.create_task(_do_flush())
        )

    def process(self, data: str | bytes) -> None:
        """
        Process input data.

        Args:
            data: Input data as string or bytes
        """
        # Clear any pending timeout
        self._clear_timeout()

        # Handle high-byte conversion (for compatibility with parseKeypress)
        # If buffer has single byte > 127, convert to ESC + (byte - 128)
        if isinstance(data, bytes):
            if len(data) == 1 and data[0] > 127:
                byte = data[0] - 128
                data = f"{ESC}{chr(byte)}"
            else:
                data = data.decode("utf-8", errors="replace")

        if len(data) == 0 and len(self._buffer) == 0:
            self._emit_data("")
            return

        self._buffer += data

        # Handle bracketed paste mode
        if self._paste_mode:
            self._paste_buffer += self._buffer
            self._buffer = ""

            end_index = self._paste_buffer.find(BRACKETED_PASTE_END)
            if end_index != -1:
                pasted_content = self._paste_buffer[:end_index]
                remaining = self._paste_buffer[
                    end_index + len(BRACKETED_PASTE_END):
                ]

                self._paste_mode = False
                self._paste_buffer = ""

                self._emit_paste(pasted_content)

                if remaining:
                    self.process(remaining)
            return

        start_index = self._buffer.find(BRACKETED_PASTE_START)
        if start_index != -1:
            if start_index > 0:
                before_paste = self._buffer[:start_index]
                result = extract_complete_sequences(before_paste)
                for sequence in result.sequences:
                    self._emit_data(sequence)

            self._buffer = self._buffer[start_index + len(BRACKETED_PASTE_START):]
            self._paste_mode = True
            self._paste_buffer = self._buffer
            self._buffer = ""

            end_index = self._paste_buffer.find(BRACKETED_PASTE_END)
            if end_index != -1:
                pasted_content = self._paste_buffer[:end_index]
                remaining = self._paste_buffer[
                    end_index + len(BRACKETED_PASTE_END):
                ]

                self._paste_mode = False
                self._paste_buffer = ""

                self._emit_paste(pasted_content)

                if remaining:
                    self.process(remaining)
            return

        result = extract_complete_sequences(self._buffer)
        self._buffer = result.remainder

        for sequence in result.sequences:
            self._emit_data(sequence)

        if self._buffer:
            self._schedule_flush()

    def flush(self) -> list[str]:
        """Flush the buffer and return any remaining data."""
        self._clear_timeout()

        if not self._buffer:
            return []

        sequences = [self._buffer]
        self._buffer = ""
        return sequences

    def clear(self) -> None:
        """Clear the buffer and any pending state."""
        self._clear_timeout()
        self._buffer = ""
        self._paste_mode = False
        self._paste_buffer = ""

    def get_buffer(self) -> str:
        """Get the current buffer contents."""
        return self._buffer

    def destroy(self) -> None:
        """Clean up resources."""
        self.clear()
