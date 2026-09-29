# EZScore_v1 — R38.16i1 — Autocomplete route repair

Le template référence `app_song_lyrics_ovh_autocomplete`, mais Symfony ne connaît pas cette route.

Ce hotfix répare explicitement :

- `LyricsOvhClient::suggestFast()`
- `LyricsOvhController::autocomplete()`
- l'import de `LyricsOvhController.php` dans `config/routes.yaml` si nécessaire

Aucune migration.

```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R38_16I1_AUTOCOMPLETE_ROUTE_REPAIR.zip" -C H:\EZScore_v1

python .\scripts\install_r38_16i1_autocomplete_route_repair.py H:\EZScore_v1

php .\tests\r38_16i1_autocomplete_route_repair_contract.php H:\EZScore_v1

php -l .\src\Service\LyricsOvhClient.php
php -l .\src\Controller\LyricsOvhController.php

php bin\console cache:clear
php bin\console cache:warmup

php bin\console debug:router | Select-String "lyrics_ovh_autocomplete"

git status --short
```
