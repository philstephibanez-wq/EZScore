# EZScore_STEM_LAZY_UI_R1

Base distante vérifiée :

```text
master = 907105f1100c95d9eebc7043cbdf56a6ddada7ab
EZScore_LYRICS_RENDER_REMOTE_R1b
```

Le retour dans `1 · STEM` ne monte plus automatiquement les surfaces lourdes.

Avant, deux opérations étaient déclenchées à chaque retour :
- `_download_stems(all_stems)` lit chaque WAV avec `read_bytes()`;
- `_render_stem_player(...)` prépare/enregistre les médias et remonte WebAudio.

Sur l'instance web, cela peut provoquer un timeout de connexion navigateur
alors que le serveur Python continue à tourner.

Nouveau comportement :

```text
Paroles → STEM
        ↓
page légère immédiatement
        ↓
▶ Ouvrir le lecteur STEM       (à la demande)
⬇ Préparer les téléchargements (à la demande)
```

En quittant STEM, le player et les téléchargements sont remis à l'état fermé.

Ergonomie Android :
- boutons pleine largeur ;
- ordre DOM naturel ;
- contrôles internes du lecteur déjà focusables ;
- aucune action lourde déclenchée par le simple changement d'étape.

Application :

```powershell
cd H:\EZScore

tar -xf "$env:USERPROFILE\Downloads\EZScore_STEM_LAZY_UI_R1.zip" -C H:\EZScore

.\.venv-py313\Scripts\python.exe .\scripts\apply_stem_lazy_ui_r1.py

.\.venv-py313\Scripts\python.exe -m py_compile `
  .\ezscore\ui\stem_lab_analysis.py `
  .\scripts\test_stem_lazy_ui_r1_contract.py

$env:PYTHONPATH = "H:\EZScore"
.\.venv-py313\Scripts\python.exe .\scripts\test_stem_lazy_ui_r1_contract.py
```

Attendu :

```text
PATCH OK
...
STEM LAZY UI R1 CONTRACT OK
return-to-STEM heavy auto mount: NO
WAV payloads on simple return: NO
player mount requires explicit action: YES
leaving STEM unloads heavy surfaces: YES
Android remote full-width controls: YES
```

Puis redémarrer Streamlit.

Test :
1. `2 · Paroles`;
2. retour `1 · STEM` : aucun timeout attendu ;
3. `▶ Ouvrir le lecteur STEM` seulement quand nécessaire ;
4. retour Paroles puis STEM : lecteur refermé automatiquement.
