# EZScore_v1 — R38.17B

R38.17A aborted during its own pre-write validation because the installer checked
for `_r3817_effective_t0`, while the injected function is correctly named
`_r3817a_effective_t0`.

Because validation happens before file writes, R38.17A did not modify EZScore.

R38.17B changes only this installer validation typo and keeps the same alignment patch.

## Installation

```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R38_17B_ACOUSTIC_SYLLABIC_ALIGNMENT_REPAIR.zip" -C H:\EZScore_v1

python .\scripts\install_r38_17b_acoustic_syllabic_alignment_repair.py H:\EZScore_v1

php .\tests\r38_17b_acoustic_syllabic_alignment_repair_contract.php H:\EZScore_v1

H:\EZScore_v1\.venv-py313\Scripts\python.exe -m py_compile .\analysis\lyrics_timeline_analysis.py
php -l .\src\Service\LyricsTimelineResultService.php

php bin\console cache:clear
php bin\console cache:warmup

git status --short
```

Expected:
- `R38_17B_ACOUSTIC_SYLLABIC_ALIGNMENT_REPAIR_INSTALL_OK`
- `R38_17B_ACOUSTIC_SYLLABIC_ALIGNMENT_REPAIR_CONTRACT_OK`
