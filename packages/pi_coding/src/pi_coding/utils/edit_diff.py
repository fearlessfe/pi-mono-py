"""
Shared diff computation utilities for the edit tool.
Used by both edit.py (for execution) and tool-execution.py (for preview rendering).

Python port of edit-diff.ts — uses difflib instead of npm's 'diff' package.
"""

from __future__ import annotations

import difflib
import os
import re
from dataclasses import dataclass
from typing import Literal, Optional


def detect_line_ending(content: str) -> Literal["\r\n", "\n"]:
    """Detect the dominant line ending in content."""
    crlf_idx = content.find("\r\n")
    lf_idx = content.find("\n")
    if lf_idx == -1:
        return "\n"
    if crlf_idx == -1:
        return "\n"
    return "\r\n" if crlf_idx < lf_idx else "\n"


def normalize_to_lf(text: str) -> str:
    """Normalize all line endings to LF."""
    return text.replace("\r\n", "\n").replace("\r", "\n")


def restore_line_endings(text: str, ending: str) -> str:
    """Restore line endings to the specified type."""
    return text.replace("\n", "\r\n") if ending == "\r\n" else text


def normalize_for_fuzzy_match(text: str) -> str:
    """
    Normalize text for fuzzy matching. Applies progressive transformations:
    - Strip trailing whitespace from each line
    - Normalize smart quotes to ASCII equivalents
    - Normalize Unicode dashes/hyphens to ASCII hyphen
    - Normalize special Unicode spaces to regular space
    """
    # Strip trailing whitespace per line
    result = "\n".join(line.rstrip() for line in text.split("\n"))
    # Smart single quotes → '
    result = re.sub("[\u2018\u2019\u201a\u201b]", "'", result)
    # Smart double quotes → "
    result = re.sub('[\u201c\u201d\u201e\u201f]', '"', result)
    # Various dashes/hyphens → -
    # U+2010 hyphen, U+2011 non-breaking hyphen, U+2012 figure dash,
    # U+2013 en-dash, U+2014 em-dash, U+2015 horizontal bar, U+2212 minus
    result = re.sub("[\u2010\u2011\u2012\u2013\u2014\u2015\u2212]", "-", result)
    # Special spaces → regular space
    # U+00A0 NBSP, U+2002-U+200A various spaces, U+202F narrow NBSP,
    # U+205F medium math space, U+3000 ideographic space
    result = re.sub("[\u00a0\u2002-\u200a\u202f\u205f\u3000]", " ", result)
    return result


@dataclass
class FuzzyMatchResult:
    """Result of a fuzzy text match."""

    found: bool
    """Whether a match was found."""

    index: int
    """The index where the match starts (in the content used for replacement)."""

    match_length: int
    """Length of the matched text."""

    used_fuzzy_match: bool
    """Whether fuzzy matching was used (False = exact match)."""

    content_for_replacement: str
    """The content to use for replacement operations.
    When exact match: original content.  When fuzzy match: normalized content."""


def fuzzy_find_text(content: str, old_text: str) -> FuzzyMatchResult:
    """
    Find *old_text* in *content*, trying exact match first, then fuzzy match.

    When fuzzy matching is used, the returned ``content_for_replacement`` is the
    fuzzy-normalized version of the content (trailing whitespace stripped,
    Unicode quotes/dashes normalised to ASCII).
    """
    # Try exact match first
    exact_index = content.find(old_text)
    if exact_index != -1:
        return FuzzyMatchResult(
            found=True,
            index=exact_index,
            match_length=len(old_text),
            used_fuzzy_match=False,
            content_for_replacement=content,
        )

    # Try fuzzy match – work entirely in normalized space
    fuzzy_content = normalize_for_fuzzy_match(content)
    fuzzy_old_text = normalize_for_fuzzy_match(old_text)
    fuzzy_index = fuzzy_content.find(fuzzy_old_text)

    if fuzzy_index == -1:
        return FuzzyMatchResult(
            found=False,
            index=-1,
            match_length=0,
            used_fuzzy_match=False,
            content_for_replacement=content,
        )

    # When fuzzy matching, we work in the normalized space for replacement.
    # This means the output will have normalized whitespace/quotes/dashes,
    # which is acceptable since we're fixing minor formatting differences anyway.
    return FuzzyMatchResult(
        found=True,
        index=fuzzy_index,
        match_length=len(fuzzy_old_text),
        used_fuzzy_match=True,
        content_for_replacement=fuzzy_content,
    )


def strip_bom(content: str) -> tuple[str, str]:
    """Strip UTF-8 BOM if present.

    Returns:
        A ``(bom, text)`` tuple where *bom* is the BOM character (or ``""``)
        and *text* is the content without it.
    """
    if content.startswith("\ufeff"):
        return ("\ufeff", content[1:])
    return ("", content)


# ---------------------------------------------------------------------------
# Internal helpers for line-level diffing (replaces npm 'diff' package)
# ---------------------------------------------------------------------------

@dataclass
class _DiffPart:
    """Internal representation of a diff part, analogous to Diff.diffLines output."""

    value: str
    added: bool = False
    removed: bool = False


def _diff_lines(old_content: str, new_content: str) -> list[_DiffPart]:
    """Compute line-level diffs using :mod:`difflib`, returning a list of
    :class:`_DiffPart` objects compatible with the npm ``Diff.diffLines`` shape.
    """
    old_lines = old_content.splitlines(True)
    new_lines = new_content.splitlines(True)

    matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
    parts: list[_DiffPart] = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            parts.append(_DiffPart(value="".join(old_lines[i1:i2])))
        elif tag == "replace":
            parts.append(_DiffPart(value="".join(old_lines[i1:i2]), removed=True))
            parts.append(_DiffPart(value="".join(new_lines[j1:j2]), added=True))
        elif tag == "delete":
            parts.append(_DiffPart(value="".join(old_lines[i1:i2]), removed=True))
        elif tag == "insert":
            parts.append(_DiffPart(value="".join(new_lines[j1:j2]), added=True))

    return parts


# ---------------------------------------------------------------------------
# Public diff generation
# ---------------------------------------------------------------------------

def generate_diff_string(
    old_content: str,
    new_content: str,
    context_lines: int = 4,
) -> dict[str, str | int | None]:
    """Generate a unified diff string with line numbers and context.

    Returns:
        A dict with keys ``"diff"`` (str) and ``"first_changed_line"``
        (int | None).
    """
    parts = _diff_lines(old_content, new_content)
    output: list[str] = []

    old_lines = old_content.split("\n")
    new_lines = new_content.split("\n")
    max_line_num = max(len(old_lines), len(new_lines))
    line_num_width = len(str(max_line_num))

    old_line_num = 1
    new_line_num = 1
    last_was_change = False
    first_changed_line: Optional[int] = None

    for i, part in enumerate(parts):
        raw = part.value.split("\n")
        if raw and raw[-1] == "":
            raw.pop()

        if part.added or part.removed:
            # Capture the first changed line (in the new file)
            if first_changed_line is None:
                first_changed_line = new_line_num

            # Show the change
            for line in raw:
                if part.added:
                    line_num_str = str(new_line_num).rjust(line_num_width)
                    output.append(f"+{line_num_str} {line}")
                    new_line_num += 1
                else:  # removed
                    line_num_str = str(old_line_num).rjust(line_num_width)
                    output.append(f"-{line_num_str} {line}")
                    old_line_num += 1
            last_was_change = True
        else:
            # Context lines – only show a few before/after changes
            next_part_is_change = (
                i < len(parts) - 1
                and (parts[i + 1].added or parts[i + 1].removed)
            )

            if last_was_change or next_part_is_change:
                lines_to_show = list(raw)
                skip_start = 0
                skip_end = 0

                if not last_was_change:
                    # Show only last N lines as leading context
                    skip_start = max(0, len(raw) - context_lines)
                    lines_to_show = raw[skip_start:]

                if not next_part_is_change and len(lines_to_show) > context_lines:
                    # Show only first N lines as trailing context
                    skip_end = len(lines_to_show) - context_lines
                    lines_to_show = lines_to_show[:context_lines]

                # Add ellipsis if we skipped lines at start
                if skip_start > 0:
                    output.append(f" {''.rjust(line_num_width)} ...")
                    old_line_num += skip_start
                    new_line_num += skip_start

                for line in lines_to_show:
                    line_num_str = str(old_line_num).rjust(line_num_width)
                    output.append(f" {line_num_str} {line}")
                    old_line_num += 1
                    new_line_num += 1

                # Add ellipsis if we skipped lines at end
                if skip_end > 0:
                    output.append(f" {''.rjust(line_num_width)} ...")
                    old_line_num += skip_end
                    new_line_num += skip_end
            else:
                # Skip these context lines entirely
                old_line_num += len(raw)
                new_line_num += len(raw)

            last_was_change = False

    return {"diff": "\n".join(output), "first_changed_line": first_changed_line}


# ---------------------------------------------------------------------------
# High-level edit-diff entry point
# ---------------------------------------------------------------------------

@dataclass
class EditDiffResult:
    """Result of a successful diff computation."""

    diff: str
    first_changed_line: Optional[int]


@dataclass
class EditDiffError:
    """Result when diff computation encounters an error."""

    error: str


def compute_edit_diff(
    path: str,
    old_text: str,
    new_text: str,
    cwd: str,
) -> EditDiffResult | EditDiffError:
    """Compute the diff for an edit operation without applying it.

    Used for preview rendering in the TUI before the tool executes.
    """
    # Resolve path relative to cwd
    absolute_path = path if os.path.isabs(path) else os.path.join(cwd, path)

    try:
        # Check if file exists and is readable
        if not os.path.isfile(absolute_path) or not os.access(absolute_path, os.R_OK):
            return EditDiffError(error=f"File not found: {path}")

        # Read the file
        with open(absolute_path, encoding="utf-8") as f:
            raw_content = f.read()

        # Strip BOM before matching (LLM won't include invisible BOM in old_text)
        _, content = strip_bom(raw_content)

        normalized_content = normalize_to_lf(content)
        normalized_old_text = normalize_to_lf(old_text)
        normalized_new_text = normalize_to_lf(new_text)

        # Find the old text using fuzzy matching (tries exact first, then fuzzy)
        match_result = fuzzy_find_text(normalized_content, normalized_old_text)

        if not match_result.found:
            return EditDiffError(
                error=(
                    f"Could not find the exact text in {path}. "
                    "The old text must match exactly including all whitespace and newlines."
                ),
            )

        # Count occurrences using fuzzy-normalized content for consistency
        fuzzy_content = normalize_for_fuzzy_match(normalized_content)
        fuzzy_old_text = normalize_for_fuzzy_match(normalized_old_text)
        occurrences = fuzzy_content.count(fuzzy_old_text)

        if occurrences > 1:
            return EditDiffError(
                error=(
                    f"Found {occurrences} occurrences of the text in {path}. "
                    "The text must be unique. Please provide more context to make it unique."
                ),
            )

        # Compute the new content using the matched position
        # When fuzzy matching was used, content_for_replacement is the normalized version
        base_content = match_result.content_for_replacement
        new_content = (
            base_content[: match_result.index]
            + normalized_new_text
            + base_content[match_result.index + match_result.match_length :]
        )

        # Check if it would actually change anything
        if base_content == new_content:
            return EditDiffError(
                error=(
                    f"No changes would be made to {path}. "
                    "The replacement produces identical content."
                ),
            )

        # Generate the diff
        result = generate_diff_string(base_content, new_content)
        return EditDiffResult(
            diff=str(result["diff"]),
            first_changed_line=int(result["first_changed_line"]) if result["first_changed_line"] is not None else None,
        )

    except Exception as err:
        return EditDiffError(error=str(err))
