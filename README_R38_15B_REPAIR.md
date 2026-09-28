# EZScore_v1 — R38.15b repair

R38.15a contenait encore deux défauts :

1. l'installeur sur-échappait le namespace PHP de `SongLyricsJobService`, donc il ne trouvait jamais la signature réelle de `extractLyrics()`;
2. le test PHP utilisait une chaîne interpolée et exécutait involontairement `$jobs`, `$song` et `$user`.

R38.15b corrige ces deux points et importe aussi explicitement `LyricsHistoryController.php` dans `config/routes.yaml`.

La migration `Version20260929090000` est déjà exécutée. Ne pas la relancer pour ce hotfix.

```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R38_15B_REPAIR.zip" -C H:\EZScore_v1

python .\scripts\install_r38_15b_repair.py H:\EZScore_v1

php .\tests\r38_15b_repair_contract.php H:\EZScore_v1

php -l .\src\Controller\SongLabController.php
php -l .\src\Controller\LyricsHistoryController.php

php bin\console cache:clear
php bin\console debug:router | Select-String "lyrics_history"

git status --short
```

Attendu :

```text
R38_15B_REPAIR_INSTALL_OK
R38_15B_REPAIR_CONTRACT_OK
```
