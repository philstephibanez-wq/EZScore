from __future__ import annotations
import ast
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
path=ROOT/"ezscore/player/stem_analysis_conductor.py"
src=path.read_text(encoding="utf-8")
ast.parse(src,filename=str(path))

assert "const pixelsPerSecond=100;" in src
assert "function ezNodeWidth(node)" in src
assert "function ezIsContractionSuffix(text)" in src
assert "previousRight + 10" in src
assert "previousWidth) + 1" in src
assert "function scheduleParolesLayout()" in src
assert "document.fonts?.ready" in src
assert "new ResizeObserver" in src
assert "left:0;" in src
assert "left:50%;" not in src
assert "let pixelsPerSecond=96;" not in src
assert "computeGlobalScale" not in src

from ezscore.player import stem_analysis_conductor as conductor
js=conductor._JS

assert "const pixelsPerSecond=100;" in js
assert "function layoutWordsLikeParoles()" in js
assert "previousRight + 10" in js
assert "function scheduleParolesLayout()" in js
assert "timelineX=xForTime(t)" in js
assert js.count("let activeWordIndex") == 1

print("STEM USE PAROLES LAYOUT R1 CONTRACT OK")
print("Paroles scale 100 px/s: YES")
print("Paroles collision layout reused: YES")
print("track origin x=0: YES")
print("fonts/resize/hidden relayout: YES")
print("final JS activeWordIndex declarations: 1")
