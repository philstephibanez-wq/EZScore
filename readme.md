# EZScore_v1 — R34 trois profils d’accords simultanés

R34 met en œuvre le modèle retenu pour ChordsLab :

```text
Timeline commune
├── Débutant
├── Intermédiaire
└── Expert
```

## Ce qui change

Une seule analyse audio calcule les éléments lourds une fois :

- beats ;
- downbeats ;
- chroma ;
- tonalité ;
- observations harmoniques.

Puis les trois profils sont générés dans le même job.

### Débutant

- majeur / mineur simples ;
- fort lissage temporel ;
- pas d’enrichissement.

### Intermédiaire

- triades prioritaires ;
- 7, m7, sus, dim si réellement soutenus par le signal.

### Expert

- enrichissements supplémentaires ;
- notamment maj7, 6, m6, add9 ;
- changements moins pénalisés.

## Switch immédiat

Changer Débutant / Intermédiaire / Expert dans ChordsLab :

- change immédiatement la couche affichée ;
- ne lance pas de nouvelle analyse ;
- persiste le profil sélectionné en arrière-plan.

## Édition isolée

Les corrections manuelles sont propres au profil.

Exemple :

```text
Débutant      E  -> Em   (correction utilisateur)
Intermédiaire E7         (inchangé)
Expert        Emaj7      (inchangé)
```

Le reset agit uniquement sur le profil courant.

## Affichage des accords

Notation standard guitariste conservée.

```text
C       oui
Cmaj    non : redondant
C7      oui
Cmaj7   oui : information réellement différente
Cm7     oui
```

Aucun remplacement automatique par des symboles jazz du type triangle.

Les cases de beat ont maintenant une largeur fixe. Les noms longs réduisent localement leur police au lieu d’élargir la mesure pendant le défilement.

## Volume / progression

Le CSS R34 rapproche et renforce le libellé Volume, son slider et son pourcentage.

La progression d’analyse occupe toute la largeur disponible et est plus visible.

## Installation

```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R34_THREE_CHORD_PROFILES.zip" -C H:\EZScore_v1

H:\EZScore_v1\.venv-py313\Scripts\python.exe .\scripts\apply_r34_three_profiles.py

php -l .\src\Service\ChordTimelineResultService.php
php -l .\src\Controller\SongLabController.php
php -l .\src\Domain\Song\SongTimelineEventRepository.php

node --check .\public\assets\js\chordslab.js
H:\EZScore_v1\.venv-py313\Scripts\python.exe -m py_compile .\analysis\chord_timeline_analysis.py

php .\tests\r34_contract.php
php bin\console lint:twig templates
php bin\console cache:clear
```

Attendu :

```text
22 R34 checks passed.
```

Ensuite :

1. fermer / relancer EZScore Analysis Worker ;
2. Ctrl+F5 ;
3. lancer une seule **Réanalyse des accords** ;
4. une fois terminée, passer entre Débutant / Intermédiaire / Expert sans relancer de job.

La première analyse R34 est nécessaire pour remplir les trois couches.

## Base de données

Aucune migration Doctrine : le profil est stocké dans le payload JSON des événements accords existants. Les beats restent uniques.

## Généralité

Aucun titre, artiste, song ID ou cas particulier Aline n’est codé dans le moteur.
