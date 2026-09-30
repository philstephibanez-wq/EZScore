param(
    [ValidateSet("online", "local")]
    [string]$Instance = "online",
    [ValidateSet("prod", "dev")]
    [string]$Environment = "prod"
)

$ErrorActionPreference = "Stop"
$Project = Split-Path -Parent $PSScriptRoot
Set-Location $Project

if ($Instance -eq "local" -and $Environment -ne "dev") {
    throw "Le serveur LOCAL est réservé à l'environnement dev."
}

$Port = if ($Instance -eq "online") { 8511 } else { 8502 }
$LogDir = Join-Path $Project "var\log"
$RuntimeDir = Join-Path $Project "var\runtime"
New-Item -ItemType Directory -Force -Path $LogDir,$RuntimeDir | Out-Null

$PidFile = Join-Path $RuntimeDir ("ezscore-web-{0}.pid" -f $Instance)
$MetaFile = Join-Path $RuntimeDir ("ezscore-web-{0}.json" -f $Instance)
$OutLog = Join-Path $LogDir ("ezscore-web-{0}.out.log" -f $Instance)
$ErrLog = Join-Path $LogDir ("ezscore-web-{0}.err.log" -f $Instance)
$Php = (Get-Command php -ErrorAction Stop).Source
$PublicDir = Join-Path $Project "public"

function Test-EZScorePhpServer {
    param([Parameter(Mandatory=$true)][int]$ProcessId)
    try {
        $Proc = Get-CimInstance Win32_Process -Filter "ProcessId = $ProcessId" -ErrorAction Stop
        if ($null -eq $Proc) { return $false }
        $Cmd = [string]$Proc.CommandLine
        if ([string]::IsNullOrWhiteSpace($Cmd)) { return $false }
        $Normalized = $Cmd.ToLowerInvariant().Replace('"','')
        $ExpectedBind = "-s 127.0.0.1:$Port"
        $ExpectedDocRoot = ("-t " + $PublicDir).ToLowerInvariant()
        return ($Normalized.Contains($ExpectedBind) -and $Normalized.Contains($ExpectedDocRoot))
    }
    catch { return $false }
}

if (Test-Path $PidFile) {
    $StoredPid = 0
    [void][int]::TryParse((Get-Content $PidFile -Raw -ErrorAction SilentlyContinue).Trim(), [ref]$StoredPid)
    if ($StoredPid -gt 0 -and (Test-EZScorePhpServer -ProcessId $StoredPid)) {
        $StoredEnv = ""
        try { $StoredEnv = (Get-Content $MetaFile -Raw | ConvertFrom-Json).environment } catch {}
        if ($StoredEnv -eq $Environment) {
            Write-Output "[OK] Serveur $Instance déjà actif (PID $StoredPid, env $Environment, port $Port)."
            exit 0
        }
        throw "Le serveur $Instance est déjà actif avec env=$StoredEnv. Arrêter/redémarrer via le Worker."
    }
    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
    Remove-Item $MetaFile -Force -ErrorAction SilentlyContinue
}

$Listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
if ($null -ne $Listener) {
    $ExistingPid = [int]$Listener.OwningProcess
    if (Test-EZScorePhpServer -ProcessId $ExistingPid) {
        throw "Un serveur EZScore non enregistré écoute déjà sur $Port (PID $ExistingPid). Arrêter ce processus avant de relancer."
    }
    $Name = (Get-Process -Id $ExistingPid -ErrorAction SilentlyContinue).ProcessName
    throw "Le port $Port est utilisé par PID $ExistingPid ($Name), hors contrôle EZScore."
}

$Arguments = @("-S", "127.0.0.1:$Port", "-t", $PublicDir)
$OldAppEnv = $env:APP_ENV
$OldAppDebug = $env:APP_DEBUG
$OldInstance = $env:EZSCORE_INSTANCE
try {
    $env:APP_ENV = $Environment
    $env:APP_DEBUG = if ($Environment -eq "dev") { "1" } else { "0" }
    $env:EZSCORE_INSTANCE = $Instance

    $Process = Start-Process `
        -FilePath $Php `
        -ArgumentList $Arguments `
        -WorkingDirectory $Project `
        -WindowStyle Hidden `
        -PassThru `
        -RedirectStandardOutput $OutLog `
        -RedirectStandardError $ErrLog
}
finally {
    $env:APP_ENV = $OldAppEnv
    $env:APP_DEBUG = $OldAppDebug
    $env:EZSCORE_INSTANCE = $OldInstance
}

$Process.Id | Set-Content -Path $PidFile -Encoding ASCII
@{
    schema_version = "ezscore.web-instance.v1"
    instance = $Instance
    environment = $Environment
    port = $Port
    pid = $Process.Id
    started_at = (Get-Date).ToString("o")
} | ConvertTo-Json | Set-Content -Path $MetaFile -Encoding UTF8

Start-Sleep -Milliseconds 500
if ($Process.HasExited) {
    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
    Remove-Item $MetaFile -Force -ErrorAction SilentlyContinue
    $Err = if (Test-Path $ErrLog) { Get-Content $ErrLog -Raw -ErrorAction SilentlyContinue } else { "" }
    throw "Le serveur PHP $Instance s'est arrêté immédiatement. $Err"
}

Write-Output "[OK] Serveur $Instance démarré (PID $($Process.Id), env $Environment, port $Port)."
Write-Output "[CMD] APP_ENV=$Environment EZSCORE_INSTANCE=$Instance php -S 127.0.0.1:$Port -t $PublicDir"
