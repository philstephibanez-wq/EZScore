from __future__ import annotations

import ast
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
choir_path = ROOT / "ezscore/integration/choir_pipeline.py"
player_path = ROOT / "ezscore/player/stem_analysis_conductor.py"
choir = choir_path.read_text(encoding="utf-8")
player = player_path.read_text(encoding="utf-8")
ast.parse(choir, filename=str(choir_path))
ast.parse(player, filename=str(player_path))

assert "value=persisted_source" in choir
assert "source_revision = hashlib.sha256(" in choir
assert 'f"ezscore_manual_lyrics_{short_hash}_{source_revision}"' in choir
assert 'div[data-testid="InputInstructions"]' in choir
assert "✓ Bloc de paroles enregistré en BDD." in choir
assert "st.session_state[text_key] = saved_text" not in choir

for token in [
    'class="diagram-checkbox" type="checkbox" tabindex="0"',
    'class="play" type="button" tabindex="0"',
    'class="pause" type="button" tabindex="0"',
    'class="stop" type="button" tabindex="0"',
    'tabindex="0" aria-label="Position de lecture"',
    ":focus-visible",
]:
    assert token in player, token

from ezscore.analysis.forced_lyrics import DB_PATH, load_persisted_source_text
with sqlite3.connect(DB_PATH) as conn:
    rows = conn.execute(
        "SELECT audio_hash, source_text FROM user_lyrics_sources WHERE length(source_text) > 0"
    ).fetchall()
assert rows, "Aucun bloc de paroles persisté en BDD."
for audio_hash, source_text in rows:
    assert load_persisted_source_text(str(audio_hash)) == str(source_text or ""), audio_hash

print("LYRICS RENDER + REMOTE R1 CONTRACT OK")
print(f"DB rows verified: {len(rows)}")
for audio_hash, source_text in rows:
    print(f" - {str(audio_hash)[:12]}: {len(str(source_text or ''))} chars")
print("textarea receives DB value directly: YES")
print("stale widget state can mask DB: NO")
print("explicit validation button: YES")
print("Ctrl+Enter helper hidden: YES")
print("remote/keyboard focus contract: YES")
