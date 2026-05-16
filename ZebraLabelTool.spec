# PyInstaller spec for Zebra Label Tool desktop GUI.
#
# Build locally:
#   pyinstaller ZebraLabelTool.spec --clean --noconfirm
#
# Output:
#   dist/ZebraLabelTool.exe  (single-file windowed app, Windows)
#
# Notes:
#   * CustomTkinter ships theme JSON files; qrcode ships encoding tables.
#     Both are bundled with collect_data_files() below.
#   * Submodule collection keeps lazy imports inside customtkinter/qrcode
#     from breaking inside the frozen build.
#   * UPX is disabled to keep antivirus false-positives down on Windows.

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

hiddenimports = (
    collect_submodules('customtkinter')
    + collect_submodules('qrcode')
    + collect_submodules('PIL')
    + collect_submodules('certifi')
    + [
        'zebra_label_tool',
        'zebra_label_tool.app',
        'zebra_label_tool.cli',
        'zebra_label_tool.printing',
        'zebra_label_tool.zpl_renderer',
        'zebra_label_tool.preview',
    ]
)

datas = (
    collect_data_files('customtkinter')
    + collect_data_files('qrcode')
    + [('src/zebra_label_tool/fonts/DejaVuSansMono-Bold.ttf', 'zebra_label_tool/fonts/DejaVuSansMono-Bold.ttf')]
)

a = Analysis(
    ['main.py'],
    pathex=['src'],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['pytest', 'tkinter.test'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='ZebraLabelTool',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['desktop/src-tauri/icons/icon.ico'],
)
