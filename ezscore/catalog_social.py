from __future__ import annotations

"""Persistence sociale du répertoire EZScore.

Ce module reste volontairement indépendant de Streamlit :
- notation collective 1..5 par utilisateur et par chanson ;
- playlists privées par utilisateur ;
- ordre stable des chansons dans une playlist.

La base par défaut est celle d'EZScore, mais ``db_path`` peut être injecté
pour les tests.
"""

from datetime import datetime, timezone
from pathlib import Path
import sqlite3
from typing import Any, Iterable


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _resolve_db_path(db_path: str | Path | None = None) -> Path:
    if db_path is not None:
        return Path(db_path)
    from ezscore.persistence import DB_PATH
    return Path(DB_PATH)


def _connect(db_path: str | Path | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(_resolve_db_path(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def ensure_catalog_social_schema(db_path: str | Path | None = None) -> None:
    with _connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS song_ratings (
                user_id INTEGER NOT NULL,
                audio_hash TEXT NOT NULL,
                rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (user_id, audio_hash),
                FOREIGN KEY (audio_hash)
                    REFERENCES songs(audio_hash)
                    ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_song_ratings_audio_hash
                ON song_ratings(audio_hash);

            CREATE TABLE IF NOT EXISTS user_playlists (
                playlist_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL COLLATE NOCASE,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE (user_id, name)
            );

            CREATE INDEX IF NOT EXISTS idx_user_playlists_user
                ON user_playlists(user_id);

            CREATE TABLE IF NOT EXISTS user_playlist_items (
                playlist_id INTEGER NOT NULL,
                audio_hash TEXT NOT NULL,
                position INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                PRIMARY KEY (playlist_id, audio_hash),
                FOREIGN KEY (playlist_id)
                    REFERENCES user_playlists(playlist_id)
                    ON DELETE CASCADE,
                FOREIGN KEY (audio_hash)
                    REFERENCES songs(audio_hash)
                    ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_playlist_items_order
                ON user_playlist_items(playlist_id, position, audio_hash);
            """
        )
        conn.commit()


def _clean_user_id(user_id: Any) -> int:
    try:
        value = int(user_id)
    except (TypeError, ValueError) as exc:
        raise ValueError("user_id invalide") from exc
    if value <= 0:
        raise ValueError("user_id invalide")
    return value


def _clean_audio_hash(audio_hash: Any) -> str:
    value = str(audio_hash or "").strip()
    if not value:
        raise ValueError("audio_hash vide")
    return value


def _clean_playlist_name(name: Any) -> str:
    value = " ".join(str(name or "").strip().split())
    if not value:
        raise ValueError("Le nom de la playlist est vide.")
    if len(value) > 120:
        raise ValueError("Le nom de la playlist est trop long.")
    return value


def set_song_rating(
    user_id: Any,
    audio_hash: Any,
    rating: Any,
    *,
    db_path: str | Path | None = None,
) -> None:
    ensure_catalog_social_schema(db_path)
    uid = _clean_user_id(user_id)
    song = _clean_audio_hash(audio_hash)
    try:
        score = int(rating)
    except (TypeError, ValueError) as exc:
        raise ValueError("La note doit être comprise entre 1 et 5.") from exc
    if score < 1 or score > 5:
        raise ValueError("La note doit être comprise entre 1 et 5.")

    now = _now_iso()
    with _connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO song_ratings (
                user_id, audio_hash, rating, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id, audio_hash)
            DO UPDATE SET
                rating = excluded.rating,
                updated_at = excluded.updated_at
            """,
            (uid, song, score, now, now),
        )
        conn.commit()


def rating_summary(
    audio_hash: Any,
    user_id: Any | None = None,
    *,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    ensure_catalog_social_schema(db_path)
    song = _clean_audio_hash(audio_hash)
    uid = None if user_id in (None, "") else _clean_user_id(user_id)

    with _connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT AVG(rating) AS average_rating,
                   COUNT(*) AS rating_count
            FROM song_ratings
            WHERE audio_hash = ?
            """,
            (song,),
        ).fetchone()

        user_rating = None
        if uid is not None:
            own = conn.execute(
                """
                SELECT rating
                FROM song_ratings
                WHERE audio_hash = ? AND user_id = ?
                """,
                (song, uid),
            ).fetchone()
            if own is not None:
                user_rating = int(own["rating"])

    average = row["average_rating"] if row is not None else None
    count = int(row["rating_count"] or 0) if row is not None else 0
    return {
        "average": round(float(average), 2) if average is not None else None,
        "count": count,
        "user_rating": user_rating,
    }


def rating_summaries(
    audio_hashes: Iterable[Any],
    user_id: Any | None = None,
    *,
    db_path: str | Path | None = None,
) -> dict[str, dict[str, Any]]:
    ensure_catalog_social_schema(db_path)
    songs = []
    seen = set()
    for item in audio_hashes:
        song = _clean_audio_hash(item)
        if song not in seen:
            songs.append(song)
            seen.add(song)

    if not songs:
        return {}

    uid = None if user_id in (None, "") else _clean_user_id(user_id)
    placeholders = ",".join("?" for _ in songs)

    with _connect(db_path) as conn:
        rows = conn.execute(
            f"""
            SELECT audio_hash,
                   AVG(rating) AS average_rating,
                   COUNT(*) AS rating_count
            FROM song_ratings
            WHERE audio_hash IN ({placeholders})
            GROUP BY audio_hash
            """,
            songs,
        ).fetchall()

        own_by_song: dict[str, int] = {}
        if uid is not None:
            own_rows = conn.execute(
                f"""
                SELECT audio_hash, rating
                FROM song_ratings
                WHERE user_id = ?
                  AND audio_hash IN ({placeholders})
                """,
                [uid, *songs],
            ).fetchall()
            own_by_song = {
                str(row["audio_hash"]): int(row["rating"])
                for row in own_rows
            }

    aggregated = {
        str(row["audio_hash"]): {
            "average": round(float(row["average_rating"]), 2),
            "count": int(row["rating_count"] or 0),
            "user_rating": own_by_song.get(str(row["audio_hash"])),
        }
        for row in rows
    }

    for song in songs:
        aggregated.setdefault(
            song,
            {
                "average": None,
                "count": 0,
                "user_rating": own_by_song.get(song),
            },
        )
    return aggregated


def create_user_playlist(
    user_id: Any,
    name: Any,
    *,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    ensure_catalog_social_schema(db_path)
    uid = _clean_user_id(user_id)
    playlist_name = _clean_playlist_name(name)
    now = _now_iso()

    with _connect(db_path) as conn:
        existing = conn.execute(
            """
            SELECT playlist_id, name, created_at, updated_at
            FROM user_playlists
            WHERE user_id = ? AND name = ? COLLATE NOCASE
            """,
            (uid, playlist_name),
        ).fetchone()

        if existing is not None:
            return {
                "playlist_id": int(existing["playlist_id"]),
                "user_id": uid,
                "name": str(existing["name"]),
                "created_at": str(existing["created_at"]),
                "updated_at": str(existing["updated_at"]),
                "created": False,
            }

        cur = conn.execute(
            """
            INSERT INTO user_playlists (
                user_id, name, created_at, updated_at
            )
            VALUES (?, ?, ?, ?)
            """,
            (uid, playlist_name, now, now),
        )
        conn.commit()
        playlist_id = int(cur.lastrowid)

    return {
        "playlist_id": playlist_id,
        "user_id": uid,
        "name": playlist_name,
        "created_at": now,
        "updated_at": now,
        "created": True,
    }


def list_user_playlists(
    user_id: Any,
    *,
    audio_hash: Any | None = None,
    db_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    ensure_catalog_social_schema(db_path)
    uid = _clean_user_id(user_id)
    song = None if audio_hash in (None, "") else _clean_audio_hash(audio_hash)

    with _connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT p.playlist_id,
                   p.name,
                   p.created_at,
                   p.updated_at,
                   COUNT(i.audio_hash) AS song_count
            FROM user_playlists p
            LEFT JOIN user_playlist_items i
              ON i.playlist_id = p.playlist_id
            WHERE p.user_id = ?
            GROUP BY p.playlist_id, p.name, p.created_at, p.updated_at
            ORDER BY p.name COLLATE NOCASE, p.playlist_id
            """,
            (uid,),
        ).fetchall()

        membership: set[int] = set()
        if song is not None:
            member_rows = conn.execute(
                """
                SELECT i.playlist_id
                FROM user_playlist_items i
                JOIN user_playlists p
                  ON p.playlist_id = i.playlist_id
                WHERE p.user_id = ? AND i.audio_hash = ?
                """,
                (uid, song),
            ).fetchall()
            membership = {int(row["playlist_id"]) for row in member_rows}

    return [
        {
            "playlist_id": int(row["playlist_id"]),
            "user_id": uid,
            "name": str(row["name"]),
            "created_at": str(row["created_at"]),
            "updated_at": str(row["updated_at"]),
            "song_count": int(row["song_count"] or 0),
            "contains_song": int(row["playlist_id"]) in membership,
        }
        for row in rows
    ]


def _owned_playlist(
    conn: sqlite3.Connection,
    user_id: int,
    playlist_id: Any,
) -> sqlite3.Row:
    try:
        pid = int(playlist_id)
    except (TypeError, ValueError) as exc:
        raise ValueError("playlist_id invalide") from exc

    row = conn.execute(
        """
        SELECT playlist_id, user_id, name
        FROM user_playlists
        WHERE playlist_id = ? AND user_id = ?
        """,
        (pid, user_id),
    ).fetchone()
    if row is None:
        raise PermissionError("Playlist introuvable ou non autorisée.")
    return row


def delete_user_playlist(
    user_id: Any,
    playlist_id: Any,
    *,
    db_path: str | Path | None = None,
) -> bool:
    ensure_catalog_social_schema(db_path)
    uid = _clean_user_id(user_id)
    with _connect(db_path) as conn:
        row = _owned_playlist(conn, uid, playlist_id)
        conn.execute(
            "DELETE FROM user_playlists WHERE playlist_id = ?",
            (int(row["playlist_id"]),),
        )
        conn.commit()
    return True


def add_song_to_playlist(
    user_id: Any,
    playlist_id: Any,
    audio_hash: Any,
    *,
    db_path: str | Path | None = None,
) -> bool:
    ensure_catalog_social_schema(db_path)
    uid = _clean_user_id(user_id)
    song = _clean_audio_hash(audio_hash)
    now = _now_iso()

    with _connect(db_path) as conn:
        playlist = _owned_playlist(conn, uid, playlist_id)
        pid = int(playlist["playlist_id"])

        exists = conn.execute(
            """
            SELECT 1
            FROM user_playlist_items
            WHERE playlist_id = ? AND audio_hash = ?
            """,
            (pid, song),
        ).fetchone()
        if exists is not None:
            return False

        next_position = conn.execute(
            """
            SELECT COALESCE(MAX(position), 0) + 1
            FROM user_playlist_items
            WHERE playlist_id = ?
            """,
            (pid,),
        ).fetchone()[0]

        conn.execute(
            """
            INSERT INTO user_playlist_items (
                playlist_id, audio_hash, position, created_at
            )
            VALUES (?, ?, ?, ?)
            """,
            (pid, song, int(next_position), now),
        )
        conn.execute(
            """
            UPDATE user_playlists
            SET updated_at = ?
            WHERE playlist_id = ?
            """,
            (now, pid),
        )
        conn.commit()
    return True


def remove_song_from_playlist(
    user_id: Any,
    playlist_id: Any,
    audio_hash: Any,
    *,
    db_path: str | Path | None = None,
) -> bool:
    ensure_catalog_social_schema(db_path)
    uid = _clean_user_id(user_id)
    song = _clean_audio_hash(audio_hash)
    now = _now_iso()

    with _connect(db_path) as conn:
        playlist = _owned_playlist(conn, uid, playlist_id)
        pid = int(playlist["playlist_id"])
        cur = conn.execute(
            """
            DELETE FROM user_playlist_items
            WHERE playlist_id = ? AND audio_hash = ?
            """,
            (pid, song),
        )
        deleted = cur.rowcount > 0

        if deleted:
            rows = conn.execute(
                """
                SELECT audio_hash
                FROM user_playlist_items
                WHERE playlist_id = ?
                ORDER BY position, created_at, audio_hash
                """,
                (pid,),
            ).fetchall()
            for position, row in enumerate(rows, start=1):
                conn.execute(
                    """
                    UPDATE user_playlist_items
                    SET position = ?
                    WHERE playlist_id = ? AND audio_hash = ?
                    """,
                    (position, pid, str(row["audio_hash"])),
                )
            conn.execute(
                """
                UPDATE user_playlists
                SET updated_at = ?
                WHERE playlist_id = ?
                """,
                (now, pid),
            )
        conn.commit()
    return deleted


def list_playlist_songs(
    user_id: Any,
    playlist_id: Any,
    *,
    db_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    ensure_catalog_social_schema(db_path)
    uid = _clean_user_id(user_id)

    with _connect(db_path) as conn:
        playlist = _owned_playlist(conn, uid, playlist_id)
        pid = int(playlist["playlist_id"])

        rows = conn.execute(
            """
            SELECT i.audio_hash,
                   i.position,
                   i.created_at AS added_at,
                   s.original_filename,
                   s.title,
                   s.artist,
                   s.editor,
                   s.cover_path,
                   s.updated_at
            FROM user_playlist_items i
            JOIN songs s
              ON s.audio_hash = i.audio_hash
            WHERE i.playlist_id = ?
            ORDER BY i.position, i.created_at, i.audio_hash
            """,
            (pid,),
        ).fetchall()

    return [dict(row) for row in rows]
