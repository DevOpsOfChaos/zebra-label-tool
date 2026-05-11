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
