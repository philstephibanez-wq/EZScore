# EZScore_MUSIC_TIMELINE_R2

Base GitHub vérifiée :

```text
master = a01d36ab90614a78cb8d731aa0f39b39bcdb0111
EZScore_MUSIC_TIMELINE_R1
```

## Diagnostic réel

Sur `Je te donne.mp3` :

```text
NB=508
TEMPO=123.046875

beat 0 = 10.216780 s
beat 1 = 10.681179 s
beat 2 = 11.168798 s
...
```

Le premier mot MMS_FA commence vers :

```text
9.870 s
```

Le problème n'est donc plus l'alignement des paroles : le STEM Batterie ne
contient pas suffisamment d'attaques au début et le beat tracker commence sa
grille à 10.216780 s.

## Correction R2

R2 ne déplace **aucun** beat détecté.

Il mesure l'intervalle médian de la grille détectée puis la prolonge vers
l'arrière, en conservant strictement sa phase :

```text
... pré-roll extrapolé ...
≈ 9.x s
10.216780 s    <- premier beat détecté original, inchangé
10.681179 s    <- inchangé
11.168798 s    <- inchangé
...
```

Les beats ajoutés portent :

```json
"preroll_extrapolated": true
```

Pour chacun, l'accord est demandé à la timeline `lv-chordia` existante sur
l'intervalle correspondant. Aucun accord n'est copié depuis le premier beat
détecté.

## Cache existant déjà créé par R1

Important : R2 répare également **le `structure_analysis.json` déjà présent**.

Il n'est donc pas nécessaire de :
- supprimer la chanson ;
- régénérer les STEM ;
- réaligner les 430 mots ;
- relancer une réanalyse complète.

À la première ouverture après R2, `ensure_music_timeline()` reconnaît que la
grille existante commence trop tard et complète uniquement son pré-roll.

## Invariants

```text
audio original = t=0 canonique
timestamps MMS_FA = inchangés
beats détectés = inchangés
pré-roll = phase de la grille extrapolée vers l'arrière
accords pré-roll = lv-chordia
structure_analysis.json = cache unique existant
nouveau cache = aucun
Madmom = aucun
```

## Application

```powershell
cd H:\EZScore

tar -xf "$env:USERPROFILE\Downloads\EZScore_MUSIC_TIMELINE_R2.zip" -C H:\EZScore

.\.venv-py313\Scripts\python.exe -m py_compile `
  .\ezscore\analysis\music_timeline.py `
  .\scripts\test_music_timeline_r2_contract.py `
  .\scripts\test_music_timeline_r2_functional.py

.\.venv-py313\Scripts\python.exe .\scripts\test_music_timeline_r2_contract.py
.\.venv-py313\Scripts\python.exe .\scripts\test_music_timeline_r2_functional.py
```

Attendu :

```text
MUSIC TIMELINE R2 CONTRACT OK
existing late timeline: REPAIRED IN PLACE
detected beat timestamps: NEVER MOVED
pre-roll phase: MEDIAN DETECTED INTERVAL
pre-roll harmony: LV-CHORDIA EXISTING CACHE
new cache file: NONE

MUSIC TIMELINE R2 FUNCTIONAL OK
...
first_detected_preserved= 10.21678
```

Puis redémarrer Streamlit.

## Vérification après ouverture du morceau

```powershell
$dir = Get-ChildItem .\data\analysis\stem_lab -Directory |
  Where-Object Name -like "cd8e4603f548*" |
  Select-Object -First 1

$p = Join-Path $dir.FullName "structure_analysis.json"
$d = Get-Content $p -Raw | ConvertFrom-Json

$d.timeline_preroll
$d.beat_timeline | Select-Object -First 25 index,time,chord,preroll_extrapolated
```

Le beat à `10.21678` doit toujours exister exactement ; plusieurs beats doivent
désormais le précéder.

## Git après test

```powershell
git status --short

git add ezscore/analysis/music_timeline.py `
        scripts/test_music_timeline_r2_contract.py `
        scripts/test_music_timeline_r2_functional.py `
        readme.md

git commit -m "EZScore_MUSIC_TIMELINE_R2"
git push origin master
```
