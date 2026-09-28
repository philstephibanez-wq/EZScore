# EZScore_v1 R38.8

This hotfix deliberately does NOT depend on any pre-existing `interpolate_unmatched()` implementation.

It replaces only `align_provided_text()` structurally, adds its own `_r388_fill_unmatched()`, adds acoustic first-vocal-onset detection, passes `lead_vocals` only as onset evidence, keeps the original source MP3 as the analysis/playback clock, and mutualizes the ChordsLab/LyricsLab song card with Tempo.

Install:
```powershell
cd H:\EZScore_v1
tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R38_8_ROBUST_ACOUSTIC_ANCHOR.zip" -C H:\EZScore_v1
python .\scripts\install_r38_8.py H:\EZScore_v1
python -m py_compile .\analysis\lyrics_timeline_analysis.py
python -m py_compile .\worker_app\lyrics_worker_r37.py
php .\tests\r38_8_contract.php H:\EZScore_v1
python .\tests\test_r38_8_monotonic_contract.py H:\EZScore_v1
php bin\console cache:clear
```
