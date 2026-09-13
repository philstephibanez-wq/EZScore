# EZScore R25 — paroles continues et diagrammes synchronisés

R25 corrige les deux régressions constatées après le passage au bandeau par mesure de R24.

## Paroles synchronisées

Les paroles ne sont plus figées dans la carte de mesure.

Le player utilise maintenant deux couches indépendantes :

- **accords / beats** : une carte stable par mesure ;
- **paroles** : un ruban continu basé sur les timestamps Whisper.

Le ruban de paroles :

- défile continûment de droite vers gauche ;
- conserve le mot courant dans la zone centrale ;
- met en évidence le mot courant ;
- atténue les mots déjà passés ;
- garde les mots à venir visibles pour l'anticipation ;
- suit directement `audio.currentTime`, donc reste synchronisé avec le MP3, y compris quand la vitesse de lecture change.

Cette logique est active dans le player Vue et dans le player de contrôle Édition MP3 + MIDI.

## Diagrammes guitare synchronisés

Le player Vue expose maintenant directement l'option :

`Diagrammes guitare`

Le contrôle est visible à côté de la vitesse.

Quand l'option est active :

- le diagramme apparaît au-dessus du nom de l'accord courant ;
- il utilise le voicing sélectionné dans le back-office ;
- il change automatiquement si l'accord change à l'intérieur d'une mesure ;
- la carte de mesure reste stable.

Le player d'édition dispose lui aussi d'un contrôle direct d'affichage des diagrammes, en complément de la configuration persistante des voicings dans l'expander du back-office.

La préférence persistée du morceau reste utilisée comme valeur initiale. Le toggle embarqué dans le player agit immédiatement sur l'affichage courant.

## Bandeau par mesure conservé

Le contrat R24 reste inchangé :

```text
┌────────────┐
│   [diag]   │   optionnel
│     Em     │
│  - . - .   │
└────────────┘
```

- une carte = une mesure ;
- le nom de l'accord n'est pas répété par beat ;
- le beat courant est surligné ;
- la carte courante reste centrée pendant la mesure ;
- le changement de carte intervient au changement de mesure ;
- les mesures à venir restent visibles à droite.

## Vitesse

En mode Vue :

- 0.5×
- 0.75×
- 0.9×
- 1.0×
- 1.1×
- 1.25×
- 1.5×

Le MP3 reste l'horloge maître et le ruban de paroles suit `audio.currentTime`.

## Fichiers modifiés

R25 modifie uniquement :

- `ezscore/player/web_player.py`
- `ezscore/midi/web_player.py`
- `readme.md`

## Étape suivante

Après validation de R25, le prochain chantier est l'authentification et les droits :

- admin ;
- editor ;
- reader ;
- anonymous ;
- permissions serveur ;
- séparation front-office / back-office ;
- préparation des accès authentifiés et payants.

Le site actuellement exposé via Cloudflare Tunnel restera le point d'entrée public, mais les fonctions de back-office devront être protégées avant ouverture plus large.
