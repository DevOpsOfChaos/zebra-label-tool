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
