from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

# Avoid importing heavy chord model dependencies: the helper only needs the
# symbol names to exist at module import time.
fake = types.ModuleType("ezscore.analysis.chords_quality")
fake.analyze_chords_absolute = lambda *args, **kwargs: {}
fake.chord_for_interval = lambda segments, start, end: ("N", "N", 0.0)
sys.modules["ezscore.analysis.chords_quality"] = fake

path = Path(__file__).resolve().parents[1] / "ezscore/analysis/music_timeline.py"
spec = importlib.util.spec_from_file_location("music_timeline_r2_under_test", path)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)

beats = [
    {"index": 0, "time": 10.21678, "chord": "C"},
    {"index": 1, "time": 10.681179, "chord": "C"},
    {"index": 2, "time": 11.168798, "chord": "G/3"},
    {"index": 3, "time": 11.656417, "chord": "G/3"},
    {"index": 4, "time": 12.167256, "chord": "D"},
]

merged, added, interval = module._prepend_phase_locked_beats(
    beats=beats,
    chord_segments=[{"dummy": True}],
    harmony_engine="test",
)

assert added > 0
assert merged[added]["time"] == 10.21678
assert merged[added + 1]["time"] == 10.681179
assert 0.0 < merged[0]["time"] < interval * 1.1
assert all(
    merged[i]["time"] < merged[i + 1]["time"]
    for i in range(len(merged) - 1)
)

print("MUSIC TIMELINE R2 FUNCTIONAL OK")
print("added=", added)
print("interval=", round(interval, 6))
print("first_timeline=", merged[0]["time"])
print("first_detected_preserved=", merged[added]["time"])
