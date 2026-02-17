"""
Component interface for pi-tui

TypeScript Reference: _ts_reference/tui.ts (lines 20-50)
See MAPPING.md for detailed mapping.

Original TypeScript:
```typescript
interface Component {
    render(width: number): string[];
    handleInput?(data: string): void;
    invalidate?(): void;
    wantsKeyRelease?: boolean;
}

interface Focusable {
    focused: boolean;
}
```
"""

from abc import ABC, abstractmethod
from typing import Protocol


class Component(ABC):
    """
    Base component interface.
    
    All TUI components must implement this interface.
    
    TypeScript Reference: _ts_reference/tui.ts:20-35
    """
    
    @abstractmethod
    def render(self, width: int) -> list[str]:
        """
        Render the component to lines for the given viewport width.
        
        Args:
            width: Current viewport width in columns
            
        Returns:
            Array of strings, each representing a line
        """
        ...
    
    def handle_input(self, data: str) -> None:
        """
        Optional handler for keyboard input when component has focus.
        
        Args:
            data: Raw input data from terminal
        """
        pass
    
    def invalidate(self) -> None:
        """
        Invalidate any cached rendering state.
        
        Called when theme changes or when component needs to re-render from scratch.
        """
        pass
    
    wants_key_release: bool = False
    """If True, component receives key release events (Kitty protocol)."""


class Focusable(Protocol):
    """
    Protocol for components that can receive focus and display a hardware cursor.
    
    When focused, the component should emit CURSOR_MARKER at the cursor position
    in its render output. TUI will find this marker and position the hardware
    cursor there for proper IME candidate window positioning.
    
    TypeScript Reference: _ts_reference/tui.ts:37-45
    """
    
    focused: bool
    """Set by TUI when focus changes. Component should emit CURSOR_MARKER when True."""


def is_focusable(component: Component | None) -> bool:
    """
    Type guard to check if a component implements Focusable.
    
    TypeScript Reference: _ts_reference/tui.ts:47-50
    
    Args:
        component: Component to check
        
    Returns:
        True if component implements Focusable protocol
    """
    return component is not None and hasattr(component, "focused")
