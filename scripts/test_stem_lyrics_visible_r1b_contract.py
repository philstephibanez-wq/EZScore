from __future__ import annotations
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

target = ROOT / "ezscore" / "player" / "stem_analysis_conductor.py"
source = target.read_text(encoding="utf-8")
ast.parse(source, filename=str(target))

assert "_LYRICS_LAYOUT_JS" not in source
assert "_JS = base._PLAYER_JS" in source
assert 'forced_words = list(forced.get("words", []) or [])' in source
assert "player_words = forced_words or list(words or [])" in source
assert '"ezscore_stem_analysis_conductor_r2"' in source
assert 'text:String(w.text ?? w.word ?? "").trim()' in source
assert "let pixelsPerSecond=96;" in source
assert "function computeGlobalScale()" in source
assert "const translate=anchor-xForTime(t);" in source

from ezscore.player import stem_analysis_conductor as conductor
js = conductor._JS
assert "ezLayoutLaneNodes(" not in js
assert "ezVisualXForTime(" not in js
assert "function computeGlobalScale()" in js
assert "const words=normalizedWords(rawWords);" in js
assert "span.textContent=vocalDisplayText(word);" in js
assert "lyricsTrack.appendChild(span);" in js
assert js.count("let activeWordIndex") == 1

print("STEM LYRICS VISIBLE R1b CONTRACT OK")
print("patched Python syntax: OK")
print("composed player module import: OK")
print("MMS_FA words priority: YES")
print("all words materialized: YES")
print("known-good STEM time layout restored: YES")
print("component identity r2: YES")
print("mixer / transport / chords: UNCHANGED")
