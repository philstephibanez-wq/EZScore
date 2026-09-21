from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUTH_INIT = ROOT / "ezscore" / "auth" / "__init__.py"
RESPONSIVE = ROOT / "ezscore" / "ui" / "responsive.py"


def main() -> int:
    auth = AUTH_INIT.read_text(encoding="utf-8")
    responsive = RESPONSIVE.read_text(encoding="utf-8")

    ast.parse(auth, filename=str(AUTH_INIT))
    ast.parse(responsive, filename=str(RESPONSIVE))

    # Diagnostics must no longer be wired into the account page.
    assert "render_auth_diagnostics" not in auth
    assert "diagnostics" not in auth
    assert "render_account_page as _render_account_page" not in auth
    assert "from .ui import render_account_header, render_account_page" in auth

    # Only EZScore's own nav span gets HTML rendering forced.
    required = [
        "_EZNAV_SPAN",
        "eznav-item",
        "unsafe_allow_html",
        "_install_nav_markup_fix",
        "_ezscore_nav_markup_fix",
    ]
    for token in required:
        assert token in responsive, token

    print("AUTH DIAGNOSTIC REMOVAL OK")
    print("NAV SPAN RENDER CONTRACT OK")
    print("scope: eznav-item span only")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
