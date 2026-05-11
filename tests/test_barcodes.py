import pytest

from zebra_label_tool.barcodes import (
    barcode_label,
    clamp_barcode_height,
    clamp_qr_magnification,
    normalize_barcode_type,
    validate_barcode_payload,
)


def test_normalize_barcode_type_accepts_labels_and_aliases():
    assert normalize_barcode_type("QR Code") == "qr"
    assert normalize_barcode_type("code-128") == "code128"
    assert normalize_barcode_type("Data Matrix") == "datamatrix"
    assert barcode_label("upca") == "UPC-A"


def test_ean_and_upc_payload_validation():
    assert validate_barcode_payload("ean13", "4006381333931") == "4006381333931"
    assert validate_barcode_payload("upca", "036000291452") == "036000291452"
    with pytest.raises(ValueError, match="EAN-13"):
        validate_barcode_payload("ean13", "ABC")
    with pytest.raises(ValueError, match="UPC-A"):
        validate_barcode_payload("upca", "123")


def test_code39_payload_is_uppercase_and_restricted():
    assert validate_barcode_payload("code39", "ab 12") == "AB 12"
    with pytest.raises(ValueError, match="Code 39"):
        validate_barcode_payload("code39", "ä")


def test_barcode_size_clamps_are_safe():
    assert clamp_barcode_height("1", "code128") == 20
    assert clamp_barcode_height("999", "code128") == 240
    assert clamp_qr_magnification("0") == 1
    assert clamp_qr_magnification("99") == 10
