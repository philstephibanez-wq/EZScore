# EZScore_STEM_CONDUCTOR_SHARED_R1

Base GitHub vérifiée :

```text
master = 5235963939750c2341a410d04bcdb045c490ab56
EZScore_STEM_USE_PAROLES_LAYOUT_R1
```

Le player STEM est présent directement quand on entre dans `1 · STEM`.

Le conducteur charge le moteur déjà validé de `Analyse > Paroles` :

```text
templates/views/lyrics-layout.js
```

Il utilise directement :

```text
ezLayoutLaneNodes(...)
ezVisualXForTime(...)
```

Aucune réduction de données :

```javascript
const words = normalizedWords(rawWords);
const lyricNodes = words.map(...);
const chordItems = beats.map(...);
```

Donc tous les mots et tous les beats/accords reçus sont matérialisés dans le
conducteur continu. Accords et paroles utilisent exactement le même repère
visuel.

La ligne textuelle Chœurs est masquée dans Paroles. `backing_vocals.wav`
reste disponible dans le mixer audio STEM.

## Application

Ne pas réappliquer R2b : le master est déjà plus récent.

```powershell
cd H:\EZScore

tar -xf "$env:USERPROFILE\Downloads\EZScore_STEM_CONDUCTOR_SHARED_R1.zip" -C H:\EZScore

.\.venv-py313\Scripts\python.exe .\scripts\apply_stem_conductor_shared_r1.py

.\.venv-py313\Scripts\python.exe -m py_compile `
  .\ezscore\player\stem_analysis_conductor.py `
  .\ezscore\ui\stem_lab_analysis.py `
  .\ezscore\ui\chords_lyrics_editor.py `
  .\scripts\test_stem_conductor_shared_r1_contract.py

$env:PYTHONPATH = "H:\EZScore"
.\.venv-py313\Scripts\python.exe .\scripts\test_stem_conductor_shared_r1_contract.py
```

Attendu :

```text
PATCH OK
 - STEM ouvre directement le player
 - TOUS les mots du payload sont créés dans le conducteur
 - TOUS les beats/accords sont créés dans le conducteur
 - accords + paroles utilisent le même lyrics-layout.js que Paroles
 - ligne textuelle Chœurs masquée dans Paroles
 - backing_vocals audio inchangé dans le mixer STEM

STEM CONDUCTOR SHARED R1 CONTRACT OK
shared Paroles layout engine in final JS: YES
all words mapped to lyric nodes: YES
all beats mapped to chord items: YES
same visual timeline for chords + lyrics: YES
player auto-present in STEM: YES
textual choir lane in Paroles: HIDDEN
final JS activeWordIndex declarations: 1
```

Puis redémarrer Streamlit.
