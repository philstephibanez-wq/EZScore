# EZScore_STEM_CONDUCTOR_R1

Base GitHub vérifiée avant livraison :

```text
master = 87f1e7c3ae9b63cbbff611b6f7c5d03c35341f9d
```

Ce livrable concerne uniquement le **lecteur STEM de l'onglet Analyse**.
Le player Karaoké/publication n'est pas modifié.

## Contrat appliqué

Deux lignes continues :

```text
Accords :  Am   -   -   -      Am   -   -   -      Em   -   -   -
Paroles :       Je vous parle d'un temps ...
```

Notation EZScore :

```text
Am---  = Am sur le premier temps + maintien sur 3 temps
```

Si le même accord continue dans la mesure suivante, il est répété au premier
temps de la nouvelle mesure :

```text
mesure 1 : Am---
mesure 2 : Am---
mesure 3 : Em---
```

`-` = maintien harmonique d'un temps.

## Alignement et absence de chevauchement

Accords et paroles utilisent exactement la même fonction :

```text
X(t) = t * pixelsPerSecond
```

Aucun mot n'est déplacé individuellement.

Le player mesure les largeurs réelles des mots puis augmente une seule
échelle globale en pixels/seconde jusqu'à ce que les mots successifs ne se
chevauchent plus.

Donc :

```text
accord à 20.000 s -> X(20.000)
mot à 20.000 s    -> X(20.000)
```

reste toujours vrai.

Il n'y a ni retour à la ligne, ni deuxième rangée de paroles.

## Prolongation vocale

Convention active :

```text
-  = maintien d'accord
_  = prolongation vocale
```

R1 ajoute des `_` quand la durée acoustique d'un mot dépasse nettement sa
durée attendue.

Exemple :

```text
bohème___
```

Le placement interne exact, par exemple `bohè___me`, nécessitera ensuite les
spans phonétiques MMS_FA. R1 ne fabrique pas une syllabe interne par heuristique.

## Diagrammes guitare

Le lecteur possède une case `Diagrammes guitare`.

Si elle est cochée et qu'un voicing EZScore existe pour l'accord courant, le
diagramme courant apparaît sous les deux lignes.

La préférence EZScore existante sert de valeur initiale.

## Application

```powershell
cd H:\EZScore

tar -xf "$env:USERPROFILE\Downloads\EZScore_STEM_CONDUCTOR_R1.zip" -C H:\EZScore

.\.venv-py313\Scripts\python.exe -m py_compile `
  .\ezscore\player\stem_analysis_conductor.py `
  .\ezscore\integration\choir_pipeline.py `
  .\scripts\test_stem_conductor_contract.py

.\.venv-py313\Scripts\python.exe .\scripts\test_stem_conductor_contract.py
```

Attendu :

```text
STEM CONDUCTOR CONTRACT OK
timeline rows: 2
lyrics wrapping: DISABLED
lyrics collision policy: GLOBAL SCALE
chords: repeated at measure start
chord sustain: '-'
vocal sustain: '_'
diagram: OPTIONAL
karaoke player: UNTOUCHED
```

Puis redémarrer Streamlit normalement.
