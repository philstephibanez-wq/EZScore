# EZScore_v1 — R41.0F FULL launcher + CI + ChordsLab seeker

Base GitHub exacte : `282e46195f3be16dd8fbbeab9b4a57a5dbe8ede4` (`cleanup`).

Ce FULL consolide le seeker R41.0E local avec les correctifs Worker/launcher et CI.
Ne pas empiler R41.0E puis R41.0F.

## Correctifs

- splash existant conservé ;
- lancement Worker verrouillé sur le venv projet `.venv-py313` et `pythonw.exe` ;
- `EZSCORE_STEM_PYTHON` transmis explicitement au Worker ;
- probe Worker 20s -> 60s pour éviter un faux échec de démarrage à froid ;
- diagnostic réel des candidats Python en cas d'échec ;
- `find_analysis_python.ps1` vérifie aussi `lv_chordia` ;
- suppression du bootstrap stale avant lancement du Worker ;
- CI : création d'un `.env` physique avant `composer install` ;
- seeker ChordsLab consolidé, toujours sur l'horloge audio partagée.

Aucune modification de `analysis/chord_timeline_analysis.py`, du moteur accords HQ, du pipeline STEMS/LYRICS ou de la tonalité.

## Avant installation

R41.0E étant local/non poussé, revenir au master propre `282e46195f3be16dd8fbbeab9b4a57a5dbe8ede4` avec **Discard All Changes** dans Fork.
Supprimer `_r41_0e_full` s'il est encore présent.

```powershell
cd H:\EZScore_v1
git status --short
git rev-parse HEAD
```

Attendu : aucune sortie pour status et HEAD `282e46195f3be16dd8fbbeab9b4a57a5dbe8ede4`.

## Installation

```powershell
tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R41_0F_FULL_LAUNCHER_CI_SEEKER.zip" -C H:\EZScore_v1

H:\EZScore_v1\.venv-py313\Scripts\python.exe .\_r41_0f_full\scripts\apply_r41_0f.py H:\EZScore_v1
```

Attendu :

`R41_0F_FULL_LAUNCHER_CI_SEEKER_INSTALL_OK`

Sinon : STOP.

Puis :

```powershell
H:\EZScore_v1\.venv-py313\Scripts\python.exe .\_r41_0f_full\tests\r41_0f_contract.py H:\EZScore_v1

git diff --check
git status --short
```

Attendu :

`R41_0F_FULL_LAUNCHER_CI_SEEKER_CONTRACT_OK`

## Test fonctionnel

1. Fermer toutes les fenêtres Worker.
2. Lancer `EZScore-Launcher.cmd`.
3. Vérifier le splash.
4. Vérifier ensuite :
   - Python STEM = `H:\EZScore_v1\.venv-py313\Scripts\python.exe`
   - GPU = NVIDIA GeForce RTX 2060
   - aucun `Python STEM INTRouvable`.
5. Vérifier le seeker ChordsLab.
6. Après push, vérifier que GitHub Actions dépasse `Install dependencies`.
