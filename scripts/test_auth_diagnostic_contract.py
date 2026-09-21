from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIAG = ROOT / "ezscore" / "auth" / "diagnostics.py"
INIT = ROOT / "ezscore" / "auth" / "__init__.py"


def main() -> int:
    diag = DIAG.read_text(encoding="utf-8")
    init = INIT.read_text(encoding="utf-8")
    ast.parse(diag, filename=str(DIAG))
    ast.parse(init, filename=str(INIT))

    required_diag = [
        "_PERSIST_COMPONENT_KEY",
        "_PERSIST_TOKEN",
        "_PERSIST_STORE",
        "_PERSIST_CLEAR",
        "resolve_persistent_session",
        "app_sessions",
        "render_auth_diagnostics",
        "Actualiser le diagnostic",
    ]
    for token in required_diag:
        assert token in diag, token

    assert "render_account_page as _render_account_page" in init
    assert "render_auth_diagnostics()" in init
    assert "_render_account_page()" in init

    forbidden = [
        "create_persistent_session(",
        "revoke_persistent_session(",
        "st.login(",
        "st.logout(",
        "DELETE FROM",
        "UPDATE app_sessions",
        "INSERT INTO app_sessions",
    ]
    for token in forbidden:
        assert token not in diag, "Diagnostic must be read-only: " + token

    print("AUTH DIAGNOSTIC CONTRACT OK")
    print("mode: read-only")
    print("visible: Compte EZScore")
    print("raw secrets/tokens: not displayed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
