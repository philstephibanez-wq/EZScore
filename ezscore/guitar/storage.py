"""Persistence for per-song guitar voicing/display choices."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from ezscore.persistence import DB_PATH


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_schema() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS song_guitar_preferences (
                audio_hash TEXT PRIMARY KEY,
                show_diagrams INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS song_chord_voicings (
                audio_hash TEXT NOT NULL,
                chord_symbol TEXT NOT NULL,
                voicing_name TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (audio_hash, chord_symbol)
            )
            """
        )
        conn.commit()


def load_show_diagrams(audio_hash: str) -> bool:
    ensure_schema()
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT show_diagrams FROM song_guitar_preferences WHERE audio_hash = ?",
            (str(audio_hash),),
        ).fetchone()
    return bool(row[0]) if row else False


def save_show_diagrams(audio_hash: str, enabled: bool) -> None:
    ensure_schema()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO song_guitar_preferences(audio_hash, show_diagrams, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(audio_hash) DO UPDATE SET
                show_diagrams = excluded.show_diagrams,
                updated_at = excluded.updated_at
            """,
            (str(audio_hash), 1 if enabled else 0, _now()),
        )
        conn.commit()


def load_voicings(audio_hash: str) -> dict[str, str]:
    ensure_schema()
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            """
            SELECT chord_symbol, voicing_name
            FROM song_chord_voicings
            WHERE audio_hash = ?
            """,
            (str(audio_hash),),
        ).fetchall()
    return {str(symbol): str(name) for symbol, name in rows}


def save_voicing(audio_hash: str, chord_symbol: str, voicing_name: str) -> None:
    ensure_schema()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO song_chord_voicings(
                audio_hash, chord_symbol, voicing_name, updated_at
            )
            VALUES (?, ?, ?, ?)
            ON CONFLICT(audio_hash, chord_symbol) DO UPDATE SET
                voicing_name = excluded.voicing_name,
                updated_at = excluded.updated_at
            """,
            (str(audio_hash), str(chord_symbol), str(voicing_name), _now()),
        )
        conn.commit()
