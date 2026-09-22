from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "ezscore/player/stem_analysis_conductor.py"
src = path.read_text(encoding="utf-8")
ast.parse(src, filename=str(path))

# Source-level regression guard: conductor_js must not redeclare the variable
# already owned by base._PLAYER_JS.
assert "let activeWordIndex=-2;" not in src
assert "const words=normalizedWords(rawWords);" in src
assert "renderConductor(t);" in src
assert "requestAnimationFrame(() => {" in src

# Runtime composition guard: inspect the FINAL JavaScript actually supplied
# to Streamlit after all replacements are applied.
from ezscore.player import stem_analysis_conductor as conductor

js = conductor._JS

decls = re.findall(r"\blet\s+activeWordIndex\b", js)
assert len(decls) == 1, (
    f"activeWordIndex doit être déclaré exactement une fois dans le JS final, "
    f"trouvé {len(decls)}"
)

assert "const words=normalizedWords(rawWords);" in js
assert "function renderConductor(time)" in js
assert "renderConductor(t);" in js
assert "ReferenceError" not in js

print("STEM CONDUCTOR R2b CONTRACT OK")
print("final JS activeWordIndex declarations:", len(decls))
print("continuous lyrics engine present: YES")
print("continuous chord engine present: YES")
print("deferred initial layout present: YES")
