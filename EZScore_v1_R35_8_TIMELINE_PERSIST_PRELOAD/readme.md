# EZScore_v1 — R35.8 TIMELINE / PERSIST / PRELOAD

Correctif fonctionnel à appliquer après R35.7.

## Changements

- Timeline du prompteur présente dès **t=0.000 du MP3**.
- Si le début est silencieux, batterie seule, foule/bruit ou sans harmonie exploitable, les beats/mesures existent et affichent `.`.
- Une intro piano/pad/synthé/cordes peut produire des accords : elle n'est vide que si aucune harmonie exploitable n'est détectée.
- Filtre `applaudissements / foule` **persisté par chanson**, sauvegardé dès le changement de la case.
- Opus réellement préchargés dès l'ouverture de StemsLab/ChordsLab, sans autoplay.
- Cache-busting des scripts audio pour éviter qu'un ancien JS reste en cache.
- `Réinitialiser les accords` visible uniquement s'il existe de vraies corrections manuelles.
- Suppression des crochets `[]` autour des accords dans les cadres, y compris pour d'anciens résultats `[C]`, `[Am]`, etc.

## Installation

```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R35_8_TIMELINE_PERSIST_PRELOAD.zip" -C H:\EZScore_v1

python .\EZScore_v1_R35_8_TIMELINE_PERSIST_PRELOAD\scripts\apply_r35_8.py H:\EZScore_v1

php bin\console doctrine:migrations:migrate --no-interaction
php bin\console cache:clear
php bin\console lint:container
php bin\console lint:twig templates

python -m py_compile .\analysis\chord_timeline_analysis.py
python -m py_compile .\worker_app\ezscore_analysis_worker.pyw

php .\EZScore_v1_R35_8_TIMELINE_PERSIST_PRELOAD\tests\r35_8_contract.php H:\EZScore_v1

git diff --check
git status --short
```

Attendu :

```text
R35_8_APPLIED_OK
R35_8_CONTRACT_OK
```

Pour une chanson déjà analysée, **Réanalyser les accords** est nécessaire pour reconstruire la beat-grid et les événements `.` depuis t=0. Il n'est pas nécessaire de refaire les stems.

Le script ne committe et ne pousse rien.
