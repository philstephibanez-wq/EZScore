# EZScore_MADMOM_API_R1

Base concernée : `EZScore_TECHNICAL_TIMELINE_R2` appliquée localement.

## Cause exacte

L'erreur :

```text
ModuleNotFoundError: No module named 'madmom_infer.features.beats'
```

vient d'un import trop couplé à l'organisation interne du paquet.

EZScore utilisait :

```python
from madmom_infer.features.beats import ...
```

Le correctif utilise l'API publique documentée :

```python
import madmom_infer as mm
beats = mm.detect_beats(audio_path)
```

## Version fixée

```text
madmom-infer==0.2.0
```

Cette version supporte Python 3.13.

## Application

```powershell
cd H:\EZScore

tar -xf "$env:USERPROFILE\Downloads\EZScore_MADMOM_API_R1.zip" -C H:\EZScore

.\.venv-py313\Scripts\python.exe -m pip install --upgrade --force-reinstall `
  madmom-infer==0.2.0

.\.venv-py313\Scripts\python.exe .\scripts\test_madmom_public_api.py

.\.venv-py313\Scripts\python.exe -m py_compile `
  .\ezscore\analysis\rhythm_quality.py `
  .\scripts\test_madmom_public_api.py `
  .\scripts\test_madmom_api_contract.py

.\.venv-py313\Scripts\python.exe .\scripts\test_madmom_api_contract.py
```

Attendu :

```text
madmom-infer version: 0.2.0
detect_beats callable: True
MADMOM PUBLIC API OK

MADMOM API CONTRACT OK
internal processor import: REMOVED
public detect_beats API: ENABLED
```

Puis redémarrer complètement Streamlit.

Au premier vrai calcul de beats, `madmom-infer` peut télécharger ses poids de
modèle.
