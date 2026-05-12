import builtins

from zebra_label_tool.preview_symbols import (
    encode_code128,
    encode_code39,
    encode_ean13,
    encode_linear_symbol,
    encode_qr_matrix,
    encode_upca,
    normalize_ean13_payload,
    normalize_upca_payload,
    preview_datamatrix_matrix,
    preview_pdf417_matrix,
)


def test_code128_preview_uses_real_start_and_stop_patterns():
    symbol = encode_code128("ABC")
    assert symbol.modules[:6] == ((True, 2), (False, 1), (True, 1), (False, 2), (True, 1), (False, 4))
    assert symbol.modules[-7:] == ((True, 2), (False, 3), (True, 3), (False, 1), (True, 1), (False, 1), (True, 2))


def test_code39_preview_adds_start_stop_and_intercharacter_gap():
    symbol = encode_code39("A-1")
    assert symbol.label == "A-1"
    assert len(symbol.modules) > 30
    assert any(not is_bar and width == 1 for is_bar, width in symbol.modules)


def test_ean_and_upc_preview_compute_missing_check_digits():
    assert normalize_ean13_payload("400638133393") == "4006381333931"
    assert normalize_upca_payload("03600029145") == "036000291452"
    assert encode_ean13("400638133393").label == "4006381333931"
    assert encode_upca("03600029145").label == "036000291452"


def test_linear_dispatch_returns_modules():
    symbol = encode_linear_symbol("code128", "ASSET-1")
    assert symbol.modules
    assert symbol.label == "ASSET-1"


def test_qr_matrix_is_square_matrix_with_quiet_zone():
    matrix = encode_qr_matrix("https://example.local/device/1")
    assert len(matrix.cells) == len(matrix.cells[0])
    assert len(matrix.cells) >= 21
    # qrcode exact mode and the fallback both keep a quiet first row.
    assert not any(matrix.cells[0])


def test_qr_matrix_falls_back_when_optional_qrcode_package_is_missing(monkeypatch):
    real_import = builtins.__import__

    def blocked_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "qrcode" or name.startswith("qrcode."):
            raise ModuleNotFoundError("No module named 'qrcode'")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", blocked_import)
    matrix = encode_qr_matrix("https://example.local/device/1")
    assert matrix.exact is False
    assert len(matrix.cells) == len(matrix.cells[0])
    assert not any(matrix.cells[0])
    assert any(any(row) for row in matrix.cells)


def test_datamatrix_and_pdf417_previews_are_deterministic_layout_previews():
    dm = preview_datamatrix_matrix("PART-42")
    pdf = preview_pdf417_matrix("DOCUMENT")
    assert dm.exact is False
    assert pdf.exact is False
    assert dm.cells == preview_datamatrix_matrix("PART-42").cells
    assert pdf.cells == preview_pdf417_matrix("DOCUMENT").cells
