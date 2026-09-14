# EZScore — correctif MIDI Analyse

Base fonctionnelle conservée :

- découpage R33 ;
- correctif pré-roll / post-roll des paroles ;
- SSO/auth inchangé.

## Bug corrigé

Dans `EZScore.py`, la vue Analyse appelle :

```python
_midi_bytes = build_midi_file(...)
```

mais le fichier n'importe actuellement que :

```python
from ezscore.midi import MIDI_INSTRUMENTS
```

Le module `ezscore.midi` exporte pourtant déjà `build_midi_file` et sa signature
correspond exactement à l'appel existant.

Le résultat était :

```text
NameError: name 'build_midi_file' is not defined
```

## Correctif

Cette livraison ajoute un pont de compatibilité très limité dans
`ezscore/ui/app_shell.py` :

```python
from ezscore.midi import build_midi_file as _build_midi_file
builtins.build_midi_file = _build_midi_file
```

Aucun code de génération MIDI n'est modifié.

Cette solution évite de remplacer le gros `EZScore.py` pendant la phase de
stabilisation actuelle. Le pont pourra être supprimé lorsque la vue Analyse
sera sortie du monolithe et importera directement `build_midi_file`.

## Invariants

```text
timeline accords  : inchangée
timeline phonèmes : inchangée
timeline paroles  : inchangée
structure R33     : inchangée
pré-roll paroles  : conservé
SSO/auth           : inchangé
```

## Fichiers livrés

```text
ezscore/ui/app_shell.py
readme.md
```

Aucune base SQLite.
Aucun audio.
Aucun `apply_*.py`.

## Installation

Dézipper dans `H:\EZScore` en conservant l'arborescence.

Puis :

```powershell
cd H:\EZScore
python -m py_compile .\ezscore\ui\app_shell.py
python -m py_compile .\EZScore.py
python -m compileall -q .\ezscore
python -m streamlit run .\EZScore.py
```

## Recette

Ouvrir un morceau puis :

```text
Analyse
→ Comparaison audio / accords
```

Le bloc ne doit plus afficher :

```text
NameError: name 'build_midi_file' is not defined
```

Le bouton `Télécharger le MIDI des accords` doit être disponible.
