param(
    [string]$CaddyExe = "H:\Caddy\caddy.exe"
)

$ErrorActionPreference = "Stop"

$Project = Split-Path -Parent $PSScriptRoot
$RuntimeDir = Join-Path $Project "var\runtime"
$LogDir = Join-Path $Project "var\log"
$Config = Join-Path $Project "config\caddy\Caddyfile"
$PidFile = Join-Path $RuntimeDir "ezscore-caddy.pid"
$OutLog = Join-Path $LogDir "ezscore-caddy.out.log"
$ErrLog = Join-Path $LogDir "ezscore-caddy.err.log"
$ValidateOut = Join-Path $RuntimeDir "caddy-validate.out.tmp"
$ValidateErr = Join-Path $RuntimeDir "caddy-validate.err.tmp"

New-Item -ItemType Directory -Force -Path $RuntimeDir,$LogDir | Out-Null

if (-not (Test-Path $CaddyExe)) {
    throw "Caddy introuvable: $CaddyExe"
}
if (-not (Test-Path $Config)) {
    throw "Caddyfile introuvable: $Config"
}

function Test-EZScoreCaddy {
    param([Parameter(Mandatory=$true)][int]$ProcessId)

    try {
        $Proc = Get-CimInstance Win32_Process -Filter "ProcessId = $ProcessId" -ErrorAction Stop
        if ($null -eq $Proc) { return $false }
        $Cmd = [string]$Proc.CommandLine
        if ([string]::IsNullOrWhiteSpace($Cmd)) { return $false }
        $Normalized = $Cmd.ToLowerInvariant().Replace('"','')
        return $Normalized.Contains("caddy") -and $Normalized.Contains("run") -and $Normalized.Contains("config\caddy\caddyfile")
    }
    catch {
        return $false
    }
}

if (Test-Path $PidFile) {
    $StoredPid = 0
    [void][int]::TryParse((Get-Content $PidFile -Raw -ErrorAction SilentlyContinue).Trim(), [ref]$StoredPid)
    if ($StoredPid -gt 0 -and (Test-EZScoreCaddy -ProcessId $StoredPid)) {
        Write-Output "[OK] Caddy déjà actif (PID $StoredPid)."
        exit 0
    }
    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
}

foreach ($Port in @(8501,8502,8520)) {
    $Listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -ne $Listener) {
        $ExistingPid = [int]$Listener.OwningProcess
        if (-not (Test-EZScoreCaddy -ProcessId $ExistingPid)) {
            $Name = (Get-Process -Id $ExistingPid -ErrorAction SilentlyContinue).ProcessName
            throw "Le port $Port est déjà utilisé par PID $ExistingPid ($Name). Arrêter ce processus avant de lancer EZScore."
        }
    }
}

$env:EZSCORE_MEDIA_ROOT = (Join-Path $Project "var\storage\stems").Replace("\","/")

# Caddy writes normal INFO validation messages to stderr.
# With Windows PowerShell + ErrorActionPreference=Stop, invoking the native
# command directly can convert that harmless stderr into NativeCommandError.
# Run validation as a child process and judge only its exit code.
Remove-Item $ValidateOut,$ValidateErr -Force -ErrorAction SilentlyContinue
$ValidationProcess = Start-Process `
    -FilePath $CaddyExe `
    -ArgumentList @("validate","--config",$Config,"--adapter","caddyfile") `
    -WorkingDirectory $Project `
    -WindowStyle Hidden `
    -Wait `
    -PassThru `
    -RedirectStandardOutput $ValidateOut `
    -RedirectStandardError $ValidateErr

$ValidationText = @()
if (Test-Path $ValidateOut) { $ValidationText += Get-Content $ValidateOut -ErrorAction SilentlyContinue }
if (Test-Path $ValidateErr) { $ValidationText += Get-Content $ValidateErr -ErrorAction SilentlyContinue }

if ($ValidationProcess.ExitCode -ne 0) {
    $Details = ($ValidationText -join [Environment]::NewLine)
    Remove-Item $ValidateOut,$ValidateErr -Force -ErrorAction SilentlyContinue
    throw "Caddyfile invalide: $Details"
}

Remove-Item $ValidateOut,$ValidateErr -Force -ErrorAction SilentlyContinue

$Process = Start-Process `
    -FilePath $CaddyExe `
    -ArgumentList @("run","--config",$Config,"--adapter","caddyfile") `
    -WorkingDirectory $Project `
    -WindowStyle Hidden `
    -PassThru `
    -RedirectStandardOutput $OutLog `
    -RedirectStandardError $ErrLog

$Process.Id | Set-Content -Path $PidFile -Encoding ASCII

$Deadline = (Get-Date).AddSeconds(8)
$Ready = $false
while ((Get-Date) -lt $Deadline) {
    if ($Process.HasExited) { break }
    try {
        $R = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:2019/config/" -TimeoutSec 1
        if ($R.StatusCode -eq 200) {
            $Ready = $true
            break
        }
    }
    catch {}
    Start-Sleep -Milliseconds 150
}

if (-not $Ready) {
    if (-not $Process.HasExited) {
        Stop-Process -Id $Process.Id -Force -ErrorAction SilentlyContinue
    }
    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
    $Err = if (Test-Path $ErrLog) { Get-Content $ErrLog -Raw -ErrorAction SilentlyContinue } else { "" }
    throw "Caddy n'a pas démarré correctement. $Err"
}

Write-Output "[OK] Caddy actif (PID $($Process.Id)) · ONLINE=:8501 · DEV=:8502 · MEDIA=:8520"
