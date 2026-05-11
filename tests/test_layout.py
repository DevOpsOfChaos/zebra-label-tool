import pytest

from zebra_label_tool.layout import auto_fontsize, calc_positions, calculate_layout, mm_to_dots


def test_mm_to_dots_common_300_dpi_label_width():
    assert mm_to_dots(57, 300) == 673


def test_mm_to_dots_rejects_invalid_values():
    with pytest.raises(ValueError):
        mm_to_dots(0, 300)
    with pytest.raises(ValueError):
        mm_to_dots(57, 0)


def test_auto_fontsize_keeps_short_text():
    assert auto_fontsize(58, "Short") == 58


def test_auto_fontsize_shrinks_long_text_but_keeps_minimum():
    assert auto_fontsize(58, "X" * 56) == 29
    assert auto_fontsize(20, "X" * 200) == 10


def test_calculate_layout_one_line_no_barcode():
    layout = calculate_layout(
        line1="Sonderverschraubungen",
        line2="",
        width_mm=57,
        height_mm=17,
        font_size=58,
        dpi=300,
        barcode=False,
        barcode_text="",
        barcode_pos="below",
    )
    assert layout.pw == 673
    assert layout.ll == 201
    assert layout.num_lines == 1
    assert layout.has_bar is False
    assert layout.pos_y_text >= 4


def test_calculate_layout_two_lines():
    layout = calculate_layout(
        line1="Line 1",
        line2="Line 2",
        width_mm=57,
        height_mm=19,
        font_size=58,
        dpi=300,
        barcode=False,
        barcode_text="",
        barcode_pos="below",
    )
    assert layout.num_lines == 2
    assert layout.block_h == 126


def test_calculate_layout_with_barcode_below():
    layout = calculate_layout(
        line1="Shelf",
        line2="A-12",
        width_mm=57,
        height_mm=19,
        font_size=42,
        dpi=300,
        barcode=True,
        barcode_text="A12",
        barcode_pos="below",
    )
    assert layout.has_bar is True
    assert layout.pos_y_bar > layout.pos_y_text


def test_calculate_layout_rejects_unknown_barcode_position():
    with pytest.raises(ValueError):
        calculate_layout("A", "", 57, 19, 58, 300, True, "123", "middle")


def test_calc_positions_keeps_legacy_dict_shape():
    result = calc_positions("A", "B", 57, 19, 58, 300, False, "", "below")
    assert result["pw"] == 673
    assert result["num_lines"] == 2
    assert "pos_y_text" in result


def test_calculate_layout_with_barcode_right_reserves_side_area():
    layout = calculate_layout(
        line1="Device",
        line2="ESP32",
        width_mm=57,
        height_mm=29,
        font_size=32,
        dpi=300,
        barcode=True,
        barcode_text="DEV-1",
        barcode_pos="right",
    )
    assert layout.has_bar is True
    assert layout.bar_x > layout.text_x
    assert layout.text_w < layout.pw
    assert layout.bar_w >= 24


def test_calculate_layout_with_barcode_left_places_text_after_code_area():
    layout = calculate_layout("A", "", 57, 29, 32, 300, True, "CODE", "left")
    assert layout.bar_x < layout.text_x
    assert layout.text_w > 0
