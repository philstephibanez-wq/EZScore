# EZScore SESSION REMOTE URL REMOVE R1

Suppression complète de la dette `remote_url`.

## Installation

Extraire à la racine de `H:\EZScore`, puis :

```powershell
cd H:\EZScore
powershell -ExecutionPolicy Bypass -File .\scripts\install_session_remote_url_remove_r1.ps1 ; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; php bin\console cache:clear ; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; php bin\console doctrine:migrations:migrate --no-interaction ; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; php -l .\src\Domain\Event\Event.php ; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; php -l .\src\Controller\EventController.php ; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; php .\tests\session_remote_url_remove_r1_contract.php
```

Attendu :
`SESSION_REMOTE_URL_REMOVE_R1_CONTRACT_OK`

Puis vérifier la page Sessions : plus aucun champ « Lien distant ».
