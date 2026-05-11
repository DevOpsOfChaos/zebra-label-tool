# Changelog

## Unreleased

### Added

- Built-in workflow presets for device labels, asset tags, storage bins, and cable markers.
- Compact preset selector in the main GUI.
- Text cleanup tools from the top menu: whitespace cleanup, remove empty lines, uppercase, lowercase, title case, and wrap long lines.
- Batch labels window for generating one ZPL stream from multiple label blocks.
- Optional batch behavior to use each label block's first line as barcode content.
- Layout quality warnings when auto-fit shrinks text, text is missing, barcode content is long, or the text-line limit is reached.
- Test coverage for presets, text tools, and batch ZPL generation.

### Changed

- The main GUI keeps the frequent workflow visible and moves heavier operations into menus/windows.
- ZPL remains available on demand instead of occupying the main window.
- Documentation now describes presets, batch generation, and the cleaner menu workflow.

### Fixed

- The changelog content is now a real changelog instead of duplicating roadmap text.
