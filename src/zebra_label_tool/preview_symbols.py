"""Preview symbol builders for barcodes and QR codes.

The printer remains the source of truth for the final ZPL rendering. These helpers
build high-fidelity local preview patterns for the symbologies where a compact
pure-Python implementation is practical. QR uses the optional `qrcode` package
which is declared as a runtime dependency.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Iterable

from .barcodes import normalize_barcode_type, validate_barcode_payload


@dataclass(frozen=True)
class LinearSymbol:
    """Alternating barcode modules, starting with a bar."""

    modules: tuple[tuple[bool, int], ...]
    label: str


@dataclass(frozen=True)
class MatrixSymbol:
    """2D preview matrix. True cells are dark modules."""

    cells: tuple[tuple[bool, ...], ...]
    label: str
    exact: bool = True


_CODE39_PATTERNS = {
    "0": "nnnwwnwnn", "1": "wnnwnnnnw", "2": "nnwwnnnnw", "3": "wnwwnnnnn",
    "4": "nnnwwnnnw", "5": "wnnwwnnnn", "6": "nnwwwnnnn", "7": "nnnwnnwnw",
    "8": "wnnwnnwnn", "9": "nnwwnnwnn", "A": "wnnnnwnnw", "B": "nnwnnwnnw",
    "C": "wnwnnwnnn", "D": "nnnnwwnnw", "E": "wnnnwwnnn", "F": "nnwnwwnnn",
    "G": "nnnnnwwnw", "H": "wnnnnwwnn", "I": "nnwnnwwnn", "J": "nnnnwwwnn",
    "K": "wnnnnnnww", "L": "nnwnnnnww", "M": "wnwnnnnwn", "N": "nnnnwnnww",
    "O": "wnnnwnnwn", "P": "nnwnwnnwn", "Q": "nnnnnnwww", "R": "wnnnnnwwn",
    "S": "nnwnnnwwn", "T": "nnnnwnwwn", "U": "wwnnnnnnw", "V": "nwwnnnnnw",
    "W": "wwwnnnnnn", "X": "nwnnwnnnw", "Y": "wwnnwnnnn", "Z": "nwwnwnnnn",
    "-": "nwnnnnwnw", ".": "wwnnnnwnn", " ": "nwwnnnwnn", "$": "nwnwnwnnn",
    "/": "nwnwnnnwn", "+": "nwnnnwnwn", "%": "nnnwnwnwn", "*": "nwnnwnwnn",
}

# Code 128 patterns from ISO/IEC 15417 table. Each string is bar/space widths.
_CODE128_PATTERNS = (
    "212222", "222122", "222221", "121223", "121322", "131222", "122213", "122312", "132212", "221213",
    "221312", "231212", "112232", "122132", "122231", "113222", "123122", "123221", "223211", "221132",
    "221231", "213212", "223112", "312131", "311222", "321122", "321221", "312212", "322112", "322211",
    "212123", "212321", "232121", "111323", "131123", "131321", "112313", "132113", "132311", "211313",
    "231113", "231311", "112133", "112331", "132131", "113123", "113321", "133121", "313121", "211331",
    "231131", "213113", "213311", "213131", "311123", "311321", "331121", "312113", "312311", "332111",
    "314111", "221411", "431111", "111224", "111422", "121124", "121421", "141122", "141221", "112214",
    "112412", "122114", "122411", "142112", "142211", "241211", "221114", "413111", "241112", "134111",
    "111242", "121142", "121241", "114212", "124112", "124211", "411212", "421112", "421211", "212141",
    "214121", "412121", "111143", "111341", "131141", "114113", "114311", "411113", "411311", "113141",
    "114131", "311141", "411131", "211412", "211214", "211232", "2331112",
)

_L_CODES = {
    "0": "0001101", "1": "0011001", "2": "0010011", "3": "0111101", "4": "0100011",
    "5": "0110001", "6": "0101111", "7": "0111011", "8": "0110111", "9": "0001011",
}
_G_CODES = {
    "0": "0100111", "1": "0110011", "2": "0011011", "3": "0100001", "4": "0011101",
    "5": "0111001", "6": "0000101", "7": "0010001", "8": "0001001", "9": "0010111",
}
_R_CODES = {
    "0": "1110010", "1": "1100110", "2": "1101100", "3": "1000010", "4": "1011100",
    "5": "1001110", "6": "1010000", "7": "1000100", "8": "1001000", "9": "1110100",
}
_EAN_PARITY = {
    "0": "LLLLLL", "1": "LLGLGG", "2": "LLGGLG", "3": "LLGGGL", "4": "LGLLGG",
    "5": "LGGLLG", "6": "LGGGLL", "7": "LGLGLG", "8": "LGLGGL", "9": "LGGLGL",
}


def _bits_to_modules(bits: str) -> tuple[tuple[bool, int], ...]:
    if not bits:
        return tuple()
    modules: list[tuple[bool, int]] = []
    current = bits[0] == "1"
    count = 0
    for bit in bits:
        is_bar = bit == "1"
        if is_bar == current:
            count += 1
        else:
            modules.append((current, count))
            current = is_bar
            count = 1
    modules.append((current, count))
    return tuple(modules)


def _width_pattern_to_modules(patterns: Iterable[str]) -> tuple[tuple[bool, int], ...]:
    modules: list[tuple[bool, int]] = []
    for pattern in patterns:
        for index, width in enumerate(pattern):
            modules.append((index % 2 == 0, int(width)))
    return tuple(modules)


def _gtin_check_digit(digits_without_check: str) -> str:
    total = 0
    reversed_digits = list(map(int, reversed(digits_without_check)))
    for index, digit in enumerate(reversed_digits):
        total += digit * (3 if index % 2 == 0 else 1)
    return str((10 - (total % 10)) % 10)


def normalize_ean13_payload(payload: str) -> str:
    text = validate_barcode_payload("ean13", payload)
    if len(text) == 12:
        text += _gtin_check_digit(text)
    return text


def normalize_upca_payload(payload: str) -> str:
    text = validate_barcode_payload("upca", payload)
    if len(text) == 11:
        text += _gtin_check_digit(text)
    return text


def encode_code39(payload: str) -> LinearSymbol:
    text = validate_barcode_payload("code39", payload)
    full = f"*{text}*"
    modules: list[tuple[bool, int]] = []
    for char_index, char in enumerate(full):
        pattern = _CODE39_PATTERNS[char]
        for index, width in enumerate(pattern):
            modules.append((index % 2 == 0, 3 if width == "w" else 1))
        if char_index != len(full) - 1:
            modules.append((False, 1))
    return LinearSymbol(tuple(modules), text)


def encode_code128(payload: str) -> LinearSymbol:
    text = validate_barcode_payload("code128", payload)
    codes = [104]  # Start B
    for char in text:
        ordinal = ord(char)
        if ordinal < 32 or ordinal > 127:
            # Keep preview robust; ZPL/printer handles broader subsets differently.
            ordinal = ord("?")
        codes.append(ordinal - 32)
    checksum = codes[0] + sum(index * code for index, code in enumerate(codes[1:], start=1))
    codes.append(checksum % 103)
    codes.append(106)
    return LinearSymbol(_width_pattern_to_modules(_CODE128_PATTERNS[code] for code in codes), text)


def encode_ean13(payload: str) -> LinearSymbol:
    text = normalize_ean13_payload(payload)
    first = text[0]
    left = text[1:7]
    right = text[7:]
    parity = _EAN_PARITY[first]
    bits = "101"
    for digit, side in zip(left, parity):
        bits += _L_CODES[digit] if side == "L" else _G_CODES[digit]
    bits += "01010"
    for digit in right:
        bits += _R_CODES[digit]
    bits += "101"
    return LinearSymbol(_bits_to_modules(bits), text)


def encode_upca(payload: str) -> LinearSymbol:
    text = normalize_upca_payload(payload)
    bits = "101"
    for digit in text[:6]:
        bits += _L_CODES[digit]
    bits += "01010"
    for digit in text[6:]:
        bits += _R_CODES[digit]
    bits += "101"
    return LinearSymbol(_bits_to_modules(bits), text)


def encode_linear_symbol(barcode_type: str, payload: str) -> LinearSymbol:
    key = normalize_barcode_type(barcode_type)
    if key == "code128":
        return encode_code128(payload)
    if key == "code39":
        return encode_code39(payload)
    if key == "ean13":
        return encode_ean13(payload)
    if key == "upca":
        return encode_upca(payload)
    raise ValueError(f"No linear preview encoder for {barcode_type}")


def encode_qr_matrix(payload: str, *, border: int = 4) -> MatrixSymbol:
    import qrcode
    from qrcode.constants import ERROR_CORRECT_M

    qr = qrcode.QRCode(version=None, error_correction=ERROR_CORRECT_M, box_size=1, border=max(0, int(border)))
    qr.add_data(str(payload or ""))
    qr.make(fit=True)
    matrix = tuple(tuple(bool(cell) for cell in row) for row in qr.get_matrix())
    return MatrixSymbol(matrix, str(payload or ""), exact=True)


def _hash_bits(payload: str, count: int) -> list[int]:
    bits: list[int] = []
    seed = sha256(str(payload or "").encode("utf-8")).digest()
    while len(bits) < count:
        for byte in seed:
            for shift in range(8):
                bits.append((byte >> shift) & 1)
                if len(bits) >= count:
                    break
            if len(bits) >= count:
                break
        seed = sha256(seed).digest()
    return bits


def preview_datamatrix_matrix(payload: str, size: int = 18) -> MatrixSymbol:
    size = max(12, min(int(size), 36))
    bits = _hash_bits(payload, size * size)
    cells: list[list[bool]] = []
    index = 0
    for row in range(size):
        line: list[bool] = []
        for col in range(size):
            if col == 0 or row == size - 1:
                line.append(True)  # solid L finder
            elif row == 0 or col == size - 1:
                line.append((row + col) % 2 == 0)  # alternating timing border
            else:
                line.append(bool(bits[index]))
                index += 1
        cells.append(line)
    return MatrixSymbol(tuple(tuple(row) for row in cells), "Data Matrix preview", exact=False)


def preview_pdf417_matrix(payload: str, rows: int = 9, cols: int = 34) -> MatrixSymbol:
    rows = max(5, min(int(rows), 20))
    cols = max(18, min(int(cols), 72))
    bits = _hash_bits(payload, rows * cols)
    cells: list[list[bool]] = []
    index = 0
    for row in range(rows):
        line: list[bool] = []
        for col in range(cols):
            # visually stable start/stop guard zones, hashed payload in the middle
            if col in {0, 1, 3, cols - 4, cols - 2, cols - 1}:
                line.append(True)
            elif col in {2, cols - 3}:
                line.append(False)
            else:
                line.append(bool(bits[index]))
                index += 1
        cells.append(line)
    return MatrixSymbol(tuple(tuple(row) for row in cells), "PDF417 preview", exact=False)


def encode_matrix_symbol(barcode_type: str, payload: str, *, magnification: int = 4) -> MatrixSymbol:
    key = normalize_barcode_type(barcode_type)
    if key == "qr":
        return encode_qr_matrix(payload)
    if key == "datamatrix":
        return preview_datamatrix_matrix(payload, size=max(14, int(magnification or 4) * 4))
    if key == "pdf417":
        return preview_pdf417_matrix(payload)
    raise ValueError(f"No matrix preview encoder for {barcode_type}")
