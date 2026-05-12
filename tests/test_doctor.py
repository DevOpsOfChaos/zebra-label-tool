from __future__ import annotations

from zebra_label_tool.doctor import check_environment, format_results, main


def test_doctor_reports_python_and_optional_preview_dependency():
    results = check_environment(include_desktop=False)
    names = {result.name for result in results}
    assert "Python" in names
    assert "qrcode" in names
    assert all(result.status in {"OK", "WARN", "INFO", "ERROR"} for result in results)


def test_doctor_format_is_human_readable():
    text = format_results(check_environment(include_desktop=False))
    assert "Zebra Label Tool environment check" in text
    assert "Python" in text


def test_doctor_main_does_not_fail_on_warnings(capsys):
    assert main(["--no-desktop"]) == 0
    captured = capsys.readouterr()
    assert "environment check" in captured.out
