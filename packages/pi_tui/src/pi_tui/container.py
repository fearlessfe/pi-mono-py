"""
Container component - a component that contains other components

TypeScript Reference: _ts_reference/tui.ts (lines 100-130)
See MAPPING.md for detailed mapping.

Original TypeScript:
```typescript
class Container implements Component {
    children: Component[] = [];
    
    addChild(component: Component): void { ... }
    removeChild(component: Component): void { ... }
    clear(): void { ... }
    invalidate(): void { ... }
    render(width: number): string[] { ... }
}
```
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pi_tui.component import Component


class Container:
    """
    Container - a component that groups child components.
    
    TypeScript Reference: _ts_reference/tui.ts:100-130
    """
    
    children: list[Component]
    
    def __init__(self) -> None:
        self.children = []
    
    def add_child(self, component: Component) -> None:
        """Add a child component."""
        self.children.append(component)
    
    def remove_child(self, component: Component) -> None:
        """Remove a child component."""
        try:
            self.children.remove(component)
        except ValueError:
            pass
    
    def clear(self) -> None:
        """Remove all child components."""
        self.children.clear()
    
    def invalidate(self) -> None:
        """Invalidate all child components."""
        for child in self.children:
            child.invalidate()
    
    def render(self, width: int) -> list[str]:
        """
        Render all children to lines.
        
        Args:
            width: Viewport width
            
        Returns:
            Combined lines from all children
        """
        lines: list[str] = []
        for child in self.children:
            lines.extend(child.render(width))
        return lines
