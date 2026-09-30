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

    Set-LauncherStatus "wait" "Initialisation du Worker…" 78 "running" "Attente de l'état initial du Worker."
    $BootstrapFile = Join-Path $RuntimeDir "analysis-worker-bootstrap.json"
    Remove-Item $BootstrapFile -Force -ErrorAction SilentlyContinue
    $Deadline = (Get-Date).AddSeconds(60)
    $WorkerReady = $false
    while ((Get-Date) -lt $Deadline) {
        if (Test-Path $BootstrapFile) {
            try {
                $Bootstrap = Get-Content $BootstrapFile -Raw | ConvertFrom-Json
                if ($Bootstrap.ready -eq $true) {
                    $WorkerReady = $true
                    break
                }
            } catch {}
        }
        Start-Sleep -Milliseconds 400
    }
    if (-not $WorkerReady) {
        throw "Le Worker n'a pas publié son état prêt dans les 60 secondes."
    }
    Set-LauncherStatus "stabilize" "Worker prêt…" 90 "running" "Initialisation stabilisée."
    Start-Sleep -Milliseconds 900

    Set-LauncherStatus "ready" "EZScore Worker prêt." 100 "ready" "Aucune page web n'est ouverte automatiquement. Utilisez le bouton Ouvrir du serveur ONLINE ou LOCAL."
}
catch {
    Set-LauncherStatus "error" "Échec du démarrage." 100 "error" $_.Exception.Message
    exit 1
}
