$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $true

$RepoRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $RepoRoot ".venv-py313\Scripts\python.exe"
$Requirements = Join-Path $RepoRoot "requirements-analysis-hq.txt"

if (-not (Test-Path $Python)) {
    throw "Environnement Python 3.13 introuvable : $Python`nCreer d'abord : py -3.13 -m venv .venv-py313"
}

function Invoke-Python {
    param([Parameter(ValueFromRemainingArguments=$true)][string[]]$Args)
    & $Python @Args
    if ($LASTEXITCODE -ne 0) {
        throw "Commande Python en echec (code $LASTEXITCODE): $($Args -join ' ')"
    }
}

Write-Host "EZScore - environnement Python 3.13 / GPU Turing"
Invoke-Python -c "import sys; assert sys.version_info[:2] == (3,13), sys.version; print('Python=',sys.version); print('Exe=',sys.executable)"

Invoke-Python -m pip install --upgrade pip setuptools wheel
Invoke-Python -m pip install -r $Requirements

Write-Host ""
Write-Host "Verification pile GPU..."
Invoke-Python -c "import torch,triton; print('Torch=',torch.__version__); print('CUDA=',torch.version.cuda); print('CUDA available=',torch.cuda.is_available()); print('GPU=',torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'NONE'); print('Capability=',torch.cuda.get_device_capability(0) if torch.cuda.is_available() else 'NONE'); print('Triton=',triton.__version__)"

Write-Host ""
Write-Host "Verification audioop Python 3.13..."
Invoke-Python -c "import audioop; print('audioop OK:', audioop.__file__)"

Write-Host ""
Write-Host "Verification imports EZScore..."
Invoke-Python -c "import streamlit,plotly,librosa,soundfile,whisper,bs_roformer,lv_chordia,demucs; print('Imports principaux: OK')"

Write-Host ""
Write-Host 'BS-RoFormer : $env:BS_ROFORMER_MODELS_PATH="H:\EZScoreModels\bs-roformer"'
Write-Host 'Whisper     : H:\EZScoreModels\whisper'
Write-Host 'Lancement   : .\.venv-py313\Scripts\python.exe -m streamlit run EZScore.py'
