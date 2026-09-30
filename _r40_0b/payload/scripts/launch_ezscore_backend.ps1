param()

$ErrorActionPreference = "Stop"
$Project = Split-Path -Parent $PSScriptRoot
Set-Location $Project

$RuntimeDir = Join-Path $Project "var\runtime"
New-Item -ItemType Directory -Force -Path $RuntimeDir | Out-Null
$StatusFile = Join-Path $RuntimeDir "launcher-status.json"

function Set-LauncherStatus {
    param(
        [Parameter(Mandatory=$true)][string]$Stage,
        [Parameter(Mandatory=$true)][string]$Message,
        [Parameter(Mandatory=$true)][int]$Percent,
        [ValidateSet("running","ready","error")][string]$State = "running",
        [string]$Detail = ""
    )
    $Payload = [ordered]@{
        state = $State
        stage = $Stage
        message = $Message
        percent = [Math]::Max(0, [Math]::Min(100, $Percent))
        detail = $Detail
        updated_at = (Get-Date).ToString("o")
    }
    $Tmp = "$StatusFile.tmp"
    $Payload | ConvertTo-Json -Depth 4 | Set-Content -Path $Tmp -Encoding UTF8
    Move-Item -Path $Tmp -Destination $StatusFile -Force
}

try {
    Set-LauncherStatus "init" "Initialisation..." 8

    Set-LauncherStatus "legacy" "Vérification de l'ancien worker…" 18
    $LegacyTask = Get-ScheduledTask -TaskName "EZScore STEM Worker" -ErrorAction SilentlyContinue
    if ($null -ne $LegacyTask) {
        Stop-ScheduledTask -TaskName "EZScore STEM Worker" -ErrorAction SilentlyContinue
        Disable-ScheduledTask -TaskName "EZScore STEM Worker" -ErrorAction SilentlyContinue | Out-Null
    }

    Set-LauncherStatus "token" "Vérification du canal Worker…" 32
    & (Join-Path $PSScriptRoot "ensure_analysis_worker_token.ps1") | Out-Null

    Set-LauncherStatus "worker" "Ouverture de EZScore Analysis Worker..." 58 "running" "Le Worker restaure les modes ONLINE/LOCAL persistés et démarre les serveurs nécessaires."
    & (Join-Path $PSScriptRoot "start_analysis_worker_desktop.ps1") | Out-Null

    Set-LauncherStatus "wait" "Restauration de l'environnement…" 78 "running" "ONLINE et LOCAL sont pilotés indépendamment par le Worker."
    Start-Sleep -Seconds 2

    $BrowserUrl = if ($env:EZSCORE_BROWSER_URL) { $env:EZSCORE_BROWSER_URL.TrimEnd('/') } else { "https://ezscore.logandplay.com" }
    $ControlFile = Join-Path $RuntimeDir "ezscore-server-control.json"
    try {
        if (Test-Path $ControlFile) {
            $Control = Get-Content $ControlFile -Raw | ConvertFrom-Json
            if ($Control.worker.target -eq "local") {
                $BrowserUrl = "http://127.0.0.1:8502"
            }
        }
    } catch {}

    Set-LauncherStatus "browser" "Ouverture de EZScore..." 92 "running" $BrowserUrl
    Start-Process ($BrowserUrl + "/fr/catalog")

    Set-LauncherStatus "ready" "EZScore est prêt." 100 "ready" "Le Worker gère les serveurs ONLINE et LOCAL ainsi que leurs états persistés."
}
catch {
    Set-LauncherStatus "error" "Échec du démarrage." 100 "error" $_.Exception.Message
    exit 1
}
