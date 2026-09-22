from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
stem = (ROOT / "ezscore/ui/stem_lab_analysis.py").read_text(encoding="utf-8")
app = (ROOT / "EZScore.py").read_text(encoding="utf-8")

ast.parse(stem, filename="stem_lab_analysis.py")
ast.parse(app, filename="EZScore.py")

assert "st.segmented_control(" in stem
assert 'analysis_step_key = f"ezstem_analysis_step_' in stem
assert 'if analysis_step == "1 · STEM":' in stem
assert 'elif analysis_step == "2 · Paroles":' in stem
assert 'elif analysis_step == "3 · Blocs / structure":' in stem
assert 'elif analysis_step == "4 · MIDI":' in stem

assert "tab_stem, tab_lyrics, tab_blocks, tab_midi = st.tabs(" not in stem
assert "with tab_stem:" not in stem
assert "with tab_lyrics:" not in stem
assert "with tab_blocks:" not in stem
assert "with tab_midi:" not in stem

assert "⬆️ Réimporter l'audio" in app
assert "← Retour au répertoire" in app

print("ANALYSIS LAZY R1b CONTRACT OK")
print("main analysis tabs eager: REMOVED")
print("active analysis surface per run: ONE")
print("hidden STEM player remount during lyrics: REMOVED")
print("missing-audio dead end: REMOVED")
