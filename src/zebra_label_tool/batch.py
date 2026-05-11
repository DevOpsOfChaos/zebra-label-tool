"""Batch label helpers for generating several labels from one base setup."""

from __future__ import annotations

from dataclasses import replace
from collections.abc import Iterable

from .label_spec import LabelSpec, MAX_TEXT_LINES
from .text_tools import normalize_editor_text


def parse_batch_blocks(text: str) -> tuple[tuple[str, ...], ...]:
    """Parse batch text into label text blocks.

    Blank lines separate labels. Lines inside one block become multiple printed
    lines on the same label.
    """
    blocks: list[tuple[str, ...]] = []
    current: list[str] = []
    for raw_line in str(text or "").replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = raw_line.strip()
        if not line:
            if current:
                blocks.append(tuple(current[:MAX_TEXT_LINES]))
                current = []
            continue
        current.append(line)
    if current:
        blocks.append(tuple(current[:MAX_TEXT_LINES]))
    return tuple(blocks)


def build_batch_specs(
    base: LabelSpec,
    blocks: Iterable[Iterable[str]],
    *,
    barcode_from_first_line: bool = False,
) -> tuple[LabelSpec, ...]:
    """Clone a base label spec for several different text blocks."""
    specs: list[LabelSpec] = []
    for block in blocks:
        lines = normalize_editor_text("\n".join(str(line) for line in block), remove_empty=False)
        barcode_text = lines[0].strip() if barcode_from_first_line and lines else base.barcode_text
        specs.append(
            replace(
                base,
                text_lines=tuple(lines[:MAX_TEXT_LINES]) or ("",),
                barcode_text=barcode_text,
            )
        )
    return tuple(specs)


def generate_batch_zpl(
    base: LabelSpec,
    blocks: Iterable[Iterable[str]],
    *,
    barcode_from_first_line: bool = False,
) -> str:
    """Generate one ZPL stream containing multiple labels."""
    specs = build_batch_specs(base, blocks, barcode_from_first_line=barcode_from_first_line)
    return "\n".join(spec.to_zpl() for spec in specs)
