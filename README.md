# EZScore R30 FIX2 — sauts de ligne visibles dans le parolier

Correctif incrémental à appliquer après R30 FIX1.

## Paroles + accords

Les retours à la ligne validés dans Blocs > Édition restent la source canonique.
Le parolier matérialise maintenant explicitement la séparation entre deux vers manuels.

Aucun texte n'est recalculé, aucun accord n'est déplacé et aucune réanalyse n'est lancée.

Le même découpage est également repris par le rendu imprimable basé sur la même fonction de lignes.

## Fichiers modifiés

- ezscore/persistence.py
- readme.md
