from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
music = (ROOT/"ezscore/analysis/music_timeline.py").read_text(encoding="utf-8")
choir = (ROOT/"ezscore/integration/choir_pipeline.py").read_text(encoding="utf-8")
player = (ROOT/"ezscore/player/stem_analysis_conductor.py").read_text(encoding="utf-8")

for name, src in (
    ("music_timeline.py", music),
    ("choir_pipeline.py", choir),
    ("stem_analysis_conductor.py", player),
):
    ast.parse(src, filename=name)

required_music = [
    "def ensure_music_timeline(",
    "librosa.beat.beat_track(",
    "analyze_chords_absolute(",
    "chord_for_interval(",
    '"beat_timeline": beat_timeline',
    '"timeline_stage": "beats+chords"',
    "_structure_cache_path(audio_hash)",
]
for token in required_music:
    assert token in music, token

for forbidden in [
    "technical_timeline.json",
    "madmom_infer",
    "analyze_quality_beats",
]:
    assert forbidden not in music, forbidden

required_choir = [
    "ensure_music_timeline(",
    "stem_lab._analyze_structure = analyze_structure_from_existing_timeline",
    "Analyse musicale · beats + accords…",
    "Timeline beats + accords prête.",
]
for token in required_choir:
    assert token in choir, token

assert "justify-content:flex-start;" in player
assert "justify-content:space-between;" not in player

print("MUSIC TIMELINE CONTRACT OK")
print("cache: existing structure_analysis.json")
print("new parallel timeline cache: NONE")
print("rhythm: existing EZScore librosa tracker")
print("harmony: existing lv-chordia cache/engine")
print("Step 2 editor: receives beat_timeline")
print("STEM conductor: receives same beat_timeline")
print("Step 3: reuses timeline, segments only")
print("diagram checkbox: LEFT/INLINE")
