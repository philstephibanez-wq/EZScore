$ErrorActionPreference = "Stop"
$Project = Split-Path -Parent $PSScriptRoot
Set-Location $Project

Write-Host "[INFO] R25.2: the old git-show translation restore is disabled."
Write-Host "[INFO] Repairing the current UTF-8 files without passing their contents through the PowerShell console code page..."

php .\scripts\fix_translation_encoding_r25_2.php
if ($LASTEXITCODE -ne 0) {
    throw "Translation encoding repair failed with exit code $LASTEXITCODE."
}

Write-Host "[OK] Translation encoding repair complete."
