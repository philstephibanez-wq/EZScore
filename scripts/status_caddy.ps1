$Project = Split-Path -Parent $PSScriptRoot
$PidFile = Join-Path $Project "var\runtime\ezscore-caddy.pid"

$PidValue = 0
if (Test-Path $PidFile) {
    [void][int]::TryParse((Get-Content $PidFile -Raw -ErrorAction SilentlyContinue).Trim(), [ref]$PidValue)
}

$Proc = if ($PidValue -gt 0) { Get-Process -Id $PidValue -ErrorAction SilentlyContinue } else { $null }

if ($null -eq $Proc) {
    Write-Output "CADDY_STOPPED"
    exit 1
}

Write-Output "CADDY_RUNNING PID=$PidValue ONLINE=http://127.0.0.1:8501 DEV=http://127.0.0.1:8502 MEDIA=http://127.0.0.1:8520"
