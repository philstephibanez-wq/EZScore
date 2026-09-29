# EZScore_v1 — R38.16l1

Hotfix de l'installateur R38.16l.

Cause de l'échec :
Python `re.sub()` interprétait `\L` dans le texte PHP de remplacement (`\LogicException`) comme une séquence d'échappement de template regex.

R38.16l1 utilise désormais une fonction de remplacement littérale (`lambda`) et n'interprète plus les antislashs PHP.

Le comportement fonctionnel reste celui demandé :
- Restaurer = prendre exactement la sauvegarde cliquée ;
- aucune nouvelle révision `Restauration` ;
- aucune sauvegarde automatique avant restauration ;
- une seule révision exacte `Actuelle`.

La migration `Version20260929080000.php` a déjà été extraite avec R38.16l, donc ce hotfix ne la remplace pas.

```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R38_16L1_RESTORE_EXACT_REVISION_REPAIR.zip" -C H:\EZScore_v1

python .\scripts\install_r38_16l1_restore_exact_revision_repair.py H:\EZScore_v1

php .\tests\r38_16l1_restore_exact_revision_repair_contract.php H:\EZScore_v1

php -l .\src\Domain\Song\Song.php
php -l .\src\Service\LyricsSourceHistoryService.php
php -l .\src\Controller\LyricsHistoryController.php
php -l .\migrations\Version20260929080000.php

php bin\console doctrine:migrations:migrate --no-interaction

php bin\console cache:clear
php bin\console cache:warmup

git status --short
```
