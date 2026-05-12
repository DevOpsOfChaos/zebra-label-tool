"""Helpers for generating numbered label series."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, Literal

from .label_spec import LabelSpec, MAX_TEXT_LINES
from .text_tools import normalize_editor_text

BarcodeMode = Literal["none", "value", "first_line", "all_text"]


class NumberSequenceError(ValueError):
    """Raised when a number sequence cannot be generated safely."""


@dataclass(frozen=True)
class NumberSequenceOptions:
    """Configuration for numbered label generation."""

    start: int = 1
    count: int = 10
    step: int = 1
    padding: int = 3
    prefix: str = ""
    suffix: str = ""
    line_template: str = "{value}"
    barcode_mode: BarcodeMode = "none"
    enable_barcode: bool = False


def _parse_int(value: object, field_name: str, *, minimum: int | None = None, maximum: int | None = None) -> int:
    try:
        parsed = int(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise NumberSequenceError(f"{field_name} must be a whole number") from exc
    if minimum is not None and parsed < minimum:
        raise NumberSequenceError(f"{field_name} must be at least {minimum}")
    if maximum is not None and parsed > maximum:
        raise NumberSequenceError(f"{field_name} must be at most {maximum}")
    return parsed


def normalize_number_sequence_options(
    *,
    start: object = 1,
    count: object = 10,
    step: object = 1,
    padding: object = 3,
    prefix: object = "",
    suffix: object = "",
    line_template: object = "{value}",
    barcode_mode: object = "none",
    enable_barcode: object = False,
) -> NumberSequenceOptions:
    """Validate user-supplied sequence settings."""
    parsed_step = _parse_int(step, "Step")
    if parsed_step == 0:
        raise NumberSequenceError("Step must not be zero")
    parsed_count = _parse_int(count, "Count", minimum=1, maximum=5000)
    parsed_padding = _parse_int(padding, "Padding", minimum=0, maximum=12)
    parsed_mode = str(barcode_mode or "none").strip().lower().replace(" ", "_").replace("-", "_")
    aliases = {
        "off": "none",
        "no": "none",
        "number": "value",
        "sequence": "value",
        "generated": "value",
        "first": "first_line",
        "label": "all_text",
        "text": "all_text",
    }
    parsed_mode = aliases.get(parsed_mode, parsed_mode)
    if parsed_mode not in {"none", "value", "first_line", "all_text"}:
        raise NumberSequenceError("Barcode mode must be none, value, first_line, or all_text")
    parsed_template = str(line_template or "{value}").replace("\r\n", "\n").replace("\r", "\n").strip("\n")
    if not parsed_template.strip():
        parsed_template = "{value}"
    return NumberSequenceOptions(
        start=_parse_int(start, "Start"),
        count=parsed_count,
        step=parsed_step,
        padding=parsed_padding,
        prefix=str(prefix or ""),
        suffix=str(suffix or ""),
        line_template=parsed_template,
        barcode_mode=parsed_mode,  # type: ignore[arg-type]
        enable_barcode=_parse_bool(enable_barcode),
    )


def _parse_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return bool(value)


def format_sequence_value(number: int, *, padding: int = 0, prefix: str = "", suffix: str = "") -> str:
    """Format one number with optional zero padding, prefix, and suffix."""
    sign = "-" if number < 0 else ""
    body = str(abs(int(number))).zfill(max(0, int(padding)))
    return f"{prefix}{sign}{body}{suffix}"


def generate_sequence_values(options: NumberSequenceOptions) -> tuple[str, ...]:
    """Return the formatted values for a sequence."""
    return tuple(
        format_sequence_value(options.start + index * options.step, padding=options.padding, prefix=options.prefix, suffix=options.suffix)
        for index in range(options.count)
    )


def render_sequence_lines(template: str, *, value: str, number: int, index: int) -> tuple[str, ...]:
    """Render a multi-line text template for one generated sequence value.

    Supported placeholders:
    - ``{value}`` / ``{number}``: formatted value including prefix/suffix/padding
    - ``{raw}``: raw integer without prefix/suffix
    - ``{index}``: one-based sequence index
    - ``{index0}``: zero-based sequence index
    """
    variables = {
        "value": value,
        "number": value,
        "raw": number,
        "index": index + 1,
        "index0": index,
    }
    try:
        rendered = str(template).format(**variables)
    except (KeyError, ValueError) as exc:
        raise NumberSequenceError(f"Invalid template placeholder: {exc}") from exc
    lines = normalize_editor_text(rendered, remove_empty=False)
    return tuple(lines[:MAX_TEXT_LINES]) or (value,)


def _barcode_payload(mode: BarcodeMode, value: str, lines: Iterable[str]) -> str:
    visible = [str(line).strip() for line in lines if str(line).strip()]
    if mode == "value":
        return value
    if mode == "first_line":
        return visible[0] if visible else value
    if mode == "all_text":
        return " | ".join(visible) or value
    return ""


def build_number_sequence_specs(base: LabelSpec, options: NumberSequenceOptions) -> tuple[LabelSpec, ...]:
    """Clone a base label spec into a numbered label series."""
    specs: list[LabelSpec] = []
    for index in range(options.count):
        number = options.start + index * options.step
        value = format_sequence_value(number, padding=options.padding, prefix=options.prefix, suffix=options.suffix)
        lines = render_sequence_lines(options.line_template, value=value, number=number, index=index)
        barcode_text = _barcode_payload(options.barcode_mode, value, lines)
        specs.append(
            replace(
                base,
                text_lines=lines,
                barcode=options.enable_barcode and options.barcode_mode != "none",
                barcode_text=barcode_text,
            )
        )
    return tuple(specs)


def generate_number_sequence_zpl(base: LabelSpec, options: NumberSequenceOptions) -> str:
    """Generate one ZPL stream for a numbered label series."""
    return "\n".join(spec.to_zpl() for spec in build_number_sequence_specs(base, options))
