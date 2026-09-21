# EZScore_TECHNICAL_TIMELINE_R2

Base GitHub vérifiée :

```text
master = daa4be565c6f5b24d774a1ad8aa5919d9deded79
EZScore_TECHNICAL_TIMELINE_R1
```

## Pourquoi R1 restait KO

R1 branchait `technical_timeline.json` en modifiant dynamiquement
`lyrics_inline_editor._load_timing`.

Le rendu `Paroles + accords` dépendait donc encore de l'ordre d'installation
des patches Streamlit. En cas d'échec de construction de la timeline,
l'exception était en plus avalée et l'ancien message générique réapparaissait :

```text
Timeline de beats absente
```

R2 supprime cette dépendance.

## R2

`chords_lyrics_editor.py` consomme directement la timeline technique :

```text
structure/karaoke timing existant
        ↓ sinon
technical_timeline.json
        ↓ sinon
construction directe :
  Batterie -> madmom-infer -> beats
  Original -> lv-chordia -> accords
```

Le player STEM fait également cette vérification directement avec les chemins
audio qu'il possède déjà.

Il n'y a aucun beat synthétique/factice.

Si le moteur de beats, le STEM Batterie ou l'audio original est réellement
indisponible, l'éditeur affiche maintenant **l'erreur technique exacte** au
lieu du message générique.

## Application

```powershell
cd H:\EZScore

tar -xf "$env:USERPROFILE\Downloads\EZScore_TECHNICAL_TIMELINE_R2.zip" -C H:\EZScore

.\.venv-py313\Scripts\python.exe -m py_compile `
  .\ezscore\analysis\technical_timeline.py `
  .\ezscore\player\stem_analysis_conductor.py `
  .\ezscore\ui\chords_lyrics_editor.py `
  .\scripts\test_technical_timeline_r2_contract.py

.\.venv-py313\Scripts\python.exe .\scripts\test_technical_timeline_r2_contract.py
```

Attendu :

```text
TECHNICAL TIMELINE R2 CONTRACT OK
editor timing: DIRECT
STEM conductor timing: DIRECT
monkey-patch timing dependency: REMOVED
silent timing errors: REMOVED
fake beats: NONE
```

Redémarrer ensuite complètement Streamlit.

Au premier affichage sans cache technique, la construction beats + accords peut
prendre un peu de temps. Les exécutions suivantes réutilisent
`technical_timeline.json`.
