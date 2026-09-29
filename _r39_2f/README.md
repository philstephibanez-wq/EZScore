# EZScore_v1 — R39.2F Move visual settings in Lyrics

Périmètre strictement limité à `templates/song/lyricslab.html.twig`.

Le composant partagé `_live_visual_settings.html.twig` est déplacé :

- après le bloc d'édition des paroles ;
- immédiatement avant la timeline/prompteur Lyrics.

Aucun autre comportement n'est modifié.

## Installation

```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R39_2F_MOVE_VISUAL_SETTINGS_LYRICS.zip" -C H:\EZScore_v1

H:\EZScore\.venv-py313\Scripts\python.exe .\_r39_2f\scripts\apply_r39_2f.py H:\EZScore_v1

H:\EZScore\.venv-py313\Scripts\python.exe .\_r39_2f\tests\r39_2f_move_visual_settings_lyrics_contract.py H:\EZScore_v1

php bin\console cache:clear

git diff --check
git status --short
```

Attendu :

```text
R39_2F_MOVE_VISUAL_SETTINGS_LYRICS_INSTALL_OK
R39_2F_MOVE_VISUAL_SETTINGS_LYRICS_CONTRACT_OK
```
