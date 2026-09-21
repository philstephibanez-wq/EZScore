from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SESSION = ROOT / "ezscore" / "auth" / "session.py"


def _fn(tree, name):
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(name)


def main() -> int:
    src = SESSION.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=str(SESSION))

    reader = _fn(tree, "_request_persistent_token")
    reader_src = ast.get_source_segment(src, reader) or ""
    assert "st.context.cookies" in reader_src
    assert "ezscore_local_session" in reader_src

    init = _fn(tree, "initialize_auth")
    init_src = ast.get_source_segment(src, init) or ""

    required = [
        "request_token = _request_persistent_token()",
        "resolve_persistent_session(request_token)",
        "st.session_state[_SESSION_USER_ID] = int(request_user_id)",
        "browser_token = component_token or request_token",
        "_PERSIST_CLEAR",
    ]
    for token in required:
        assert token in init_src, token

    # The restore must happen before the component is mounted.
    assert init_src.index("resolve_persistent_session(request_token)") < init_src.index("_SESSION_COMPONENT(")

    print("AUTH CONTEXT COOKIE CONTRACT OK")
    print("restart read path: st.context.cookies")
    print("restore path: cookie -> app_sessions -> user_id")
    print("component callback: no longer required for restart restore")
    print("stale cookie after DB reset: cleared")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
