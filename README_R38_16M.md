# EZScore_v1 — R38.16m — Lyrics extract pipeline fix

Symptôme ciblé :
- `Extraire les paroles` est lancé ;
- le job apparaît dans le worker ;
- le job se termine ;
- le textarea reste vide.

Cause structurelle trouvée dans le code poussé :
`SongLyricsJobService::queue()` réutilisait **n'importe quel job lyrics actif**, sans vérifier son `mode`.
Un clic `extract` pouvait donc silencieusement récupérer un job `align` déjà actif.

Corrections :
- un job actif n'est réutilisé que si son mode est identique ;
- conflit `align`/`extract` explicite au lieu d'être silencieux ;
- suppression de la sauvegarde automatique avant Whisper (conforme à la règle : pas d'autosave) ;
- status Lyrics expose `mode`, `source_characters`, `result_characters`, `recognized_words` ;
- `complete(extract)` vérifie que le texte a réellement été persisté ;
- si R38.16L est installé, l'extraction met `lyrics_current_revision_id` à NULL : le texte extrait n'est PAS considéré comme une version sauvegardée ;
- l'UI ne prétend plus qu'une extraction vide est réussie.

Aucune migration.

```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R38_16M_LYRICS_EXTRACT_PIPELINE_FIX.zip" -C H:\EZScore_v1

python .\scripts\install_r38_16m_lyrics_extract_pipeline_fix.py H:\EZScore_v1

php .\tests\r38_16m_lyrics_extract_pipeline_fix_contract.php H:\EZScore_v1

php -l .\src\Service\SongLyricsJobService.php
php -l .\src\Controller\SongLabController.php
php -l .\src\Controller\AnalysisDesktopController.php

php bin\console cache:clear
php bin\console cache:warmup

git status --short
```

Test Happy Birthday :
1. aucune tâche Lyrics active ;
2. cliquer une seule fois `Extraire les paroles` ;
3. laisser le worker terminer ;
4. à `completed`, le bloc doit être rechargé avec le texte ;
5. si le backend n'a réellement rien persisté, l'UI affiche explicitement l'échec au lieu d'un faux succès.
