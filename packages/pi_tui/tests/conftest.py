"""
Shared pytest fixtures for pi_tui tests.
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, Mock
from typing import Callable, Generator

import pytest


# =============================================================================
# Kitty Protocol Fixtures
# =============================================================================


@pytest.fixture
def reset_kitty_protocol() -> Generator[None, None, None]:
    """Reset Kitty protocol state before/after each test."""
    from pi_tui.keys import set_kitty_protocol_active, is_kitty_protocol_active
    
    original_state = is_kitty_protocol_active()
    set_kitty_protocol_active(False)
    yield
    set_kitty_protocol_active(original_state)


@pytest.fixture
def kitty_protocol_active() -> Generator[None, None, None]:
    """Run test with Kitty protocol enabled."""
    from pi_tui.keys import set_kitty_protocol_active
    
    set_kitty_protocol_active(True)
    yield
    set_kitty_protocol_active(False)


# =============================================================================
# Terminal Mock Fixtures
# =============================================================================


class MockTerminal:
    """Mock terminal for testing without real I/O."""

    def __init__(self, width: int = 80, height: int = 24) -> None:
        self._columns = width
        self._rows = height
        self._writes: list[str] = []
        self._kitty_protocol_active = False
        self._started = False

    @property
    def columns(self) -> int:
        return self._columns

    @property
    def rows(self) -> int:
        return self._rows

    @property
    def kitty_protocol_active(self) -> bool:
        return self._kitty_protocol_active

    def write(self, data: str) -> None:
        self._writes.append(data)

    def get_writes(self) -> list[str]:
        return self._writes.copy()

    def clear_writes(self) -> None:
        self._writes.clear()

    def start(
        self,
        on_input: Callable[[str], None],
        on_resize: Callable[[], None],
    ) -> None:
        self._started = True
        self._on_input = on_input
        self._on_resize = on_resize

    def stop(self) -> None:
        self._started = False

    async def drain_input(self, max_ms: float = 1000, idle_ms: float = 50) -> None:
        pass

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

    def simulate_input(self, data: str) -> None:
        """Simulate terminal input for testing."""
        if hasattr(self, "_on_input") and self._on_input:
            self._on_input(data)

    def simulate_resize(self, width: int, height: int) -> None:
        """Simulate terminal resize for testing."""
        self._columns = width
        self._rows = height
        if hasattr(self, "_on_resize") and self._on_resize:
            self._on_resize()


@pytest.fixture
def mock_terminal() -> MockTerminal:
    """Provide a mock terminal for component tests."""
    return MockTerminal()


@pytest.fixture
def mock_terminal_wide() -> MockTerminal:
    """Provide a wide mock terminal (120x40)."""
    return MockTerminal(width=120, height=40)


@pytest.fixture
def mock_terminal_narrow() -> MockTerminal:
    """Provide a narrow mock terminal (40x20)."""
    return MockTerminal(width=40, height=20)


# =============================================================================
# Callback Mock Fixtures
# =============================================================================


@pytest.fixture
def data_callback() -> MagicMock:
    """Provide a mock callback for data events."""
    return MagicMock()


@pytest.fixture
def paste_callback() -> MagicMock:
    """Provide a mock callback for paste events."""
    return MagicMock()


# =============================================================================
# ANSI Test Data Fixtures
# =============================================================================


@pytest.fixture(params=[
    "\x1b[31mRed\x1b[0m",
    "\x1b[1;3;4mStyled\x1b[0m",
    "Plain text",
    "日本語\x1b[31mRed\x1b[0m",
    "\x1b[38;5;196m256-color\x1b[0m",
    "\x1b[48;2;255;0;0mRGB background\x1b[0m",
])
def ansi_text_samples(request) -> str:
    """Provide various ANSI strings for testing."""
    return request.param


@pytest.fixture(params=[
    ("Hello", 5),
    ("Hello World", 11),
    ("\x1b[31mRed\x1b[0m", 3),
    ("\x1b[1;3;4mStyled\x1b[0m", 6),
    ("日本語", 6),
    ("🎉🎊", 4),
    ("", 0),
])
def text_width_samples(request) -> tuple[str, int]:
    """Provide (text, expected_visible_width) samples."""
    return request.param


# =============================================================================
# Key Sequence Test Data Fixtures
# =============================================================================


@pytest.fixture(params=[
    ("\x1b[A", "up"),
    ("\x1b[B", "down"),
    ("\x1b[C", "right"),
    ("\x1b[D", "left"),
    ("\x1b[H", "home"),
    ("\x1b[F", "end"),
    ("\x1b[5~", "pageUp"),
    ("\x1b[6~", "pageDown"),
    ("\x1b[2~", "insert"),
    ("\x1b[3~", "delete"),
])
def legacy_arrow_sequences(request) -> tuple[str, str]:
    """Provide (sequence, key_id) for legacy arrow keys."""
    return request.param


@pytest.fixture(params=[
    ("\x1bOP", "f1"),
    ("\x1bOQ", "f2"),
    ("\x1bOR", "f3"),
    ("\x1bOS", "f4"),
    ("\x1b[15~", "f5"),
    ("\x1b[17~", "f6"),
    ("\x1b[18~", "f7"),
    ("\x1b[19~", "f8"),
    ("\x1b[20~", "f9"),
    ("\x1b[21~", "f10"),
    ("\x1b[23~", "f11"),
    ("\x1b[24~", "f12"),
])
def legacy_function_sequences(request) -> tuple[str, str]:
    """Provide (sequence, key_id) for legacy function keys."""
    return request.param


# =============================================================================
# Component Test Fixtures
# =============================================================================


class MockComponent:
    """Mock component for testing Container and TUI."""

    def __init__(self, render_output: list[str] | None = None) -> None:
        self._render_output = render_output or ["mock line"]
        self.render_calls: list[int] = []
        self.input_calls: list[str] = []
        self.invalidate_calls = 0
        self.wants_key_release = False

    def render(self, width: int) -> list[str]:
        self.render_calls.append(width)
        return self._render_output

    def handle_input(self, data: str) -> None:
        self.input_calls.append(data)

    def invalidate(self) -> None:
        self.invalidate_calls += 1


class MockFocusableComponent(MockComponent):
    """Mock component that implements Focusable protocol."""

    def __init__(self, render_output: list[str] | None = None) -> None:
        super().__init__(render_output)
        self.focused = False


@pytest.fixture
def mock_component() -> MockComponent:
    """Provide a mock component for testing."""
    return MockComponent()


@pytest.fixture
def mock_focusable_component() -> MockFocusableComponent:
    """Provide a mock focusable component for testing."""
    return MockFocusableComponent()


@pytest.fixture
def mock_component_factory():
    """Provide a factory for creating mock components."""
    def create(render_output: list[str] | None = None) -> MockComponent:
        return MockComponent(render_output)
    return create


# =============================================================================
# Event Loop Fixtures
# =============================================================================


@pytest.fixture
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Provide an event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# =============================================================================
# Utility Fixtures
# =============================================================================


@pytest.fixture
def sample_lines() -> list[str]:
    """Provide sample lines for rendering tests."""
    return [
        "Line 1",
        "Line 2 with more content",
        "Line 3",
    ]


@pytest.fixture
def sample_multiline_text() -> str:
    """Provide sample multiline text for wrapping tests."""
    return "This is a sample text that should be wrapped across multiple lines when rendered at narrow widths."
