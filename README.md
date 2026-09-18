# EZScore — ACL + EFSM R1

Ce lot ajoute une couche ACL centralisée et corrige le bug majeur où un morceau
ouvert depuis **Répertoire général** pouvait être redirigé vers un ancien état
Groupe / Playlist.

Architecture :

```text
UI
↓
EFSM event
↓
ACL guard
↓
transition
↓
service / persistence
```

## Correction Répertoire

Deux chemins sont désormais explicites :

```text
open_song_from_repertoire(...)
open_song_from_playlist(...)
```

Depuis le Répertoire général, l'EFSM force d'abord :

```text
repertoire.list
```

et efface l'historique Groupe/Playlist avant d'ouvrir la chanson.

Depuis une playlist, le parent playlist est conservé pour permettre le retour.

Le radio **Répertoire général** force également `repertoire.list` depuis tout
état imbriqué, y compris `group.detail` et `playlist.detail`.

## ACL

Nouveaux modules :

```text
ezscore/acl/actions.py
ezscore/acl/policy.py
ezscore/acl/resolver.py
ezscore/acl/guards.py
```

Actions préparées :

```text
group.*
playlist.*
event.*
song.*
karaoke.join
karaoke.host
karaoke.transport
```

Les transitions EFSM sensibles `OPEN_GROUP`, `OPEN_PLAYLIST` et `OPEN_SONG`
passent désormais par l'ACL.

La persistence existante continue aussi de vérifier les droits au niveau métier.

## Non-régression Analyse + Paroles

Non modifiés / non livrés :

```text
EZScore.py
ezscore/ui/app_shell.py
ezscore/ui/stem_lab_analysis.py
ezscore/ui/editorial_timeline.py
ezscore/ui/lyrics_inline_editor.py
ezscore/player/karaoke_stem_webaudio*.py
templates/views/lyrics-editor.*
ezscore/catalog_social.py
```

Le hook R5.10 reste présent dans `ezscore/ui/__init__.py`.

## Installation

```powershell
cd H:\EZScore

Expand-Archive `
  -Path "$env:USERPROFILE\Downloads\EZScore_ACL_EFSM_R1.zip" `
  -DestinationPath . `
  -Force

python -m py_compile `
  .\ezscore\acl\actions.py `
  .\ezscore\acl\policy.py `
  .\ezscore\acl\resolver.py `
  .\ezscore\acl\guards.py `
  .\ezscore\navigation\session_adapter.py `
  .\ezscore\ui\catalog_home.py `
  .\ezscore\ui\__init__.py

git diff --check
git status --short
```

## Test prioritaire

1. Cliquer Répertoire.
2. Ouvrir Aline depuis Répertoire général.
3. Vérifier qu'elle s'ouvre et qu'aucun Groupe/Playlist ne reprend la main.
4. Revenir Répertoire.
5. Blues Fiber → Concert avril → Aline.
6. Vérifier ouverture directe Analyse.
7. Retour → Concert avril.
8. Vérifier ordre setlist.
9. Vérifier Aline et Dance Me dans Analyse > Paroles.
