# EZScore_v1 R38.10 — sequential t0→tn timeline

Agreed model:

- **beats/chords:** regular and strictly sequential on the beat grid, t0→tn;
- **lyrics:** strictly monotonic timestamps on the same absolute audio clock, with variable cadence;
- **first word:** immutable acoustic trigger from the existing onset detector;
- **remaining words:** monotonic global source↔Whisper alignment;
- **unrecognized words:** placed from actual Whisper acoustic word onsets, never a fixed 190 ms/word;
- **display:** chord lane uses the regular beat metric; lyric lane uses its independent variable metric so the current word passes under the current chord/beat;
- **sections:** never used to calculate time. Existing section chips remain display metadata and the current section is lit from the current absolute time.

No ChordsLab analysis worker is modified.

Install:

```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R38_10_SEQUENTIAL_TIMELINE.zip" -C H:\EZScore_v1

python .\scripts\install_r38_10.py H:\EZScore_v1

python -m py_compile .\analysis\lyrics_timeline_analysis.py

php .\tests\r38_10_contract.php H:\EZScore_v1
python .\tests\test_r38_10_sequential_timeline.py H:\EZScore_v1

node --check .\public\assets\js\lyricslab-r37.js

php bin\console cache:clear
```

Restart the desktop Worker and re-run LyricsLab analysis.

Expected log:

```text
[LYRICS] First vocal onset: ... ms (rms_sustained)
[LYRICS] Sequential timeline: trigger=... ms; source=...; recognized=...; lexical=...; acoustic_resample=...
```

Validate: first phrase, middle verse, late refrain, regular chord/beat motion, variable lyric motion, and current section highlight. Do not push until these checks pass.
