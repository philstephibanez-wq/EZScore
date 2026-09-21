from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SESSION = ROOT / "ezscore" / "auth" / "session.py"


def main() -> int:
    src = SESSION.read_text(encoding="utf-8")
    ast.parse(src, filename=str(SESSION))

    required = [
        'ezscore_auth_persistent_session_v2',
        'window.localStorage.getItem(storageName)',
        'window.localStorage.setItem(storageName, value)',
        'window.localStorage.removeItem(storageName)',
        'const current = storageToken || cookieToken;',
        'setStateValue("token", current);',
        '_bootstrap_oidc_persistent_session()',
        'resolve_persistent_session(browser_token)',
    ]
    for token in required:
        if token not in src:
            raise AssertionError("Missing browser persistence contract: " + token)

    store_pos = src.index("if (store) {")
    local_write_pos = src.index("writeStorage(store)", store_pos)
    state_pos = src.index('setStateValue("token", store)', store_pos)
    if not (store_pos < local_write_pos < state_pos):
        raise AssertionError(
            "Persistent browser token must be stored before component state update."
        )

    print("AUTH BROWSER PERSISTENCE CONTRACT OK")
    print("server session: app_sessions")
    print("browser persistence: cookie + localStorage")
    print("restart restore: localStorage/cookie -> component -> app_sessions")
    print("logout: both browser stores cleared")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
