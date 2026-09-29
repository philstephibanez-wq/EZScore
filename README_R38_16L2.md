# EZScore_v1 — R38.16l2

R38.16l1 supposait à tort que la migration R38.16l avait déjà été copiée. Or le premier installateur avait échoué avant cette copie.

R38.16l2 est autonome :
- il contient la migration ;
- il la copie lui-même ;
- il ne demande pas qu'elle existe avant installation ;
- il applique la sémantique : **Restaurer = utiliser exactement la sauvegarde cliquée**, sans créer de doublon `Restauration`.

```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R38_16L2_RESTORE_EXACT_REVISION.zip" -C H:\EZScore_v1

python .\scripts\install_r38_16l2_restore_exact_revision.py H:\EZScore_v1

php .\tests\r38_16l2_restore_exact_revision_contract.php H:\EZScore_v1

php -l .\src\Domain\Song\Song.php
php -l .\src\Service\LyricsSourceHistoryService.php
php -l .\src\Controller\LyricsHistoryController.php
php -l .\migrations\Version20260929080000.php

php bin\console doctrine:migrations:migrate --no-interaction

php bin\console cache:clear
php bin\console cache:warmup

git status --short
```
