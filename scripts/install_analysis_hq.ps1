$ErrorActionPreference = "Stop"

Write-Host "EZScore - installation des moteurs d'analyse haute qualite"
python -m pip install --upgrade pip
python -m pip install --upgrade -r requirements-analysis-hq.txt

Write-Host ""
Write-Host "Verification imports..."
python -c "import bs_roformer; import lv_chordia; import madmom_infer; import soundfile; print('Analyse HQ: imports OK')"

Write-Host ""
Write-Host "Les poids BS-RoFormer ne sont pas dans Git."
Write-Host "Ils seront telecharges automatiquement et verifies SHA-256 au premier usage."
Write-Host "Pour les stocker sur un disque specifique:"
Write-Host '  $env:BS_ROFORMER_MODELS_PATH="H:\EZScoreModels\bs-roformer"'
Write-Host ""
Write-Host "Installation terminee."
