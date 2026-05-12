"""Small command line interface for generating ZPL without starting the GUI."""

from __future__ import annotations

import argparse
import sys

from .barcodes import BARCODE_TYPES
from .label_spec import LabelSpec, LabelSpecError
from .number_sequences import NumberSequenceError, generate_number_sequence_zpl, normalize_number_sequence_options


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate simple Zebra/ZPL labels.")
    parser.add_argument("line1", help="First label line")
    parser.add_argument("line2", nargs="?", default="", help="Optional second label line")
    parser.add_argument("--line", action="append", dest="extra_lines", default=[], help="Additional text line. Can be used multiple times.")
    parser.add_argument("--width-mm", type=str, default="57", help="Label width in millimetres")
    parser.add_argument("--height-mm", type=str, default="19", help="Label height in millimetres")
    parser.add_argument("--dpi", type=str, default="300", help="Printer DPI: 203, 300, or 600")
    parser.add_argument("--font-size", type=str, default="58", help="ZPL font size in dots")
    parser.add_argument("--font-style", choices=["A0", "A"], default="A0")
    parser.add_argument("--alignment", choices=["left", "center", "right", "justify"], default="center")
    parser.add_argument("--rotation", choices=["normal", "90", "180", "270"], default="normal")
    parser.add_argument("--line-gap", type=str, default="10", help="Gap between text lines in dots")
    parser.add_argument("--offset-x", type=str, default="0", help="Horizontal text/barcode offset in dots")
    parser.add_argument("--offset-y", type=str, default="0", help="Vertical text/barcode offset in dots")
    parser.add_argument("--no-auto-fit", action="store_true", help="Disable automatic font shrinking")
    parser.add_argument("--copies", type=str, default="1", help="Number of copies")
    parser.add_argument("--inverted", action="store_true", help="Print white-on-black")
    parser.add_argument("--border", action="store_true", help="Draw a border")
    parser.add_argument("--barcode", default="", help="Optional barcode/2D-code content")
    parser.add_argument("--barcode-type", choices=list(BARCODE_TYPES), default="code128", help="Barcode/2D-code type")
    parser.add_argument("--barcode-pos", choices=["above", "below", "left", "right"], default="below")
    parser.add_argument("--barcode-height", type=str, default="40", help="Linear barcode height or reserved 2D-code area in dots")
    parser.add_argument("--hide-barcode-text", action="store_true", help="Hide human-readable text below linear barcodes")
    parser.add_argument("--barcode-magnification", type=str, default="4", help="QR/Data Matrix module magnification")

    parser.add_argument("--sequence-count", type=str, default="0", help="Generate a numbered label series instead of one label")
    parser.add_argument("--sequence-start", type=str, default="1", help="First number for --sequence-count")
    parser.add_argument("--sequence-step", type=str, default="1", help="Step between numbers for --sequence-count")
    parser.add_argument("--sequence-padding", type=str, default="3", help="Zero-padding width for generated numbers")
    parser.add_argument("--sequence-prefix", default="", help="Text before each generated number")
    parser.add_argument("--sequence-suffix", default="", help="Text after each generated number")
    parser.add_argument("--sequence-template", default="", help="Text template for each numbered label. Supports {value}, {raw}, {index}, {index0}.")
    parser.add_argument("--sequence-enable-barcode", action="store_true", help="Enable barcode/QR for every generated number label")
    parser.add_argument("--sequence-barcode-mode", choices=["none", "value", "first_line", "all_text"], default="value", help="Barcode payload source for numbered labels")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    lines = [args.line1]
    if args.line2:
        lines.append(args.line2)
    lines.extend(args.extra_lines)
    try:
        spec = LabelSpec.from_raw(
            lines=lines,
            width_mm=args.width_mm,
            height_mm=args.height_mm,
            dpi=args.dpi,
            font_size=args.font_size,
            font_style=args.font_style,
            alignment=args.alignment,
            rotation=args.rotation,
            line_gap=args.line_gap,
            offset_x=args.offset_x,
            offset_y=args.offset_y,
            auto_fit=not args.no_auto_fit,
            copies=args.copies,
            inverted=args.inverted,
            border=args.border,
            barcode=bool(args.barcode),
            barcode_text=args.barcode,
            barcode_type=args.barcode_type,
            barcode_pos=args.barcode_pos,
            barcode_height=args.barcode_height,
            barcode_show_text=not args.hide_barcode_text,
            barcode_magnification=args.barcode_magnification,
        )
    except LabelSpecError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    try:
        sequence_count = int(str(args.sequence_count).strip())
    except ValueError:
        print("error: Sequence count must be a whole number", file=sys.stderr)
        return 2

    if sequence_count < 0:
        print("error: Sequence count must be at least 0", file=sys.stderr)
        return 2

    if sequence_count > 0:
        template = args.sequence_template or "\n".join(lines)
        try:
            options = normalize_number_sequence_options(
                start=args.sequence_start,
                count=args.sequence_count,
                step=args.sequence_step,
                padding=args.sequence_padding,
                prefix=args.sequence_prefix,
                suffix=args.sequence_suffix,
                line_template=template,
                enable_barcode=args.sequence_enable_barcode,
                barcode_mode=args.sequence_barcode_mode if args.sequence_enable_barcode else "none",
            )
            print(generate_number_sequence_zpl(spec, options))
        except NumberSequenceError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        return 0

    print(spec.to_zpl())
    return 0
