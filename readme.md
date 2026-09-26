# EZScore_v1 — R33.1a correctif d'application

R33.1 initial échouait sur `public/assets/js/chordslab.js` parce que son patcher cherchait la variante formatée du bloc `highlightAt()`, alors que R33 avait livré ce fichier sous forme compacte.

R33.1a corrige le patcher et supporte explicitement :

- la variante compacte réellement livrée en R33 ;
- la variante formatée ;
- un fallback structurel limité au bloc du beat courant.

Le script reste idempotent et refuse toute modification s'il ne reconnaît pas une structure sûre.

Le premier lancement R33.1 a déjà pu installer certains fichiers avant l'échec. C'est prévu : R33.1a reconnaît ces fichiers comme déjà appliqués et reprend au point suivant.

## Installation

```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R33_1a_RIFF_WAKERLOCK_PATCHER_FIX.zip" -C H:\EZScore_v1

H:\EZScore_v1\.venv-py313\Scripts\python.exe .\scripts\apply_r33_1_riff_wakelock.py

php .\tests\r33_1a_contract.php
node --check .\public\assets\js\chordslab.js
node --check .\public\assets\js\chordslab-r33-1.js
H:\EZScore_v1\.venv-py313\Scripts\python.exe -m py_compile .\analysis\chord_timeline_analysis.py
php -l .\src\Service\ChordTimelineAnalysisService.php
php bin\console lint:yaml translations
php bin\console lint:twig templates
php bin\console cache:clear
```

Attendu :

```text
8 R33.1a checks passed.
```

Puis `Ctrl+F5` et réanalyse des accords.

Aucune migration Doctrine.
