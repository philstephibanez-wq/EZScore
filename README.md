# EZScore R23 — player Vue, beats, highlight et vitesse

R23 poursuit la séparation **front-office / back-office** et la modularisation du player.

## Player visible dans les vues

Les vues **Grille** et **Paroles + accords** affichent maintenant un player MP3 lorsque le mode est **Vue**.

Ce player de lecture ne contient **aucun MIDI**. Il réutilise la même identité visuelle et la même timeline que le player d’édition :

- pochette ;
- titre / artiste ;
- transport MP3 ;
- bandeau accords + paroles ;
- beats visibles ;
- accord courant mis en évidence ;
- anticipation à droite ;
- passé atténué à gauche ;
- diagramme guitare optionnel au-dessus du nom de l’accord courant.

Le mode **Édition** conserve le player de contrôle **MP3 + MIDI**.

## Vitesse de lecture en mode Vue

Le player Vue propose :

- 0.5×
- 0.75×
- 0.9×
- 1.0×
- 1.1×
- 1.25×
- 1.5×

La vitesse est appliquée via `HTMLMediaElement.playbackRate`. Le navigateur conserve la hauteur autant que possible via `preservesPitch`.

Le bandeau reste synchronisé car sa source de temps reste `audio.currentTime`.

## Bandeau rythmique

R23 remplace la logique visuelle centrée uniquement sur les changements d’accord par une timeline **un élément par beat**.

Chaque élément contient :

- numéro du beat ;
- accord lorsqu’un changement survient ;
- fragment de paroles correspondant au beat ;
- mesure ;
- horodatage début / fin.

Le déplacement est continu pendant le beat, pas uniquement au changement d’accord.

L’élément courant reçoit un highlight visible ; les éléments futurs restent lisibles pour l’anticipation.

## Diagramme courant

Quand l’option diagrammes est activée dans le back-office :

- le voicing choisi reste persistant ;
- le diagramme de l’accord courant apparaît au-dessus du nom de l’accord ;
- la vue Lecture réutilise exactement ce choix ;
- le diagramme n’est jamais obligatoire.

Le rendu SVG a été renforcé pour les thèmes sombres : grille, barrés, doigts, cordes ouvertes et cordes étouffées sont plus contrastés.

## Player d’édition

Le player MP3 + MIDI conserve le MP3 comme horloge maître et utilise désormais la même timeline visuelle par beat que le player Vue.

R23 augmente aussi la hauteur du composant afin d’éviter la petite fenêtre interne et les scrollbars qui masquaient le bandeau.

## Modularisation R23

Nouveaux modules :

- `ezscore/player/timeline.py` — timeline canonique du player à partir de la grille effective ;
- `ezscore/player/web_player.py` — player MP3 sans MIDI pour le mode Vue.

Modules adaptés :

- `EZScore.py` — orchestration Vue / Édition ;
- `ezscore/backoffice/player.py` — partage de la timeline canonique ;
- `ezscore/midi/web_player.py` — beats, highlight, diagramme courant, fenêtre agrandie ;
- `ezscore/player/__init__.py` ;
- `ezscore/guitar/voicings.py` — lisibilité SVG.

Principe maintenu : **`EZScore.py` orchestre, les responsabilités restent dans des modules dédiés.**

## Contrat d’accès

Le front n’est pas nécessairement public. À terme :

- anonyme : uniquement contenus autorisés ;
- lecteur authentifié : accès selon droits ;
- abonné : accès selon offre ;
- éditeur : front + back-office ;
- admin : tous droits.

Authentification, autorisation et facturation restent séparées.

## Livrable R23

Le ZIP contient uniquement les fichiers modifiés ou ajoutés par R23 :

- `EZScore.py`
- `readme.md`
- `ezscore/backoffice/player.py`
- `ezscore/midi/web_player.py`
- `ezscore/player/__init__.py`
- `ezscore/player/timeline.py`
- `ezscore/player/web_player.py`
- `ezscore/guitar/voicings.py`

Dézipper dans `H:\EZScore` en conservant l’arborescence.
