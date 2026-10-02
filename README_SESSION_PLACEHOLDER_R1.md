# EZScore Session Placeholder R1

Corrige l'affichage bizarre des sélecteurs **Groupe** et **Playlist**.

Cause : le tiret long `—` injecté par PowerShell 5.1 a été réencodé en mojibake (`â€”`).

Correction : les placeholders utilisent désormais l'entité HTML ASCII `&mdash;`,
donc aucun risque d'encodage Windows.

## Installation

```powershell
cd H:\EZScore
powershell -ExecutionPolicy Bypass -File .\scripts\fix_session_placeholders_r1.ps1 ; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; php bin\console cache:clear ; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; php .\tests\session_placeholder_r1_contract.php
```

Attendu :
`SESSION_PLACEHOLDER_R1_CONTRACT_OK`
