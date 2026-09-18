# EZScore — Playlists navigation + audio guard R1

## 1. Mes playlists dans le menu principal

Le menu utilisateur affiche désormais directement :

```text
🎵 Répertoire
👤 Profil
👥 Mes groupes
🎶 Mes playlists
```

`Mes playlists` ouvre l'état EFSM :

```text
playlists.list
```

La liste est celle de `list_accessible_playlists`, donc elle regroupe :

```text
- playlists personnelles ;
- playlists appartenant à un groupe dont je suis membre ;
- playlists partagées directement avec moi.
```

Le rattachement ou non à un groupe ne change donc pas leur accessibilité depuis
**Mes playlists**.

## 2. Dirty Old Town / Chargement audio bloqué

Symptôme observé :

```text
Chargement audio…
0:00 / 0:00
```

Le lecteur R12c lui-même n'est pas modifié.

Un garde très limité est installé autour de son appel. Avant le rendu, les
fichiers déjà présents dans :

```text
browser_preview/*.browser64.mp3
```

sont contrôlés avec `ffprobe`, quand `ffprobe` est disponible.

Si une pré-écoute existante est non décodable ou de durée nulle :

```text
- elle est supprimée ;
- le moteur existant la recrée normalement via FFmpeg ;
- un warning visible indique quel fichier a été réparé.
```

Aucun STEM, audio original, cache Whisper, accords, paroles ou timeline n'est
supprimé.

Si `ffprobe` n'est pas disponible, le contrôle est ignoré et le comportement
R12c reste strictement celui d'avant.

Le résultat des probes est mémorisé en RAM par `(path, size, mtime)` afin de ne
pas relancer `ffprobe` à chaque rerun.

## 3. Warnings LF / CRLF

Les messages Git :

```text
LF will be replaced by CRLF the next time Git touches it
```

sont des avertissements de normalisation de fins de ligne sous Windows. Ce ne
sont ni des erreurs Python, ni des erreurs Git, ni une corruption des fichiers.

Ce lot ne modifie ni `.gitignore` ni `.gitattributes` pour éviter une
normalisation massive et parasite du dépôt.

## Non-régression

Non modifiés / non livrés :

```text
EZScore.py
ezscore/ui/app_shell.py
ezscore/ui/stem_lab_analysis.py
ezscore/ui/editorial_timeline.py
ezscore/ui/lyrics_inline_editor.py
ezscore/player/karaoke_stem_webaudio.py
ezscore/player/karaoke_stem_webaudio_r12c.py
templates/views/lyrics-editor.*
ezscore/catalog_social.py
```

Le wrapper R12c reste le lecteur validé. La seule intervention audio est le
contrôle des MP3 de pré-écoute déjà générés avant de lui passer la main.

## Installation

```powershell
cd H:\EZScore

Expand-Archive `
  -Path "$env:USERPROFILE\Downloads\EZScore_PLAYLIST_NAV_AUDIO_GUARD_R1.zip" `
  -DestinationPath . `
  -Force

python -m py_compile .\ezscore\ui\__init__.py

git diff --check
git status --short
```

## Tests prioritaires

1. Vérifier `🎶 Mes playlists` dans le menu.
2. L'ouvrir depuis Répertoire.
3. Vérifier les playlists personnelles ET les playlists de groupe.
4. Ouvrir Dirty Old Town > Analyse > STEM.
5. Cliquer Lecture.
6. Si une preview était corrompue, vérifier le message de reconstruction.
7. Vérifier que la durée devient non nulle et que la lecture démarre.
8. Vérifier Aline > Analyse > Paroles.
9. Vérifier Dance Me > Analyse > Paroles.
10. Vérifier retour Groupe -> Playlist -> chanson -> Playlist.
