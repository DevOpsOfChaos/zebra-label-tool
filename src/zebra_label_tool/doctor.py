"""Environment diagnostics for Zebra Label Tool development and packaging."""

from __future__ import annotations

from dataclasses import dataclass
from importlib.util import find_spec
from pathlib import Path
import platform
import shutil
import sys


@dataclass(frozen=True)
class CheckResult:
    name: str
    status: str
    detail: str

    @property
    def is_error(self) -> bool:
        return self.status == "ERROR"


def _repo_root() -> Path:
    # src/zebra_label_tool/doctor.py -> src -> repo root in an editable/dev tree.
    return Path(__file__).resolve().parents[2]


def _command_version(command: str, *args: str) -> str | None:
    executable = shutil.which(command)
    if not executable:
        return None
    return executable


def check_environment(*, include_desktop: bool = True, repo_root: Path | None = None) -> list[CheckResult]:
    """Return local diagnostics without mutating the system."""

    root = repo_root or _repo_root()
    results: list[CheckResult] = []

    py_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    if sys.version_info >= (3, 10):
        results.append(CheckResult("Python", "OK", f"{py_version} at {sys.executable}"))
    else:
        results.append(CheckResult("Python", "ERROR", f"{py_version}; Python 3.10+ is required"))

    customtkinter_available = find_spec("customtkinter") is not None
    results.append(
        CheckResult(
            "customtkinter",
            "OK" if customtkinter_available else "WARN",
            "installed; legacy Python GUI can start" if customtkinter_available else "missing; install requirements.txt for the legacy Python GUI",
        )
    )

    qrcode_available = find_spec("qrcode") is not None
    results.append(
        CheckResult(
            "qrcode",
            "OK" if qrcode_available else "WARN",
            "installed; Python QR previews are exact" if qrcode_available else "missing; Python QR preview uses deterministic fallback, install requirements.txt for exact preview",
        )
    )

    if platform.system() == "Windows":
        pywin32_available = find_spec("win32print") is not None
        results.append(
            CheckResult(
                "pywin32 / win32print",
                "OK" if pywin32_available else "WARN",
                "installed; Windows RAW printing is available" if pywin32_available else "missing; install requirements.txt before printing from Python",
            )
        )
    else:
        results.append(CheckResult("pywin32 / win32print", "INFO", "not required on this non-Windows environment"))

    desktop_dir = root / "desktop"
    if include_desktop and desktop_dir.exists():
        for command, label in (("node", "Node.js"), ("npm", "npm"), ("cargo", "Cargo")):
            found = _command_version(command)
            results.append(
                CheckResult(
                    label,
                    "OK" if found else "WARN",
                    found or f"{command} not found on PATH; required for Tauri development",
                )
            )

        icon = desktop_dir / "src-tauri" / "icons" / "icon.ico"
        results.append(
            CheckResult(
                "Tauri Windows icon",
                "OK" if icon.is_file() else "ERROR",
                str(icon) if icon.is_file() else "missing desktop/src-tauri/icons/icon.ico",
            )
        )

        package_json = desktop_dir / "package.json"
        results.append(
            CheckResult(
                "Tauri package.json",
                "OK" if package_json.is_file() else "ERROR",
                str(package_json) if package_json.is_file() else "missing desktop/package.json",
            )
        )

    return results


def format_results(results: list[CheckResult]) -> str:
    width = max((len(result.name) for result in results), default=8)
    lines = ["Zebra Label Tool environment check", ""]
    for result in results:
        lines.append(f"{result.status:<5} {result.name:<{width}}  {result.detail}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    strict = "--strict" in args
    include_desktop = "--no-desktop" not in args
    results = check_environment(include_desktop=include_desktop)
    print(format_results(results))
    if strict and any(result.is_error for result in results):
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
