# EZScore — Analyseur Chœurs V4.1

## Pourquoi V4 était fausse

Le test a montré :

```text
KEEP Sous ... share=0.00 sim=0.87
KEEP Sous ... share=0.00 sim=0.82
```

C'était incohérent.

La V4 pouvait classer `doubling` uniquement parce que l'activité du stem
Chœurs était forte relativement à son propre niveau moyen. Une fuite minuscule
du Chant dans un stem Chœurs très calme pouvait donc être considérée comme un
doublage réel.

## Correction V4.1

Pour un mot simultané avec le Chant, l'activité relative du stem Chœurs ne suffit
plus.

Il faut désormais une part acoustique réelle du stem Chœurs par rapport aux deux
stems :

```text
backing_share < 0.12
    -> lead_leakage
    -> DROP

backing_share >= 0.25
    -> doubling
    -> KEEP

0.12 <= backing_share < 0.25
    -> analyse spectrale / cas faible
```

Un mot Chœurs sans Chant simultané reste `backing_only` et est conservé.

Aucune règle spécifique à une chanson, un artiste, un mot ou un timestamp.

## Référence rollback

```text
branche : restore/full-reanalysis-r1
HEAD    : 9fedde9557e6ed9100ba29caaebcfcce848ef493

engine Chœurs stable précédent :
ezscore-choir-whisper-small-v3
schema 3
```

## Installation

Dézipper directement dans :

```text
H:\EZScore
```

Puis :

```powershell
cd H:\EZScore
python -m py_compile .\ezscore\analysis\choirs.py
```

## Test

```powershell
python -m ezscore.analysis.choirs `
  --audio-hash "41ea46f13ff411c003e180e719844f944af3366aad4183060121e78f99c478d0" `
  --force
```

Le point à vérifier immédiatement : les deux `Sous` avec `share=0.00` ne doivent
plus apparaître en `KEEP`.
