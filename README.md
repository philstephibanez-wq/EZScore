# EZScore_MADMOM_API_R2

Base GitHub vérifiée :

```text
master = d3602562fae60c5bbd04ed81025113be64160169
EZScore_MADMOM_API_R1
```

## Cause du KO R1

La machine contient bien :

```text
madmom-infer 0.2.0
```

mais cette version installée n'expose pas `madmom_infer.detect_beats`.

R1 avait donc encore choisi une API non réellement disponible dans la release
présente.

## Correction R2

La documentation de la release 0.2.0 indique explicitement que son pipeline
complet disponible est :

```python
from madmom_infer.features.downbeats import (
    RNNDownBeatProcessor,
    DBNDownBeatTrackingProcessor,
)
```

R2 utilise donc directement ce pipeline :

```text
drums.wav
  ↓
RNNDownBeatProcessor
  ↓ activations beat/downbeat
DBNDownBeatTrackingProcessor
  ↓ [time, beat_position]
temps absolus des beats
  ↓
technical_timeline.json
```

EZScore ne conserve ici que la colonne `time`. La signature métrique reste
appliquée plus tard ; elle ne déplace jamais les timestamps.

## Pas de réinstallation nécessaire

Si `madmom-infer 0.2.0` est déjà installé, ne réinstallez rien.

## Application

```powershell
cd H:\EZScore

tar -xf "$env:USERPROFILE\Downloads\EZScore_MADMOM_API_R2.zip" -C H:\EZScore

.\.venv-py313\Scripts\python.exe .\scripts\test_madmom_020_api.py

.\.venv-py313\Scripts\python.exe -m py_compile `
  .\ezscore\analysis\rhythm_quality.py `
  .\scripts\test_madmom_020_api.py `
  .\scripts\test_madmom_api_r2_contract.py

.\.venv-py313\Scripts\python.exe .\scripts\test_madmom_api_r2_contract.py
```

Attendu :

```text
madmom-infer version: 0.2.0
RNNDownBeatProcessor: <class ...>
DBNDownBeatTrackingProcessor: <class ...>
MADMOM 0.2.0 DOWNBEAT API OK

MADMOM API R2 CONTRACT OK
detect_beats dependency: REMOVED
features.beats dependency: REMOVED
0.2.0 downbeats pipeline: ENABLED
```

Puis redémarrer Streamlit.

## Première exécution

Le premier vrai passage `RNNDownBeatProcessor` peut télécharger les poids
madmom nécessaires. Ces poids sont séparément sous licence CC BY-NC-SA 4.0
(non-commerciale), point à conserver en tête pour une future exploitation
commerciale d'EZScore.
