$ErrorActionPreference = "Stop"

$Project = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Project ".venv-py313\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    exit 1
}

$Probe = Join-Path $env:TEMP ("ezscore-worker-probe-" + [guid]::NewGuid().ToString("N") + ".py")
try {
    @'
import bs_roformer
import mel_band_roformer
import lv_chordia
import torch
raise SystemExit(0 if torch.cuda.is_available() else 2)
'@ | Set-Content -Path $Probe -Encoding UTF8

    $Process = Start-Process `
        -FilePath $Python `
        -ArgumentList @($Probe) `
        -Wait `
        -PassThru `
        -NoNewWindow

    if ($Process.ExitCode -eq 0) {
        Write-Output $Python
        exit 0
    }
}
finally {
    Remove-Item $Probe -Force -ErrorAction SilentlyContinue
}

exit 1
