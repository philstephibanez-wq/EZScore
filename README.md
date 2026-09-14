# EZScore — MIDI + performances Analyse — livraison corrigée

Base GitHub vérifiée avant génération :

```text
master = 15518e2e7e50a3d78835d70574457ec3528ad930
commit = EZScore_R30_MIDI_FIX2_FAST
```

## Diagnostic GitHub

Le `master` courant contient encore dans `EZScore.py` :

```python
from ezscore.midi import MIDI_INSTRUMENTS
```

alors que la vue Analyse appelle ensuite :

```python
build_midi_file(...)
```

Le `NameError` est donc confirmé sur le code GitHub courant.

Le module `ezscore.midi` exporte déjà correctement :

```python
build_midi_file
```

Le problème est uniquement la résolution du symbole dans le monolithe.

La vue Analyse GitHub courante utilise aussi encore l'ancien `timeline.py`,
qui crée une trace Plotly et un rectangle pour chaque région d'accord. Cela
explique les temps de rendu très élevés sur certains morceaux.

## Correctif MIDI

`ezscore/ui/app_shell.py` conserve le pré-roll des paroles déjà validé et
ajoute un pont très étroit :

```python
_persistence.build_midi_file = _build_midi_file
_persistence.__all__.append("build_midi_file")
```

Pourquoi cela fonctionne :

1. `EZScore.py` importe `ezscore.ui.app_shell`;
2. le pont expose alors `build_midi_file` dans `ezscore.persistence`;
3. plus bas, `EZScore.py` exécute déjà :

```python
from ezscore.persistence import *
```

4. `build_midi_file` devient donc disponible dans le namespace du monolithe.

Aucun `builtins`, aucun calcul MIDI au démarrage.

## Correctif performances Analyse

`ezscore/timeline.py` est remplacé par la version optimisée :

- waveform en `Scattergl`;
- toutes les régions d'accords dans une seule trace `Bar`;
- tous les noms d'accords dans une seule trace texte;
- environ 4 traces Plotly au total au lieu de centaines;
- cache waveform Streamlit conservé.

Trace attendue :

```text
[EZTRACE][ANALYSE_TIMELINE_PERF]
beats=...
regions=...
waveform_points=...
plotly_traces=...
```

`plotly_traces` doit rester autour de 4.

## Fichiers livrés

```text
ezscore/ui/app_shell.py
ezscore/timeline.py
readme.md
```

Le ZIP ne contient PAS de répertoire racine supplémentaire : il peut être
dézippé directement dans `H:\EZScore`.

Aucune DB.
Aucun audio.
Aucun `apply_*.py`.
Aucun fichier auth/SSO.

## Installation

```powershell
cd H:\EZScore

tar -xf "$env:USERPROFILE\Downloads\EZScore_R30_MIDI_PERF_FINAL.zip" -C H:\EZScore

python -m py_compile .\ezscore\ui\app_shell.py
python -m py_compile .\ezscore\timeline.py
python -m py_compile .\EZScore.py
python -m compileall -q .\ezscore

python -m streamlit run .\EZScore.py
```

## Recette

1. Ouvrir une chanson.
2. Passer en `Analyse`.
3. Vérifier l'absence de :

```text
NameError: name 'build_midi_file' is not defined
```

4. Vérifier la présence en console de :

```text
[EZTRACE][MIDI_SYMBOL] build_midi_file exported=true
[EZTRACE][ANALYSE_TIMELINE_PERF] ...
```

5. Vérifier que le bouton de téléchargement MIDI apparaît.
6. Tester `Analyse -> Grille -> Analyse` pour comparer le temps du second rendu.

Le découpage R33 et le pré-roll des paroles restent inchangés.
