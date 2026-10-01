# EZScore_v1 — R38.13b Continuous harmonic grid

Patch local, à ne pas pousser tant qu'il n'est pas validé.

## But

Supprimer tout saut de ruban harmonique au changement de mesure **quelle que soit la signature** :
- 2/4
- 3/4
- 4/4
- 6/8
- et toute autre signature dont le numérateur représente le nombre de cellules visibles.

## Cause corrigée

R38.13 regroupait les beats à partir de `measure_index`/`beat_index` historiques puis complétait une mesure avec des beats synthétiques.

Exemple critique : une source encore groupée en 4/4 affichée en 6/8 produisait :
- 4 timestamps réels,
- puis 2 timestamps synthétiques,
- puis la mesure source suivante revenait à son timestamp réel.

La timeline d'affichage devenait donc non monotone à chaque frontière de mesure, d'où le saut observé sur Aline.

## Nouvelle règle

La signature n'altère jamais le temps.

Les beats source sont triés une fois par temps absolu puis re-indexés **globalement et continûment** :

```text
2/4 : 0 1 | 2 3 | 4 5 | ...
3/4 : 0 1 2 | 3 4 5 | ...
4/4 : 0 1 2 3 | 4 5 6 7 | ...
6/8 : 0 1 2 3 4 5 | 6 7 8 9 10 11 | ...
```

Aucun beat synthétique. Aucun recalage temporel à une frontière de mesure.

La mesure est uniquement une représentation graphique.

## Installation

```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R38_13B_CONTINUOUS_GRID_ALL_SIGNATURES.zip" -C H:\EZScore_v1

python .\scripts\install_r38_13b_continuous_grid.py H:\EZScore_v1

php .\tests\r38_13b_contract.php H:\EZScore_v1
node .\tests\test_r38_13b_all_signatures.js H:\EZScore_v1
node --check .\public\assets\js\lyricslab-r37.js

php bin\console cache:clear
php bin\console cache:warmup
```

Attendu :

```text
R38_13B_JS_OK
R38_13B_TWIG_OK
R38_13B_INSTALL_OK
R38_13B_CONTINUOUS_GRID_CONTRACT_OK
R38_13B_ALL_SIGNATURES_CONTINUOUS_OK
```

Puis Ctrl+F5.

Aucune réanalyse audio/paroles/accords n'est nécessaire : c'est uniquement une correction de projection/affichage.
