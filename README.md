# EZScore — Ordered Playlists & Events R1

## Portée

Ce lot termine le **brouillon fonctionnel** de la gestion des playlists
ordonnées avant de commencer le karaoké.

Principes retenus :

```text
Groupe
├── Playlist ordonnée
├── Répétition
│   └── Playlist ordonnée / setlist
└── Concert
    └── Playlist ordonnée / setlist
```

La playlist reste la source de vérité musicale. Une répétition ou un concert
ajoute les métadonnées de contexte, mais utilise une playlist ordonnée normale.

## Ouvrir la playlist

Le libellé ambigu `Ouvrir dans Playlists` est remplacé fonctionnellement par :

```text
Ouvrir la playlist
```

Le clic transporte le `playlist_id` et ouvre directement la playlist concernée,
pas simplement la page générale des playlists.

## Setlist ordonnée

Chaque playlist possède déjà `user_playlist_items.position`.

Ce lot l'exploite comme ordre de passage partagé.

La page d'une playlist affiche :

```text
☰ 1  Aline
☰ 2  Dance Me
☰ 3  Tombe la neige
```

L'ordre est modifiable par :

- drag & drop ;
- boutons `↑` / `↓` de secours.

Chaque changement valide que la liste contient exactement les mêmes morceaux,
sans doublon ni disparition, puis réécrit les positions en transaction.

Pour une playlist de groupe, tous les membres autorisés retrouvent le même ordre.

## Préparer une répétition / un concert

Dans **Mes groupes > Playlists**, deux actions sont ajoutées :

```text
🎤 Préparer une répétition
🎸 Préparer un concert
```

Le formulaire contient :

- titre ;
- date ;
- heure ;
- lieu ;
- objectif / notes.

La création produit :

1. un événement de groupe ;
2. sa playlist/setlist ordonnée ;
3. l'ouverture directe de cette playlist.

## Modèle ajouté

```text
group_events
- event_id
- group_id
- playlist_id
- event_type       # rehearsal / concert
- title
- starts_at
- location
- notes
- created_by_user_id
- created_at
- updated_at
```

Un événement référence une playlist unique. Cela prépare directement la future
session de karaoké sans coupler encore le player à cette couche.

## Architecture du drag/drop

Module Python :

```text
ezscore/ui/playlist_order_editor.py
```

Templates obligatoires :

```text
templates/views/playlist-order-editor.html
templates/views/playlist-order-editor.css
templates/views/playlist-order-editor.js
```

Le composant navigateur ne touche jamais SQLite. Il ne fait que retourner un
ordre de `audio_hash`. La validation et la persistence restent dans :

```text
ezscore/catalog_social.py
```

## Templates supplémentaires

```text
templates/views/catalog-playlist-detail.score
templates/views/catalog-event.score
templates/views/group-event.score
```

## i18n

Catalogues mis à jour :

```text
i18n/catalog.fr.json
i18n/catalog.en.json
i18n/groups.fr.json
i18n/groups.en.json
```

## Non-régression Analyse + Paroles

Ce lot NE CONTIENT PAS et NE MODIFIE PAS :

```text
EZScore.py
ezscore/ui/__init__.py
ezscore/ui/app_shell.py
ezscore/ui/stem_lab_analysis.py
ezscore/ui/editorial_timeline.py
ezscore/ui/lyrics_inline_editor.py
ezscore/player/karaoke_stem_webaudio*.py
templates/views/lyrics-editor.*
```

Donc sont hors périmètre :

- correctif Aline `beat_timeline[].time` ;
- Paroles R5.10 ;
- ancres ;
- `↵` ;
- accords éditoriaux ;
- player Analyse/STEM ;
- timestamps techniques.

## Installation

```powershell
cd H:\EZScore

Expand-Archive `
  -Path "$env:USERPROFILE\Downloads\EZScore_ORDERED_PLAYLISTS_EVENTS_R1.zip" `
  -DestinationPath . `
  -Force

python -m py_compile `
  .\ezscore\catalog_social.py `
  .\ezscore\ui\catalog_home.py `
  .\ezscore\ui\groups_home.py `
  .\ezscore\ui\playlist_order_editor.py

node --check .\templates\views\playlist-order-editor.js

git diff --check
git status --short
```

## Test ciblé

1. Ouvrir `Mes groupes`.
2. Ouvrir Blues Fiber.
3. Cliquer `Préparer une répétition`.
4. Créer une répétition.
5. Vérifier l'ouverture directe de sa playlist.
6. Ajouter plusieurs chansons via le `＋` du Répertoire.
7. Revenir à la playlist.
8. Drag/drop : déplacer le morceau 3 en position 1.
9. Recharger la page : l'ordre doit être conservé.
10. Vérifier `↑` / `↓`.
11. Se connecter avec un autre membre du groupe : même ordre.
12. Préparer un concert et vérifier la setlist distincte.
13. Ouvrir Aline > Analyse > Paroles : accords présents.
14. Ouvrir Dance Me > Analyse > Paroles : R5.10 intact.
15. Vérifier le player Analyse/STEM.
