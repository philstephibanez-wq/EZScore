# EZScore_v1 R38.7 — Acoustic first-vocal anchor + shared song card

## Scope

Priority fix only. No ChordsLab analysis algorithm is modified.

- Lyrics alignment: source MP3 remains the Whisper/timeline clock.
- First lyric anchor: detected acoustically from the time-aligned `lead_vocals` stem.
- No whole-song SequenceMatcher for the first anchor; repeated refrains cannot relocate the first source word to a later occurrence.
- If the vocal stem is unavailable, fallback is the first Whisper timed word (analysis does not fail solely because the first phrase is imperfectly recognized).
- ChordsLab and LyricsLab now use the same `_lab_song_card.html.twig`.
- Shared card displays `Titre | Interprète | Tonalité | Signature | Capo | Tempo`.
- Tempo is derived from the same canonical beat events used by ChordsLab.
- LyricsLab diagram preference uses a stable song-id key.

No new Python package is required. This deliberately avoids adding a network/runtime dependency such as `torch.hub`/Silero in this stabilization patch.

## Install (PowerShell)

```powershell
cd H:\EZScore_v1
tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R38_7_ACOUSTIC_ANCHOR_SHARED_CARD.zip" -C H:\EZScore_v1
python .\scripts\install_r38_7.py H:\EZScore_v1
python -m py_compile .\analysis\lyrics_timeline_analysis.py
python -m py_compile .\worker_app\lyrics_worker_r37.py
php .\tests\r38_7_contract.php H:\EZScore_v1
python .\tests\test_r38_7_monotonic_contract.py H:\EZScore_v1
php bin\console cache:clear
```

Then restart the desktop analysis worker and run **Analyser les paroles** once.
Expected worker log contains something like:

```text
Détection onset vocal: lead_vocals -> ...
[LYRICS] First vocal onset: NNNN ms (rms_sustained)
```

Do not push until the first word, tempo display, and diagram persistence are visually validated.
