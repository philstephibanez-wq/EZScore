# EZScore — MIDI FIX2 / suppression de la régression de lenteur

## Constat

La première correction MIDI utilisait :

```python
builtins.build_midi_file = ...
```

Même si cette affectation est simple, elle modifiait l'espace global Python de
tout le processus Streamlit. Puisque la lenteur est apparue immédiatement après
cette livraison, ce mécanisme est supprimé complètement.

## Correctif

Cette version repart de `app_shell.py` validé juste avant le correctif MIDI,
donc elle conserve le correctif de pré-roll des paroles.

Le symbole MIDI est fourni de façon beaucoup plus étroite :

```python
_persistence.build_midi_file = _build_midi_file
_persistence.__all__.append("build_midi_file")
```

`EZScore.py` exécute ensuite déjà :

```python
from ezscore.persistence import *
```

Il récupère donc `build_midi_file` normalement, sans modifier `builtins`.

## Effet attendu

- aucune génération MIDI hors de la vue `Analyse` ;
- aucune modification globale du runtime Python ;
- pré-roll des paroles conservé ;
- moteur R33 inchangé ;
- erreur `build_midi_file is not defined` corrigée.

## Installation

```powershell
cd H:\EZScore
tar -xf "$env:USERPROFILE\Downloads\EZScore_R30_MIDI_FIX2_FAST.zip" -C H:\EZScore

python -m py_compile .\ezscore\ui\app_shell.py
python -m py_compile .\EZScore.py
python -m compileall -q .\ezscore

python -m streamlit run .\EZScore.py
```

## Recette

Tester d'abord la navigation entre :

```text
Grille
Paroles + accords
Blocs
Analyse
```

La réactivité doit revenir à celle d'avant le premier correctif MIDI.

Ensuite, dans `Analyse`, vérifier que le bouton MIDI fonctionne et qu'il n'y a
plus de `NameError`.
