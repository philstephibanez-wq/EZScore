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

$env:EZSCORE_STEM_PYTHON = $ExpectedPython

$App = Join-Path $Project "worker_app\ezscore_analysis_worker.pyw"
if (-not (Test-Path $App)) {
    throw "Desktop worker app missing: $App"
}

$LogDir = Join-Path $Project "var\log"
$RuntimeDir = Join-Path $Project "var\runtime"
New-Item -ItemType Directory -Force -Path $LogDir,$RuntimeDir | Out-Null

$StdoutLog = Join-Path $LogDir "analysis-worker-bootstrap.stdout.log"
$StderrLog = Join-Path $LogDir "analysis-worker-bootstrap.stderr.log"
$PidFile = Join-Path $RuntimeDir "analysis-worker.pid"
$BootstrapFile = Join-Path $RuntimeDir "analysis-worker-bootstrap.json"

Remove-Item $StdoutLog,$StderrLog,$PidFile -Force -ErrorAction SilentlyContinue

$WorkerProcess = Start-Process `
    -FilePath $ExpectedPython `
    -ArgumentList @("`"$App`"") `
    -WorkingDirectory $Project `
    -WindowStyle Hidden `
    -RedirectStandardOutput $StdoutLog `
    -RedirectStandardError $StderrLog `
    -PassThru

$WorkerProcess.Id | Set-Content -Path $PidFile -Encoding ascii

$Deadline = (Get-Date).AddSeconds(8)
while ((Get-Date) -lt $Deadline) {
    if (Test-Path $BootstrapFile) {
        Write-Host "[OK] EZScore Analysis Worker launched. PID=$($WorkerProcess.Id)"
        exit 0
    }

    if ($WorkerProcess.HasExited) {
        $stderr = ""
        if (Test-Path $StderrLog) {
            $stderr = (Get-Content $StderrLog -Raw -ErrorAction SilentlyContinue).Trim()
        }
        if ([string]::IsNullOrWhiteSpace($stderr)) {
            $stderr = "aucune sortie stderr"
        }
        throw "Worker exited during bootstrap (exit=$($WorkerProcess.ExitCode)). $stderr"
    }

    Start-Sleep -Milliseconds 200
}

if ($WorkerProcess.HasExited) {
    throw "Worker exited during bootstrap (exit=$($WorkerProcess.ExitCode))."
}

Write-Host "[OK] EZScore Analysis Worker launched. PID=$($WorkerProcess.Id); bootstrap encore en cours."
