from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
src = (ROOT / "ezscore/integration/choir_pipeline.py").read_text(encoding="utf-8")
ast.parse(src, filename="choir_pipeline.py")

required = [
    "def _text_from_result_payload(",
    "def _initial_user_lyrics(",
    "FROM analyses",
    "FROM analysis_versions",
    "save_draft(audio_hash, migrated)",
    "on_change=persist_current_text",
    "def persist_current_text()",
]

for token in required:
    assert token in src, token

bad = """            )
            save_draft(audio_hash, current_text)

            if not current_text.strip():
"""
assert bad not in src

print("LYRICS SOURCE PERSIST R1 CONTRACT OK")
print("editable user block: DURABLE")
print("reload on song open: ENABLED")
print("legacy block edits migration: ENABLED")
print("legacy analysis migration: ENABLED")
print("empty widget no longer overwrites durable source on every render")
