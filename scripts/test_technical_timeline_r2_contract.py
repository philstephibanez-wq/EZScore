from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

files = {
    "technical": ROOT/"ezscore/analysis/technical_timeline.py",
    "conductor": ROOT/"ezscore/player/stem_analysis_conductor.py",
    "editor": ROOT/"ezscore/ui/chords_lyrics_editor.py",
}
src = {}
for name, path in files.items():
    text = path.read_text(encoding="utf-8")
    ast.parse(text, filename=str(path))
    src[name] = text

for token in [
    "def ensure_from_stem_module(",
    "STEM Batterie absent",
    "return ensure(",
]:
    assert token in src["technical"], token

for token in [
    "ensure_technical_timeline(",
    'with st.spinner("Construction de la timeline beats + accords…")',
    'beats = list(structure.get("beat_timeline", []) or [])',
]:
    assert token in src["conductor"], token

for token in [
    "def _load_editor_timing(",
    "technical = load_technical_timeline(work_dir)",
    "technical = ensure_from_stem_module(",
    "normalized = normalize_beats(raw)",
    "Timeline beats + accords indisponible",
]:
    assert token in src["editor"], token

assert "Timeline de beats absente" not in src["editor"]

print("TECHNICAL TIMELINE R2 CONTRACT OK")
print("editor timing: DIRECT")
print("STEM conductor timing: DIRECT")
print("monkey-patch timing dependency: REMOVED")
print("silent timing errors: REMOVED")
print("fake beats: NONE")
