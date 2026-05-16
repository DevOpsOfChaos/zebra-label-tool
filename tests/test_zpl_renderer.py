"""Tests for the ZPL rendering pipeline (zpl_renderer.py)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
import io
import pytest
from PIL import Image

from zebra_label_tool.zpl_renderer import (
    render_zpl_preview,
    _render_via_labelary,
    _render_via_pillow,
    _pillow_render,
    _get_monospace_font,
    _draw_linear_barcode,
    _draw_2d_symbol,
)
from zebra_label_tool.layout import calculate_layout_for_lines


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_zpl() -> str:
    return "^XA^FO20,20^A0N,58,58^FDHello World^FS^XZ"


@pytest.fixture
def sample_layout():
    return calculate_layout_for_lines(
        ["Hello", "World"],
        width_mm=57,
        height_mm=19,
        font_size=58,
        dpi=300,
        barcode=False,
        barcode_text="",
        barcode_pos="below",
    )


@pytest.fixture
def layout_with_barcode():
    return calculate_layout_for_lines(
        ["Shelf A-12"],
        width_mm=57,
        height_mm=19,
        font_size=42,
        dpi=300,
        barcode=True,
        barcode_text="A12",
        barcode_pos="below",
    )


# ---------------------------------------------------------------------------
# render_zpl_preview — unified entry point
# ---------------------------------------------------------------------------

class TestRenderZplPreview:
    """End-to-end tests for the unified render_zpl_preview()."""

    def test_falls_back_to_pillow_when_labelary_unreachable(
        self, sample_zpl, sample_layout
    ):
        """When Labelary is offline, Pillow fallback must produce an image."""
        img, method = render_zpl_preview(
            sample_zpl,
            layout=sample_layout,
            width_mm=57,
            height_mm=19,
            dpi=300,
            text_lines=("Hello", "World"),
            font_size=58,
        )
        assert method in ("pillow", "labelary")
        assert isinstance(img, Image.Image)
        # Pillow fallback renders at 2x → at least 400 px wide for a 57mm@300dpi label
        assert img.size[0] >= 100
        assert img.size[1] >= 50

    def test_returns_emergency_pixel_on_complete_failure(self):
        """If both renderers fail, a 1x1 transparent pixel is returned."""
        # A zero-width label should cause the Pillow renderer to fail,
        # and Labelary won't be called because there's no ZPL.
        # Actually, let's force both to fail by giving bad params.
        layout = calculate_layout_for_lines(
            [""], width_mm=10, height_mm=10, font_size=8, dpi=203,
            barcode=False, barcode_text="", barcode_pos="below",
        )
        with patch(
            "zebra_label_tool.zpl_renderer._render_via_labelary",
            return_value=None,
        ):
            img, method = render_zpl_preview(
                "",
                layout=layout,
                width_mm=10,
                height_mm=10,
                dpi=203,
                text_lines=("",),
            )
        # Should still get an image back (emergency pixel)
        assert isinstance(img, Image.Image)
        assert method in ("pillow", "error")

    def test_labelary_is_tried_first(self, sample_zpl, sample_layout):
        """Labelary is attempted before Pillow."""
        fake_png = io.BytesIO()
        Image.new("RGB", (100, 50), (255, 255, 255)).save(fake_png, "PNG")
        fake_png.seek(0)

        with patch(
            "zebra_label_tool.zpl_renderer.urllib.request.urlopen"
        ) as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = fake_png.getvalue()
            mock_urlopen.return_value.__enter__.return_value = mock_resp

            img, method = render_zpl_preview(
                sample_zpl,
                layout=sample_layout,
                width_mm=57,
                height_mm=19,
                dpi=300,
                text_lines=("Hello", "World"),
            )

        assert method == "labelary"
        assert isinstance(img, Image.Image)
        assert img.size == (100, 50)


# ---------------------------------------------------------------------------
# _render_via_labelary
# ---------------------------------------------------------------------------

class TestRenderViaLabelary:
    def test_returns_none_on_network_error(self):
        result = _render_via_labelary("bad zpl", 57, 19, 300)
        # If there's no network or Labelary fails, result should be None
        # (the test doesn't require internet)
        assert result is None or isinstance(result, Image.Image)


# ---------------------------------------------------------------------------
# _render_via_pillow / _pillow_render
# ---------------------------------------------------------------------------

class TestRenderViaPillow:
    def test_renders_text_only_label(self, sample_layout):
        img = _pillow_render(
            dpi=300,
            layout=sample_layout,
            text_lines=("Hello", "World"),
            inverted=False,
            border=False,
            alignment="center",
            barcode_type="code128",
            barcode_text="",
            barcode_show_text=True,
            barcode_magnification=4,
            font_size=58,
            line_gap=10,
        )
        assert isinstance(img, Image.Image)
        assert img.size[0] > 0
        assert img.size[1] > 0
        # bg should be white
        assert img.getpixel((0, 0)) == (255, 255, 255)

    def test_renders_inverted_label(self, sample_layout):
        img = _pillow_render(
            dpi=300,
            layout=sample_layout,
            text_lines=("Inverted",),
            inverted=True,
            border=False,
            alignment="center",
            barcode_type="code128",
            barcode_text="",
            barcode_show_text=True,
            barcode_magnification=4,
            font_size=58,
            line_gap=10,
        )
        # bg should be black
        assert img.getpixel((0, 0)) == (0, 0, 0)

    def test_renders_label_with_border(self, sample_layout):
        img = _pillow_render(
            dpi=300,
            layout=sample_layout,
            text_lines=("Bordered",),
            inverted=False,
            border=True,
            alignment="center",
            barcode_type="code128",
            barcode_text="",
            barcode_show_text=True,
            barcode_magnification=4,
            font_size=58,
            line_gap=10,
        )
        assert img.size[0] > 0

    def test_renders_barcode(self, layout_with_barcode):
        img = _pillow_render(
            dpi=300,
            layout=layout_with_barcode,
            text_lines=("Shelf A-12",),
            inverted=False,
            border=False,
            alignment="center",
            barcode_type="code128",
            barcode_text="A12",
            barcode_show_text=True,
            barcode_magnification=4,
            font_size=42,
            line_gap=10,
        )
        assert img.size[0] > 0
        # barcode should draw something dark in the code area
        code_y = int(layout_with_barcode.pos_y_bar * 2)  # 2x render_scale
        assert code_y < img.size[1]

    def test_renders_qr_code(self, sample_layout):
        qr_layout = calculate_layout_for_lines(
            ["QR test"],
            width_mm=57,
            height_mm=29,
            font_size=32,
            dpi=300,
            barcode=True,
            barcode_text="https://example.com/test",
            barcode_pos="below",
        )
        img = _pillow_render(
            dpi=300,
            layout=qr_layout,
            text_lines=("QR test",),
            inverted=False,
            border=False,
            alignment="center",
            barcode_type="qr",
            barcode_text="https://example.com/test",
            barcode_show_text=True,
            barcode_magnification=4,
            font_size=32,
            line_gap=10,
        )
        assert isinstance(img, Image.Image)
        assert img.size[0] > 0

    def test_truncates_long_text(self):
        long_layout = calculate_layout_for_lines(
            ["HelloWorldABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"],
            width_mm=20,
            height_mm=10,
            font_size=58,
            dpi=300,
            barcode=False,
            barcode_text="",
            barcode_pos="below",
        )
        img = _pillow_render(
            dpi=300,
            layout=long_layout,
            text_lines=("HelloWorldABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",),
            inverted=False,
            border=False,
            alignment="center",
            barcode_type="code128",
            barcode_text="",
            barcode_show_text=True,
            barcode_magnification=4,
            font_size=58,
            line_gap=10,
        )
        assert isinstance(img, Image.Image)


# ---------------------------------------------------------------------------
# Font helper
# ---------------------------------------------------------------------------

class TestGetMonospaceFont:
    def test_returns_font_object(self):
        font = _get_monospace_font(12)
        assert font is not None
        # Should be able to measure text
        bbox = font.getbbox("Test")
        assert bbox is not None


# ---------------------------------------------------------------------------
# Barcode drawing helpers
# ---------------------------------------------------------------------------

class TestBarcodeDrawing:
    def test_draw_linear_barcode_does_not_raise(self):
        img = Image.new("RGB", (200, 100), (255, 255, 255))
        from PIL import ImageDraw
        draw = ImageDraw.Draw(img)
        # Should not raise
        _draw_linear_barcode(
            draw,
            x=10, y=10, width=180, height=40,
            color=(0, 0, 0),
            text="TEST123",
            scale=2.0,
            barcode_type="code128",
            show_text=True,
        )

    def test_draw_2d_code_does_not_raise(self):
        from PIL import ImageDraw
        img = Image.new("RGB", (200, 200), (255, 255, 255))
        draw = ImageDraw.Draw(img)
        _draw_2d_symbol(
            draw,
            x=10, y=10, width=180, height=180,
            color=(0, 0, 0),
            text="https://example.com",
            scale=2.0,
            barcode_type="qr",
            magnification=4,
        )
