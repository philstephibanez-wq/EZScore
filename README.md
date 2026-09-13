# EZScore R24 — bandeau par mesure, beats animés et diagramme optionnel

R24 corrige le comportement du bandeau demandé après R23.

## Principe visuel

Le bandeau n'affiche plus une case par beat.

Il affiche maintenant **une case par mesure**, sur le même principe visuel que la grille :

```text
┌────────────┐
│   [diag]   │   optionnel
│     Em     │
│  - . - .   │
└────────────┘
```

Le diagramme, lorsqu'il est activé, apparaît **au-dessus du nom de l'accord courant**.

## Défilement

Le bandeau ne défile plus rapidement à chaque beat.

- une mesure = une carte ;
- la carte courante reste centrée pendant la mesure ;
- le passage visuel à la carte suivante se fait au changement de mesure ;
- la mesure précédente reste visible à gauche ;
- les mesures suivantes restent visibles à droite pour l'anticipation.

Le mouvement est donc beaucoup plus stable.

## Beats

La ligne inférieure de la carte reprend la logique compacte de la grille.

- le nom principal de l'accord n'est pas répété sur chaque beat ;
- `-` représente une tenue / continuité ;
- `.` représente le marqueur déjà utilisé par la grille ;
- un changement d'accord exceptionnel au milieu de la mesure peut apparaître dans la subdivision correspondante ;
- le beat courant est surligné ;
- les beats déjà passés restent marqués plus discrètement.

Le nom affiché au centre de la carte suit l'accord réellement courant si un changement intervient à l'intérieur de la mesure.

## Diagrammes guitare

Les choix de voicing R22/R23 sont conservés.

- affichage optionnel ;
- même voicing en Vue et en Édition ;
- diagramme de l'accord courant au-dessus du nom ;
- changement automatique si l'accord change dans la mesure.

## Mode Vue

Les vues **Grille** et **Paroles + accords** conservent :

- player MP3 ;
- pochette, titre, artiste ;
- variation de vitesse ;
- pitch préservé autant que possible ;
- bandeau par mesure ;
- paroles associées à la mesure ;
- diagramme optionnel.

Aucun MIDI n'est utilisé en mode Vue.

## Mode Édition

Le player de contrôle conserve :

- MP3 maître ;
- MIDI SoundFont ;
- volumes MP3 / MIDI ;
- même bandeau par mesure ;
- même beat courant ;
- même diagramme optionnel.

Ainsi Vue et Édition utilisent la même représentation temporelle sans dupliquer le modèle métier.

## Modularisation

R24 modifie uniquement :

- `ezscore/player/timeline.py`
- `ezscore/player/web_player.py`
- `ezscore/backoffice/player.py`
- `ezscore/midi/web_player.py`
- `readme.md`

La timeline canonique ajoute maintenant `build_measure_timeline()`, utilisée par les deux players.

## Suite prévue

Après validation de R24, l'étape suivante est la **mise en ligne sur Cloudflare**, même si EZScore n'est pas encore fonctionnellement terminé. La publication devra préserver la séparation front-office / back-office et préparer l'authentification / autorisation déjà prévue.

## Livrable

Le ZIP contient uniquement les fichiers modifiés de R24.

Dézipper dans `H:\EZScore` en conservant l'arborescence.
