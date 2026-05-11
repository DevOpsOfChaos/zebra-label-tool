"""Text preparation helpers used by the GUI and tests."""

from __future__ import annotations

import re
import textwrap
from collections.abc import Iterable


WhitespaceMode = str
TextTransform = str


def normalize_editor_text(text: str, *, remove_empty: bool = False, collapse_spaces: bool = False) -> tuple[str, ...]:
    """Normalize text from the multi-line editor without destroying useful content.

    Trailing whitespace is always removed. Leading whitespace is removed because ZPL
    labels rarely need accidental indentation. Empty lines can be preserved or
    removed depending on the caller.
    """
    lines = str(text or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    cleaned: list[str] = []
    for line in lines:
        value = line.strip()
        if collapse_spaces:
            value = re.sub(r"\s+", " ", value)
        if remove_empty and not value:
            continue
        cleaned.append(value)
    while cleaned and not cleaned[-1]:
        cleaned.pop()
    return tuple(cleaned or [""])


def transform_lines(lines: Iterable[str], transform: TextTransform) -> tuple[str, ...]:
    """Apply a predictable text transform to label lines."""
    normalized = [str(line) for line in lines]
    mode = str(transform or "").strip().lower().replace("-", "_")
    if mode == "uppercase":
        return tuple(line.upper() for line in normalized)
    if mode == "lowercase":
        return tuple(line.lower() for line in normalized)
    if mode in {"title", "title_case"}:
        return tuple(line.title() for line in normalized)
    if mode == "strip":
        return tuple(line.strip() for line in normalized)
    if mode in {"remove_empty", "compact"}:
        return tuple(line for line in (item.strip() for item in normalized) if line) or ("",)
    raise ValueError(f"Unsupported text transform: {transform}")


def wrap_lines(lines: Iterable[str], max_chars: int, *, max_lines: int = 12) -> tuple[str, ...]:
    """Wrap long editor lines into multiple printable label lines."""
    if max_chars < 4:
        raise ValueError("max_chars must be at least 4")
    if max_lines < 1:
        raise ValueError("max_lines must be at least 1")

    wrapped: list[str] = []
    for line in lines:
        text = str(line).strip()
        if not text:
            wrapped.append("")
            continue
        parts = textwrap.wrap(text, width=max_chars, break_long_words=False, break_on_hyphens=False)
        wrapped.extend(parts or [text])
        if len(wrapped) >= max_lines:
            break
    return tuple(wrapped[:max_lines] or [""])
