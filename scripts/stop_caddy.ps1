$ErrorActionPreference = "Stop"

$Project = Split-Path -Parent $PSScriptRoot
$PidFile = Join-Path $Project "var\runtime\ezscore-caddy.pid"

if (-not (Test-Path $PidFile)) {
    Write-Output "[OK] Caddy déjà arrêté."
    exit 0
}

$PidValue = 0
[void][int]::TryParse((Get-Content $PidFile -Raw -ErrorAction SilentlyContinue).Trim(), [ref]$PidValue)

if ($PidValue -gt 0) {
    Stop-Process -Id $PidValue -Force -ErrorAction SilentlyContinue
}

Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
Write-Output "[OK] Caddy arrêté."
