# EZScore_v1 — R33.2 ChordsLab async + progression + UX

Ce livrable corrige les retours sur le premier prompteur.

## Analyse asynchrone

`Réanalyser les accords` crée maintenant un job `chords`.

Le job est pris par **EZScore Analysis Worker** au lieu de bloquer la requête PHP.

Conséquences :

- le job apparaît dans le Worker ;
- plus de blocage du serveur local pendant le calcul ;
- progression publiée vers EZScore ;
- barre de progression visible dans ChordsLab.

## Barre de progression

Étapes indicatives :

```text
5%   chargement
18%  beats
32%  chroma
50%  reconnaissance
68%  lissage
84%  timeline
96%  résultat
100% terminé
```

## Modes d'analyse

**Débutant**
- majeur / mineur uniquement ;
- pénalité forte sur les changements ;
- résultat volontairement stable.

**Intermédiaire**
- triades prioritaires ;
- 7 / m7 / sus / dim seulement si suffisamment établis ;
- lissage intermédiaire.

**Expert**
- davantage d'enrichissements ;
- pénalité de changement plus faible ;
- résultat plus détaillé.

## Alignement de mesure

R33.2 estime la phase de downbeat.

Si la confiance est faible, le premier beat détecté reste le beat 1.

Si une levée est réellement probable, elle est représentée explicitement au lieu de décaler toute la chanson.

Le prompteur utilise les `measure_index` / `beat_index` canoniques pour la signature enregistrée.

## UI

- popup navigateur du reset remplacée par une modale EZScore ;
- slider **Volume** immédiatement visible dans le transport ;
- ce slider pilote le même master que la chaîne d'effets ;
- explication dynamique du mode Débutant / Intermédiaire / Expert.

## Installation

```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R33_2_ASYNC_PROGRESS_UX.zip" -C H:\EZScore_v1

H:\EZScore_v1\.venv-py313\Scripts\python.exe .\scripts\apply_r33_2_async_progress.py

php -l .\src\Service\SongChordJobService.php
php -l .\src\Service\ChordTimelineStorage.php
php -l .\src\Service\ChordTimelineResultService.php
php -l .\src\Controller\SongLabController.php
php -l .\src\Controller\AnalysisDesktopController.php

node --check .\public\assets\js\chordslab.js
node --check .\public\assets\js\chordslab-r33-2.js

H:\EZScore_v1\.venv-py313\Scripts\python.exe -m py_compile .\analysis\chord_timeline_analysis.py
H:\EZScore_v1\.venv-py313\Scripts\python.exe -m py_compile .\worker_app\ezscore_analysis_worker.pyw

php .\tests\r33_2_contract.php
php bin\console lint:yaml translations
php bin\console lint:twig templates
php bin\console cache:clear
```

Attendu :

```text
19 R33.2 checks passed.
```

Ensuite :

1. fermer puis relancer **EZScore Analysis Worker** ;
2. `Ctrl+F5` dans le navigateur ;
3. choisir le niveau d'analyse ;
4. **Enregistrer** ;
5. cliquer **Réanalyser les accords**.

Le job doit apparaître dans le Worker et la barre de progression dans ChordsLab.

Aucune migration Doctrine.
