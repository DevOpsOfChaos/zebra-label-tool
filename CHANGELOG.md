# Changelog

## Unreleased

### Added

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

### Changed

- The main GUI now uses a cleaner light layout because native Tk menu bars cannot be reliably themed like CustomTkinter content on every platform.
- Font size, alignment, and auto-fit moved into the main text area; label setup and barcode setup moved out of the main panel.
- Current setup moved to the bottom of the preview side so it no longer competes with label text entry.
- ZPL remains available on demand instead of occupying the main window.
- Documentation now describes presets, batch generation, and the cleaner menu workflow.

### Fixed

- The changelog content is now a real changelog instead of duplicating roadmap text.
