# EZScore_v1 — R38.16i2 — PHP escape repair

R38.16i1 introduced a literal PHP syntax error:

```php
catch (\\Throwable)
```

instead of:

```php
catch (\Throwable)
```

This hotfix repairs every double-escaped `Throwable` in `src/Service/LyricsOvhClient.php`.

No migration.

```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R38_16I2_THROWABLE_ESCAPE_REPAIR.zip" -C H:\EZScore_v1

python .\scripts\install_r38_16i2_throwable_escape_repair.py H:\EZScore_v1

php .\tests\r38_16i2_throwable_escape_repair_contract.php H:\EZScore_v1

php -l .\src\Service\LyricsOvhClient.php
php -l .\src\Controller\LyricsOvhController.php

php bin\console cache:clear
php bin\console cache:warmup

php bin\console debug:router | Select-String "lyrics_ovh_autocomplete"

git status --short
```
