# EZScore — GROUPS MENU R1

## Objet

Ce lot ajoute une vraie entrée **👥 Mes groupes** dans le menu utilisateur,
directement sous **Mon profil**, avec une page dédiée de gestion des groupes.

Il exploite le modèle social déjà présent dans EZScore :

```text
user_groups
user_group_members
user_playlists(owner_type = user|group)
user_playlist_items
playlist_shares
```

Aucune nouvelle migration SQLite n'est nécessaire dans ce lot.

## UX

Menu principal utilisateur :

```text
🎵 Répertoire
👤 Mon profil
👥 Mes groupes
✏️ Mes éditions
⬆️ Importer
```

La page **Mes groupes** permet :

- créer un groupe ;
- voir tous les groupes auxquels l'utilisateur appartient ;
- afficher rôle, nombre de membres et nombre de playlists ;
- ajouter un utilisateur actif ;
- choisir `Membre` ou `Admin` ;
- modifier le rôle d'un membre ;
- retirer un membre ;
- créer une playlist appartenant au groupe ;
- voir les playlists du groupe et leur nombre de chansons ;
- retourner vers la surface Playlists ;
- supprimer le groupe pour un admin.

L'ergonomie suit le modèle mental évoqué : groupe identifiable, membres et
playlists immédiatement accessibles, proche de WhatsApp dans l'organisation
mais sans messagerie.

## Modularité

La logique de groupes reste hors du shell :

```text
ezscore/ui/groups_home.py
```

Les visuels sont externalisés dans SCORE :

```text
templates/views/groups-home.score
templates/views/group-card.score
templates/views/group-member.score
templates/views/group-playlist.score
templates/views/groups-empty.score
```

Le shell historique n'est pas modifié. `ezscore/ui/__init__.py` injecte
temporairement le bouton au rendu puis restaure les fonctions Streamlit.

Cela évite de modifier `EZScore.py` et son enum historique
`Répertoire / Chanson / Compte / Import`.

## i18n

Nouveau domaine indépendant :

```text
i18n/groups.fr.json
i18n/groups.en.json
```

Le bouton du menu et la page utilisent le service i18n déjà introduit dans
EZScore. Aucun nouveau texte métier de cette surface n'est codé en dur dans les
templates.

## Karaoké synchronisé de groupe — exigence enregistrée

Cette fonctionnalité est **spécifiée pour une phase ultérieure**, mais n'est pas
activée dans ce lot.

Le modèle cible est :

```text
Groupe
  └── Playlist
       └── KaraokeSession
            ├── session_id
            ├── group_id
            ├── playlist_id
            ├── host_user_id
            ├── current_song_id
            ├── state              # playing / paused / stopped
            ├── reference_time
            ├── position
            ├── playback_rate
            └── participants
```

Contraintes retenues :

1. Un membre autorisé crée une session depuis une playlist de groupe.
2. Un **hôte** contrôle Lecture / Pause / Stop / seek / morceau suivant.
3. Les autres membres rejoignent la même session.
4. Le serveur synchronise **l'état et une horloge commune**, pas un flux audio
   envoyé depuis le navigateur de l'hôte.
5. Chaque navigateur charge localement le même audio / les mêmes STEMs.
6. Correction périodique de dérive entre clients.
7. Les paroles, accords, sections et progression utilisent la même timeline.
8. Chaque utilisateur conserve **son propre mix local** (volumes STEM/EQ), sans
   casser la synchronisation commune.
9. La session de groupe ne doit pas écraser les préférences audio personnelles
   `user × chanson`.
10. Ce mécanisme ne doit pas être confondu avec une répétition audio réseau où
    les musiciens s'entendent mutuellement en direct ; ce dernier problème
    nécessite une chaîne audio temps réel spécialisée.

Architecture cible :

```text
                  EZScore server
               Group Karaoke Session
             state + reference clock
                       │
          ┌────────────┼────────────┐
          │            │            │
       User A        User B       User C
       local         local        local
       player        player       player
       + mix         + mix        + mix
          │            │            │
          └──── same canonical timeline ────
```

Cette architecture devra réutiliser le moteur audio HTMLMediaElement/WebAudio
validé, sans créer un troisième moteur divergent.

## Impact / non-régression

Fichiers modifiés :

```text
ezscore/ui/__init__.py
```

Nouveaux fichiers :

```text
ezscore/ui/groups_home.py
i18n/groups.fr.json
i18n/groups.en.json
templates/views/groups-home.score
templates/views/group-card.score
templates/views/group-member.score
templates/views/group-playlist.score
templates/views/groups-empty.score
readme.md
```

Non modifiés :

```text
EZScore.py
ezscore/ui/app_shell.py
ezscore/catalog_social.py
ezscore/ui/editorial_timeline.py
ezscore/ui/lyrics_inline_editor.py
player R12c
templates/views/lyrics-editor.*
analyse STEM
timestamps techniques
```

## Installation

```powershell
cd H:\EZScore

Expand-Archive `
  -Path "$env:USERPROFILE\Downloads\EZScore_GROUPS_MENU_R1.zip" `
  -DestinationPath . `
  -Force

python -m py_compile `
  .\ezscore\ui\groups_home.py `
  .\ezscore\ui\__init__.py

git diff --check
git status --short
```

Aucun JavaScript n'est modifié dans ce lot : `node --check` n'est donc pas
applicable.

## Test ciblé

1. Ouvrir EZScore avec un utilisateur enregistré.
2. Vérifier `👥 Mes groupes` directement sous `👤 Mon profil`.
3. Ouvrir Mes groupes.
4. Créer `Blues Fiber`.
5. Ajouter 4 autres utilisateurs.
6. Vérifier 5 membres au total.
7. Passer un membre en Admin puis revenir en Membre.
8. Créer `Répétition prochain concert`.
9. Vérifier que la playlist apparaît dans le groupe.
10. Cliquer `Ouvrir dans Playlists`.
11. Vérifier que la playlist reste visible dans la surface Playlists.
12. Avec un autre membre du groupe, vérifier l'accès au groupe et à sa playlist.
13. Ouvrir Aline > Analyse > Paroles : accords présents.
14. Ouvrir Dance Me > Analyse > Paroles : R5.10 inchangé.
15. Vérifier player Analyse/STEM.
16. Vérifier Répertoire et Compte.
