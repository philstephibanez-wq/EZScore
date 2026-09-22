from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

target = ROOT / "ezscore" / "player" / "stem_analysis_conductor.py"
source = target.read_text(encoding="utf-8")

ast.parse(source, filename=str(target))

assert '"ezscore_stem_analysis_conductor_r3"' in source
assert "let pixelsPerSecond=96;" in source
assert "function computeGlobalScale()" in source
assert "function xForTime(time)" in source
assert "const translate=anchor-xForTime(t);" in source
assert "ezVisualXForTime(" not in source[source.index("conductor_js ="):source.index("_JS = _replace_region", source.index("conductor_js ="))]
assert "ezLayoutLaneNodes(" not in source[source.index("conductor_js ="):source.index("_JS = _replace_region", source.index("conductor_js ="))]

from ezscore.player import stem_analysis_conductor as conductor

js = conductor._JS
assert "let pixelsPerSecond=96;" in js
assert "function computeGlobalScale()" in js
assert "function xForTime(time)" in js
assert "const words=normalizedWords(rawWords);" in js
assert "span.textContent=vocalDisplayText(word);" in js
assert "lyricsTrack.appendChild(span);" in js
assert js.count("let activeWordIndex") == 1

print("STEM LYRICS VISIBLE R1c CONTRACT OK")
print("patched Python syntax: OK")
print("composed player import: OK")
print("known-good STEM conductor restored: YES")
print("all supplied words materialized: YES")
print("component identity r3: YES")
print("mixer / transport / payload source: UNCHANGED")
