from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
player_path = ROOT / "ezscore/player/stem_analysis_conductor.py"
ui_path = ROOT / "ezscore/ui/stem_lab_analysis.py"
html_path = ROOT / "templates/views/lyrics-editor.html"
caption_path = ROOT / "ezscore/ui/chords_lyrics_editor.py"

player = player_path.read_text(encoding="utf-8")
ui = ui_path.read_text(encoding="utf-8")
html = html_path.read_text(encoding="utf-8")
caption = caption_path.read_text(encoding="utf-8")

ast.parse(player, filename=str(player_path))
ast.parse(ui, filename=str(ui_path))
ast.parse(caption, filename=str(caption_path))

assert '"lyrics-layout.js"' in player
assert '_JS = _LYRICS_LAYOUT_JS + "\\n\\n" + base._PLAYER_JS' in player
assert "ezLayoutLaneNodes({" in player
assert "ezVisualXForTime(" in player
assert "const conductorX=visualXForTime(t);" in player

assert "const words=normalizedWords(rawWords);" in player
assert "const lyricNodes=words.map(word => {" in player
assert "const chordItems=beats.map((beat,index) => {" in player

segment = player[
    player.index("const words=normalizedWords(rawWords);"):
    player.index("function findWordIndex(time)")
]
assert ".slice(" not in segment

assert '"▶ Ouvrir le lecteur STEM"' not in ui
assert '"✕ Fermer le lecteur STEM"' not in ui
assert "_render_stem_player(" in ui

assert 'class="ez-row ez-backing-row" style="display:none"' in html
assert '"Éditeur visuel R5.10 : Sections / Accords / Chant · "' in caption

from ezscore.player import stem_analysis_conductor as conductor
js = conductor._JS
layout = (ROOT / "templates/views/lyrics-layout.js").read_text(encoding="utf-8")

for fn in (
    "function ezNodeWidth(node)",
    "function ezLayoutLaneNodes({",
    "function ezVisualXForTime(",
):
    assert fn in layout
    assert fn in js

assert js.count("let activeWordIndex") == 1
assert "const lyricNodes=words.map(word => {" in js
assert "const chordItems=beats.map((beat,index) => {" in js
assert "const conductorX=visualXForTime(t);" in js

print("STEM CONDUCTOR SHARED R1 CONTRACT OK")
print("shared Paroles layout engine in final JS: YES")
print("all words mapped to lyric nodes: YES")
print("all beats mapped to chord items: YES")
print("same visual timeline for chords + lyrics: YES")
print("player auto-present in STEM: YES")
print("textual choir lane in Paroles: HIDDEN")
print("final JS activeWordIndex declarations: 1")
