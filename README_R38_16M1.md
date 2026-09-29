# EZScore_v1 — R38.16m1 — repair of R38.16m installer

R38.16m aborted before writing because its JavaScript anchor targeted an obsolete
polling shape (`completedReloaded`). The current `lyricslab-r37.js` uses the R38.2A
poller with `sessionStorage` key `ezscore.lyrics.job.reloaded.*`.

This repair:
- keeps the backend corrections from R38.16m;
- patches the actual R38.2A completed-job block;
- still performs all validation before writing any file;
- does not require a migration.

Commands:

```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R38_16M1_LYRICS_EXTRACT_PIPELINE_REPAIR.zip" -C H:\EZScore_v1

python .\scripts\install_r38_16m1_lyrics_extract_pipeline_repair.py H:\EZScore_v1

php .\tests\r38_16m1_lyrics_extract_pipeline_repair_contract.php H:\EZScore_v1

php -l .\src\Service\SongLyricsJobService.php
php -l .\src\Controller\SongLabController.php
php -l .\src\Controller\AnalysisDesktopController.php

php bin\console cache:clear
php bin\console cache:warmup

git status --short
```

Expected:
- `R38_16M1_LYRICS_EXTRACT_PIPELINE_REPAIR_INSTALL_OK`
- `R38_16M1_LYRICS_EXTRACT_PIPELINE_REPAIR_CONTRACT_OK`
