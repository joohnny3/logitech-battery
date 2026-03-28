# Mouse Battery Monitor - Launcher
# Activates venv and runs the application

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectDir = Split-Path -Parent $scriptDir
$venvPython = Join-Path $projectDir "venv\Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    Write-Host "ERROR: venv not found. Run: python -m venv venv" -ForegroundColor Red
    exit 1
}

Set-Location $projectDir
& $venvPython -m app.main
