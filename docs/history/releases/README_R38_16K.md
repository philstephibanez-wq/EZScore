# EZScore_v1 — R38.16k — Une seule sauvegarde « Actuelle »

Cause confirmée dans le code poussé :
- `LyricsHistoryController` marquait `is_current` par égalité de texte ;
- `LyricsSourceHistoryService::delete()` bloquait la suppression par la même égalité de texte.

Conséquence : plusieurs sauvegardes identiques étaient toutes « Actuelle » et impossibles à supprimer.

Correction :
- une seule révision canonique : la sauvegarde la plus récente correspondant au texte persisté ;
- `is_current` compare l'ID de révision ;
- seule cette révision précise est protégée ;
- les anciennes sauvegardes identiques peuvent être supprimées ;
- aucune migration Doctrine ;
- aucun changement Lyrics.ovh / LyricsLab / timeline.

```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R38_16K_SINGLE_CURRENT_LYRICS_REVISION.zip" -C H:\EZScore_v1

python .\scripts\install_r38_16k_single_current_lyrics_revision.py H:\EZScore_v1

php .\tests\r38_16k_single_current_lyrics_revision_contract.php H:\EZScore_v1

php -l .\src\Domain\Song\LyricsSourceRevisionRepository.php
php -l .\src\Controller\LyricsHistoryController.php
php -l .\src\Service\LyricsSourceHistoryService.php

php bin\console cache:clear
php bin\console cache:warmup

git status --short
```
