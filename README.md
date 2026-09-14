# EZScore R29 FIX5 — export du helper de paroles canonique

Correctif ciblé du FIX4.

## Cause

`EZScore.py` importe la persistance avec :

```python
from ezscore.persistence import *
```

Le module `ezscore.persistence` définit explicitement `__all__`.  
La nouvelle fonction `effective_lyrics_words_for_sections` avait été ajoutée au module mais oubliée dans cette liste.

Conséquence : la fonction existait bien dans `persistence.py`, mais n'était pas importée dans `EZScore.py`, d'où :

```text
NameError: name 'effective_lyrics_words_for_sections' is not defined
```

## Correction

`effective_lyrics_words_for_sections` est maintenant exportée dans `__all__`.

Aucun autre comportement du FIX4 n'est modifié.

## Fichiers du livrable

- `readme.md`
- `ezscore/persistence.py`
