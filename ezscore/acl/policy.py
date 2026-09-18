from __future__ import annotations
from dataclasses import dataclass
from . import actions

@dataclass(frozen=True)
class ACLFacts:
    user_id: int | None = None
    active: bool = False
    global_role: str = "anonymous"
    group_id: int | None = None
    group_role: str = ""
    playlist_id: int | None = None
    playlist_owner_type: str = ""
    playlist_owner_id: int | None = None
    playlist_share_permission: str = ""
    event_creator_user_id: int | None = None

@dataclass(frozen=True)
class ACLDecision:
    allowed: bool
    action: str
    reason: str

def decide(action: str, f: ACLFacts) -> ACLDecision:
    action = str(action or "")
    if action == actions.CATALOG_READ:
        return ACLDecision(True, action, "catalog_public")
    if not f.active or f.user_id is None:
        return ACLDecision(False, action, "authentication_required")
    if f.global_role == "admin":
        return ACLDecision(True, action, "global_admin")
    if action in {actions.GROUP_LIST, actions.GROUP_CREATE, actions.PLAYLIST_LIST}:
        return ACLDecision(True, action, "authenticated")
    if action == actions.SONG_READ:
        ok = f.global_role in {"reader", "editor"}
        return ACLDecision(ok, action, "song_read" if ok else "song_read_denied")
    if action == actions.SONG_EDIT:
        ok = f.global_role == "editor"
        return ACLDecision(ok, action, "song_edit" if ok else "song_edit_denied")

    member = f.group_role in {"member", "admin"}
    admin = f.group_role == "admin"

    if action == actions.GROUP_READ:
        return ACLDecision(member, action, "group_member" if member else "group_membership_required")
    if action in {actions.GROUP_MANAGE_MEMBERS, actions.GROUP_MANAGE_ADMINS, actions.GROUP_DELETE}:
        return ACLDecision(admin, action, "group_admin" if admin else "group_admin_required")

    personal = f.playlist_owner_type == "user" and f.playlist_owner_id == f.user_id
    group_member = f.playlist_owner_type == "group" and member and f.playlist_owner_id == f.group_id
    group_admin = f.playlist_owner_type == "group" and admin and f.playlist_owner_id == f.group_id
    share_read = f.playlist_share_permission in {"read", "edit"}
    share_edit = f.playlist_share_permission == "edit"

    if action == actions.PLAYLIST_READ:
        ok = personal or group_member or share_read
        return ACLDecision(ok, action, "playlist_read" if ok else "playlist_read_denied")
    if action in {actions.PLAYLIST_EDIT, actions.PLAYLIST_REORDER}:
        ok = personal or group_member or share_edit
        return ACLDecision(ok, action, "playlist_edit" if ok else "playlist_edit_denied")
    if action in {actions.PLAYLIST_MANAGE, actions.PLAYLIST_DELETE}:
        ok = personal or group_admin
        return ACLDecision(ok, action, "playlist_manage" if ok else "playlist_manage_denied")
    if action == actions.PLAYLIST_CREATE:
        if f.group_id is None:
            return ACLDecision(True, action, "personal_playlist")
        return ACLDecision(member, action, "group_member" if member else "group_membership_required")
    if action == actions.EVENT_CREATE:
        return ACLDecision(member, action, "group_member" if member else "group_membership_required")
    if action in {actions.EVENT_EDIT, actions.EVENT_DELETE}:
        creator = f.event_creator_user_id == f.user_id and f.event_creator_user_id is not None
        ok = admin or creator
        return ACLDecision(ok, action, "event_manage" if ok else "event_manage_denied")
    if action == actions.KARAOKE_JOIN:
        return ACLDecision(member, action, "group_member" if member else "group_membership_required")
    if action in {actions.KARAOKE_HOST, actions.KARAOKE_TRANSPORT}:
        return ACLDecision(admin, action, "group_admin" if admin else "group_admin_required")
    return ACLDecision(False, action, "unknown_action")
