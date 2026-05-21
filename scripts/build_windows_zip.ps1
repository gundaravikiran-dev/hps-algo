$ErrorActionPreference = "Stop"

Set-Location (Join-Path $PSScriptRoot "..")

$appPath = "dist\HPS-Algo"
$zipPath = "dist\HPS-Algo-Windows.zip"

if (-not (Test-Path $appPath)) {
    throw "Missing $appPath. Run scripts\build_windows_app.ps1 first."
}

if (Test-Path $zipPath) {
    Remove-Item $zipPath -Force
}

Compress-Archive -Path $appPath -DestinationPath $zipPath -CompressionLevel Optimal
