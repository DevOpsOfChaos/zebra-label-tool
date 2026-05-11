import pytest

from zebra_label_tool.label_spec import LabelSpec, LabelSpecError


def test_label_spec_accepts_decimal_comma_dimensions():
    spec = LabelSpec.from_raw(width_mm="57,5", height_mm="19", dpi="300", copies="2")
    assert spec.width_mm == 57.5
    assert spec.height_mm == 19
    assert spec.copies == 2


def test_label_spec_generates_zpl():
    spec = LabelSpec.from_raw(line1="Shelf", line2="A-12", border=True)
    zpl = spec.to_zpl()
    assert "^FDShelf\\&A-12^FS" in zpl
    assert "^FO2,2^GB" in zpl


def test_label_spec_rejects_bad_dimensions():
    with pytest.raises(LabelSpecError, match="Width"):
        LabelSpec.from_raw(width_mm="abc")
    with pytest.raises(LabelSpecError, match="Height"):
        LabelSpec.from_raw(height_mm="0")


def test_label_spec_rejects_unsupported_dpi():
    with pytest.raises(LabelSpecError, match="DPI"):
        LabelSpec.from_raw(dpi="999")


def test_label_spec_rejects_bad_copies():
    with pytest.raises(LabelSpecError, match="Copies"):
        LabelSpec.from_raw(copies="0")


def test_label_spec_history_label():
    spec = LabelSpec.from_raw(line1="A", line2="B")
    assert spec.history_label() == "A  |  B"


def test_label_spec_accepts_multiple_text_lines():
    spec = LabelSpec.from_raw(lines=["Line 1", "Line 2", "Line 3"])
    assert spec.text_lines == ("Line 1", "Line 2", "Line 3")
    assert spec.line1 == "Line 1"
    assert spec.line2 == "Line 2"
    assert "^FDLine 1\\&Line 2\\&Line 3^FS" in spec.to_zpl()


def test_label_spec_rejects_too_many_lines():
    with pytest.raises(LabelSpecError, match="at most"):
        LabelSpec.from_raw(lines=[str(i) for i in range(13)])


def test_label_spec_rejects_bad_alignment_and_rotation():
    with pytest.raises(LabelSpecError, match="alignment"):
        LabelSpec.from_raw(alignment="diagonal")
    with pytest.raises(LabelSpecError, match="rotation"):
        LabelSpec.from_raw(rotation="45")


def test_label_spec_supports_offsets_line_gap_and_no_auto_fit():
    spec = LabelSpec.from_raw(lines=["A", "B"], line_gap="18", offset_x="7", offset_y="-2", auto_fit="false")
    assert spec.line_gap == 18
    assert spec.offset_x == 7
    assert spec.offset_y == -2
    assert spec.auto_fit is False
