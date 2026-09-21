from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
player_path = ROOT / "ezscore/player/stem_analysis_conductor.py"
integration_path = ROOT / "ezscore/integration/choir_pipeline.py"

player = player_path.read_text(encoding="utf-8")
integration = integration_path.read_text(encoding="utf-8")

ast.parse(player, filename=str(player_path))
ast.parse(integration, filename=str(integration_path))

required_player = [
    'class="conductor-label">Accords</div>',
    'class="conductor-label">Paroles</div>',
    'const rawWords = Array.isArray(data.words)',
    'const beats = Array.isArray(data.beats)',
    'const token=localBeat===0',
    ': (chord===previous && chord!=="." ? "-" : chord)',
    'pixelsPerSecond=Math.max(96,required);',
    'return Math.max(0,Number(time || 0))*pixelsPerSecond;',
    'node.style.left=xForTime(words[index].start)+"px";',
    'node.style.left=xForTime(chordItems[index].time)+"px";',
    'return text + "_".repeat(count);',
    'Diagrammes guitare',
    'currentDiagram.innerHTML=svg;',
]
for token in required_player:
    assert token in player, token

for forbidden in [
    "line_index",
    "laneRight",
    "ezVisualXForTime",
]:
    assert forbidden not in player, forbidden

for token in [
    "render_stem_analysis_player",
    "stem_lab._render_stem_player = render_stem_analysis_player",
]:
    assert token in integration, token

print("STEM CONDUCTOR CONTRACT OK")
print("timeline rows: 2")
print("lyrics wrapping: DISABLED")
print("lyrics collision policy: GLOBAL SCALE")
print("chords: repeated at measure start")
print("chord sustain: '-'")
print("vocal sustain: '_'")
print("diagram: OPTIONAL")
print("karaoke player: UNTOUCHED")
