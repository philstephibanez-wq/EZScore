# EZScore R29 FIX6 — paroles alignées + contrôles morceau permanents

Correctif cumulatif des régressions observées après R29.

## Paroles : même découpage, même texte partout

La vue `Blocs > Édition` reste l'unique éditeur canonique des paroles.

Le défaut venait d'une différence de frontière temporelle entre :
- l'éditeur de blocs : fin de bloc = fin de dernière mesure + 1 ms ;
- `Paroles + accords` / player : fin de bloc = fin exacte de la mesure.

Un mot placé sur la frontière pouvait donc appartenir à deux blocs différents selon la vue.

FIX6 uniformise la convention :
- `time_start` = début de la première mesure ;
- `time_end` = fin de la dernière mesure + 0,001 s.

La même clé de bloc est donc utilisée par :
- Blocs ;
- Paroles + accords ;
- player Vue ;
- player MIDI de contrôle.

Lorsqu'une correction de paroles est validée, une ancienne correction chevauchant le même bloc est supprimée afin d'éviter qu'une correction historique ne réapparaisse dans une autre vue.

## Contrôles permanents du morceau

Les commandes de navigation du morceau ne sont plus dans le flux vertical principal.

Elles sont regroupées dans le panneau gauche, sous le profil :
- Vue : Grille / Paroles + accords / Blocs / Analyse ;
- Mode : Vue / Éditer ;
- Capodastre.

Elles restent donc accessibles même lorsqu'on est descendu loin dans la partition.

Sur smartphone/tablette, elles restent dans le drawer latéral tactile.

## Capodastre

Le capo reste un réglage d'affichage temps réel :
- grille : transposée pour les formes à jouer ;
- Paroles + accords : transposé ;
- player Vue : transposé ;
- diagrammes guitare : transposés ;
- player MIDI : noms/diagrammes transposés mais harmonie MIDI réelle inchangée ;
- aucune réanalyse.

## Fichiers du livrable

- `EZScore.py`
- `readme.md`
- `ezscore/persistence.py`
- `ezscore/player/web_player.py`
- `ezscore/backoffice/player.py`
