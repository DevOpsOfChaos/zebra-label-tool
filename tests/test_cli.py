from zebra_label_tool.cli import main


def test_cli_generates_zpl(capsys):
    exit_code = main(["A", "B", "--border"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "^XA" in captured.out
    assert "^FDA\\&B^FS" in captured.out
    assert "^GB" in captured.out
