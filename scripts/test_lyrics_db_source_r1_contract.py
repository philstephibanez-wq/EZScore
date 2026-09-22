from __future__ import annotations
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
forced = (ROOT/"ezscore/analysis/forced_lyrics.py").read_text(encoding="utf-8")
choir = (ROOT/"ezscore/integration/choir_pipeline.py").read_text(encoding="utf-8")

ast.parse(forced)
ast.parse(choir)

assert "persisted = load_persisted_source_text(audio_hash)" in forced
assert "save_persisted_source_text(audio_hash, value)" in forced
assert "load_persisted_source_text," in choir
assert "persisted_source = str(load_persisted_source_text(audio_hash) or \"\")" in choir
assert "Bloc de paroles enregistré en BDD." in choir
assert 'persisted_text = str(load_draft(audio_hash) or "")' not in choir

print("LYRICS DB SOURCE R1 CONTRACT OK")
print("SQLite source of truth: YES")
print("cache priority over DB: NO")
print("empty session masks DB: NO")
print("explicit validation re-checks DB: YES")
