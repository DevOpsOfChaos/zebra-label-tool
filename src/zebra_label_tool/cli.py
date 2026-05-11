"""Small command line interface for generating ZPL without starting the GUI."""

from __future__ import annotations

import argparse

from .zpl import generate_zpl


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate simple Zebra/ZPL labels.")
    parser.add_argument("line1", help="First label line")
    parser.add_argument("line2", nargs="?", default="", help="Optional second label line")
    parser.add_argument("--width-mm", type=float, default=57, help="Label width in millimetres")
    parser.add_argument("--height-mm", type=float, default=19, help="Label height in millimetres")
    parser.add_argument("--dpi", type=int, default=300, choices=[203, 300, 600], help="Printer DPI")
    parser.add_argument("--font-size", type=int, default=58, help="ZPL font size in dots")
    parser.add_argument("--copies", type=int, default=1, help="Number of copies")
    parser.add_argument("--inverted", action="store_true", help="Print white-on-black")
    parser.add_argument("--border", action="store_true", help="Draw a border")
    parser.add_argument("--barcode", default="", help="Optional Code128 barcode content")
    parser.add_argument("--barcode-pos", choices=["above", "below"], default="below")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    print(
        generate_zpl(
            line1=args.line1,
            line2=args.line2,
            width_mm=args.width_mm,
            height_mm=args.height_mm,
            font_size=args.font_size,
            dpi=args.dpi,
            copies=args.copies,
            inverted=args.inverted,
            border=args.border,
            barcode=bool(args.barcode),
            barcode_text=args.barcode,
            barcode_pos=args.barcode_pos,
        )
    )
    return 0
