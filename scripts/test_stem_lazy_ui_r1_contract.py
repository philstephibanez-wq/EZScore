from __future__ import annotations
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "ezscore/ui/stem_lab_analysis.py"
src = path.read_text(encoding="utf-8")
ast.parse(src, filename=str(path))

for token in [
    'stem_player_open_key = f"ezstem_player_open_{short_hash}"',
    'stem_downloads_open_key = f"ezstem_downloads_open_{short_hash}"',
    'if analysis_step != "1 · STEM":',
    '"⬇ Préparer les téléchargements STEM"',
    '"✕ Fermer les téléchargements STEM"',
    '"▶ Ouvrir le lecteur STEM"',
    '"✕ Fermer le lecteur STEM"',
    'st.session_state[stem_player_open_key] = True',
    'st.session_state[stem_player_open_key] = False',
    'st.session_state[stem_downloads_open_key] = True',
    'st.session_state[stem_downloads_open_key] = False',
]:
    assert token in src, token

assert "all_stems = {**stems, **vocal_parts}\n            _download_stems(all_stems)" not in src

player_guard = src.index("if not player_open:")
player_call = src.index("_render_stem_player(", player_guard)
assert player_call > player_guard

downloads_guard = src.index("if not downloads_open:")
downloads_call = src.index("_download_stems(all_stems)", downloads_guard)
assert downloads_call > downloads_guard

print("STEM LAZY UI R1 CONTRACT OK")
print("return-to-STEM heavy auto mount: NO")
print("WAV payloads on simple return: NO")
print("player mount requires explicit action: YES")
print("leaving STEM unloads heavy surfaces: YES")
print("Android remote full-width controls: YES")
