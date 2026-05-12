from zebra_label_tool.cli import main


def test_cli_generates_zpl(capsys):
    exit_code = main(["A", "B", "--border"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "^XA" in captured.out
    assert "^FDA\\&B^FS" in captured.out
    assert "^GB" in captured.out


def test_cli_rejects_invalid_width(capsys):
    exit_code = main(["A", "--width-mm", "0"])
    captured = capsys.readouterr()
    assert exit_code == 2
    assert "Width" in captured.err


def test_cli_generates_qr_code(capsys):
    exit_code = main(["Device", "--barcode", "DEV-1", "--barcode-type", "qr", "--barcode-magnification", "5"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "^BQN,2,5" in captured.out
    assert "^FDLA,DEV-1^FS" in captured.out


def test_cli_can_generate_numbered_series(capsys):
    exit_code = main([
        "Asset {value}",
        "Shelf A",
        "--sequence-count",
        "2",
        "--sequence-start",
        "7",
        "--sequence-padding",
        "3",
        "--sequence-prefix",
        "AS-",
    ])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out.count("^XA") == 2
    assert "Asset AS-007" in captured.out
    assert "Asset AS-008" in captured.out


def test_cli_sequence_can_generate_barcodes_from_values(capsys):
    exit_code = main([
        "Asset {value}",
        "--barcode-type",
        "code128",
        "--sequence-count",
        "1",
        "--sequence-enable-barcode",
        "--sequence-barcode-mode",
        "value",
    ])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "^BCN" in captured.out
    assert "^FD001^FS" in captured.out
