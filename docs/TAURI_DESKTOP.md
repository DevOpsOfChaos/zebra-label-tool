# Tauri Desktop Client

This repository now contains a second desktop client under `desktop/`.

The existing Python/CustomTkinter app remains available through `python main.py`. The Tauri client is a new UI direction and does not depend on the old Tkinter layout. It rethinks the workflow around modes, cards, a modern preview pane, and a cleaner control hierarchy.

## Why a second client?

The Tkinter app is useful and still acts as the stable baseline, but it is visually limited by native widgets and Tk styling. The Tauri client gives the project a modern WebView UI while keeping the Python ZPL/printing core available.

## Current capabilities

- Mode-based workflow:
  - Text only
  - Text + code
  - Code only
  - Number sequence
  - Number sequence + code
  - Multiple labels
- Collapsible printer settings
- Collapsible label settings
- Modern label preview pane
- ZPL generation in the frontend for immediate feedback
- Barcode/QR/DataMatrix/PDF417 preview through `bwip-js`
- ZPL copy/export
- Python bridge for printer discovery and RAW printing
- German/English UI switch
- Light/dark theme switch

## Development requirements

You need Node.js and Rust for Tauri development. On Windows, Tauri also needs Microsoft C++ Build Tools and WebView2.

## Check prerequisites

Before running the full Tauri dev command, check the local desktop toolchain:

```powershell
cd desktop
npm run doctor
```

This catches the common failures first: missing Cargo, missing Node/npm, and missing icon files.

## Start in development mode

From the repository root:

```powershell
cd desktop
npm install
npm run tauri dev
```

The Tauri dev command starts Vite and then opens the desktop window.

## Build a desktop package

```powershell
cd desktop
npm install
npm run tauri build
```

Build output is written below `desktop/src-tauri/target/`.

## Python bridge notes

The Tauri backend commands use the existing Python package for printer discovery and RAW printing:

- `zebra_label_tool.printing.get_printers`
- `zebra_label_tool.printing.send_zpl_to_printer`

During development, the backend points `PYTHONPATH` at the repository `src/` directory. This keeps the new UI connected to the current Python printing backend without bundling Python yet.

Future packaging work should decide whether to:

1. keep Python as an external dependency,
2. bundle a Python runtime,
3. move printer backends into Rust,
4. or expose printing through a small local service.

Do not silently remove the Python app until the Tauri client has been manually verified on Windows with a real printer.

## Build note

The Tauri scaffold includes `src-tauri/icons/icon.ico`, which is required for Windows resource generation. If the build reports a missing icon, make sure the `desktop/src-tauri/icons/` directory was copied into the repo.

## Responsive layout

The desktop client is no longer designed around a full-screen-only layout. It has compact breakpoints for medium and narrow windows, reduced default window size, lower minimum window dimensions, and a collapsible left sidebar so the preview can use more of the window.

## Sequence workflows

The Tauri client supports numeric, letter-based, and mixed letter/number sequences. Sequence barcode/QR content can use generated values, the first printed line, all printed text, or a custom payload template such as `asset:{value}`, `rack-{letter}-{number:000}`, or `asset:{value}-{index}`.


## UI workflow polish

The Tauri client now uses progressive disclosure: workflow modes stay visible, printer/label settings are stable in the left sidebar, detailed controls live inside collapsible sections, common label templates are available on demand, ZPL copy/export live in the preview header, and the sidebar can fully collapse when more preview room is needed.
