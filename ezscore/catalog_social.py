from __future__ import annotations

"""Données sociales du Répertoire EZScore.

Responsabilités :
- notation collective d'une chanson ;
- playlists personnelles ;
- playlists de groupe ;
- partage direct d'une playlist avec un utilisateur ;
- droits lecture / édition sans dépendance Streamlit.

Ce module ne modifie jamais les données musicales ou éditoriales d'une chanson.
"""

from datetime import datetime, timezone
from pathlib import Path
import sqlite3
from typing import Any, Iterable


PLAYLIST_OWNER_USER = "user"
PLAYLIST_OWNER_GROUP = "group"
PLAYLIST_PERMISSION_READ = "read"
PLAYLIST_PERMISSION_EDIT = "edit"
GROUP_ROLE_ADMIN = "admin"
GROUP_ROLE_MEMBER = "member"


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


def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {
        str(row[1])
        for row in conn.execute(f'PRAGMA table_info("{table}")').fetchall()
    }


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    return conn.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table' AND name = ?
        """,
        (table,),
    ).fetchone() is not None


def _create_schema(conn: sqlite3.Connection) -> None:
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

        CREATE TABLE IF NOT EXISTS user_groups (
            group_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL COLLATE NOCASE,
            created_by_user_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS user_group_members (
            group_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL DEFAULT 'member'
                CHECK (role IN ('admin', 'member')),
            joined_at TEXT NOT NULL,
            PRIMARY KEY (group_id, user_id),
            FOREIGN KEY (group_id)
                REFERENCES user_groups(group_id)
                ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_user_group_members_user
            ON user_group_members(user_id, group_id);

        CREATE TABLE IF NOT EXISTS user_playlists (
            playlist_id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_type TEXT NOT NULL
                CHECK (owner_type IN ('user', 'group')),
            owner_id INTEGER NOT NULL,
            name TEXT NOT NULL COLLATE NOCASE,
            created_by_user_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE (owner_type, owner_id, name)
        );

        CREATE INDEX IF NOT EXISTS idx_user_playlists_owner
            ON user_playlists(owner_type, owner_id, name);

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

        CREATE TABLE IF NOT EXISTS playlist_shares (
            playlist_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            permission TEXT NOT NULL DEFAULT 'read'
                CHECK (permission IN ('read', 'edit')),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (playlist_id, user_id),
            FOREIGN KEY (playlist_id)
                REFERENCES user_playlists(playlist_id)
                ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_playlist_shares_user
            ON playlist_shares(user_id, playlist_id);

        CREATE TABLE IF NOT EXISTS group_events (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER NOT NULL,
            playlist_id INTEGER NOT NULL UNIQUE,
            event_type TEXT NOT NULL
                CHECK (event_type IN ('rehearsal', 'concert')),
            title TEXT NOT NULL,
            starts_at TEXT NOT NULL DEFAULT '',
            location TEXT NOT NULL DEFAULT '',
            notes TEXT NOT NULL DEFAULT '',
            created_by_user_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (group_id)
                REFERENCES user_groups(group_id)
                ON DELETE CASCADE,
            FOREIGN KEY (playlist_id)
                REFERENCES user_playlists(playlist_id)
                ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_group_events_group
            ON group_events(group_id, starts_at, event_id);
        """
    )


def _migrate_r1_playlists(conn: sqlite3.Connection) -> None:
    """Migre le schéma R1 user_id/name vers owner_type/owner_id.

    Le lot R1 a pu être appliqué avant R2. La migration conserve les ids et
    le contenu des playlists afin qu'aucun utilisateur ne perde sa liste.
    """
    if not _table_exists(conn, "user_playlists"):
        return

    columns = _table_columns(conn, "user_playlists")
    if "owner_type" in columns:
        return
    if "user_id" not in columns:
        return

    had_items = _table_exists(conn, "user_playlist_items")
    conn.execute("PRAGMA foreign_keys = OFF")
    try:
        if had_items:
            conn.execute(
                "ALTER TABLE user_playlist_items "
                "RENAME TO user_playlist_items_r1_legacy"
            )
        conn.execute(
            "ALTER TABLE user_playlists "
            "RENAME TO user_playlists_r1_legacy"
        )
        _create_schema(conn)

        conn.execute(
            """
            INSERT INTO user_playlists (
                playlist_id, owner_type, owner_id, name,
                created_by_user_id, created_at, updated_at
            )
            SELECT
                playlist_id, 'user', user_id, name,
                user_id, created_at, updated_at
            FROM user_playlists_r1_legacy
            """
        )

        if had_items:
            conn.execute(
                """
                INSERT INTO user_playlist_items (
                    playlist_id, audio_hash, position, created_at
                )
                SELECT playlist_id, audio_hash, position, created_at
                FROM user_playlist_items_r1_legacy
                """
            )
            conn.execute("DROP TABLE user_playlist_items_r1_legacy")

        conn.execute("DROP TABLE user_playlists_r1_legacy")
        conn.commit()
    finally:
        conn.execute("PRAGMA foreign_keys = ON")


def ensure_catalog_social_schema(
    db_path: str | Path | None = None,
) -> None:
    path = _resolve_db_path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.row_factory = sqlite3.Row
        _migrate_r1_playlists(conn)
        _create_schema(conn)
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


def _clean_name(name: Any, label: str) -> str:
    value = " ".join(str(name or "").strip().split())
    if not value:
        raise ValueError(f"{label} vide.")
    if len(value) > 120:
        raise ValueError(f"{label} trop long.")
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
    songs: list[str] = []
    seen: set[str] = set()
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

    result = {
        str(row["audio_hash"]): {
            "average": round(float(row["average_rating"]), 2),
            "count": int(row["rating_count"] or 0),
            "user_rating": own_by_song.get(str(row["audio_hash"])),
        }
        for row in rows
    }
    for song in songs:
        result.setdefault(
            song,
            {
                "average": None,
                "count": 0,
                "user_rating": own_by_song.get(song),
            },
        )
    return result


def create_user_group(
    user_id: Any,
    name: Any,
    *,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    ensure_catalog_social_schema(db_path)
    uid = _clean_user_id(user_id)
    group_name = _clean_name(name, "Nom du groupe")
    now = _now_iso()

    with _connect(db_path) as conn:
        existing = conn.execute(
            """
            SELECT g.group_id, g.name, g.created_at, g.updated_at
            FROM user_groups g
            JOIN user_group_members m
              ON m.group_id = g.group_id
            WHERE m.user_id = ?
              AND g.name = ? COLLATE NOCASE
            """,
            (uid, group_name),
        ).fetchone()
        if existing is not None:
            return {
                "group_id": int(existing["group_id"]),
                "name": str(existing["name"]),
                "created": False,
            }

        cur = conn.execute(
            """
            INSERT INTO user_groups (
                name, created_by_user_id, created_at, updated_at
            )
            VALUES (?, ?, ?, ?)
            """,
            (group_name, uid, now, now),
        )
        gid = int(cur.lastrowid)
        conn.execute(
            """
            INSERT INTO user_group_members (
                group_id, user_id, role, joined_at
            )
            VALUES (?, ?, 'admin', ?)
            """,
            (gid, uid, now),
        )
        conn.commit()

    return {"group_id": gid, "name": group_name, "created": True}


def _group_membership(
    conn: sqlite3.Connection,
    user_id: int,
    group_id: Any,
) -> sqlite3.Row:
    try:
        gid = int(group_id)
    except (TypeError, ValueError) as exc:
        raise ValueError("group_id invalide") from exc
    row = conn.execute(
        """
        SELECT g.group_id, g.name, m.role
        FROM user_groups g
        JOIN user_group_members m
          ON m.group_id = g.group_id
        WHERE g.group_id = ? AND m.user_id = ?
        """,
        (gid, user_id),
    ).fetchone()
    if row is None:
        raise PermissionError("Groupe introuvable ou non autorisé.")
    return row


def _group_admin(
    conn: sqlite3.Connection,
    user_id: int,
    group_id: Any,
) -> sqlite3.Row:
    row = _group_membership(conn, user_id, group_id)
    if str(row["role"]) != GROUP_ROLE_ADMIN:
        raise PermissionError("Administration du groupe requise.")
    return row


def list_user_groups(
    user_id: Any,
    *,
    db_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    ensure_catalog_social_schema(db_path)
    uid = _clean_user_id(user_id)

    with _connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT
                g.group_id,
                g.name,
                g.created_by_user_id,
                g.created_at,
                g.updated_at,
                me.role,
                (
                    SELECT COUNT(*)
                    FROM user_group_members gm
                    WHERE gm.group_id = g.group_id
                ) AS member_count,
                (
                    SELECT COUNT(*)
                    FROM user_playlists p
                    WHERE p.owner_type = 'group'
                      AND p.owner_id = g.group_id
                ) AS playlist_count
            FROM user_groups g
            JOIN user_group_members me
              ON me.group_id = g.group_id
            WHERE me.user_id = ?
            ORDER BY g.name COLLATE NOCASE, g.group_id
            """,
            (uid,),
        ).fetchall()
    return [dict(row) for row in rows]


def list_group_members(
    user_id: Any,
    group_id: Any,
    *,
    db_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    ensure_catalog_social_schema(db_path)
    uid = _clean_user_id(user_id)
    with _connect(db_path) as conn:
        _group_membership(conn, uid, group_id)
        rows = conn.execute(
            """
            SELECT user_id, role, joined_at
            FROM user_group_members
            WHERE group_id = ?
            ORDER BY CASE role WHEN 'admin' THEN 0 ELSE 1 END,
                     user_id
            """,
            (int(group_id),),
        ).fetchall()
    return [dict(row) for row in rows]


def add_group_member(
    actor_user_id: Any,
    group_id: Any,
    member_user_id: Any,
    role: str = GROUP_ROLE_MEMBER,
    *,
    db_path: str | Path | None = None,
) -> bool:
    ensure_catalog_social_schema(db_path)
    actor = _clean_user_id(actor_user_id)
    member = _clean_user_id(member_user_id)
    member_role = str(role or GROUP_ROLE_MEMBER).strip().lower()
    if member_role not in (GROUP_ROLE_ADMIN, GROUP_ROLE_MEMBER):
        raise ValueError("Rôle de groupe invalide.")

    now = _now_iso()
    with _connect(db_path) as conn:
        group = _group_admin(conn, actor, group_id)
        gid = int(group["group_id"])
        exists = conn.execute(
            """
            SELECT 1
            FROM user_group_members
            WHERE group_id = ? AND user_id = ?
            """,
            (gid, member),
        ).fetchone()
        if exists is not None:
            return False

        conn.execute(
            """
            INSERT INTO user_group_members (
                group_id, user_id, role, joined_at
            )
            VALUES (?, ?, ?, ?)
            """,
            (gid, member, member_role, now),
        )
        conn.execute(
            "UPDATE user_groups SET updated_at = ? WHERE group_id = ?",
            (now, gid),
        )
        conn.commit()
    return True


def update_group_member_role(
    actor_user_id: Any,
    group_id: Any,
    member_user_id: Any,
    role: str,
    *,
    db_path: str | Path | None = None,
) -> None:
    ensure_catalog_social_schema(db_path)
    actor = _clean_user_id(actor_user_id)
    member = _clean_user_id(member_user_id)
    new_role = str(role or "").strip().lower()
    if new_role not in (GROUP_ROLE_ADMIN, GROUP_ROLE_MEMBER):
        raise ValueError("Rôle de groupe invalide.")

    with _connect(db_path) as conn:
        group = _group_admin(conn, actor, group_id)
        gid = int(group["group_id"])
        current = conn.execute(
            """
            SELECT role
            FROM user_group_members
            WHERE group_id = ? AND user_id = ?
            """,
            (gid, member),
        ).fetchone()
        if current is None:
            raise ValueError("Membre introuvable.")

        if str(current["role"]) == GROUP_ROLE_ADMIN and new_role != GROUP_ROLE_ADMIN:
            admins = conn.execute(
                """
                SELECT COUNT(*)
                FROM user_group_members
                WHERE group_id = ? AND role = 'admin'
                """,
                (gid,),
            ).fetchone()[0]
            if int(admins or 0) <= 1:
                raise ValueError("Le groupe doit conserver au moins un administrateur.")

        conn.execute(
            """
            UPDATE user_group_members
            SET role = ?
            WHERE group_id = ? AND user_id = ?
            """,
            (new_role, gid, member),
        )
        conn.commit()


def remove_group_member(
    actor_user_id: Any,
    group_id: Any,
    member_user_id: Any,
    *,
    db_path: str | Path | None = None,
) -> bool:
    ensure_catalog_social_schema(db_path)
    actor = _clean_user_id(actor_user_id)
    member = _clean_user_id(member_user_id)

    with _connect(db_path) as conn:
        group = _group_admin(conn, actor, group_id)
        gid = int(group["group_id"])
        target = conn.execute(
            """
            SELECT role
            FROM user_group_members
            WHERE group_id = ? AND user_id = ?
            """,
            (gid, member),
        ).fetchone()
        if target is None:
            return False

        if str(target["role"]) == GROUP_ROLE_ADMIN:
            admins = conn.execute(
                """
                SELECT COUNT(*)
                FROM user_group_members
                WHERE group_id = ? AND role = 'admin'
                """,
                (gid,),
            ).fetchone()[0]
            if int(admins or 0) <= 1:
                raise ValueError("Le groupe doit conserver au moins un administrateur.")

        conn.execute(
            """
            DELETE FROM user_group_members
            WHERE group_id = ? AND user_id = ?
            """,
            (gid, member),
        )
        conn.commit()
    return True


def delete_user_group(
    user_id: Any,
    group_id: Any,
    *,
    db_path: str | Path | None = None,
) -> None:
    ensure_catalog_social_schema(db_path)
    uid = _clean_user_id(user_id)
    with _connect(db_path) as conn:
        group = _group_admin(conn, uid, group_id)
        gid = int(group["group_id"])
        conn.execute(
            """
            DELETE FROM user_playlists
            WHERE owner_type = 'group' AND owner_id = ?
            """,
            (gid,),
        )
        conn.execute("DELETE FROM user_groups WHERE group_id = ?", (gid,))
        conn.commit()


def create_playlist(
    user_id: Any,
    name: Any,
    *,
    owner_type: str = PLAYLIST_OWNER_USER,
    owner_id: Any | None = None,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    ensure_catalog_social_schema(db_path)
    uid = _clean_user_id(user_id)
    playlist_name = _clean_name(name, "Nom de la playlist")
    kind = str(owner_type or PLAYLIST_OWNER_USER).strip().lower()
    if kind not in (PLAYLIST_OWNER_USER, PLAYLIST_OWNER_GROUP):
        raise ValueError("Type de propriétaire invalide.")

    if kind == PLAYLIST_OWNER_USER:
        oid = uid
    else:
        oid = int(owner_id)
        with _connect(db_path) as conn:
            _group_membership(conn, uid, oid)

    now = _now_iso()
    with _connect(db_path) as conn:
        existing = conn.execute(
            """
            SELECT playlist_id, owner_type, owner_id, name,
                   created_by_user_id, created_at, updated_at
            FROM user_playlists
            WHERE owner_type = ? AND owner_id = ?
              AND name = ? COLLATE NOCASE
            """,
            (kind, oid, playlist_name),
        ).fetchone()
        if existing is not None:
            item = dict(existing)
            item["created"] = False
            return item

        cur = conn.execute(
            """
            INSERT INTO user_playlists (
                owner_type, owner_id, name,
                created_by_user_id, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (kind, oid, playlist_name, uid, now, now),
        )
        conn.commit()
        pid = int(cur.lastrowid)

    return {
        "playlist_id": pid,
        "owner_type": kind,
        "owner_id": oid,
        "name": playlist_name,
        "created_by_user_id": uid,
        "created_at": now,
        "updated_at": now,
        "created": True,
    }


def create_user_playlist(
    user_id: Any,
    name: Any,
    *,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    return create_playlist(
        user_id,
        name,
        owner_type=PLAYLIST_OWNER_USER,
        db_path=db_path,
    )


def _playlist_access(
    conn: sqlite3.Connection,
    user_id: int,
    playlist_id: Any,
) -> dict[str, Any]:
    try:
        pid = int(playlist_id)
    except (TypeError, ValueError) as exc:
        raise ValueError("playlist_id invalide") from exc

    playlist = conn.execute(
        """
        SELECT playlist_id, owner_type, owner_id, name,
               created_by_user_id, created_at, updated_at
        FROM user_playlists
        WHERE playlist_id = ?
        """,
        (pid,),
    ).fetchone()
    if playlist is None:
        raise PermissionError("Playlist introuvable ou non autorisée.")

    owner_type = str(playlist["owner_type"])
    owner_id = int(playlist["owner_id"])

    can_read = False
    can_edit = False
    can_manage = False
    source = ""

    if owner_type == PLAYLIST_OWNER_USER and owner_id == user_id:
        can_read = can_edit = can_manage = True
        source = "personal"

    elif owner_type == PLAYLIST_OWNER_GROUP:
        member = conn.execute(
            """
            SELECT role
            FROM user_group_members
            WHERE group_id = ? AND user_id = ?
            """,
            (owner_id, user_id),
        ).fetchone()
        if member is not None:
            can_read = can_edit = True
            can_manage = str(member["role"]) == GROUP_ROLE_ADMIN
            source = "group"

    if not can_read:
        share = conn.execute(
            """
            SELECT permission
            FROM playlist_shares
            WHERE playlist_id = ? AND user_id = ?
            """,
            (pid, user_id),
        ).fetchone()
        if share is not None:
            can_read = True
            can_edit = str(share["permission"]) == PLAYLIST_PERMISSION_EDIT
            source = "shared"

    if not can_read:
        raise PermissionError("Playlist introuvable ou non autorisée.")

    result = dict(playlist)
    result.update(
        {
            "can_read": can_read,
            "can_edit": can_edit,
            "can_manage": can_manage,
            "access_source": source,
        }
    )
    return result


def list_accessible_playlists(
    user_id: Any,
    *,
    audio_hash: Any | None = None,
    editable_only: bool = False,
    db_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    ensure_catalog_social_schema(db_path)
    uid = _clean_user_id(user_id)
    song = None if audio_hash in (None, "") else _clean_audio_hash(audio_hash)

    with _connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT DISTINCT
                p.playlist_id,
                p.owner_type,
                p.owner_id,
                p.name,
                p.created_by_user_id,
                p.created_at,
                p.updated_at
            FROM user_playlists p
            LEFT JOIN user_group_members gm
              ON p.owner_type = 'group'
             AND p.owner_id = gm.group_id
             AND gm.user_id = ?
            LEFT JOIN playlist_shares ps
              ON ps.playlist_id = p.playlist_id
             AND ps.user_id = ?
            WHERE
                (p.owner_type = 'user' AND p.owner_id = ?)
                OR gm.user_id IS NOT NULL
                OR ps.user_id IS NOT NULL
            ORDER BY p.name COLLATE NOCASE, p.playlist_id
            """,
            (uid, uid, uid),
        ).fetchall()

        result = []
        for row in rows:
            access = _playlist_access(conn, uid, int(row["playlist_id"]))
            if editable_only and not access["can_edit"]:
                continue

            count = conn.execute(
                """
                SELECT COUNT(*)
                FROM user_playlist_items
                WHERE playlist_id = ?
                """,
                (int(row["playlist_id"]),),
            ).fetchone()[0]
            access["song_count"] = int(count or 0)

            if song is not None:
                member = conn.execute(
                    """
                    SELECT 1
                    FROM user_playlist_items
                    WHERE playlist_id = ? AND audio_hash = ?
                    """,
                    (int(row["playlist_id"]), song),
                ).fetchone()
                access["contains_song"] = member is not None
            result.append(access)

    return result


def list_user_playlists(
    user_id: Any,
    *,
    audio_hash: Any | None = None,
    db_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    """Alias compatible R1 : retourne maintenant toutes les playlists accessibles."""
    return list_accessible_playlists(
        user_id,
        audio_hash=audio_hash,
        db_path=db_path,
    )


def share_playlist(
    actor_user_id: Any,
    playlist_id: Any,
    target_user_id: Any,
    permission: str = PLAYLIST_PERMISSION_READ,
    *,
    db_path: str | Path | None = None,
) -> None:
    ensure_catalog_social_schema(db_path)
    actor = _clean_user_id(actor_user_id)
    target = _clean_user_id(target_user_id)
    perm = str(permission or PLAYLIST_PERMISSION_READ).strip().lower()
    if perm not in (PLAYLIST_PERMISSION_READ, PLAYLIST_PERMISSION_EDIT):
        raise ValueError("Permission de partage invalide.")
    if actor == target:
        raise ValueError("Le propriétaire dispose déjà de la playlist.")

    now = _now_iso()
    with _connect(db_path) as conn:
        access = _playlist_access(conn, actor, playlist_id)
        if not access["can_manage"]:
            raise PermissionError("Gestion de la playlist requise.")

        conn.execute(
            """
            INSERT INTO playlist_shares (
                playlist_id, user_id, permission, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(playlist_id, user_id)
            DO UPDATE SET
                permission = excluded.permission,
                updated_at = excluded.updated_at
            """,
            (int(access["playlist_id"]), target, perm, now, now),
        )
        conn.commit()


def unshare_playlist(
    actor_user_id: Any,
    playlist_id: Any,
    target_user_id: Any,
    *,
    db_path: str | Path | None = None,
) -> bool:
    ensure_catalog_social_schema(db_path)
    actor = _clean_user_id(actor_user_id)
    target = _clean_user_id(target_user_id)
    with _connect(db_path) as conn:
        access = _playlist_access(conn, actor, playlist_id)
        if not access["can_manage"]:
            raise PermissionError("Gestion de la playlist requise.")
        cur = conn.execute(
            """
            DELETE FROM playlist_shares
            WHERE playlist_id = ? AND user_id = ?
            """,
            (int(access["playlist_id"]), target),
        )
        conn.commit()
        return cur.rowcount > 0


def list_playlist_shares(
    actor_user_id: Any,
    playlist_id: Any,
    *,
    db_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    ensure_catalog_social_schema(db_path)
    actor = _clean_user_id(actor_user_id)
    with _connect(db_path) as conn:
        access = _playlist_access(conn, actor, playlist_id)
        if not access["can_manage"]:
            raise PermissionError("Gestion de la playlist requise.")
        rows = conn.execute(
            """
            SELECT user_id, permission, created_at, updated_at
            FROM playlist_shares
            WHERE playlist_id = ?
            ORDER BY user_id
            """,
            (int(access["playlist_id"]),),
        ).fetchall()
    return [dict(row) for row in rows]


def delete_user_playlist(
    user_id: Any,
    playlist_id: Any,
    *,
    db_path: str | Path | None = None,
) -> bool:
    ensure_catalog_social_schema(db_path)
    uid = _clean_user_id(user_id)
    with _connect(db_path) as conn:
        access = _playlist_access(conn, uid, playlist_id)
        if not access["can_manage"]:
            raise PermissionError("Gestion de la playlist requise.")
        conn.execute(
            "DELETE FROM user_playlists WHERE playlist_id = ?",
            (int(access["playlist_id"]),),
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
        access = _playlist_access(conn, uid, playlist_id)
        if not access["can_edit"]:
            raise PermissionError("Droit d'édition de la playlist requis.")
        pid = int(access["playlist_id"])

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
            "UPDATE user_playlists SET updated_at = ? WHERE playlist_id = ?",
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
        access = _playlist_access(conn, uid, playlist_id)
        if not access["can_edit"]:
            raise PermissionError("Droit d'édition de la playlist requis.")
        pid = int(access["playlist_id"])

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
                "UPDATE user_playlists SET updated_at = ? WHERE playlist_id = ?",
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
        access = _playlist_access(conn, uid, playlist_id)
        pid = int(access["playlist_id"])

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


EVENT_TYPE_REHEARSAL = "rehearsal"
EVENT_TYPE_CONCERT = "concert"


def reorder_playlist_songs(
    user_id: Any,
    playlist_id: Any,
    ordered_audio_hashes: Iterable[Any],
    *,
    db_path: str | Path | None = None,
) -> list[str]:
    """Persist an exact playlist order.

    The submitted order must contain exactly the current songs, once each.
    This prevents a drag/drop UI from silently adding or dropping songs.
    """
    ensure_catalog_social_schema(db_path)
    uid = _clean_user_id(user_id)
    ordered = [_clean_audio_hash(value) for value in ordered_audio_hashes]

    if len(ordered) != len(set(ordered)):
        raise ValueError("Ordre de playlist invalide : chanson dupliquée.")

    now = _now_iso()
    with _connect(db_path) as conn:
        access = _playlist_access(conn, uid, playlist_id)
        if not access["can_edit"]:
            raise PermissionError("Droit d'édition de la playlist requis.")

        pid = int(access["playlist_id"])
        rows = conn.execute(
            """
            SELECT audio_hash
            FROM user_playlist_items
            WHERE playlist_id = ?
            ORDER BY position, created_at, audio_hash
            """,
            (pid,),
        ).fetchall()
        current = [str(row["audio_hash"]) for row in rows]

        if len(current) != len(ordered) or set(current) != set(ordered):
            raise ValueError(
                "Ordre de playlist invalide : la liste des chansons a changé."
            )

        for position, audio_hash in enumerate(ordered, start=1):
            conn.execute(
                """
                UPDATE user_playlist_items
                SET position = ?
                WHERE playlist_id = ? AND audio_hash = ?
                """,
                (position, pid, audio_hash),
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

    return ordered


def playlist_event(
    user_id: Any,
    playlist_id: Any,
    *,
    db_path: str | Path | None = None,
) -> dict[str, Any] | None:
    """Return the rehearsal/concert metadata attached to an accessible playlist."""
    ensure_catalog_social_schema(db_path)
    uid = _clean_user_id(user_id)

    with _connect(db_path) as conn:
        access = _playlist_access(conn, uid, playlist_id)
        row = conn.execute(
            """
            SELECT event_id, group_id, playlist_id, event_type, title,
                   starts_at, location, notes, created_by_user_id,
                   created_at, updated_at
            FROM group_events
            WHERE playlist_id = ?
            """,
            (int(access["playlist_id"]),),
        ).fetchone()

    return dict(row) if row is not None else None


def list_group_events(
    user_id: Any,
    group_id: Any,
    *,
    db_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    """List events visible to a group member, with their ordered playlist size."""
    ensure_catalog_social_schema(db_path)
    uid = _clean_user_id(user_id)

    with _connect(db_path) as conn:
        membership = _group_membership(conn, uid, group_id)
        gid = int(membership["group_id"])
        rows = conn.execute(
            """
            SELECT e.event_id,
                   e.group_id,
                   e.playlist_id,
                   e.event_type,
                   e.title,
                   e.starts_at,
                   e.location,
                   e.notes,
                   e.created_by_user_id,
                   e.created_at,
                   e.updated_at,
                   p.name AS playlist_name,
                   COUNT(i.audio_hash) AS song_count
            FROM group_events e
            JOIN user_playlists p
              ON p.playlist_id = e.playlist_id
            LEFT JOIN user_playlist_items i
              ON i.playlist_id = e.playlist_id
            WHERE e.group_id = ?
            GROUP BY
                e.event_id, e.group_id, e.playlist_id, e.event_type,
                e.title, e.starts_at, e.location, e.notes,
                e.created_by_user_id, e.created_at, e.updated_at,
                p.name
            ORDER BY
                CASE WHEN e.starts_at = '' THEN 1 ELSE 0 END,
                e.starts_at,
                e.event_id
            """,
            (gid,),
        ).fetchall()

    return [dict(row) for row in rows]


def prepare_group_event(
    user_id: Any,
    group_id: Any,
    event_type: str,
    title: Any,
    *,
    starts_at: Any = "",
    location: Any = "",
    notes: Any = "",
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    """Create a rehearsal/concert and its ordered group playlist atomically."""
    ensure_catalog_social_schema(db_path)
    uid = _clean_user_id(user_id)
    kind = str(event_type or "").strip().lower()
    if kind not in (EVENT_TYPE_REHEARSAL, EVENT_TYPE_CONCERT):
        raise ValueError("Type d'événement invalide.")

    event_title = _clean_name(title, "Titre de l'événement")
    when = str(starts_at or "").strip()
    place = str(location or "").strip()
    note = str(notes or "").strip()
    now = _now_iso()

    # Membership check before creating anything.
    with _connect(db_path) as conn:
        membership = _group_membership(conn, uid, group_id)
        gid = int(membership["group_id"])

    playlist = create_playlist(
        uid,
        event_title,
        owner_type=PLAYLIST_OWNER_GROUP,
        owner_id=gid,
        db_path=db_path,
    )
    if not bool(playlist.get("created")):
        raise ValueError(
            "Une playlist de ce nom existe déjà dans le groupe. "
            "Choisissez un autre titre pour la répétition ou le concert."
        )

    pid = int(playlist["playlist_id"])
    try:
        with _connect(db_path) as conn:
            cur = conn.execute(
                """
                INSERT INTO group_events (
                    group_id, playlist_id, event_type, title,
                    starts_at, location, notes,
                    created_by_user_id, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    gid, pid, kind, event_title,
                    when, place, note,
                    uid, now, now,
                ),
            )
            conn.commit()
            event_id = int(cur.lastrowid)
    except Exception:
        # Roll back the companion playlist if the event insert failed.
        with _connect(db_path) as conn:
            conn.execute(
                "DELETE FROM user_playlists WHERE playlist_id = ?",
                (pid,),
            )
            conn.commit()
        raise

    return {
        "event_id": event_id,
        "group_id": gid,
        "playlist_id": pid,
        "event_type": kind,
        "title": event_title,
        "starts_at": when,
        "location": place,
        "notes": note,
        "created_by_user_id": uid,
        "created_at": now,
        "updated_at": now,
    }
