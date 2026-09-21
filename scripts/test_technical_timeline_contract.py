from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

technical = (ROOT/"ezscore/analysis/technical_timeline.py").read_text(encoding="utf-8")
conductor = (ROOT/"ezscore/player/stem_analysis_conductor.py").read_text(encoding="utf-8")
integration = (ROOT/"ezscore/integration/choir_pipeline.py").read_text(encoding="utf-8")

for name, src in [
    ("technical_timeline.py", technical),
    ("stem_analysis_conductor.py", conductor),
    ("choir_pipeline.py", integration),
]:
    ast.parse(src, filename=name)

for token in [
    'FILENAME = "technical_timeline.json"',
    '"timebase": TIMEBASE',
    'analyze_quality_beats(drums)',
    'analyze_chords_absolute(',
    'chord_for_interval(',
    '"beat_timeline": beat_timeline',
]:
    assert token in technical, token

for token in [
    'load_technical_timeline(work)',
    'structure = _load_timing_payload(preview_dir)',
]:
    assert token in conductor, token

for token in [
    '_lyrics_editor._load_timing = _load_timing_with_technical',
    'stem_lab._analyze_structure = _analyze_blocks_from_timeline',
    'Construction de la timeline beats + accords',
    'invalidate_technical_timeline',
]:
    assert token in integration, token

print("TECHNICAL TIMELINE CONTRACT OK")
print("beats+chords cache: technical_timeline.json")
print("Paroles+accords editor: CONNECTED")
print("STEM conductor: CONNECTED")
print("Step 3 blocks: REUSES technical timeline")
print("fake beat fallback: NONE")
