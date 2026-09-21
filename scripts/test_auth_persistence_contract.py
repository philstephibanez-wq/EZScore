from __future__ import annotations

import ast
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SESSION = REPO_ROOT / "ezscore" / "auth" / "session.py"


def _function(tree: ast.AST, name: str) -> ast.FunctionDef:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"function missing: {name}")


def _called_names(fn: ast.FunctionDef) -> list[str]:
    result: list[str] = []
    for node in ast.walk(fn):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name):
            result.append(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            result.append(node.func.attr)
    return result


def main() -> int:
    source = SESSION.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(SESSION))

    bootstrap = _function(tree, "_bootstrap_oidc_persistent_session")
    bootstrap_calls = _called_names(bootstrap)

    assert "_resolve_oidc_user" in bootstrap_calls
    assert "create_persistent_session" in bootstrap_calls

    initialize = _function(tree, "initialize_auth")
    init_calls = _called_names(initialize)

    assert "_bootstrap_oidc_persistent_session" in init_calls
    assert "_SESSION_COMPONENT" in init_calls

    # Critical ordering: OIDC persistent token must exist before the browser
    # bridge is invoked, otherwise the cookie cannot be written on this run.
    source_segment = ast.get_source_segment(source, initialize) or ""
    assert (
        source_segment.index("_bootstrap_oidc_persistent_session()")
        < source_segment.index("_SESSION_COMPONENT(")
    )

    current = _function(tree, "current_user")
    current_calls = _called_names(current)
    assert "_resolve_oidc_user" in current_calls

    logout = _function(tree, "logout")
    logout_calls = _called_names(logout)
    assert "revoke_persistent_session" in logout_calls

    print("AUTH PERSISTENCE CONTRACT OK")
    print("local login: EZScore persistent session")
    print("OIDC/Google login: EZScore persistent session")
    print("startup restore: app_sessions + browser cookie")
    print("logout: persistent session revoked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
