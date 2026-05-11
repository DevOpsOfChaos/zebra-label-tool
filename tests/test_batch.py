from zebra_label_tool.batch import build_batch_specs, generate_batch_zpl, parse_batch_blocks
from zebra_label_tool.label_spec import LabelSpec


def test_parse_batch_blocks_uses_blank_lines_as_label_separator():
    assert parse_batch_blocks("A\nRack 1\n\nB\nRack 2\n") == (("A", "Rack 1"), ("B", "Rack 2"))


def test_generate_batch_zpl_contains_one_label_per_block():
    spec = LabelSpec.from_raw(lines=["BASE"], width_mm=57, height_mm=19, dpi=300)
    zpl = generate_batch_zpl(spec, [("A",), ("B",)])
    assert zpl.count("^XA") == 2
    assert "^FDA^FS" in zpl
    assert "^FDB^FS" in zpl


def test_batch_can_use_first_line_as_barcode():
    spec = LabelSpec.from_raw(lines=["BASE"], barcode=True, barcode_text="BASE")
    specs = build_batch_specs(spec, [("A-1", "Rack"), ("A-2",)], barcode_from_first_line=True)
    assert specs[0].barcode_text == "A-1"
    assert specs[1].barcode_text == "A-2"
