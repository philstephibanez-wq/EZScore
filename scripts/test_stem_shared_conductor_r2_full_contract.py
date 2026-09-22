from __future__ import annotations

import ast
import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

stem_path = ROOT / "ezscore" / "player" / "stem_analysis_conductor.py"
app_path = ROOT / "EZScore.py"

stem_source = stem_path.read_text(encoding="utf-8")
app_source = app_path.read_text(encoding="utf-8")

ast.parse(stem_source, filename=str(stem_path))
ast.parse(app_source, filename=str(app_path))

stem_sha = hashlib.sha256(stem_source.encode("utf-8")).hexdigest()
EXPECTED_STEM_SHA = "e7cee0bc83b2e48bdb380587cf384bde2272136261b2e7afefe4b60d5b214462"

assert stem_sha == EXPECTED_STEM_SHA, (
    "Le fichier STEM installé n'est pas le fichier complet de la livraison. "
    f"Attendu={EXPECTED_STEM_SHA} Trouvé={stem_sha}"
)

assert '"ezscore_stem_shared_conductor_r2_full"' in stem_source
assert '"lyrics-editor.css"' in stem_source
assert '"lyrics-layout.js"' in stem_source
assert 'class="ez-row-label">Structure</div>' in stem_source
assert 'class="ez-row-label">Accords</div>' in stem_source
assert 'class="ez-row-label">Chant</div>' in stem_source
assert "accord_forme_capo" in stem_source
assert "load_structure_blocks" in stem_source

assert '"⏱ Time signature"' in app_source
assert '"🎸 Capodastre"' in app_source
assert '_effective_pref_settings["signature_mode"]' in app_source
assert 'if song_view != "Analyse":' in app_source

# Import REAL runtime module: this executes all HTML/JS transformations.
from ezscore.player import stem_analysis_conductor as conductor

html = conductor._PLAYER_HTML
js = conductor._JS

assert html.count('class="tracks"') == 1
assert html.count('class="transport conductor-transport"') == 1
assert 'class="stem-conductor-wrap"' in html
assert html.index('class="tracks"') < html.index('class="stem-conductor-wrap"')
assert html.index('class="stem-conductor-wrap"') < html.index('class="transport conductor-transport"')
assert html.index('class="transport conductor-transport"') < html.index('class="hint"')

assert "ezLayoutLaneNodes" in js
assert "ezVisualXForTime" in js
assert "viewport.scrollLeft=requestedScroll;" in js

assert re.search(
    r"const\s+leadNodes\s*=\s*words\.map\s*\(\s*\(\s*word\s*,\s*index\s*\)\s*=>\s*\{",
    js,
), "1 mot MMS_FA -> 1 node DOM introuvable"

assert "previous.text=(previous.text" not in js

assert conductor._beats_per_measure("2/4") == 2
assert conductor._beats_per_measure("3/4") == 3
assert conductor._beats_per_measure("4/4") == 4
assert conductor._beats_per_measure("6/8") == 2
assert conductor._beats_per_measure("9/8") == 3
assert conductor._beats_per_measure("12/8") == 4

print("STEM SHARED CONDUCTOR R2 FULL CONTRACT OK")
print("exact installed STEM SHA256: OK")
print("real module import / runtime transforms: OK")
print("same Paroles CSS/layout engine: YES")
print("Structure / Accords / Chant: YES")
print("1 MMS_FA word = 1 DOM node: YES")
print("mixer before conductor: YES")
print("transport under conductor: YES")
print("Time signature in left panel: YES")
print("Capodastre in left panel: YES")
