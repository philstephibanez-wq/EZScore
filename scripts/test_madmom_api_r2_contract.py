from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
src = (ROOT/"ezscore/analysis/rhythm_quality.py").read_text(encoding="utf-8")
ast.parse(src)

assert "detect_beats" not in src
assert "madmom_infer.features.beats" not in src
assert "from madmom_infer.features.downbeats import" in src
assert "RNNDownBeatProcessor" in src
assert "DBNDownBeatTrackingProcessor" in src
assert 'decoded[:, 0]' in src
assert 'ENGINE = "madmom-infer-rnn-downbeat-dbn"' in src

print("MADMOM API R2 CONTRACT OK")
print("detect_beats dependency: REMOVED")
print("features.beats dependency: REMOVED")
print("0.2.0 downbeats pipeline: ENABLED")
