# EZScore_TECHNICAL_TIMELINE_R1

Base GitHub vérifiée avant livraison :

```text
master = 27a2ff8d7c7bbd8869933dd489cce45714cbefd6
```

## Cause corrigée

`Paroles + accords` était affiché dès l'étape 2, mais la timeline beats+accords
n'était créée qu'à l'étape 3 `Blocs / structure`.

Donc l'éditeur disait :

```text
Timeline de beats absente
```

Ce n'était pas un problème MMS_FA. C'était un problème d'ordre architectural.

## Nouvelle séparation

EZScore possède maintenant un cache technique indépendant :

```text
technical_timeline.json
```

Il contient uniquement :

```text
beats absolus
accord par beat
tempo
moteurs utilisés
timebase = original_audio_seconds
```

Il ne contient aucun bloc, aucune mise en page éditoriale et aucune décision
de structure.

Pipeline :

```text
STEM
  ↓
Batterie -> beats
Original -> accords
  ↓
technical_timeline.json
  ├── player STEM
  ├── Paroles + accords
  └── Étape 3 -> blocs / structure
```

L'étape 3 ne relance donc plus beats + accords : elle réutilise la timeline
technique et ne fait que la projection métrique / segmentation.

## Cache existant

Si `structure_analysis.json` contient déjà une vraie `beat_timeline`, elle est
promue dans `technical_timeline.json` sans réanalyse.

Sinon la timeline est construite avec :
- `madmom-infer` sur le STEM Batterie ;
- `lv-chordia` sur l'audio original ;
- le cache lv-chordia existant est réutilisé s'il est déjà présent.

Aucun beat artificiel n'est créé.

## Application

```powershell
cd H:\EZScore

tar -xf "$env:USERPROFILE\Downloads\EZScore_TECHNICAL_TIMELINE_R1.zip" -C H:\EZScore

.\.venv-py313\Scripts\python.exe -m py_compile `
  .\ezscore\analysis\technical_timeline.py `
  .\ezscore\player\stem_analysis_conductor.py `
  .\ezscore\integration\choir_pipeline.py `
  .\scripts\test_technical_timeline_contract.py

.\.venv-py313\Scripts\python.exe .\scripts\test_technical_timeline_contract.py
```

Attendu :

```text
TECHNICAL TIMELINE CONTRACT OK
beats+chords cache: technical_timeline.json
Paroles+accords editor: CONNECTED
STEM conductor: CONNECTED
Step 3 blocks: REUSES technical timeline
fake beat fallback: NONE
```

Puis redémarrage complet de Streamlit.

Au premier affichage après ce patch, si aucune timeline technique n'existe
encore, EZScore affichera temporairement :

```text
Construction de la timeline beats + accords…
```

Ensuite elle est persistée et réutilisée.
