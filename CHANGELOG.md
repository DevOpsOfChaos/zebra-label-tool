# Changelog

## Unreleased

### Added

- Help menu entries for a quick guide and keyboard shortcut reference.
- Barcode and 2D-code support for Code 128, Code 39, EAN-13, UPC-A, QR Code, Data Matrix, and PDF417.
- Shared barcode metadata and payload validation in `barcodes.py`.
- CLI options for barcode type, barcode height, hidden human-readable text, and QR/Data Matrix magnification.
- Built-in workflow presets for device labels, asset tags, QR device links, storage bins, and cable markers.
- Compact preset selector in the main GUI.
- Text cleanup tools from the top menu: whitespace cleanup, remove empty lines, uppercase, lowercase, title case, and wrap long lines.
- Batch labels window for generating one ZPL stream from multiple label blocks.
- Optional batch behavior to use each label block's first line as barcode content.
- Layout quality warnings when auto-fit shrinks text, text is missing, barcode content is long, or the text-line limit is reached.
- Test coverage for presets, text tools, batch ZPL generation, barcode validation, QR/Data Matrix/PDF417 ZPL generation, and QR import.

- Real local preview patterns for Code 128, Code 39, EAN-13, UPC-A, and QR Code.
- Deterministic layout previews for Data Matrix and PDF417 while Zebra firmware remains the final renderer.
- Built-in preset input dialogs so barcode/QR presets can be filled before applying.
- Additional built-in presets for Wi-Fi QR labels, part-number labels, and retail EAN labels.

- Persistent UI language selection with built-in English and German.
- First-start language prompt when no language has been saved yet.
- Settings menu with language switching.
- Compact main-window label layout area for label size, code position, and code-area size.
- Side code areas so barcodes/QR codes can sit left or right of the text.
- Tests for side code-area layout and translation fallback.

### Changed

- The red clear button now resets label text, selected template state, and active barcode/QR payload instead of only clearing text.
- Enter now stays inside the multi-line editor and creates another printed label line instead of printing.
- Printing moved to `Ctrl+P` and the **Print label** button to avoid accidental output.
- `Ctrl+C` and `Ctrl+Z` are no longer app-level ZPL shortcuts, so normal text copy/undo behavior is preserved.
- The main GUI now uses a cleaner light layout because native Tk menu bars cannot be reliably themed like CustomTkinter content on every platform.
- Font size, alignment, and auto-fit moved into the main text area; label setup and barcode setup moved out of the main panel.
- Current setup moved to the bottom of the preview side so it no longer competes with label text entry.
- ZPL remains available on demand instead of occupying the main window.
- Documentation now describes presets, batch generation, and the cleaner menu workflow.

- Recent labels were removed from the main GUI to reduce noise.
- Templates moved to the bottom of the main panel.
- Label setup now includes code area position and reserved code size.
- The text options dialog uses readable cancel/apply button styling.

### Fixed

- Fixed an accidental duplicate widget argument in the main action row.
- The changelog content is now a real changelog instead of duplicating roadmap text.
