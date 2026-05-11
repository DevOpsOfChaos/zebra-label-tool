import pytest

from zebra_label_tool.zpl import generate_zpl


def test_generate_basic_single_line_zpl():
    zpl = generate_zpl("Sonderverschraubungen", "", 57, 17, 58, dpi=300)
    assert zpl.startswith("^XA\n")
    assert "^PW673" in zpl
    assert "^LL201" in zpl
    assert "^FD Sonderverschraubungen" not in zpl
    assert "^FDSonderverschraubungen^FS" in zpl
    assert zpl.endswith("^XZ")


def test_generate_two_line_zpl_uses_zpl_line_break():
    zpl = generate_zpl("QSRL", "QSLV", 57, 19, 58, dpi=300)
    assert "^FDQSRL\\&QSLV^FS" in zpl
    assert "^FB" in zpl


def test_generate_copies_adds_pq():
    zpl = generate_zpl("A", "", 57, 19, 58, copies=3)
    assert "^PQ3,0,1,Y" in zpl


def test_generate_copies_clamps_to_one():
    zpl = generate_zpl("A", "", 57, 19, 58, copies=0)
    assert "^PQ" not in zpl


def test_generate_inverted_label():
    zpl = generate_zpl("A", "", 57, 19, 58, inverted=True)
    assert "^GB" in zpl
    assert "^FR^FDA^FS" in zpl


def test_generate_border():
    zpl = generate_zpl("A", "", 57, 19, 58, border=True)
    assert "^FO2,2^GB" in zpl


def test_generate_barcode():
    zpl = generate_zpl("Shelf", "A-12", 57, 19, 42, barcode=True, barcode_text="A12")
    assert "^BCN,40,Y,N,N" in zpl
    assert "^FDA12^FS" in zpl


def test_generate_barcode_ignores_empty_barcode_text():
    zpl = generate_zpl("Shelf", "A-12", 57, 19, 42, barcode=True, barcode_text="")
    assert "^BCN" not in zpl


@pytest.mark.parametrize("dpi,expected_width", [(203, "^PW456"), (300, "^PW673"), (600, "^PW1346")])
def test_generate_dpi_variants(dpi, expected_width):
    zpl = generate_zpl("A", "", 57, 19, 58, dpi=dpi)
    assert expected_width in zpl


def test_generate_invalid_dimensions_raise_clear_error():
    with pytest.raises(ValueError):
        generate_zpl("A", "", 0, 19, 58)


def test_generate_unknown_font_style_falls_back_to_a0():
    zpl = generate_zpl("A", "", 57, 19, 58, font_style="BAD")
    assert "^A0N," in zpl


def test_generate_multiple_text_lines():
    zpl = generate_zpl(width_mm=57, height_mm=19, font_size=42, lines=["A", "B", "C"])
    assert "^FBA" not in zpl
    assert "^FDA\\&B\\&C^FS" in zpl
    assert "^FB" in zpl


def test_generate_text_alignment_rotation_and_gap():
    zpl = generate_zpl("A", "B", 57, 19, 42, alignment="left", rotation="90", line_gap=18)
    assert "^A0R," in zpl
    assert ",18,L,0" in zpl


def test_generate_offsets_text_origin():
    zpl = generate_zpl("A", "", 57, 19, 42, offset_x=12)
    assert "^FO32," in zpl


def test_generate_qr_code_zpl():
    zpl = generate_zpl("Device", "ESP32", 57, 29, 32, barcode=True, barcode_text="https://example.local/device/1", barcode_type="qr", barcode_magnification=5)
    assert "^BQN,2,5" in zpl
    assert "^FDLA,https://example.local/device/1^FS" in zpl


def test_generate_code39_and_hides_human_text():
    zpl = generate_zpl("A", "", 57, 19, 42, barcode=True, barcode_text="abc-123", barcode_type="code39", barcode_show_text=False)
    assert "^B3N,N," in zpl
    assert ",N,N" in zpl
    assert "^FDABC-123^FS" in zpl


def test_generate_ean13_rejects_non_numeric_content():
    with pytest.raises(ValueError, match="EAN-13"):
        generate_zpl("A", "", 57, 19, 42, barcode=True, barcode_text="ABC", barcode_type="ean13")


def test_generate_datamatrix_and_pdf417_zpl():
    dm = generate_zpl("Part", "", 57, 29, 32, barcode=True, barcode_text="PART-42", barcode_type="datamatrix", barcode_magnification=4)
    pdf = generate_zpl("Part", "", 57, 29, 32, barcode=True, barcode_text="PART-42", barcode_type="pdf417", barcode_height=80)
    assert "^BXN,4,200" in dm
    assert "^B7N,80" in pdf


def test_generate_ean13_adds_check_digit_for_12_digit_payload():
    zpl = generate_zpl("Retail", "", 57, 29, 32, barcode=True, barcode_text="400638133393", barcode_type="ean13")
    assert "^FD4006381333931^FS" in zpl


def test_generate_upca_adds_check_digit_for_11_digit_payload():
    zpl = generate_zpl("Retail", "", 57, 29, 32, barcode=True, barcode_text="03600029145", barcode_type="upca")
    assert "^FD036000291452^FS" in zpl
