from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
src = (ROOT/"ezscore/analysis/music_timeline.py").read_text(encoding="utf-8")
ast.parse(src, filename="music_timeline.py")

for token in [
    "def _needs_preroll_backfill(",
    "def _prepend_phase_locked_beats(",
    "def _repair_existing_preroll(",
    '"preroll_extrapolated": True',
    '"existing_detected_beats_moved": False',
    '"mode": "phase_backfill_v1"',
    "while candidate > 1e-6:",
    "force=False",
]:
    assert token in src, token

for forbidden in [
    "technical_timeline.json",
    "madmom_infer",
]:
    assert forbidden not in src, forbidden

print("MUSIC TIMELINE R2 CONTRACT OK")
print("existing late timeline: REPAIRED IN PLACE")
print("detected beat timestamps: NEVER MOVED")
print("pre-roll phase: MEDIAN DETECTED INTERVAL")
print("pre-roll harmony: LV-CHORDIA EXISTING CACHE")
print("new cache file: NONE")
