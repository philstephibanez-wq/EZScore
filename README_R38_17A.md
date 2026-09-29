# EZScore_v1 — R38.17A

Repair of the R38.17 delivery installer.

The previous R38.17 ZIP contained a malformed installer (`PY_PATCH=r`) and therefore
failed before `main()` and before any EZScore source file was modified.

R38.17A stores the Python override in a separate patch resource to eliminate nested
string-generation errors.

## Install

```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R38_17A_ACOUSTIC_SYLLABIC_ALIGNMENT_REPAIR.zip" -C H:\EZScore_v1

python .\scripts\install_r38_17a_acoustic_syllabic_alignment_repair.py H:\EZScore_v1

php .\tests\r38_17a_acoustic_syllabic_alignment_repair_contract.php H:\EZScore_v1

H:\EZScore_v1\.venv-py313\Scripts\python.exe -m py_compile .\analysis\lyrics_timeline_analysis.py
php -l .\src\Service\LyricsTimelineResultService.php

php bin\console cache:clear
php bin\console cache:warmup

git status --short
```

Expected:
- `R38_17A_ACOUSTIC_SYLLABIC_ALIGNMENT_REPAIR_INSTALL_OK`
- `R38_17A_ACOUSTIC_SYLLABIC_ALIGNMENT_REPAIR_CONTRACT_OK`
