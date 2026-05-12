import pytest

from zebra_label_tool.label_spec import LabelSpec
from zebra_label_tool.number_sequences import (
    NumberSequenceError,
    build_number_sequence_specs,
    format_sequence_value,
    generate_number_sequence_zpl,
    generate_sequence_values,
    normalize_number_sequence_options,
    render_sequence_lines,
)


def test_format_sequence_value_supports_prefix_padding_suffix():
    assert format_sequence_value(7, padding=4, prefix="DEV-", suffix="-A") == "DEV-0007-A"


def test_sequence_values_support_step_and_count():
    options = normalize_number_sequence_options(start=5, count=3, step=2, padding=2, prefix="A")
    assert generate_sequence_values(options) == ("A05", "A07", "A09")


def test_negative_step_is_allowed_but_zero_step_is_rejected():
    options = normalize_number_sequence_options(start=3, count=3, step=-1, padding=1)
    assert generate_sequence_values(options) == ("3", "2", "1")
    with pytest.raises(NumberSequenceError):
        normalize_number_sequence_options(step=0)


def test_render_sequence_lines_supports_placeholders():
    assert render_sequence_lines("Asset {value}\nItem {index}\nRaw {raw}", value="A-007", number=7, index=2) == (
        "Asset A-007",
        "Item 3",
        "Raw 7",
    )


def test_invalid_template_placeholder_is_reported():
    with pytest.raises(NumberSequenceError):
        render_sequence_lines("{missing}", value="001", number=1, index=0)


def test_build_number_sequence_specs_can_use_generated_value_as_barcode():
    base = LabelSpec.from_raw(lines=["Base"], barcode_type="code128", barcode_pos="below")
    options = normalize_number_sequence_options(
        start=1,
        count=2,
        padding=3,
        prefix="AS-",
        line_template="Asset {value}\nShelf A",
        enable_barcode=True,
        barcode_mode="value",
    )
    specs = build_number_sequence_specs(base, options)
    assert specs[0].text_lines == ("Asset AS-001", "Shelf A")
    assert specs[0].barcode is True
    assert specs[0].barcode_text == "AS-001"
    assert specs[1].barcode_text == "AS-002"


def test_build_number_sequence_specs_can_use_first_line_as_barcode():
    base = LabelSpec.from_raw(lines=["Base"], barcode_type="code128")
    options = normalize_number_sequence_options(
        count=1,
        line_template="Cable {value}\nTarget",
        enable_barcode=True,
        barcode_mode="first_line",
    )
    spec = build_number_sequence_specs(base, options)[0]
    assert spec.barcode_text == "Cable 001"


def test_number_sequence_zpl_contains_one_label_per_generated_value():
    base = LabelSpec.from_raw(lines=["Base"], width_mm=57, height_mm=19, dpi=300)
    options = normalize_number_sequence_options(start=9, count=2, padding=2, line_template="No. {value}")
    zpl = generate_number_sequence_zpl(base, options)
    assert zpl.count("^XA") == 2
    assert "^FDNo. 09^FS" in zpl
    assert "^FDNo. 10^FS" in zpl
