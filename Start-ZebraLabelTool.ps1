# Easy launcher for Zebra Label Tool (Windows PowerShell).
#
# Strategy: prefer a packaged binary in dist/, then a sibling exe,
# then a local .venv source install, otherwise print install hints.
#
# Run:   .\Start-ZebraLabelTool.ps1
# or right-click -> Run with PowerShell.

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

$candidates = @(
    "dist/ZebraLabelTool.exe",
    "ZebraLabelTool.exe"
)

foreach ($candidate in $candidates) {
    $path = Join-Path $PSScriptRoot $candidate
    if (Test-Path $path) {
        Write-Host "Starting $candidate ..."
        Start-Process -FilePath $path
        return
    }
}

$pythonw = Join-Path $PSScriptRoot ".venv/Scripts/pythonw.exe"
$main = Join-Path $PSScriptRoot "main.py"
if ((Test-Path $pythonw) -and (Test-Path $main)) {
    Write-Host "Starting Python GUI from local .venv ..."
    Start-Process -FilePath $pythonw -ArgumentList $main
    return
}

Write-Host ""
Write-Host "Zebra Label Tool is not installed yet." -ForegroundColor Yellow
Write-Host ""
Write-Host "Either:"
Write-Host "  * download ZebraLabelTool.exe from"
Write-Host "    https://github.com/DevOpsOfChaos/zebra-label-tool/releases"
Write-Host "    and put it next to this script,"
Write-Host "  * or run the source setup once:"
Write-Host "      py -m venv .venv"
Write-Host "      .\.venv\Scripts\Activate.ps1"
Write-Host "      pip install -r requirements.txt"
Write-Host "      python main.py"
Write-Host ""
Read-Host "Press Enter to close" | Out-Null
exit 1
