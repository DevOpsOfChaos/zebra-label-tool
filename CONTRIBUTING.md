# Contributing

Thanks for considering a contribution. The project is intentionally small. Please keep PRs small too.

## Project principles

- Keep the tool simple and fast.
- Preserve fast label creation as the primary workflow.
- Keep ZPL/layout logic independent from GUI and printer backends.
- Prefer small, testable, reviewable changes.
- Do not commit private printer names, local settings (`settings.json`), screenshots with sensitive data, or generated label content with personal info.

## Local setup

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
pytest -q
python -m zebra_label_tool.doctor
python main.py
```

## Tauri client

```powershell
cd desktop
npm install
npm run doctor
npm run tauri dev
```

Requires Node.js, Rust, Microsoft C++ Build Tools, and WebView2 on Windows.

## Translations

UI strings live in:

- Python UI: `src/zebra_label_tool/i18n.py`
- Tauri client: `desktop/src/i18n.ts`

Both registries are flat key → string maps. Keep DE/EN keys in parity. To add a new language, add another dictionary using the same keys; missing keys fall back to English.

## Before opening a pull request

```powershell
python -m compileall .
pytest -q
```

For UI work, also run the doctor and start the app at least once on Windows so the menus and dialogs are sanity-checked.

Include in the PR description:

- the use case / motivation,
- the changed files,
- any printer model used for manual validation (just the model, not its network identity),
- screenshots for visible UI changes.

## What we don't want in PRs

- Unrelated drive-by refactors. Keep diffs small.
- Removing or renaming i18n keys without a migration note.
- Adding heavyweight dependencies to the Python GUI side.
- Network calls in the printing path.
- Vendor design suite parity. This tool intentionally stays smaller than ZebraDesigner.
