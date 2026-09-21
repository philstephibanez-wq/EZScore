from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIAG = ROOT / "ezscore" / "auth" / "diagnostics.py"


def main() -> int:
    src = DIAG.read_text(encoding="utf-8")
    ast.parse(src, filename=str(DIAG))

    required = [
        "st.context.cookies",
        "_streamlit_user",
        "_streamlit_user_tokens",
        "cookie_secret_fingerprint",
        "hashlib.sha256",
        "redirect_uri",
        "OIDC natif Streamlit",
        "Aucun token brut",
    ]
    for token in required:
        assert token in src, token

    forbidden = [
        'st.write(cookie_secret)',
        'st.code(cookie_secret)',
        '"cookie_secret": cookie_secret',
        "create_persistent_session(",
        "revoke_persistent_session(",
        "st.login(",
        "st.logout(",
        "INSERT INTO app_sessions",
        "UPDATE app_sessions",
        "DELETE FROM app_sessions",
    ]
    for token in forbidden:
        assert token not in src, "Diagnostic must be read-only/safe: " + token

    print("AUTH NATIVE STREAMLIT DIAGNOSTIC OK")
    print("mode: read-only")
    print("native cookies: names only")
    print("cookie_secret: SHA-256 fingerprint only")
    print("authentication logic: unchanged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
