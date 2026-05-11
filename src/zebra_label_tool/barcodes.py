"""Barcode and 2D code metadata shared by GUI, CLI and ZPL generation."""

from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class BarcodeType:
    key: str
    label: str
    category: str
    default_height: int
    supports_human_readable: bool = True
    supports_magnification: bool = False
    description: str = ""


BARCODE_TYPES: dict[str, BarcodeType] = {
    "code128": BarcodeType("code128", "Code 128", "linear", 40, True, False, "General purpose alphanumeric barcode."),
    "code39": BarcodeType("code39", "Code 39", "linear", 40, True, False, "Older industrial alphanumeric barcode."),
    "ean13": BarcodeType("ean13", "EAN-13", "linear", 55, True, False, "Retail article numbers, 12 or 13 digits."),
    "upca": BarcodeType("upca", "UPC-A", "linear", 55, True, False, "Retail article numbers, 11 or 12 digits."),
    "qr": BarcodeType("qr", "QR Code", "2d", 90, False, True, "Compact 2D code for URLs, IDs and longer payloads."),
    "datamatrix": BarcodeType("datamatrix", "Data Matrix", "2d", 90, False, True, "Small 2D code used on parts and equipment."),
    "pdf417": BarcodeType("pdf417", "PDF417", "2d", 90, False, False, "Stacked 2D code for longer text payloads."),
}

BARCODE_TYPE_LABELS = [barcode.label for barcode in BARCODE_TYPES.values()]
_BARCODE_LABEL_TO_KEY = {barcode.label.lower(): barcode.key for barcode in BARCODE_TYPES.values()}
_BARCODE_KEY_TO_LABEL = {barcode.key: barcode.label for barcode in BARCODE_TYPES.values()}


def normalize_barcode_type(value: str | None) -> str:
    """Return a supported barcode type key."""
    raw = str(value or "code128").strip().lower()
    if raw in BARCODE_TYPES:
        return raw
    raw = raw.replace("_", "-").replace(" ", "")
    aliases = {
        "code-128": "code128",
        "code128": "code128",
        "128": "code128",
        "code-39": "code39",
        "code39": "code39",
        "39": "code39",
        "ean-13": "ean13",
        "ean13": "ean13",
        "ean": "ean13",
        "upc-a": "upca",
        "upca": "upca",
        "upc": "upca",
        "qrcode": "qr",
        "qr-code": "qr",
        "qr": "qr",
        "data-matrix": "datamatrix",
        "datamatrix": "datamatrix",
        "dm": "datamatrix",
        "pdf-417": "pdf417",
        "pdf417": "pdf417",
    }
    if raw in aliases:
        return aliases[raw]
    if str(value or "").strip().lower() in _BARCODE_LABEL_TO_KEY:
        return _BARCODE_LABEL_TO_KEY[str(value or "").strip().lower()]
    raise ValueError(f"Unsupported barcode type: {value}")


def barcode_label(key: str) -> str:
    return _BARCODE_KEY_TO_LABEL.get(normalize_barcode_type(key), "Code 128")


def barcode_key_from_label(label: str) -> str:
    return normalize_barcode_type(label)


def is_2d_barcode(key: str) -> bool:
    return BARCODE_TYPES[normalize_barcode_type(key)].category == "2d"



def _gtin_check_digit(digits_without_check: str) -> str:
    total = 0
    reversed_digits = list(map(int, reversed(digits_without_check)))
    for index, digit in enumerate(reversed_digits):
        total += digit * (3 if index % 2 == 0 else 1)
    return str((10 - (total % 10)) % 10)

def validate_barcode_payload(barcode_type: str, payload: str) -> str:
    """Validate and normalize barcode payload where a symbology has hard constraints."""
    key = normalize_barcode_type(barcode_type)
    text = str(payload or "").strip()
    if not text:
        return text
    if key == "ean13":
        if not re.fullmatch(r"\d{12,13}", text):
            raise ValueError("EAN-13 content must contain 12 or 13 digits")
        if len(text) == 12:
            text += _gtin_check_digit(text)
    if key == "upca":
        if not re.fullmatch(r"\d{11,12}", text):
            raise ValueError("UPC-A content must contain 11 or 12 digits")
        if len(text) == 11:
            text += _gtin_check_digit(text)
    if key == "code39" and not re.fullmatch(r"[0-9A-Z .$/+%-]+", text.upper()):
        raise ValueError("Code 39 supports uppercase letters, digits, spaces and . $ / + % -")
    return text.upper() if key == "code39" else text


def clamp_barcode_height(value: int | str | None, barcode_type: str) -> int:
    key = normalize_barcode_type(barcode_type)
    default = BARCODE_TYPES[key].default_height
    try:
        parsed = int(str(value if value is not None else default).strip())
    except (TypeError, ValueError):
        parsed = default
    return max(20, min(parsed, 240))


def clamp_qr_magnification(value: int | str | None) -> int:
    try:
        parsed = int(str(value if value is not None else 4).strip())
    except (TypeError, ValueError):
        parsed = 4
    return max(1, min(parsed, 10))
