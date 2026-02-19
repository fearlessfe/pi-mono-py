"""Path resolution utilities — Python port of path-utils.ts.

Handles macOS-specific filename quirks (NFD normalization, curly quotes,
narrow no-break spaces in screenshot timestamps, etc.).
"""

import os
import re
import unicodedata

# Matches various Unicode space characters that should be normalized to ASCII space.
UNICODE_SPACES = re.compile(
    "[\u00A0\u2000-\u200A\u202F\u205F\u3000]"
)

_NARROW_NO_BREAK_SPACE = "\u202F"

# Matches " AM." or " PM." preceded by a regular space (macOS screenshot timestamps).
_AM_PM_RE = re.compile(r" (AM|PM)\.")


def normalize_unicode_spaces(s: str) -> str:
    """Replace exotic Unicode whitespace characters with plain ASCII space."""
    return UNICODE_SPACES.sub(" ", s)


def try_macos_screenshot_path(file_path: str) -> str:
    """Return *file_path* with narrow no-break space before AM/PM.

    macOS screenshot filenames use U+202F (narrow no-break space) before the
    AM/PM marker, but users typically type a regular space.
    """
    return _AM_PM_RE.sub(f"{_NARROW_NO_BREAK_SPACE}\\1.", file_path)


def try_nfd_variant(file_path: str) -> str:
    """Return the NFD (decomposed) form of *file_path*.

    macOS (HFS+/APFS) stores filenames in NFD form, so converting user input
    to NFD can resolve mismatches caused by composed characters.
    """
    return unicodedata.normalize("NFD", file_path)


def try_curly_quote_variant(file_path: str) -> str:
    """Replace straight apostrophes with right single quotation marks.

    macOS uses U+2019 (') in screenshot names such as ``Capture d\u2019\u00e9cran``,
    but users typically type U+0027 (').
    """
    return file_path.replace("'", "\u2019")


def file_exists(file_path: str) -> bool:
    """Return ``True`` if *file_path* exists on disk (file or directory)."""
    try:
        os.stat(file_path)
        return True
    except OSError:
        return False


def normalize_at_prefix(file_path: str) -> str:
    """Strip a leading ``@`` prefix from *file_path*."""
    if file_path.startswith("@"):
        return file_path[1:]
    return file_path


def expand_path(file_path: str) -> str:
    """Expand ``~`` to the user's home directory and normalize Unicode spaces."""
    normalized = normalize_unicode_spaces(normalize_at_prefix(file_path))
    if normalized == "~":
        return os.path.expanduser("~")
    if normalized.startswith("~/"):
        return os.path.expanduser("~") + normalized[1:]
    return normalized


def resolve_to_cwd(file_path: str, cwd: str) -> str:
    """Resolve *file_path* relative to *cwd*.

    Handles ``~`` expansion and absolute paths.
    """
    expanded = expand_path(file_path)
    if os.path.isabs(expanded):
        return expanded
    return os.path.normpath(os.path.join(cwd, expanded))


def resolve_read_path(file_path: str, cwd: str) -> str:
    """Resolve *file_path* for reading, trying macOS filename variants.

    Attempts the following variants in order until one exists on disk:

    1. Direct resolved path
    2. macOS AM/PM narrow no-break space variant
    3. NFD (decomposed) variant
    4. Curly quote variant (U+2019)
    5. Combined NFD + curly quote variant

    If none exist, the original resolved path is returned.
    """
    resolved = resolve_to_cwd(file_path, cwd)

    if file_exists(resolved):
        return resolved

    # Try macOS AM/PM variant (narrow no-break space before AM/PM)
    am_pm_variant = try_macos_screenshot_path(resolved)
    if am_pm_variant != resolved and file_exists(am_pm_variant):
        return am_pm_variant

    # Try NFD variant (macOS stores filenames in NFD form)
    nfd_variant = try_nfd_variant(resolved)
    if nfd_variant != resolved and file_exists(nfd_variant):
        return nfd_variant

    # Try curly quote variant (macOS uses U+2019 in screenshot names)
    curly_variant = try_curly_quote_variant(resolved)
    if curly_variant != resolved and file_exists(curly_variant):
        return curly_variant

    # Try combined NFD + curly quote (for French macOS screenshots like "Capture d'écran")
    nfd_curly_variant = try_curly_quote_variant(nfd_variant)
    if nfd_curly_variant != resolved and file_exists(nfd_curly_variant):
        return nfd_curly_variant

    return resolved
