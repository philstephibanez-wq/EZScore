# EZScore_v1 — R38.15a — Repair installer

R38.15 a bien ajouté les nouveaux fichiers et la migration a réussi, mais l'installeur s'est arrêté avant de modifier les fichiers existants car l'ancre `extractLyrics()` était trop stricte.

Deuxième défaut identifié : `LyricsHistoryController.php` n'était pas importé dans `config/routes.yaml`, ce qui explique l'absence totale de `lyrics_history` dans `debug:router`.

R38.15a corrige uniquement l'intégration :

- patch robuste de `SongLabController::extractLyrics()` ;
- sauvegarde du bloc complet avant extraction Whisper ;
- insertion de l'UI Historique dans LyricsLab ;
- chargement JS/CSS ;
- import explicite de `LyricsHistoryController.php` pour `/fr` et `/en` ;
- aucune nouvelle migration ;
- installeur idempotent.

## Commandes

```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R38_15A_REPAIR.zip" -C H:\EZScore_v1

python .\scripts\install_r38_15a_repair.py H:\EZScore_v1

php .\tests\r38_15a_repair_contract.php H:\EZScore_v1

php -l .\src\Controller\SongLabController.php
php -l .\src\Controller\LyricsHistoryController.php

php bin\console cache:clear

php bin\console debug:router | Select-String "lyrics_history"

git status --short
```

La migration `Version20260929090000` étant déjà exécutée avec succès, ne relance pas Doctrine pour ce hotfix.
