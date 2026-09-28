# EZScore_v1 — R35.10 RESET + FULL MEASURE GRID FIX

Correctif ciblé après validation visuelle de la timeline.

## 1. Popup « Réinitialiser les accords »

La popup dédiée ChordsLab est supprimée.

Désormais :
- aucune popup « Réinitialiser » ne peut apparaître pendant `Réanalyser les accords` ;
- la confirmation n’apparaît **que** si l’utilisateur clique réellement sur `Réinitialiser les accords` ;
- elle utilise la modale EZScore globale déjà en place ;
- l’ancienne mécanique JS `resetDialog/resetConfirm` est supprimée.

Le bouton `Réinitialiser les accords` reste lui-même conditionné par `has_chord_overrides` : il ne doit exister que lorsqu’une correction manuelle existe.

## 2. Première mesure complète

La cause de la première mesure incomplète était l’application de `downbeat phase` à l’indexation des mesures.

R35.10 sépare maintenant :
- **timeline/prompteur** : mesure 1 commence à `t=0` et contient exactement le nombre de beats de la signature ;
- **phase/downbeat détecté** : conservé comme métadonnée d’analyse, mais ne tronque plus la première mesure.

Donc en `3/4` :

```text
Mesure 1 : beat 1 | beat 2 | beat 3
Mesure 2 : beat 1 | beat 2 | beat 3
...
```

Même si le premier accord arrive plus tard, les cellules précédentes restent `.`.

## 3. Convention maintenue

- `.` = aucune harmonie / silence harmonique ;
- `-` = l’accord précédent continue ;
- les cellules `.` restent des beats réels de la timeline et sont éditables avec R35.9.

Cette grille absolue depuis `t=0` est également la référence correcte pour LyricsLab : un chant/apocope pourra commencer avant l’harmonie sans être repoussé vers le premier accord.

## Installation

À appliquer après R35.9 :

```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R35_10_RESET_MEASURE_GRID_FIX.zip" -C H:\EZScore_v1

python .\EZScore_v1_R35_10_RESET_MEASURE_GRID_FIX\scripts\apply_r35_10.py H:\EZScore_v1

php bin\console cache:clear
php bin\console lint:container
php bin\console lint:twig templates

python -m py_compile .\analysis\chord_timeline_analysis.py

php .\EZScore_v1_R35_10_RESET_MEASURE_GRID_FIX\tests\r35_10_contract.php H:\EZScore_v1

git diff --check
git status --short
```

Attendu :

```text
R35_10_APPLIED_OK
R35_10_CONTRACT_OK
```

## Important pour le test

La suppression de la mauvaise popup est visible immédiatement après cache clear.

Pour voir la **première mesure complète à 3 temps**, il faut refaire une **réanalyse ChordsLab**, car `measure_index` et `beat_index` sont persistés dans les événements d’analyse existants.

Aucune migration DB.
Le script ne committe et ne pousse rien.
