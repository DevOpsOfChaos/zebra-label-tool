@echo off
REM Easy launcher for Zebra Label Tool (Windows).
REM
REM Strategy:
REM   1. If the prebuilt single-file binary exists next to the repo, run it.
REM   2. Otherwise activate a local .venv and run main.py.
REM   3. Otherwise tell the user how to install.
REM
REM Double-clickable. No interactive prompts.

setlocal
set "ROOT=%~dp0"
cd /d "%ROOT%"

if exist "dist\ZebraLabelTool.exe" (
    start "" "dist\ZebraLabelTool.exe"
    exit /b 0
)

if exist "ZebraLabelTool.exe" (
    start "" "ZebraLabelTool.exe"
    exit /b 0
)

if exist ".venv\Scripts\pythonw.exe" (
    start "" ".venv\Scripts\pythonw.exe" "main.py"
    exit /b 0
)

echo Zebra Label Tool is not installed yet.
echo.
echo Either:
echo   * download ZebraLabelTool.exe from
echo     https://github.com/DevOpsOfChaos/zebra-label-tool/releases
echo     and place it next to this .bat file,
echo   * or run the source setup once:
echo       py -m venv .venv
echo       .\.venv\Scripts\Activate.ps1
echo       pip install -r requirements.txt
echo       python main.py
echo.
pause
exit /b 1
