# EZScore_v1 — R39.2A TRACK READY BADGE

Correction visuelle minimale sur la base R39.2.

Objectif :
- remettre le statut `PRÊT` lisible sur chaque piste ;
- conserver strictement les proportions actuelles du mixer ;
- ne pas réorganiser les colonnes ;
- ne pas toucher au moteur audio ni à la chaîne d'effets.

Le lot modifie uniquement :
- `public/assets/js/stems-mixer.js` : ajoute `data-state` au statut ;
- `public/assets/css/stems.css` : badge compact ;
- cache-bust CSS/JS dans StemLab, ChordsLab et LyricsLab.

## Installation

```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R39_2A_TRACK_READY_BADGE.zip" -C H:\EZScore_v1

H:\EZScore\.venv-py313\Scripts\python.exe .\_r39_2a\scripts\apply_r39_2a.py

H:\EZScore\.venv-py313\Scripts\python.exe .\tests\r39_2a_track_ready_badge_contract.py

php bin\console cache:clear

git diff --check
git status --short
```

Attendu :

```text
R39.2A_TRACK_READY_BADGE_APPLIED
R39.2A_TRACK_READY_BADGE_CONTRACT_OK
```
