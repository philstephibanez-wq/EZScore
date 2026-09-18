from __future__ import annotations

"""Dedicated EZScore user-groups surface.

This page owns group UX only:
- create a group;
- list groups the current user belongs to;
- manage members and roles;
- create and list group-owned playlists.

It intentionally does not own the general catalogue, song editing, analysis,
or the karaoke player.
"""

from pathlib import Path
from typing import Any

import streamlit as st

from EZScoreTemplate import ScoreTemplateRenderer
from ezscore.auth import current_user as auth_current_user
from ezscore.auth.storage import list_users as auth_list_users
from ezscore.catalog_social import (
    GROUP_ROLE_ADMIN,
    GROUP_ROLE_MEMBER,
    PLAYLIST_OWNER_GROUP,
    add_group_member,
    create_playlist,
    create_user_group,
    delete_user_group,
    ensure_catalog_social_schema,
    list_accessible_playlists,
    list_group_members,
    list_user_groups,
    remove_group_member,
    update_group_member_role,
)
from ezscore.i18n import t


APP_DIR = Path(__file__).resolve().parents[2]
SCORE = ScoreTemplateRenderer(APP_DIR)


def gt(key: str, **params: Any) -> str:
    return t(key, domain="groups", **params)


def _render_score(template: str, context: dict[str, Any]) -> str:
    return SCORE.render(f"templates/views/{template}", context)


def _current_user_id() -> int | None:
    user = auth_current_user() or {}
    try:
        value = int(user.get("user_id"))
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def _active_users() -> list[dict[str, Any]]:
    try:
        return [
            user
            for user in auth_list_users()
            if bool(user.get("active"))
            and user.get("user_id") is not None
        ]
    except Exception:
        return []


def _user_map() -> dict[int, dict[str, Any]]:
    return {
        int(user["user_id"]): user
        for user in _active_users()
    }


def _user_label(user: dict[str, Any] | None, user_id: int) -> str:
    payload = user or {}
    return str(
        payload.get("display_name")
        or payload.get("email")
        or f"#{user_id}"
    )


def _initial(value: str) -> str:
    text = str(value or "").strip()
    return text[:1].upper() if text else "?"


def _group_playlists(
    user_id: int,
    group_id: int,
) -> list[dict[str, Any]]:
    return [
        playlist
        for playlist in list_accessible_playlists(user_id)
        if str(playlist.get("owner_type", "")) == PLAYLIST_OWNER_GROUP
        and int(playlist.get("owner_id", -1)) == group_id
    ]


def _go_to_playlists() -> None:
    """Return to the repertoire shell and select its Playlists surface."""
    st.session_state["_ez_groups_open"] = False
    # catalog_home translates its two labels. Let it start from the Playlists
    # intent rather than coupling this module to a literal French label.
    st.session_state["_ez_catalog_open_playlists"] = True
    st.session_state["_pending_main_menu"] = "Répertoire"
    st.rerun()


def _render_member(
    *,
    actor_user_id: int,
    group_id: int,
    is_group_admin: bool,
    member: dict[str, Any],
    users: dict[int, dict[str, Any]],
) -> None:
    member_id = int(member["user_id"])
    member_role = str(member.get("role") or GROUP_ROLE_MEMBER)
    label = _user_label(users.get(member_id), member_id)
    own = member_id == actor_user_id

    role_label = (
        gt("role.admin")
        if member_role == GROUP_ROLE_ADMIN
        else gt("role.member")
    )

    with st.container(border=True):
        avatar_col, info_col, action_col = st.columns([0.45, 3.5, 1.25])

        with avatar_col:
            st.markdown(
                _render_score(
                    "group-member.score",
                    {
                        "initial": _initial(label),
                        "name": label,
                        "role": role_label,
                        "own": own,
                        "own_label": gt("member.you"),
                    },
                ),
                unsafe_allow_html=True,
            )

        with info_col:
            st.markdown(f"**{label}**")
            st.caption(
                role_label
                + (f" · {gt('member.you')}" if own else "")
            )

        with action_col:
            if not is_group_admin or own:
                return

            with st.popover("⋯"):
                new_role = st.selectbox(
                    gt("member.role"),
                    [GROUP_ROLE_MEMBER, GROUP_ROLE_ADMIN],
                    index=(
                        1
                        if member_role == GROUP_ROLE_ADMIN
                        else 0
                    ),
                    format_func=lambda value: (
                        gt("role.admin")
                        if value == GROUP_ROLE_ADMIN
                        else gt("role.member")
                    ),
                    key=f"group_role_{group_id}_{member_id}",
                )

                if st.button(
                    gt("member.save_role"),
                    key=f"group_role_save_{group_id}_{member_id}",
                    width="stretch",
                ):
                    update_group_member_role(
                        actor_user_id,
                        group_id,
                        member_id,
                        new_role,
                    )
                    st.rerun()

                if st.button(
                    gt("member.remove"),
                    key=f"group_member_remove_{group_id}_{member_id}",
                    width="stretch",
                ):
                    remove_group_member(
                        actor_user_id,
                        group_id,
                        member_id,
                    )
                    st.rerun()


def _render_add_member(
    *,
    actor_user_id: int,
    group_id: int,
    current_members: list[dict[str, Any]],
    users: dict[int, dict[str, Any]],
) -> None:
    existing = {int(member["user_id"]) for member in current_members}
    candidates = [
        user_id
        for user_id in users
        if user_id not in existing
    ]

    if not candidates:
        st.caption(gt("member.none_available"))
        return

    with st.form(f"group_add_member_{group_id}", clear_on_submit=True):
        target_user_id = st.selectbox(
            gt("member.user"),
            candidates,
            format_func=lambda user_id: _user_label(
                users.get(user_id),
                user_id,
            ),
        )
        role = st.selectbox(
            gt("member.role"),
            [GROUP_ROLE_MEMBER, GROUP_ROLE_ADMIN],
            format_func=lambda value: (
                gt("role.admin")
                if value == GROUP_ROLE_ADMIN
                else gt("role.member")
            ),
        )
        submitted = st.form_submit_button(
            gt("member.add"),
            type="primary",
            width="stretch",
        )

    if submitted:
        add_group_member(
            actor_user_id,
            group_id,
            int(target_user_id),
            role,
        )
        st.rerun()


def _render_playlist_list(
    *,
    user_id: int,
    group_id: int,
    group_name: str,
) -> None:
    playlists = _group_playlists(user_id, group_id)

    if not playlists:
        st.caption(gt("playlist.empty"))
    else:
        for playlist in playlists:
            st.markdown(
                _render_score(
                    "group-playlist.score",
                    {
                        "name": playlist["name"],
                        "count": int(
                            playlist.get("song_count", 0) or 0
                        ),
                        "song_label": (
                            gt("playlist.song")
                            if int(
                                playlist.get("song_count", 0) or 0
                            ) == 1
                            else gt("playlist.songs")
                        ),
                        "can_edit": bool(playlist.get("can_edit")),
                        "edit_label": gt("playlist.shared_edit"),
                    },
                ),
                unsafe_allow_html=True,
            )

    with st.form(
        f"group_playlist_create_{group_id}",
        clear_on_submit=True,
    ):
        playlist_name = st.text_input(
            gt("playlist.new"),
            placeholder=gt(
                "playlist.placeholder",
                group=group_name,
            ),
            label_visibility="collapsed",
        )
        submitted = st.form_submit_button(
            gt("playlist.create"),
            type="primary",
            width="stretch",
        )

    if submitted and str(playlist_name or "").strip():
        create_playlist(
            user_id,
            playlist_name,
            owner_type=PLAYLIST_OWNER_GROUP,
            owner_id=group_id,
        )
        st.rerun()

    if playlists:
        if st.button(
            gt("playlist.open_all"),
            key=f"group_open_playlists_{group_id}",
        ):
            _go_to_playlists()


def _render_group_card(
    *,
    user_id: int,
    group: dict[str, Any],
    users: dict[int, dict[str, Any]],
) -> None:
    group_id = int(group["group_id"])
    name = str(group.get("name") or gt("group.untitled"))
    role = str(group.get("role") or GROUP_ROLE_MEMBER)
    is_admin = role == GROUP_ROLE_ADMIN

    st.markdown(
        _render_score(
            "group-card.score",
            {
                "initial": _initial(name),
                "name": name,
                "role": (
                    gt("role.admin")
                    if is_admin
                    else gt("role.member")
                ),
                "member_count": int(
                    group.get("member_count", 0) or 0
                ),
                "member_label": gt("group.members"),
                "playlist_count": int(
                    group.get("playlist_count", 0) or 0
                ),
                "playlist_label": gt("group.playlists"),
            },
        ),
        unsafe_allow_html=True,
    )

    members = list_group_members(user_id, group_id)

    member_tab, playlist_tab = st.tabs(
        [
            f"👥 {gt('group.members')} ({len(members)})",
            f"🎶 {gt('group.playlists')} "
            f"({int(group.get('playlist_count', 0) or 0)})",
        ]
    )

    with member_tab:
        if is_admin:
            with st.expander(
                "＋ " + gt("member.add"),
                expanded=False,
            ):
                _render_add_member(
                    actor_user_id=user_id,
                    group_id=group_id,
                    current_members=members,
                    users=users,
                )

        for member in members:
            _render_member(
                actor_user_id=user_id,
                group_id=group_id,
                is_group_admin=is_admin,
                member=member,
                users=users,
            )

    with playlist_tab:
        _render_playlist_list(
            user_id=user_id,
            group_id=group_id,
            group_name=name,
        )

    if is_admin:
        with st.popover("⚙ " + gt("group.manage")):
            st.warning(gt("group.delete_warning"))
            if st.button(
                gt("group.delete"),
                key=f"group_delete_{group_id}",
                type="primary",
                width="stretch",
            ):
                delete_user_group(user_id, group_id)
                st.rerun()


def render_groups_home() -> None:
    """Render the dedicated 'Mes groupes' page."""
    ensure_catalog_social_schema()
    user_id = _current_user_id()

    if user_id is None:
        st.info(gt("login.required"))
        return

    users = _user_map()
    groups = list_user_groups(user_id)

    st.markdown(
        _render_score(
            "groups-home.score",
            {
                "title": gt("home.title"),
                "subtitle": gt("home.subtitle"),
                "group_count": len(groups),
                "group_label": (
                    gt("home.group")
                    if len(groups) == 1
                    else gt("home.groups")
                ),
            },
        ),
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        st.markdown(f"#### ＋ {gt('create.title')}")
        with st.form("groups_create_form", clear_on_submit=True):
            name = st.text_input(
                gt("create.name"),
                placeholder=gt("create.placeholder"),
                label_visibility="collapsed",
            )
            submitted = st.form_submit_button(
                gt("create.action"),
                type="primary",
                width="stretch",
            )

        if submitted and str(name or "").strip():
            create_user_group(user_id, name)
            st.rerun()

    if not groups:
        st.markdown(
            _render_score(
                "groups-empty.score",
                {
                    "title": gt("empty.title"),
                    "body": gt("empty.body"),
                },
            ),
            unsafe_allow_html=True,
        )
        return

    st.markdown(f"### {gt('home.my_groups')}")

    for group in groups:
        with st.container(border=True):
            _render_group_card(
                user_id=user_id,
                group=group,
                users=users,
            )
