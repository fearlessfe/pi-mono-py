"""
Keyboard input handling for terminal applications.

Supports both legacy terminal sequences and Kitty keyboard protocol.
See: https://sw.kovidgoyal.net/kitty/keyboard-protocol/

TypeScript Reference: _ts_reference/keys.ts (entire file, ~1000 lines)
See MAPPING.md for detailed mapping.

API:
- matches_key(data, key_id) - Check if input matches a key identifier
- parse_key(data) - Parse input and return the key identifier
- Key - Helper object for creating typed key identifiers
- set_kitty_protocol_active(active) - Set global Kitty protocol state
- is_kitty_protocol_active() - Query global Kitty protocol state
"""

from __future__ import annotations

import re
from typing import Literal, TypedDict

# =============================================================================
# Type Definitions
# =============================================================================

Letter = Literal[
    "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m",
    "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z",
]

SymbolKey = Literal[
    "`", "-", "=", "[", "]", "\\", ";", "'", ",", ".", "/",
    "!", "@", "#", "$", "%", "^", "&", "*", "(", ")",
    "_", "+", "|", "~", "{", "}", ":", "<", ">", "?",
]

SpecialKey = Literal[
    "escape", "esc", "enter", "return", "tab", "space", "backspace",
    "delete", "insert", "clear", "home", "end", "pageUp", "pageDown",
    "up", "down", "left", "right",
    "f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8", "f9", "f10", "f11", "f12",
]

BaseKey = Letter | SymbolKey | SpecialKey

# Build KeyId type dynamically to avoid repetition
ModifierCombo = Literal[
    "ctrl", "shift", "alt",
    "ctrl+shift", "shift+ctrl", "ctrl+alt", "alt+ctrl", "shift+alt", "alt+shift",
    "ctrl+shift+alt", "ctrl+alt+shift", "shift+ctrl+alt", "shift+alt+ctrl",
    "alt+ctrl+shift", "alt+shift+ctrl",
]

KeyId = BaseKey | str  # Simplified; full type would be template literal


class KeyEventType(TypedDict):
    """Event types from Kitty keyboard protocol (flag 2)."""
    type: Literal["press", "repeat", "release"]


# =============================================================================
# Global Kitty Protocol State
# =============================================================================

_kitty_protocol_active = False


def set_kitty_protocol_active(active: bool) -> None:
    """Set the global Kitty keyboard protocol state."""
    global _kitty_protocol_active
    _kitty_protocol_active = active


def is_kitty_protocol_active() -> bool:
    """Query whether Kitty keyboard protocol is currently active."""
    return _kitty_protocol_active


# =============================================================================
# Key Helper Class
# =============================================================================

class _KeyHelper:
    """
    Helper object for creating typed key identifiers with autocomplete.
    
    Usage:
    - Key.escape, Key.enter, Key.tab, etc. for special keys
    - Key.ctrl("c"), Key.alt("x") for single modifier
    - Key.ctrl_shift("p"), Key.ctrl_alt("x") for combined modifiers
    
    TypeScript Reference: _ts_reference/keys.ts:Key object
    """
    
    # Special keys
    escape: Literal["escape"] = "escape"
    esc: Literal["esc"] = "esc"
    enter: Literal["enter"] = "enter"
    return_: Literal["return"] = "return"
    tab: Literal["tab"] = "tab"
    space: Literal["space"] = "space"
    backspace: Literal["backspace"] = "backspace"
    delete: Literal["delete"] = "delete"
    insert: Literal["insert"] = "insert"
    clear: Literal["clear"] = "clear"
    home: Literal["home"] = "home"
    end: Literal["end"] = "end"
    pageUp: Literal["pageUp"] = "pageUp"
    pageDown: Literal["pageDown"] = "pageDown"
    up: Literal["up"] = "up"
    down: Literal["down"] = "down"
    left: Literal["left"] = "left"
    right: Literal["right"] = "right"
    f1: Literal["f1"] = "f1"
    f2: Literal["f2"] = "f2"
    f3: Literal["f3"] = "f3"
    f4: Literal["f4"] = "f4"
    f5: Literal["f5"] = "f5"
    f6: Literal["f6"] = "f6"
    f7: Literal["f7"] = "f7"
    f8: Literal["f8"] = "f8"
    f9: Literal["f9"] = "f9"
    f10: Literal["f10"] = "f10"
    f11: Literal["f11"] = "f11"
    f12: Literal["f12"] = "f12"
    
    # Symbol keys
    backtick: Literal["`"] = "`"
    hyphen: Literal["-"] = "-"
    equals: Literal["="] = "="
    leftbracket: Literal["["] = "["
    rightbracket: Literal["]"] = "]"
    backslash: Literal["\\"] = "\\"
    semicolon: Literal[";"] = ";"
    quote: Literal["'"] = "'"
    comma: Literal[","] = ","
    period: Literal["."] = "."
    slash: Literal["/"] = "/"
    
    # Single modifiers
    @staticmethod
    def ctrl(key: BaseKey) -> str:
        return f"ctrl+{key}"
    
    @staticmethod
    def shift(key: BaseKey) -> str:
        return f"shift+{key}"
    
    @staticmethod
    def alt(key: BaseKey) -> str:
        return f"alt+{key}"
    
    # Combined modifiers
    @staticmethod
    def ctrl_shift(key: BaseKey) -> str:
        return f"ctrl+shift+{key}"
    
    @staticmethod
    def shift_ctrl(key: BaseKey) -> str:
        return f"shift+ctrl+{key}"
    
    @staticmethod
    def ctrl_alt(key: BaseKey) -> str:
        return f"ctrl+alt+{key}"
    
    @staticmethod
    def alt_ctrl(key: BaseKey) -> str:
        return f"alt+ctrl+{key}"
    
    @staticmethod
    def shift_alt(key: BaseKey) -> str:
        return f"shift+alt+{key}"
    
    @staticmethod
    def alt_shift(key: BaseKey) -> str:
        return f"alt+shift+{key}"
    
    @staticmethod
    def ctrl_shift_alt(key: BaseKey) -> str:
        return f"ctrl+shift+alt+{key}"


Key = _KeyHelper()


# =============================================================================
# Constants
# =============================================================================

SYMBOL_KEYS = {
    "`", "-", "=", "[", "]", "\\", ";", "'", ",", ".", "/",
    "!", "@", "#", "$", "%", "^", "&", "*", "(", ")",
    "_", "+", "|", "~", "{", "}", ":", "<", ">", "?",
}

MODIFIERS = {
    "shift": 1,
    "alt": 2,
    "ctrl": 4,
}

LOCK_MASK = 64 + 128  # Caps Lock + Num Lock

CODEPOINTS = {
    "escape": 27,
    "tab": 9,
    "enter": 13,
    "space": 32,
    "backspace": 127,
    "kp_enter": 57414,  # Numpad Enter (Kitty protocol)
}

ARROW_CODEPOINTS = {
    "up": -1,
    "down": -2,
    "right": -3,
    "left": -4,
}

FUNCTIONAL_CODEPOINTS = {
    "delete": -10,
    "insert": -11,
    "pageUp": -12,
    "pageDown": -13,
    "home": -14,
    "end": -15,
}

# Legacy key sequences (common terminal escape sequences)
LEGACY_KEY_SEQUENCES: dict[str, list[str]] = {
    "up": ["\x1b[A", "\x1bOA"],
    "down": ["\x1b[B", "\x1bOB"],
    "right": ["\x1b[C", "\x1bOC"],
    "left": ["\x1b[D", "\x1bOD"],
    "home": ["\x1b[H", "\x1bOH", "\x1b[1~", "\x1b[7~"],
    "end": ["\x1b[F", "\x1bOF", "\x1b[4~", "\x1b[8~"],
    "insert": ["\x1b[2~"],
    "delete": ["\x1b[3~"],
    "pageUp": ["\x1b[5~", "\x1b[[5~"],
    "pageDown": ["\x1b[6~", "\x1b[[6~"],
    "clear": ["\x1b[E", "\x1bOE"],
    "f1": ["\x1bOP", "\x1b[11~", "\x1b[[A"],
    "f2": ["\x1bOQ", "\x1b[12~", "\x1b[[B"],
    "f3": ["\x1bOR", "\x1b[13~", "\x1b[[C"],
    "f4": ["\x1bOS", "\x1b[14~", "\x1b[[D"],
    "f5": ["\x1b[15~", "\x1b[[E"],
    "f6": ["\x1b[17~"],
    "f7": ["\x1b[18~"],
    "f8": ["\x1b[19~"],
    "f9": ["\x1b[20~"],
    "f10": ["\x1b[21~"],
    "f11": ["\x1b[23~"],
    "f12": ["\x1b[24~"],
}

LEGACY_SHIFT_SEQUENCES: dict[str, list[str]] = {
    "up": ["\x1b[a"],
    "down": ["\x1b[b"],
    "right": ["\x1b[c"],
    "left": ["\x1b[d"],
    "clear": ["\x1b[e"],
    "insert": ["\x1b[2$"],
    "delete": ["\x1b[3$"],
    "pageUp": ["\x1b[5$"],
    "pageDown": ["\x1b[6$"],
    "home": ["\x1b[7$"],
    "end": ["\x1b[8$"],
}

LEGACY_CTRL_SEQUENCES: dict[str, list[str]] = {
    "up": ["\x1bOa"],
    "down": ["\x1bOb"],
    "right": ["\x1bOc"],
    "left": ["\x1bOd"],
    "clear": ["\x1bOe"],
    "insert": ["\x1b[2^"],
    "delete": ["\x1b[3^"],
    "pageUp": ["\x1b[5^"],
    "pageDown": ["\x1b[6^"],
    "home": ["\x1b[7^"],
    "end": ["\x1b[8^"],
}

# Direct mapping of sequences to key IDs
LEGACY_SEQUENCE_KEY_IDS: dict[str, str] = {
    "\x1bOA": "up",
    "\x1bOB": "down",
    "\x1bOC": "right",
    "\x1bOD": "left",
    "\x1bOH": "home",
    "\x1bOF": "end",
    "\x1b[E": "clear",
    "\x1bOE": "clear",
    "\x1bOe": "ctrl+clear",
    "\x1b[e": "shift+clear",
    "\x1b[2~": "insert",
    "\x1b[2$": "shift+insert",
    "\x1b[2^": "ctrl+insert",
    "\x1b[3$": "shift+delete",
    "\x1b[3^": "ctrl+delete",
    "\x1b[[5~": "pageUp",
    "\x1b[[6~": "pageDown",
    "\x1b[a": "shift+up",
    "\x1b[b": "shift+down",
    "\x1b[c": "shift+right",
    "\x1b[d": "shift+left",
    "\x1bOa": "ctrl+up",
    "\x1bOb": "ctrl+down",
    "\x1bOc": "ctrl+right",
    "\x1bOd": "ctrl+left",
    "\x1b[5$": "shift+pageUp",
    "\x1b[6$": "shift+pageDown",
    "\x1b[7$": "shift+home",
    "\x1b[8$": "shift+end",
    "\x1b[5^": "ctrl+pageUp",
    "\x1b[6^": "ctrl+pageDown",
    "\x1b[7^": "ctrl+home",
    "\x1b[8^": "ctrl+end",
    "\x1bOP": "f1",
    "\x1bOQ": "f2",
    "\x1bOR": "f3",
    "\x1bOS": "f4",
    "\x1b[11~": "f1",
    "\x1b[12~": "f2",
    "\x1b[13~": "f3",
    "\x1b[14~": "f4",
    "\x1b[[A": "f1",
    "\x1b[[B": "f2",
    "\x1b[[C": "f3",
    "\x1b[[D": "f4",
    "\x1b[[E": "f5",
    "\x1b[15~": "f5",
    "\x1b[17~": "f6",
    "\x1b[18~": "f7",
    "\x1b[19~": "f8",
    "\x1b[20~": "f9",
    "\x1b[21~": "f10",
    "\x1b[23~": "f11",
    "\x1b[24~": "f12",
    "\x1bb": "alt+left",
    "\x1bf": "alt+right",
    "\x1bp": "alt+up",
    "\x1bn": "alt+down",
}


# =============================================================================
# Legacy Sequence Matching
# =============================================================================

def _matches_legacy_sequence(data: str, sequences: list[str]) -> bool:
    """Check if data matches any of the legacy sequences."""
    return data in sequences


def _matches_legacy_modifier_sequence(data: str, key: str, modifier: int) -> bool:
    """Check if data matches a legacy sequence with modifier."""
    if modifier == MODIFIERS["shift"]:
        return key in LEGACY_SHIFT_SEQUENCES and _matches_legacy_sequence(
            data, LEGACY_SHIFT_SEQUENCES[key]
        )
    if modifier == MODIFIERS["ctrl"]:
        return key in LEGACY_CTRL_SEQUENCES and _matches_legacy_sequence(
            data, LEGACY_CTRL_SEQUENCES[key]
        )
    return False


# =============================================================================
# Kitty Protocol Parsing
# =============================================================================

class ParsedKittySequence(TypedDict):
    """Parsed Kitty keyboard protocol sequence."""
    codepoint: int
    shifted_key: int | None
    base_layout_key: int | None
    modifier: int
    event_type: str


_last_event_type: str = "press"


def is_key_release(data: str) -> bool:
    """
    Check if the last parsed key event was a key release.
    Only meaningful when Kitty keyboard protocol with flag 2 is active.
    """
    if "\x1b[200~" in data:  # Bracketed paste
        return False
    return any(
        f":{t}" in data
        for t in ["3u", "3~", "3A", "3B", "3C", "3D", "3H", "3F"]
    )


def is_key_repeat(data: str) -> bool:
    """
    Check if the last parsed key event was a key repeat.
    Only meaningful when Kitty keyboard protocol with flag 2 is active.
    """
    if "\x1b[200~" in data:  # Bracketed paste
        return False
    return any(
        f":{t}" in data
        for t in ["2u", "2~", "2A", "2B", "2C", "2D", "2H", "2F"]
    )


def _parse_event_type(event_type_str: str | None) -> str:
    """Parse event type from Kitty protocol."""
    if not event_type_str:
        return "press"
    try:
        event_type = int(event_type_str)
        if event_type == 2:
            return "repeat"
        if event_type == 3:
            return "release"
    except ValueError:
        pass
    return "press"


def _parse_kitty_sequence(data: str) -> ParsedKittySequence | None:
    """
    Parse a Kitty keyboard protocol sequence.
    
    Format variations:
    - \x1b[<codepoint>u
    - \x1b[<codepoint>;<mod>u
    - \x1b[<codepoint>;<mod>:<event>u
    - \x1b[<codepoint>:<shifted>;<mod>u
    - \x1b[<codepoint>:<shifted>:<base>;<mod>u
    """
    global _last_event_type
    
    # CSI u format
    csi_u_match = re.match(
        r"^\x1b\[(\d+)(?::(\d*))?(?::(\d+))?(?:;(\d+))?(?::(\d+))?u$",
        data
    )
    if csi_u_match:
        codepoint = int(csi_u_match.group(1))
        shifted_key = int(csi_u_match.group(2)) if csi_u_match.group(2) else None
        base_layout_key = int(csi_u_match.group(3)) if csi_u_match.group(3) else None
        mod_value = int(csi_u_match.group(4)) if csi_u_match.group(4) else 1
        event_type = _parse_event_type(csi_u_match.group(5))
        _last_event_type = event_type
        return ParsedKittySequence(
            codepoint=codepoint,
            shifted_key=shifted_key,
            base_layout_key=base_layout_key,
            modifier=mod_value - 1,
            event_type=event_type,
        )
    
    # Arrow keys with modifier: \x1b[1;<mod>A/B/C/D
    arrow_match = re.match(r"^\x1b\[1;(\d+)(?::(\d+))?([ABCD])$", data)
    if arrow_match:
        mod_value = int(arrow_match.group(1))
        event_type = _parse_event_type(arrow_match.group(2))
        arrow_codes = {"A": -1, "B": -2, "C": -3, "D": -4}
        _last_event_type = event_type
        return ParsedKittySequence(
            codepoint=arrow_codes[arrow_match.group(3)],
            shifted_key=None,
            base_layout_key=None,
            modifier=mod_value - 1,
            event_type=event_type,
        )
    
    # Functional keys: \x1b[<num>~ or \x1b[<num>;<mod>~
    func_match = re.match(r"^\x1b\[(\d+)(?:;(\d+))?(?::(\d+))?~$", data)
    if func_match:
        key_num = int(func_match.group(1))
        mod_value = int(func_match.group(2)) if func_match.group(2) else 1
        event_type = _parse_event_type(func_match.group(3))
        func_codes = {
            2: FUNCTIONAL_CODEPOINTS["insert"],
            3: FUNCTIONAL_CODEPOINTS["delete"],
            5: FUNCTIONAL_CODEPOINTS["pageUp"],
            6: FUNCTIONAL_CODEPOINTS["pageDown"],
            7: FUNCTIONAL_CODEPOINTS["home"],
            8: FUNCTIONAL_CODEPOINTS["end"],
        }
        if key_num in func_codes:
            _last_event_type = event_type
            return ParsedKittySequence(
                codepoint=func_codes[key_num],
                shifted_key=None,
                base_layout_key=None,
                modifier=mod_value - 1,
                event_type=event_type,
            )
    
    # Home/End with modifier: \x1b[1;<mod>H/F
    home_end_match = re.match(r"^\x1b\[1;(\d+)(?::(\d+))?([HF])$", data)
    if home_end_match:
        mod_value = int(home_end_match.group(1))
        event_type = _parse_event_type(home_end_match.group(2))
        codepoint = (
            FUNCTIONAL_CODEPOINTS["home"]
            if home_end_match.group(3) == "H"
            else FUNCTIONAL_CODEPOINTS["end"]
        )
        _last_event_type = event_type
        return ParsedKittySequence(
            codepoint=codepoint,
            shifted_key=None,
            base_layout_key=None,
            modifier=mod_value - 1,
            event_type=event_type,
        )
    
    return None


def _matches_kitty_sequence(data: str, expected_codepoint: int, expected_modifier: int) -> bool:
    """Check if data matches a Kitty sequence for the expected key and modifier."""
    parsed = _parse_kitty_sequence(data)
    if not parsed:
        return False
    
    actual_mod = parsed["modifier"] & ~LOCK_MASK
    expected_mod = expected_modifier & ~LOCK_MASK
    
    if actual_mod != expected_mod:
        return False
    
    if parsed["codepoint"] == expected_codepoint:
        return True
    
    # Alternate match using base layout key for non-Latin layouts
    if parsed["base_layout_key"] is not None and parsed["base_layout_key"] == expected_codepoint:
        cp = parsed["codepoint"]
        is_latin_letter = 97 <= cp <= 122  # a-z
        is_known_symbol = chr(cp) in SYMBOL_KEYS
        if not is_latin_letter and not is_known_symbol:
            return True
    
    return False


def _matches_modify_other_keys(data: str, expected_keycode: int, expected_modifier: int) -> bool:
    """Match xterm modifyOtherKeys format: CSI 27 ; modifiers ; keycode ~"""
    match = re.match(r"^\x1b\[27;(\d+);(\d+)~$", data)
    if not match:
        return False
    mod_value = int(match.group(1))
    keycode = int(match.group(2))
    actual_mod = mod_value - 1
    return keycode == expected_keycode and actual_mod == expected_modifier


# =============================================================================
# Key Parsing
# =============================================================================

def _raw_ctrl_char(key: str) -> str | None:
    """Get the control character for a key."""
    char = key.lower()
    code = ord(char)
    if (97 <= code <= 122) or char in "[\\]_":
        return chr(code & 0x1F)
    if char == "-":
        return chr(31)  # Same as Ctrl+_
    return None


def _parse_key_id(key_id: str) -> dict | None:
    """Parse a key identifier into its components."""
    parts = key_id.lower().split("+")
    key = parts[-1]
    if not key:
        return None
    return {
        "key": key,
        "ctrl": "ctrl" in parts,
        "shift": "shift" in parts,
        "alt": "alt" in parts,
    }


def matches_key(data: str, key_id: KeyId) -> bool:
    """
    Match input data against a key identifier string.
    
    Supported key identifiers:
    - Single keys: "escape", "tab", "enter", "backspace", "delete", "home", "end", "space"
    - Arrow keys: "up", "down", "left", "right"
    - Ctrl combinations: "ctrl+c", "ctrl+z", etc.
    - Shift combinations: "shift+tab", "shift+enter"
    - Alt combinations: "alt+enter", "alt+backspace"
    - Combined modifiers: "shift+ctrl+p", "ctrl+alt+x"
    
    Use the Key helper for autocomplete: Key.ctrl("c"), Key.escape, Key.ctrl_shift("p")
    
    TypeScript Reference: _ts_reference/keys.ts:matchesKey
    
    Args:
        data: Raw input data from terminal
        key_id: Key identifier (e.g., "ctrl+c", "escape", Key.ctrl("c"))
        
    Returns:
        True if the input matches the key identifier
    """
    parsed = _parse_key_id(key_id)
    if not parsed:
        return False
    
    key = parsed["key"]  # type: ignore[assignment]
    ctrl = parsed["ctrl"]
    shift = parsed["shift"]
    alt = parsed["alt"]
    
    modifier = 0
    if shift:
        modifier |= MODIFIERS["shift"]
    if alt:
        modifier |= MODIFIERS["alt"]
    if ctrl:
        modifier |= MODIFIERS["ctrl"]
    
    # Escape
    if key in ("escape", "esc"):
        if modifier != 0:
            return False
        return data == "\x1b" or _matches_kitty_sequence(data, CODEPOINTS["escape"], 0)
    
    # Space
    if key == "space":
        if not _kitty_protocol_active:
            if ctrl and not alt and not shift and data == "\x00":
                return True
            if alt and not ctrl and not shift and data == "\x1b ":
                return True
        if modifier == 0:
            return data == " " or _matches_kitty_sequence(data, CODEPOINTS["space"], 0)
        return _matches_kitty_sequence(data, CODEPOINTS["space"], modifier)
    
    # Tab
    if key == "tab":
        if shift and not ctrl and not alt:
            return (
                data == "\x1b[Z"
                or _matches_kitty_sequence(data, CODEPOINTS["tab"], MODIFIERS["shift"])
            )
        if modifier == 0:
            return data == "\t" or _matches_kitty_sequence(data, CODEPOINTS["tab"], 0)
        return _matches_kitty_sequence(data, CODEPOINTS["tab"], modifier)
    
    # Enter
    if key in ("enter", "return"):
        if shift and not ctrl and not alt:
            if _matches_kitty_sequence(data, CODEPOINTS["enter"], MODIFIERS["shift"]):
                return True
            if _matches_kitty_sequence(data, CODEPOINTS["kp_enter"], MODIFIERS["shift"]):
                return True
            if _matches_modify_other_keys(data, CODEPOINTS["enter"], MODIFIERS["shift"]):
                return True
            if _kitty_protocol_active:
                return data == "\x1b\r" or data == "\n"
            return False
        if alt and not ctrl and not shift:
            if _matches_kitty_sequence(data, CODEPOINTS["enter"], MODIFIERS["alt"]):
                return True
            if _matches_kitty_sequence(data, CODEPOINTS["kp_enter"], MODIFIERS["alt"]):
                return True
            if _matches_modify_other_keys(data, CODEPOINTS["enter"], MODIFIERS["alt"]):
                return True
            if not _kitty_protocol_active:
                return data == "\x1b\r"
            return False
        if modifier == 0:
            return (
                data == "\r"
                or (not _kitty_protocol_active and data == "\n")
                or data == "\x1bOM"
                or _matches_kitty_sequence(data, CODEPOINTS["enter"], 0)
                or _matches_kitty_sequence(data, CODEPOINTS["kp_enter"], 0)
            )
        return (
            _matches_kitty_sequence(data, CODEPOINTS["enter"], modifier)
            or _matches_kitty_sequence(data, CODEPOINTS["kp_enter"], modifier)
        )
    
    # Backspace
    if key == "backspace":
        if alt and not ctrl and not shift:
            if data in ("\x1b\x7f", "\x1b\b"):
                return True
            return _matches_kitty_sequence(data, CODEPOINTS["backspace"], MODIFIERS["alt"])
        if modifier == 0:
            return (
                data in ("\x7f", "\x08")
                or _matches_kitty_sequence(data, CODEPOINTS["backspace"], 0)
            )
        return _matches_kitty_sequence(data, CODEPOINTS["backspace"], modifier)
    
    # Functional keys (insert, delete, home, end, pageUp, pageDown)
    functional_keys = ["insert", "delete", "home", "end", "pageup", "pagedown"]
    if key in functional_keys:
        key_map = {"pageup": "pageUp", "pagedown": "pageDown"}
        legacy_key: str = key_map.get(key, key)  # type: ignore[arg-type]
        legacy_sequences = LEGACY_KEY_SEQUENCES.get(legacy_key, [])
        cp = FUNCTIONAL_CODEPOINTS.get(legacy_key)
        
        if modifier == 0:
            if _matches_legacy_sequence(data, legacy_sequences):
                return True
            if cp and _matches_kitty_sequence(data, cp, 0):
                return True
            return False
        
        if _matches_legacy_modifier_sequence(data, key, modifier):
            return True
        if cp:
            return _matches_kitty_sequence(data, cp, modifier)
        return False
    
    # Arrow keys
    arrow_keys = ["up", "down", "left", "right"]
    if key in arrow_keys:
        legacy_sequences = LEGACY_KEY_SEQUENCES.get(key, [])
        cp = ARROW_CODEPOINTS[key]
        
        # Alt variations
        if alt and not ctrl and not shift:
            if key == "up":
                return data == "\x1bp" or _matches_kitty_sequence(data, cp, MODIFIERS["alt"])
            if key == "down":
                return data == "\x1bn" or _matches_kitty_sequence(data, cp, MODIFIERS["alt"])
            if key == "left":
                return (
                    data == "\x1b[1;3D"
                    or (not _kitty_protocol_active and data == "\x1bB")
                    or data == "\x1bb"
                    or _matches_kitty_sequence(data, cp, MODIFIERS["alt"])
                )
            if key == "right":
                return (
                    data == "\x1b[1;3C"
                    or (not _kitty_protocol_active and data == "\x1bF")
                    or data == "\x1bf"
                    or _matches_kitty_sequence(data, cp, MODIFIERS["alt"])
                )
        
        # Ctrl variations
        if ctrl and not alt and not shift and key == "left":
            return (
                data == "\x1b[1;5D"
                or _matches_legacy_modifier_sequence(data, "left", MODIFIERS["ctrl"])
                or _matches_kitty_sequence(data, cp, MODIFIERS["ctrl"])
            )
        
        if ctrl and not alt and not shift and key == "right":
            return (
                data == "\x1b[1;5C"
                or _matches_legacy_modifier_sequence(data, "right", MODIFIERS["ctrl"])
                or _matches_kitty_sequence(data, cp, MODIFIERS["ctrl"])
            )
        
        if modifier == 0:
            return (
                _matches_legacy_sequence(data, legacy_sequences)
                or _matches_kitty_sequence(data, cp, 0)
            )
        
        if _matches_legacy_modifier_sequence(data, key, modifier):
            return True
        return _matches_kitty_sequence(data, cp, modifier)
    
    # Function keys (F1-F12)
    fn_key = key if key.startswith("f") and key[1:].isdigit() else None
    if fn_key and fn_key in LEGACY_KEY_SEQUENCES:
        legacy_sequences = LEGACY_KEY_SEQUENCES[fn_key]
        if modifier == 0:
            return _matches_legacy_sequence(data, legacy_sequences)
        return False  # Function keys with modifiers not fully implemented
    
    # Clear key
    if key == "clear":
        if modifier == 0:
            return _matches_legacy_sequence(data, LEGACY_KEY_SEQUENCES.get("clear", []))
        return _matches_legacy_modifier_sequence(data, "clear", modifier)
    
    # Letter keys (a-z)
    if len(key) == 1 and key.isalpha():
        char_code = ord(key)
        
        # Ctrl combinations
        if ctrl and not alt and not shift:
            ctrl_char = _raw_ctrl_char(key)
            if ctrl_char and data == ctrl_char:
                return True
            return _matches_kitty_sequence(data, char_code, MODIFIERS["ctrl"])
        
        # Alt combinations
        if alt and not ctrl and not shift:
            if data == f"\x1b{key}" or data == f"\x1b{key.upper()}":
                return True
            return _matches_kitty_sequence(data, char_code, MODIFIERS["alt"])
        
        # No modifier
        if modifier == 0:
            return data == key or data == key.upper()
        
        # Other combinations via Kitty protocol
        return _matches_kitty_sequence(data, char_code, modifier)
    
    # Symbol keys
    if key in SYMBOL_KEYS:
        char_code = ord(key)
        
        if ctrl and not alt and not shift:
            ctrl_char = _raw_ctrl_char(key)
            if ctrl_char and data == ctrl_char:
                return True
        
        if modifier == 0:
            return data == key
        
        return _matches_kitty_sequence(data, char_code, modifier)
    
    return False


def parse_key(data: str) -> str | None:
    """
    Parse input data and return the key identifier.
    
    TypeScript Reference: _ts_reference/keys.ts:parseKey
    
    Args:
        data: Raw input data from terminal
        
    Returns:
        Key identifier string or None if not recognized
    """
    # Check legacy sequence map first
    if data in LEGACY_SEQUENCE_KEY_IDS:
        return LEGACY_SEQUENCE_KEY_IDS[data]
    
    # Single character keys
    if len(data) == 1:
        char = data
        code = ord(char)
        
        # Control characters
        if code < 32:
            if code == 9:
                return "tab"
            if code == 13:
                return "enter"
            if code == 27:
                return "escape"
            if code == 8 or code == 127:
                return "backspace"
            # Ctrl+A to Ctrl+Z
            if 1 <= code <= 26:
                return f"ctrl+{chr(code + 96)}"
        
        # Regular keys
        if char.isalpha():
            return char.lower()
        if char in SYMBOL_KEYS:
            return char
        if char == " ":
            return "space"
    
    # Parse Kitty sequence
    parsed = _parse_kitty_sequence(data)
    if parsed:
        cp = parsed["codepoint"]
        mod = parsed["modifier"]
        
        # Build key ID
        key = None
        
        # Check arrow keys
        for name, code in ARROW_CODEPOINTS.items():
            if cp == code:
                key = name
                break
        
        # Check functional keys
        if not key:
            for name, code in FUNCTIONAL_CODEPOINTS.items():
                if cp == code:
                    key = name
                    break
        
        # Regular character
        if not key and 32 <= cp <= 126:
            key = chr(cp).lower()
        
        # Function keys (F1-F12) from codepoints 57344+
        if not key and cp >= 57344:
            fn_num = cp - 57343  # F1 = 57344
            if 1 <= fn_num <= 12:
                key = f"f{fn_num}"
        
        if key:
            modifiers = []
            if mod & MODIFIERS["shift"]:
                modifiers.append("shift")
            if mod & MODIFIERS["alt"]:
                modifiers.append("alt")
            if mod & MODIFIERS["ctrl"]:
                modifiers.append("ctrl")
            
            if modifiers:
                return "+".join(modifiers + [key])
            return key
    
    return None
