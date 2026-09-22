from __future__ import annotations
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
player_path = ROOT / "ezscore/player/stem_analysis_conductor.py"
ui_path = ROOT / "ezscore/ui/stem_lab_analysis.py"

player = player_path.read_text(encoding="utf-8")
ui = ui_path.read_text(encoding="utf-8")

ast.parse(player, filename=str(player_path))
ast.parse(ui, filename=str(ui_path))

assert "let activeWordIndex=-2;" in player
assert "requestAnimationFrame(() => {" in player
assert 'f"Payload : {len(beats)} beats · {len(player_words)} mots."' in player
assert '"✕ Fermer le lecteur STEM"' not in ui
assert '"▶ Ouvrir le lecteur STEM"' in ui
assert "activeWordIndex=wordIndex" in player
assert player.count("let activeWordIndex=") == 1

print("STEM CONDUCTOR R2 CONTRACT OK")
print("activeWordIndex declared: YES")
print("initial conductor layout deferred: YES")
print("payload counts visible: YES")
print("explicit close button removed: YES")
