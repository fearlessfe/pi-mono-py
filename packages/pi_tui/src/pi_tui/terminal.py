"""
Terminal interface for pi-tui

TypeScript Reference: _ts_reference/terminal.ts
"""

from __future__ import annotations

import asyncio
import os
import re
import shutil
import signal
import sys
from typing import Any, Callable, Protocol

from pi_tui.keys import set_kitty_protocol_active
from pi_tui.stdin_buffer import StdinBuffer, StdinBufferOptions


class Terminal(Protocol):
    """
    Terminal interface - protocol for terminal implementations.

    TypeScript Reference: _ts_reference/terminal.ts:Terminal interface
    """

    @property
    def columns(self) -> int: ...

    @property
    def rows(self) -> int: ...

    @property
    def kitty_protocol_active(self) -> bool: ...

    def write(self, data: str) -> None: ...

    def start(
        self,
        on_input: Callable[[str], None],
        on_resize: Callable[[], None],
    ) -> None: ...

    def stop(self) -> None: ...

    async def drain_input(self, max_ms: float = 1000, idle_ms: float = 50) -> None: ...

    def move_by(self, lines: int) -> None: ...

    def hide_cursor(self) -> None: ...

    def show_cursor(self) -> None: ...

    def clear_line(self) -> None: ...

    def clear_from_cursor(self) -> None: ...

    def clear_screen(self) -> None: ...

    def set_title(self, title: str) -> None: ...


class ProcessTerminal:
    """
    Terminal implementation using process stdin/stdout.

    TypeScript Reference: _ts_reference/terminal.ts:ProcessTerminal class
    """

    def __init__(self) -> None:
        self._kitty_protocol_active = False
        self._started = False
        self._input_handler: Callable[[str], None] | None = None
        self._resize_handler: Callable[[], None] | None = None
        self._stdin_buffer: StdinBuffer | None = None
        self._old_term_settings: Any = None
        self._read_task: asyncio.Task | None = None

    @property
    def columns(self) -> int:
        return shutil.get_terminal_size((80, 24)).columns

    @property
    def rows(self) -> int:
        return shutil.get_terminal_size((80, 24)).lines

    @property
    def kitty_protocol_active(self) -> bool:
        return self._kitty_protocol_active

    def write(self, data: str) -> None:
        sys.stdout.write(data)
        sys.stdout.flush()

    def _enable_raw_mode(self) -> None:
        if sys.platform == "win32":
            return

        import termios
        import tty

        try:
            self._old_term_settings = termios.tcgetattr(sys.stdin.fileno())
            tty.setraw(sys.stdin.fileno())
        except (termios.error, OSError):
            pass

    def _disable_raw_mode(self) -> None:
        if sys.platform == "win32":
            return

        import termios

        if self._old_term_settings is not None:
            try:
                termios.tcsetattr(
                    sys.stdin.fileno(),
                    termios.TCSADRAIN,
                    self._old_term_settings,
                )
            except (termios.error, OSError):
                pass
            self._old_term_settings = None

    def _setup_stdin_buffer(self) -> None:
        self._stdin_buffer = StdinBuffer(StdinBufferOptions(timeout=10.0))

        kitty_response_pattern = re.compile(r"^\x1b\[\?(\d+)u$")

        def on_data(sequence: str) -> None:
            if not self._kitty_protocol_active:
                match = kitty_response_pattern.match(sequence)
                if match:
                    self._kitty_protocol_active = True
                    set_kitty_protocol_active(True)
                    self.write("\x1b[>7u")
                    return

            if self._input_handler:
                self._input_handler(sequence)

        def on_paste(content: str) -> None:
            if self._input_handler:
                self._input_handler(f"\x1b[200~{content}\x1b[201~")

        assert self._stdin_buffer is not None
        self._stdin_buffer.on_data = on_data
        self._stdin_buffer.on_paste = on_paste

    async def _read_stdin(self) -> None:
        loop = asyncio.get_event_loop()
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)

        try:
            transport, _ = await loop.connect_read_pipe(lambda: protocol, sys.stdin)
        except (OSError, ValueError):
            return

        try:
            while self._started:
                try:
                    data = await asyncio.wait_for(reader.read(1024), timeout=0.1)
                    if data and self._stdin_buffer:
                        self._stdin_buffer.process(data)
                except asyncio.TimeoutError:
                    continue
        except (asyncio.CancelledError, ConnectionError):
            pass
        finally:
            transport.close()

    def _on_sigwinch(self, _signum: int, _frame: object) -> None:
        if self._resize_handler:
            self._resize_handler()

    def start(
        self,
        on_input: Callable[[str], None],
        on_resize: Callable[[], None],
    ) -> None:
        self._input_handler = on_input
        self._resize_handler = on_resize
        self._started = True

        self._enable_raw_mode()
        self.write("\x1b[?2004h")

        if sys.platform != "win32":
            signal.signal(signal.SIGWINCH, self._on_sigwinch)
            os.kill(os.getpid(), signal.SIGWINCH)

        self._setup_stdin_buffer()
        self.write("\x1b[?u")

        loop = asyncio.get_event_loop()
        self._read_task = loop.create_task(self._read_stdin())

    def stop(self) -> None:
        self._started = False

        self.write("\x1b[?2004l")

        if self._kitty_protocol_active:
            self.write("\x1b[<u")
            self._kitty_protocol_active = False
            set_kitty_protocol_active(False)

        if self._stdin_buffer:
            self._stdin_buffer.destroy()
            self._stdin_buffer = None

        if self._read_task:
            self._read_task.cancel()
            self._read_task = None

        if sys.platform != "win32":
            try:
                signal.signal(signal.SIGWINCH, signal.SIG_DFL)
            except (ValueError, OSError):
                pass

        self._input_handler = None
        self._resize_handler = None

        self._disable_raw_mode()

    async def drain_input(self, max_ms: float = 1000, idle_ms: float = 50) -> None:
        if self._kitty_protocol_active:
            self.write("\x1b[<u")
            self._kitty_protocol_active = False
            set_kitty_protocol_active(False)

        previous_handler = self._input_handler
        self._input_handler = None

        loop = asyncio.get_event_loop()
        start_time = loop.time()
        last_data_time = start_time

        def on_data() -> None:
            nonlocal last_data_time
            last_data_time = loop.time()

        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)

        try:
            transport, _ = await loop.connect_read_pipe(lambda: protocol, sys.stdin)
        except (OSError, ValueError):
            self._input_handler = previous_handler
            return

        try:
            end_time = start_time + (max_ms / 1000.0)
            idle_seconds = idle_ms / 1000.0

            while True:
                now = loop.time()
                time_left = end_time - now
                if time_left <= 0:
                    break
                if now - last_data_time >= idle_seconds:
                    break

                try:
                    await asyncio.wait_for(
                        reader.read(1024), timeout=min(idle_seconds, time_left)
                    )
                    on_data()
                except asyncio.TimeoutError:
                    continue
        finally:
            transport.close()
            self._input_handler = previous_handler

    def move_by(self, lines: int) -> None:
        if lines > 0:
            self.write(f"\x1b[{lines}B")
        elif lines < 0:
            self.write(f"\x1b[{-lines}A")

    def hide_cursor(self) -> None:
        self.write("\x1b[?25l")

    def show_cursor(self) -> None:
        self.write("\x1b[?25h")

    def clear_line(self) -> None:
        self.write("\x1b[K")

    def clear_from_cursor(self) -> None:
        self.write("\x1b[J")

    def clear_screen(self) -> None:
        self.write("\x1b[2J\x1b[H")

    def set_title(self, title: str) -> None:
        self.write(f"\x1b]0;{title}\x07")

