# R37.0e — appliquer le résultat d'extraction à la box LyricsLab

Symptôme :
- extraction Worker arrive à 100 % ;
- `result.json` existe ;
- la box reste vide.

Cause :
le contrôleur de complétion appliquait toujours le résultat comme un alignement de mots.
En mode `extract`, le résultat contient `text`, pas `words`.

Correction :
- `mode=extract` => `Song::setLyricsSourceText($result['text'])`
- `mode=align` => comportement existant `LyricsTimelineResultService::apply(...)`

## Installation

```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R37_0E_EXTRACT_RESULT_APPLY_FIX.zip" -C H:\EZScore_v1

python .\scripts\apply_r37_0e.py H:\EZScore_v1

php -l .\src\Controller\AnalysisDesktopController.php
php bin\console cache:clear

php .\tests\r37_0e_contract.php H:\EZScore_v1

git diff --check
git status --short
```

Attendu :

```text
R37_0E_APPLIED_OK
R37_0E_CONTRACT_OK
```

Puis recliquer **Extraire les paroles**.
À la fin du job, la page se recharge et la box doit contenir le texte extrait.
