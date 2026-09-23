from __future__ import annotations

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
base = (ROOT / "ezscore/player/stem_webaudio.py").read_text(encoding="utf-8")
player = (ROOT / "ezscore/player/step1_riffstation.py").read_text(encoding="utf-8")
data = (ROOT / "ezscore/analysis/riffstation_step1.py").read_text(encoding="utf-8")

# Active STEM-LAB Step 1 call is intercepted and routed to the autonomous player.
render = base.split("def render_player(", 1)[1]
assert 'if str(key).startswith("ezstem_player_"):' in render
assert "from ezscore.player.step1_riffstation import render_step1_riffstation" in render
assert "render_step1_riffstation(" in render

# Step 2 implementation remains in the legacy base and is not removed/re-written.
assert 'class="lyrics-wrap"' in base
assert 'const lyricNodes = words.map((word) => {' in base
assert 'ezscore_stem_analysis_player' in base

# Step 1 itself has no lyric lane/data contract.
assert 'riffstation_step1.json' in data
assert 'No lyric data is accepted here.' in player
assert 'lyrics-wrap' not in player
assert 'lyric-word' not in player
assert 'words=' not in player

# No invented metric fallback in Step 1 data.
assert 'Time signature détectée absente' in data
assert 'return "4/4"' not in data
assert 'or "4/4"' not in data

# Song cartouche owns the controls that were previously in the sidebar.
for token in (
    'class="song-card"',
    'class="song-title"',
    'class="song-meta"',
    'class="work-mode"',
    'class="signature-mode"',
    'class="capo-select"',
    'class="speed"',
    'class="diagram-checkbox"',
):
    assert token in player, token
assert 'section[data-testid="stSidebar"] { display:none !important; }' in player

# State changes are live and persisted through the existing EZScore preference contract.
assert 'on_work_mode_change=lambda: None' in player
assert 'on_signature_mode_change=lambda: None' in player
assert 'on_capo_change=lambda: None' in player
assert 'save_song_preferences(' in player
assert 'work_mode_key = f"ez_work_mode_' in player

# Riffstation audit / fixed-mire geometry.
assert 'preservesPitch=true' in player
assert 'const beatSpacing=' in player
assert 'function metricXAtTime(value)' in player
assert 'const x=xForBeatIndex(index);' in player
assert "const px=playheadX-metricXAtTime(time)" in player
assert 'left:var(--playhead-x)' in player
assert 'diagram-float' in player

# At t=0 future beats remain to the right. Before first beat no chord is current.
assert 'if (Number(t || 0) < Number(beats[0].start || 0)) return -1;' in player
assert 'const firstBeatX=' in player

# Step 1 auto-builds the musical timeline once stems exist.
assert 'Construction Riffstation Step 1…' in player

print('STEP1_RIFFSTATION_R3_CONTRACT_OK')
