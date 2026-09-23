from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
base = (ROOT / "ezscore/player/stem_webaudio.py").read_text(encoding="utf-8")
player = (ROOT / "ezscore/player/step1_riffstation.py").read_text(encoding="utf-8")
data = (ROOT / "ezscore/analysis/riffstation_step1.py").read_text(encoding="utf-8")

# Step 2 is preserved: legacy shared assets remain in stem_webaudio.py.
assert 'class="lyrics-wrap"' in base
assert 'const lyricNodes = words.map((word) => {' in base
assert 'ezscore_stem_analysis_player' in base

# But the public Step 1 entry point delegates to the dedicated lyrics-free workflow.
render_tail = base.split('def render_player(', 1)[1]
assert 'from ezscore.player.step1_riffstation import render_step1_riffstation' in render_tail
assert 'render_step1_riffstation(' in render_tail
assert 'words=words' not in render_tail

# Step 1 has its own canonical musical cache and never accepts lyric data.
assert 'riffstation_step1.json' in data
assert 'No lyric data is accepted here.' in player
assert 'Aucune parole' in player
assert 'lyrics-wrap' not in player
assert 'lyric-word' not in player

# No invented time-signature fallback in the Step 1 data layer.
assert 'Time signature détectée absente' in data
assert 'return "4/4"' not in data
assert 'or "4/4"' not in data

# Step 1 owns its visible controls; they are not duplicate Streamlit widgets.
assert 'class="signature-mode"' in player
assert 'class="capo-select"' in player
assert 'class="speed"' in player
assert 'st.selectbox(' not in player
assert 'save_song_preferences(' in player
assert '"_pending_song_preferences"' in player

# Historical sidebar controls are hidden only while Step 1 is mounted.
assert 'section[data-testid="stSidebar"]' in player
assert 'aria-label="⏱ Time signature"' in player
assert 'aria-label="🎸 Capodastre"' in player

# Audible Riffstation audit requirements.
assert 'preservesPitch=true' in player
assert 'class="diagram-checkbox"' in player
assert 'class="playhead"' in player
assert 'chord_diagrams' in player

# Fixed-mire semantics: before first beat there is no current/past chord.
assert 'if (Number(t || 0) < Number(beats[0].start || 0)) return -1;' in player
assert 'const playheadX=windowNode.clientWidth*.34;' in player
assert "n.classList.toggle('past',i<index)" in player

# Step 1 workflow is automatic once stems exist.
assert 'Construction Riffstation Step 1…' in player
assert 'Analyser rythme + accords + time signature' not in player

print('STEP1_RIFFSTATION_R2_CONTRACT_OK')
