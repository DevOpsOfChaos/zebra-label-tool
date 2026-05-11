# Contributing

Thanks for considering a contribution.

## Project principles

- Keep the tool simple.
- Preserve fast label creation as the primary workflow.
- Keep ZPL/layout logic independent from GUI and printer backends.
- Prefer small, testable changes.
- Do not commit private printer names, local settings, screenshots with sensitive data, or generated labels.

## Local setup

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
pytest -q
python main.py
```

## Before opening a pull request

Run:

```powershell
python -m compileall .
pytest -q
```

Include a short description of the use case, the changed files, and any printer model used for manual validation.
