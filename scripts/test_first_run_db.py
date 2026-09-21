from __future__ import annotations

r"""First-run SQLite self-test for Windows.

The actual database test runs in a child Python process. This guarantees that
all SQLite handles opened inside EZScore modules are released when the child
exits, before the parent removes the temporary directory.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
REQUIRED = {
    "songs",
    "analyses",
    "analysis_versions",
    "app_state",
    "app_users",
    "app_identities",
    "app_sessions",
}


def _child(db_path: Path) -> int:
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))

    import sqlite3
    import ezscore.persistence as persistence
    import ezscore.auth.storage as storage
    import ezscore.auth.persistent as persistent

    root = db_path.parent

    persistence.DATA_DIR = root
    persistence.AUDIO_DIR = root / "audio"
    persistence.COVER_DIR = root / "covers"
    persistence.DB_PATH = db_path
    storage.DB_PATH = db_path
    persistent.DB_PATH = db_path

    persistence.init_persistence()
    storage.ensure_auth_schema()
    persistent.ensure_persistent_session_schema()

    conn = sqlite3.connect(db_path)
    try:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        users = int(
            conn.execute("SELECT COUNT(*) FROM app_users").fetchone()[0]
        )
    finally:
        conn.close()

    missing = sorted(REQUIRED - tables)
    if missing:
        print(json.dumps({
            "ok": False,
            "error": "missing tables",
            "missing": missing,
        }))
        return 2

    if users != 0:
        print(json.dumps({
            "ok": False,
            "error": "unexpected initial users",
            "users": users,
        }))
        return 3

    stale_cookie_ok = (
        persistent.resolve_persistent_session(
            "obsolete-browser-cookie"
        ) is None
    )
    if not stale_cookie_ok:
        print(json.dumps({
            "ok": False,
            "error": "obsolete cookie unexpectedly resolved",
        }))
        return 4

    print(json.dumps({
        "ok": True,
        "db": str(db_path),
        "tables": sorted(REQUIRED),
        "users": users,
        "stale_cookie_ok": True,
    }))
    return 0


def _parent() -> int:
    with tempfile.TemporaryDirectory(
        prefix="ezscore-first-run-"
    ) as tmp:
        db = Path(tmp) / "EZScore.sqlite3"

        command = [
            sys.executable,
            str(Path(__file__).resolve()),
            "--child",
            str(db),
        ]
        result = subprocess.run(
            command,
            cwd=str(REPO_ROOT),
            text=True,
            capture_output=True,
        )

        if result.returncode != 0:
            print("FIRST RUN FAILED")
            if result.stdout:
                print(result.stdout.rstrip())
            if result.stderr:
                print(result.stderr.rstrip(), file=sys.stderr)
            return int(result.returncode or 1)

        payload = json.loads(result.stdout.strip().splitlines()[-1])

        print("FIRST RUN OK")
        print("temporary DB:", payload["db"])
        print(
            "required tables:",
            ", ".join(payload["tables"]),
        )
        print("initial users:", payload["users"])
        print(
            "web gate target:",
            "Compte / Initialisation d'EZScore",
        )
        print(
            "obsolete persistent cookie:",
            "safely ignored",
        )
        print("temporary DB cleanup: OK")
        return 0


def main() -> int:
    if len(sys.argv) >= 3 and sys.argv[1] == "--child":
        return _child(Path(sys.argv[2]))
    return _parent()


if __name__ == "__main__":
    raise SystemExit(main())
