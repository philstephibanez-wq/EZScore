$ErrorActionPreference = "Stop"

$Project = Split-Path -Parent $PSScriptRoot
Set-Location $Project

$Python = & (Join-Path $PSScriptRoot "find_analysis_python.ps1")
if (-not $Python) {
    throw "No compatible STEM Python found. Required: bs_roformer + mel_band_roformer + CUDA."
}

$ExpectedPython = Join-Path $Project ".venv-py313\Scripts\python.exe"
if ([System.IO.Path]::GetFullPath($Python) -ne [System.IO.Path]::GetFullPath($ExpectedPython)) {
    throw "Unexpected Worker Python: $Python (expected $ExpectedPython)"
}

# Child Worker inherits this explicit interpreter path. No .pyw association or global Python.
$env:EZSCORE_STEM_PYTHON = $ExpectedPython

$Pythonw = Join-Path (Split-Path -Parent $ExpectedPython) "pythonw.exe"
if (-not (Test-Path $Pythonw)) {
    throw "pythonw.exe missing in Worker venv: $Pythonw"
}

$App = Join-Path $Project "worker_app\ezscore_analysis_worker.pyw"
if (-not (Test-Path $App)) {
    throw "Desktop worker app missing: $App"
}

Start-Process `
    -FilePath $Pythonw `
    -ArgumentList @("`"$App`"") `
    -WorkingDirectory $Project

Write-Host "[OK] EZScore Analysis Worker launched."
