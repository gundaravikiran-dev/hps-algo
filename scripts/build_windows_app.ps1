$ErrorActionPreference = "Stop"

Set-Location (Join-Path $PSScriptRoot "..")

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    throw "Missing .venv\Scripts\python.exe. Create the Windows virtual environment first."
}

& ".venv\Scripts\python.exe" -m PyInstaller `
    "packaging\HPS-Algo-Windows.spec" `
    --noconfirm `
    --clean
