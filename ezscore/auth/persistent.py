"""Persistent browser sessions for EZScore local authentication."""

from __future__ import annotations

import hashlib
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone

from ezscore.persistence import DB_PATH

SESSION_DAYS = 30


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def _hash_token(token: str) -> str:
    return hashlib.sha256(str(token).encode("utf-8")).hexdigest()


def ensure_persistent_session_schema() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS app_sessions (
                session_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token_hash TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL,
                revoked_at TEXT,
                FOREIGN KEY(user_id) REFERENCES app_users(user_id)
                    ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_app_sessions_user "
            "ON app_sessions(user_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_app_sessions_expires "
            "ON app_sessions(expires_at)"
        )
        conn.commit()


def create_persistent_session(user_id: int, *, days: int = SESSION_DAYS) -> str:
    ensure_persistent_session_schema()
    token = secrets.token_urlsafe(48)
    now = _now()
    expires = now + timedelta(days=max(1, int(days)))
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO app_sessions (
                user_id, token_hash, created_at, expires_at, last_seen_at, revoked_at
            ) VALUES (?, ?, ?, ?, ?, NULL)
            """,
            (
                int(user_id),
                _hash_token(token),
                _iso(now),
                _iso(expires),
                _iso(now),
            ),
        )
        conn.execute(
            """
            DELETE FROM app_sessions
            WHERE expires_at < ?
               OR (revoked_at IS NOT NULL AND revoked_at < ?)
            """,
            (
                _iso(now - timedelta(days=1)),
                _iso(now - timedelta(days=30)),
            ),
        )
        conn.commit()
    return token


def resolve_persistent_session(token: str) -> int | None:
    raw = str(token or "").strip()
    if not raw:
        return None
    ensure_persistent_session_schema()
    now = _now()

    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            """
            SELECT s.session_id, s.user_id, s.expires_at, s.revoked_at, u.active
            FROM app_sessions s
            JOIN app_users u ON u.user_id = s.user_id
            WHERE s.token_hash = ?
            LIMIT 1
            """,
            (_hash_token(raw),),
        ).fetchone()

        if not row:
            return None

        session_id, user_id, expires_at, revoked_at, active = row
        try:
            expires = datetime.fromisoformat(str(expires_at))
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
        except Exception:
            return None

        if revoked_at or not bool(active) or expires <= now:
            return None

        conn.execute(
            "UPDATE app_sessions SET last_seen_at = ? WHERE session_id = ?",
            (_iso(now), int(session_id)),
        )
        conn.commit()
        return int(user_id)


def revoke_persistent_session(token: str) -> None:
    raw = str(token or "").strip()
    if not raw:
        return
    ensure_persistent_session_schema()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            UPDATE app_sessions
            SET revoked_at = ?
            WHERE token_hash = ? AND revoked_at IS NULL
            """,
            (_iso(_now()), _hash_token(raw)),
        )
        conn.commit()
