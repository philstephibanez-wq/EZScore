# EZScore_v1 R38.13 — canonical ChordsLab grid + syllabic lyric timeline

Base: committed **R38.10** only. R38.11/R38.12 must not be present.

## Chord display
LyricsLab now uses the same canonical measure-slot projection policy as ChordsLab. The signature numerator is the number of visible slots per measure: 3/4=3, 4/4=4, 6/8=6. Missing slots are represented as `.`. Lyrics do not warp the chord lane.

## Syllabic lyric analysis
Words remain the editorial/display unit. Each timed word now carries nested syllables with `start_ms`, `nucleus_ms`, `end_ms`, confidence and alignment. A flattened `syllables` array is also emitted in the analyzer JSON.

Punctuation-only tokens are no longer timed events. In unmatched spans, interpolation is weighted by source syllables and sampled against local Whisper cadence rather than by word ordinal.

**Scope:** this is a first syllabic analyzer (French orthographic syllabification + Whisper acoustic cadence). `nucleus_ms` is currently the interval centre, not yet waveform-level vowel/phoneme detection. Whole words are still what LyricsLab renders/highlights.

## Install / validate
```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R38_13_CANONICAL_GRID_SYLLABIC_TIMELINE.zip" -C H:\EZScore_v1
python .\scripts\install_r38_13.py H:\EZScore_v1
php .	ests38_13_contract.php H:\EZScore_v1
python .	ests	est_r38_13_syllabic_timeline.py H:\EZScore_v1
node .	ests	est_r38_13_canonical_grid.js
node --check .\publicssets\js\lyricslab-r37.js
python -m py_compile .nalysis\lyrics_timeline_analysis.py
php bin\console cache:clear
php bin\console cache:warmup
```
Expected: `R38_13_INSTALL_OK`, `R38_13_CONTRACT_OK`, `R38_13_SYLLABIC_TIMELINE_OK`, `R38_13_CANONICAL_GRID_OK`.

Restart the permanent worker because Python analysis changed, then Ctrl+F5. Reanalyse **Aline first**, then **La Bohème**. Do not push until both are checked at beginning/middle/end.
