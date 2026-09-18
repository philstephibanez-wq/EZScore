from __future__ import annotations
from pathlib import Path
import sqlite3
from typing import Any
from ezscore.persistence import DB_PATH
from .policy import ACLFacts, ACLDecision, decide

def _int(value):
    try:
        v = int(value)
    except (TypeError, ValueError):
        return None
    return v if v > 0 else None

def _table(conn, name):
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (name,),
    ).fetchone() is not None

def resolve_facts(user_id: Any, *, group_id=None, playlist_id=None, event_id=None, db_path=None) -> ACLFacts:
    uid, gid, pid, eid = _int(user_id), _int(group_id), _int(playlist_id), _int(event_id)
    path = Path(db_path) if db_path is not None else Path(DB_PATH)
    if not path.is_file():
        return ACLFacts(user_id=uid)
    with sqlite3.connect(path) as conn:
        conn.row_factory = sqlite3.Row
        active, global_role = False, "anonymous"
        if uid and _table(conn, "app_users"):
            row = conn.execute("SELECT role,active FROM app_users WHERE user_id=?", (uid,)).fetchone()
            if row:
                active, global_role = bool(row["active"]), str(row["role"] or "anonymous")

        group_role = ""
        owner_type, owner_id, share_perm, event_creator = "", None, "", None

        if eid and _table(conn, "group_events"):
            row = conn.execute(
                "SELECT group_id,playlist_id,created_by_user_id FROM group_events WHERE event_id=?",
                (eid,),
            ).fetchone()
            if row:
                gid = gid or _int(row["group_id"])
                pid = pid or _int(row["playlist_id"])
                event_creator = _int(row["created_by_user_id"])

        if pid and _table(conn, "user_playlists"):
            row = conn.execute(
                "SELECT owner_type,owner_id FROM user_playlists WHERE playlist_id=?",
                (pid,),
            ).fetchone()
            if row:
                owner_type = str(row["owner_type"] or "")
                owner_id = _int(row["owner_id"])
                if owner_type == "group":
                    gid = gid or owner_id
            if uid and _table(conn, "playlist_shares"):
                row = conn.execute(
                    "SELECT permission FROM playlist_shares WHERE playlist_id=? AND user_id=?",
                    (pid, uid),
                ).fetchone()
                if row:
                    share_perm = str(row["permission"] or "")

        if gid and uid and _table(conn, "user_group_members"):
            row = conn.execute(
                "SELECT role FROM user_group_members WHERE group_id=? AND user_id=?",
                (gid, uid),
            ).fetchone()
            if row:
                group_role = str(row["role"] or "")

    return ACLFacts(
        user_id=uid, active=active, global_role=global_role,
        group_id=gid, group_role=group_role,
        playlist_id=pid, playlist_owner_type=owner_type,
        playlist_owner_id=owner_id, playlist_share_permission=share_perm,
        event_creator_user_id=event_creator,
    )

def decision(user_id, action, **kwargs) -> ACLDecision:
    return decide(action, resolve_facts(user_id, **kwargs))

def allowed(user_id, action, **kwargs) -> bool:
    return bool(decision(user_id, action, **kwargs).allowed)
