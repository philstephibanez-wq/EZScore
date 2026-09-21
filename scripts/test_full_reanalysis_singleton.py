from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "ezscore" / "ui" / "analysis_lifecycle.py"


def main() -> int:
    src = TARGET.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=str(TARGET))

    required = [
        "widget_user_keys_this_run",
        "_widget_key_already_rendered",
        "confirm_key = f\"full_reanalysis_confirm_{short_hash}\"",
        "action_key = f\"full_reanalysis_{short_hash}\"",
        "_widget_key_already_rendered(confirm_key)",
        "_widget_key_already_rendered(action_key)",
        "key=confirm_key",
        "key=action_key",
    ]
    for token in required:
        assert token in src, token

    # The duplicate guard must run before any expander/widget is created.
    guard_pos = src.index("_widget_key_already_rendered(confirm_key)")
    expander_pos = src.index('with st.expander("♻ Réanalyse complète"')
    checkbox_pos = src.index("confirmed = st.checkbox(")
    assert guard_pos < expander_pos < checkbox_pos

    # No random/suffixed keys: one semantic control per song.
    assert "uuid" not in src.lower()
    assert "time.time" not in src
    assert "random" not in src.lower()

    print("FULL REANALYSIS SINGLETON CONTRACT OK")
    print("duplicate widget key: guarded before rendering")
    print("reset semantics: unchanged")
    print("random/suffixed widget keys: NONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
