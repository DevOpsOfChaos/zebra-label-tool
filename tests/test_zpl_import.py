from zebra_label_tool.zpl import generate_zpl
from zebra_label_tool.zpl_import import parse_simple_zpl


def test_parse_simple_zpl_recovers_two_lines_and_size():
    zpl = generate_zpl("Shelf", "A-12", 57, 19, 42, dpi=300, copies=3, border=True)
    imported = parse_simple_zpl(zpl, dpi=300)
    assert imported.line1 == "Shelf"
    assert imported.line2 == "A-12"
    assert imported.width_mm == 57.0
    assert imported.height_mm == 19.0
    assert imported.copies == 3
    assert imported.border is True
    assert imported.font_size == 42


def test_parse_simple_zpl_recovers_barcode():
    zpl = generate_zpl("Shelf", "A-12", 57, 19, 42, barcode=True, barcode_text="A12")
    imported = parse_simple_zpl(zpl)
    assert imported.barcode is True
    assert imported.barcode_text == "A12"
    assert imported.barcode_pos == "below"


def test_parse_simple_zpl_recovers_inverted():
    zpl = generate_zpl("A", "", 57, 19, 58, inverted=True)
    imported = parse_simple_zpl(zpl)
    assert imported.inverted is True


def test_parse_simple_zpl_recovers_multiple_lines_and_text_options():
    zpl = generate_zpl(width_mm=57, height_mm=19, font_size=42, lines=["A", "B", "C"], alignment="right", rotation="90", line_gap=18)
    imported = parse_simple_zpl(zpl)
    assert imported.text_lines == ("A", "B", "C")
    assert imported.line1 == "A"
    assert imported.line2 == "B"
    assert imported.alignment == "right"
    assert imported.rotation == "90"
    assert imported.line_gap == 18


def test_parse_simple_zpl_recovers_qr_code():
    zpl = generate_zpl("Device", "ESP32", 57, 29, 32, barcode=True, barcode_text="DEV-1", barcode_type="qr", barcode_magnification=5)
    imported = parse_simple_zpl(zpl)
    assert imported.barcode is True
    assert imported.barcode_type == "qr"
    assert imported.barcode_text == "DEV-1"
    assert imported.barcode_magnification == 5
