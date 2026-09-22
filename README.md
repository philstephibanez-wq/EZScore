# EZScore_STEM_USE_PAROLES_LAYOUT_R1

Base GitHub vérifiée :

```text
master = b6c9c60d86f866c02e43f29a9afca4af3a5a2241
EZScore_STEM_CONDUCTOR_R2b
```

Le player STEM reprend maintenant la géométrie déjà validée dans
`Analyse > Paroles` :

```text
100 px / seconde
mot = max(position timeline, bord droit du mot précédent + 10 px)
suffixe contracté = bord droit précédent + 1 px
relayout après montage, fonts.ready et ResizeObserver
```

La piste commence à `left:0`, comme dans une timeline normale.
Le défilement reste basé sur les secondes absolues de la timeline canonique.

Aucune modification des timestamps, de MMS_FA, de la BDD, des beats ou de
l'audio.

## Application

```powershell
cd H:\EZScore

tar -xf "$env:USERPROFILE\Downloads\EZScore_STEM_USE_PAROLES_LAYOUT_R1.zip" -C H:\EZScore

.\.venv-py313\Scripts\python.exe .\scripts\apply_stem_use_paroles_layout_r1.py

.\.venv-py313\Scripts\python.exe -m py_compile `
  .\ezscore\player\stem_analysis_conductor.py `
  .\scripts\test_stem_use_paroles_layout_r1_contract.py

$env:PYTHONPATH = "H:\EZScore"
.\.venv-py313\Scripts\python.exe .\scripts\test_stem_use_paroles_layout_r1_contract.py
```

Attendu :

```text
PATCH OK
 - conducteur STEM utilise l'échelle Paroles : 100 px/s
 - collision des mots identique à Paroles (10 px, contractions 1 px)
 - origine de piste corrigée : x=0
 - relayout après fonts / resize / montage caché
 - timeline audio inchangée

STEM USE PAROLES LAYOUT R1 CONTRACT OK
Paroles scale 100 px/s: YES
Paroles collision layout reused: YES
track origin x=0: YES
fonts/resize/hidden relayout: YES
final JS activeWordIndex declarations: 1
```

Puis redémarrer Streamlit et ouvrir le lecteur STEM.
