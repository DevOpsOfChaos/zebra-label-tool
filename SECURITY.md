# Security Policy

Zebra Label Tool is a small local desktop utility. It should not require network access for normal GUI usage. Windows RAW printing is the only outbound action, and it targets a printer that the user has already installed.

## Supported versions

The latest commit on `main` is the supported version. There are no LTS branches.

## Reporting

For **non-sensitive** security concerns, open a GitHub issue and mark the title with `[security]`.

For **sensitive** reports (e.g. crash via crafted ZPL import file, path traversal in export, anything that could affect another user's system), please contact the maintainer privately on GitHub instead of opening a public issue.

## What not to share in public issues

- Private printer names, IPs, or shares
- Internal hostnames, asset IDs, serial numbers
- Customer or employee data inside label text
- Generated ZPL with sensitive payloads (URLs, Wi-Fi credentials, internal links)

Redact before pasting. Replace identifiers with `EXAMPLE-001` or similar.

## Threat model (short)

- The tool reads/writes local files: `settings.json`, exported `.zpl`, imported `.zpl`.
- It calls Windows print spool APIs through `pywin32`.
- It does not auto-update.
- The Tauri client uses WebView2 with a limited capability set defined in `desktop/src-tauri/capabilities/default.json`.

Out of scope: securing the printer itself, securing the user's Windows account, securing the network between the workstation and the printer.
