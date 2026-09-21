from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
src = (ROOT/"ezscore/analysis/rhythm_quality.py").read_text(encoding="utf-8")
ast.parse(src)

assert "from madmom_infer.features.beats import" not in src
assert "DBNBeatTrackingProcessor(" not in src
assert "RNNBeatProcessor(" not in src
assert 'mm.detect_beats(str(path))' in src
assert 'ENGINE = "madmom-infer-detect-beats"' in src
assert "madmom-infer==0.2.0" in src

print("MADMOM API CONTRACT OK")
print("internal processor import: REMOVED")
print("public detect_beats API: ENABLED")
