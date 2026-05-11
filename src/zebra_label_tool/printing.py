"""Printer discovery and RAW ZPL printing backend."""

from __future__ import annotations

try:  # pragma: no cover - availability depends on Windows + pywin32
    import win32print

    WINDOWS_PRINT_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised through constant checks
    win32print = None
    WINDOWS_PRINT_AVAILABLE = False


def get_printers() -> list[str]:
    """Return installed Windows printers or a clear test-mode marker."""
    if not WINDOWS_PRINT_AVAILABLE:
        return ["[Test mode - Windows printing unavailable]"]
    try:
        printers = [
            printer[2]
            for printer in win32print.EnumPrinters(
                win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
            )
        ]
        return sorted(printers) if printers else ["(No printers found)"]
    except Exception as exc:
        return [f"Error: {exc}"]


def send_zpl_to_printer(printer_name: str, zpl: str) -> None:
    """Send ZPL to a Windows printer using RAW mode."""
    if not WINDOWS_PRINT_AVAILABLE:
        raise RuntimeError("pywin32 is not installed or Windows printing is unavailable.")
    if not printer_name or printer_name.startswith("(") or printer_name.startswith("Error"):
        raise RuntimeError("No valid printer selected.")

    try:
        handle = win32print.OpenPrinter(printer_name)
    except Exception as exc:
        raise RuntimeError(
            f"Printer '{printer_name}' is not reachable. Is it powered on and connected?"
        ) from exc

    try:
        win32print.StartDocPrinter(handle, 1, ("ZPL Label", None, "RAW"))
        win32print.StartPagePrinter(handle)
        win32print.WritePrinter(handle, zpl.encode("utf-8"))
        win32print.EndPagePrinter(handle)
        win32print.EndDocPrinter(handle)
    finally:
        win32print.ClosePrinter(handle)
