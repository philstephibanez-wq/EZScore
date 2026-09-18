from __future__ import annotations

"""Accueil Répertoire / Playlists EZScore.

UI :
- deux entrées principales : Répertoire général / Playlists ;
- templates SCORE pour la présentation ;
- i18n dès cette surface (détection navigateur + override FR/EN) ;
- aucune modification du player ou de la timeline Analyse > Paroles.
"""

from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st

from EZScoreTemplate import ScoreTemplateRenderer
from ezscore.auth import allowed as auth_allowed
from ezscore.auth import current_user as auth_current_user
from ezscore.auth import require as auth_require
from ezscore.auth.storage import list_users as auth_list_users
from ezscore.catalog_social import (
    GROUP_ROLE_ADMIN,
    GROUP_ROLE_MEMBER,
    PLAYLIST_OWNER_GROUP,
    PLAYLIST_OWNER_USER,
    PLAYLIST_PERMISSION_EDIT,
    PLAYLIST_PERMISSION_READ,
    add_group_member,
    add_song_to_playlist,
    create_playlist,
    create_user_group,
    create_user_playlist,
    delete_user_group,
    delete_user_playlist,
    ensure_catalog_social_schema,
    list_accessible_playlists,
    list_group_members,
    list_playlist_shares,
    list_playlist_songs,
    list_user_groups,
    rating_summaries,
    remove_group_member,
    remove_song_from_playlist,
    set_song_rating,
    share_playlist,
    unshare_playlist,
)
from ezscore.i18n import current_language, set_language, t
from ezscore.persistence import (
    catalog_display_name,
    catalog_letter_for_song,
    catalog_primary_text,
    catalog_secondary_text,
    filter_catalog,
    get_app_state,
    get_song_editorial_version,
    get_song_workflow,
    latest_song_editorial_version,
    list_analysis_versions,
    list_song_catalog,
    list_song_editorial_versions,
    prepare_analysis_version_for_open,
    prepare_song_preferences_for_open,
    render_delete_song_controls,
    resume_song_modifications,
    set_app_state,
    song_cover_path,
)


APP_DIR = Path(__file__).resolve().parents[2]
SCORE = ScoreTemplateRenderer(APP_DIR)


def _render_score(template: str, context: dict[str, Any]) -> str:
    return SCORE.render(f"templates/views/{template}", context)


def _user_id(user: dict[str, Any] | None) -> int | None:
    if not user:
        return None
    try:
        value = int(user.get("user_id"))
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def _active_users() -> list[dict[str, Any]]:
    try:
        return [
            u for u in auth_list_users()
            if bool(u.get("active"))
        ]
    except Exception:
        return []


def _user_label(user: dict[str, Any]) -> str:
    return str(
        user.get("display_name")
        or user.get("email")
        or f"#{user.get('user_id')}"
    )


def _user_map() -> dict[int, dict[str, Any]]:
    return {
        int(user["user_id"]): user
        for user in _active_users()
        if user.get("user_id") is not None
    }


def _format_date(value: Any, *, with_time: bool = False) -> str:
    text = str(value or "").strip()
    if not text:
        return "—"
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return text[:16] if with_time else text[:10]
    return dt.strftime("%d/%m/%Y %H:%M" if with_time else "%d/%m/%Y")


def _rating_context(summary: dict[str, Any]) -> dict[str, Any]:
    average = summary.get("average")
    count = int(summary.get("count", 0) or 0)
    vote_label = t("rating.vote") if count == 1 else t("rating.votes")
    if average is None or count <= 0:
        return {
            "stars": "☆☆☆☆☆",
            "average": "—",
            "votes": f"0 {t('rating.vote')}",
        }

    rounded = max(0, min(5, int(float(average) + 0.5)))
    return {
        "stars": ("★" * rounded) + ("☆" * (5 - rounded)),
        "average": f"{float(average):.1f}".replace(".", ","),
        "votes": f"{count} {vote_label}",
    }


def _render_rating(
    audio_hash: str,
    summary: dict[str, Any],
    *,
    user: dict[str, Any] | None,
    key_prefix: str,
) -> None:
    st.markdown(
        _render_score("catalog-rating.score", _rating_context(summary)),
        unsafe_allow_html=True,
    )

    uid = _user_id(user)
    if uid is None:
        return

    own = summary.get("user_rating")
    label = (
        t("rating.rate")
        if own is None
        else t("rating.your", score=int(own))
    )
    with st.popover(label):
        st.caption(t("rating.contributes"))
        cols = st.columns(5)
        for score, col in enumerate(cols, start=1):
            selected = own is not None and score <= int(own)
            with col:
                if st.button(
                    "★" if selected else "☆",
                    key=f"{key_prefix}_rate_{score}",
                    help=t("rating.help", score=score),
                    width="stretch",
                ):
                    set_song_rating(uid, audio_hash, score)
                    st.rerun()


def _playlist_owner_label(
    playlist: dict[str, Any],
    groups_by_id: dict[int, dict[str, Any]],
) -> tuple[str, str]:
    source = str(playlist.get("access_source", ""))
    owner_type = str(playlist.get("owner_type", ""))
    if owner_type == PLAYLIST_OWNER_GROUP:
        group = groups_by_id.get(int(playlist["owner_id"]))
        return (
            str(group.get("name") if group else t("playlist.group")),
            "group",
        )
    if source == "shared":
        return t("playlist.shared.badge"), "shared"
    return t("playlist.personal.badge"), "personal"


def _render_add_playlist(
    audio_hash: str,
    *,
    user: dict[str, Any] | None,
    key_prefix: str,
) -> None:
    uid = _user_id(user)

    with st.popover("＋"):
        st.markdown(f"**{t('catalog.add_playlist')}**")
        if uid is None:
            st.info(t("catalog.login_playlists"))
            return

        playlists = list_accessible_playlists(
            uid,
            audio_hash=audio_hash,
            editable_only=True,
        )
        groups = list_user_groups(uid)
        groups_by_id = {int(g["group_id"]): g for g in groups}

        if playlists:
            for playlist in playlists:
                pid = int(playlist["playlist_id"])
                contains = bool(playlist.get("contains_song"))
                owner_label, _ = _playlist_owner_label(
                    playlist,
                    groups_by_id,
                )
                label = f"{'✓ ' if contains else ''}{playlist['name']} · {owner_label}"
                if st.button(
                    label,
                    disabled=contains,
                    key=f"{key_prefix}_add_playlist_{pid}",
                    width="stretch",
                ):
                    add_song_to_playlist(uid, pid, audio_hash)
                    st.rerun()
        else:
            st.caption(t("catalog.no_playlist"))

        st.markdown("---")
        new_name = st.text_input(
            t("catalog.new_playlist"),
            key=f"{key_prefix}_new_playlist_name",
            placeholder=t("catalog.new_playlist.placeholder"),
        )

        destinations = [("user", uid, t("catalog.personal"))]
        destinations.extend(
            (
                "group",
                int(group["group_id"]),
                str(group["name"]),
            )
            for group in groups
        )
        dest_keys = [
            f"{kind}:{oid}"
            for kind, oid, _label in destinations
        ]
        destination = st.selectbox(
            t("catalog.destination"),
            dest_keys,
            format_func=lambda value: next(
                label
                for kind, oid, label in destinations
                if value == f"{kind}:{oid}"
            ),
            key=f"{key_prefix}_playlist_destination",
        )
        if st.button(
            t("catalog.create_add"),
            key=f"{key_prefix}_create_playlist",
            disabled=not str(new_name or "").strip(),
            width="stretch",
        ):
            kind, raw_id = destination.split(":", 1)
            playlist = create_playlist(
                uid,
                new_name,
                owner_type=kind,
                owner_id=int(raw_id),
            )
            add_song_to_playlist(
                uid,
                int(playlist["playlist_id"]),
                audio_hash,
            )
            st.rerun()


def _open_song(
    audio_hash: str,
    *,
    selected_version: int | None = None,
    mode: str = "Vue",
    view: str = "Paroles + accords",
) -> None:
    st.session_state["active_song_hash"] = audio_hash
    set_app_state("last_song_hash", audio_hash)
    prepare_song_preferences_for_open(audio_hash)

    if selected_version is None:
        st.session_state.pop("active_analysis_version_no", None)
    else:
        prepare_analysis_version_for_open(audio_hash, selected_version)
        st.session_state[f"song_view_{audio_hash[:12]}"] = view
        st.session_state[f"song_mode_{audio_hash[:12]}"] = mode

    st.session_state["_pending_main_menu"] = "Chanson"
    st.rerun()


def _catalog_choices(
    audio_hash: str,
    versions: list[dict[str, Any]],
    workflow: dict[str, Any],
) -> list[dict[str, Any]]:
    version_numbers = [int(v["version_no"]) for v in versions]
    if not version_numbers:
        return []

    choices: list[dict[str, Any]] = []
    latest_snapshot_no = int(version_numbers[0])
    state = str(workflow.get("state", "working") or "working")

    if state != "published":
        choices.append(
            {
                "key": "working",
                "kind": "working",
                "snapshot_no": latest_snapshot_no,
                "label": (
                    f"V{workflow.get('target_version_label', '1.0')} · "
                    f"{workflow.get('target_edition_label', 'Standard')} · Travail"
                ),
            }
        )

    known = set(version_numbers)
    history = list_song_editorial_versions(audio_hash)
    for publication in history:
        if publication.get("status") != "published":
            continue
        source = publication.get("source_analysis_version_no")
        if source is None or int(source) not in known:
            continue
        choices.append(
            {
                "key": f"published:{publication['version_no']}",
                "kind": "published",
                "snapshot_no": int(source),
                "editorial": publication,
                "label": (
                    f"V{publication['version_label']} · "
                    f"{publication['edition_label']} · "
                    f"R{publication['release_no']}"
                ),
            }
        )

    current = get_song_editorial_version(
        audio_hash,
        workflow.get("current_version_no"),
    )
    if current is None:
        current = latest_song_editorial_version(audio_hash)

    if not choices and state == "published" and current is not None:
        source = current.get("source_analysis_version_no")
        if source is not None and int(source) in known:
            choices.append(
                {
                    "key": "published-current",
                    "kind": "published",
                    "snapshot_no": int(source),
                    "editorial": current,
                    "label": (
                        f"V{current['version_label']} · "
                        f"{current['edition_label']} · "
                        f"R{current['release_no']}"
                    ),
                }
            )
    return choices


def _song_status_context(
    item: dict[str, Any],
    versions: list[dict[str, Any]],
    workflow: dict[str, Any],
    *,
    sort_key: str,
    is_current: bool,
) -> dict[str, Any]:
    state = str(workflow.get("state", "working") or "working")
    primary = catalog_primary_text(item, sort_by=sort_key)
    note = str(workflow.get("working_note", "") or "").strip()

    current = get_song_editorial_version(
        item["audio_hash"],
        workflow.get("current_version_no"),
    )
    if current is None:
        current = latest_song_editorial_version(item["audio_hash"])

    if state in ("validated", "published") and current is not None:
        note = str(current.get("note", "") or "").strip()

    if not versions:
        status = t("status.pending")
        status_class = "pending"
    elif state == "published" and current is not None:
        status = t(
            "status.published",
            version=current["version_label"],
            edition=current["edition_label"],
            release=current["release_no"],
        )
        status_class = "published"
    elif state == "validated" and current is not None:
        status = t(
            "status.validated",
            version=current["version_label"],
        )
        status_class = "validated"
    else:
        status = t("status.working")
        status_class = "working"

    modified_candidates = [
        str(item.get("updated_at", "") or ""),
        str(workflow.get("updated_at", "") or ""),
    ]
    if current is not None:
        modified_candidates.append(str(current.get("updated_at", "") or ""))
    modified = max((x for x in modified_candidates if x), default="")

    return {
        "primary": ("▶ " if is_current else "") + primary,
        "status": status,
        "status_class": status_class,
        "modified": t(
            "status.modified",
            date=_format_date(modified, with_time=True),
        ),
        "note": t("status.note", note=note) if note else "",
        "has_note": bool(note),
    }


def _render_general_catalog(
    catalog: list[dict[str, Any]],
    *,
    user: dict[str, Any] | None,
) -> None:
    last_sort = get_app_state("catalog_sort", "title")
    choices = [t("catalog.sort.title"), t("catalog.sort.artist")]
    sort_choice = st.radio(
        t("catalog.sort"),
        choices,
        index=1 if last_sort == "artist" else 0,
        horizontal=True,
        key="catalog_social_sort_choice",
    )
    sort_key = "artist" if sort_choice == choices[1] else "title"
    set_app_state("catalog_sort", sort_key)

    catalog = sorted(
        catalog,
        key=lambda item: catalog_primary_text(item, sort_by=sort_key).casefold(),
    )

    st.caption(t("catalog.count", count=len(catalog)))
    search_query = st.text_input(
        t("catalog.search"),
        value="",
        placeholder=t("catalog.search.placeholder"),
        key="catalog_social_search",
    )

    all_label = t("catalog.all")
    letters = [all_label, "#"] + [
        chr(c) for c in range(ord("A"), ord("Z") + 1)
    ]
    default_letter = get_app_state("catalog_letter", all_label)
    if default_letter == "Tous" and all_label != "Tous":
        default_letter = all_label
    if default_letter not in letters:
        default_letter = all_label

    selected_letter = st.radio(
        t("catalog.index"),
        letters,
        index=letters.index(default_letter),
        horizontal=True,
        key="catalog_social_letter",
    )
    set_app_state("catalog_letter", selected_letter)

    filtered = filter_catalog(
        catalog,
        sort_by=sort_key,
        letter=("Tous" if selected_letter == all_label else selected_letter),
        query=search_query,
    )

    if not catalog:
        st.info(t("catalog.empty"))
        return
    if not filtered:
        st.info(t("catalog.no_result"))
        return

    uid = _user_id(user)
    summaries = rating_summaries(
        [item["audio_hash"] for item in filtered],
        uid,
    )
    current_hash = str(st.session_state.get("active_song_hash", "") or "")

    groups: dict[str, list[dict[str, Any]]] = {}
    for item in filtered:
        letter = catalog_letter_for_song(item, sort_by=sort_key)
        groups.setdefault(letter, []).append(item)

    ordered_letters = ["#"] + [chr(c) for c in range(ord("A"), ord("Z") + 1)]
    for letter in ordered_letters:
        items = groups.get(letter, [])
        if not items:
            continue

        st.markdown(
            _render_score("catalog-letter.score", {"letter": letter}),
            unsafe_allow_html=True,
        )

        for item in items:
            audio_hash = str(item["audio_hash"])
            versions = list_analysis_versions(audio_hash)
            workflow = get_song_workflow(audio_hash)
            version_choices = _catalog_choices(audio_hash, versions, workflow)

            with st.container(border=True):
                cover_col, info_col, social_col = st.columns([0.7, 4.9, 1.6])

                with cover_col:
                    cover = song_cover_path(item)
                    if cover is not None:
                        st.image(str(cover), width=72)
                    else:
                        st.markdown(
                            _render_score(
                                "catalog-cover-empty.score",
                                {"icon": "♫"},
                            ),
                            unsafe_allow_html=True,
                        )

                with info_col:
                    st.markdown(
                        _render_score(
                            "catalog-song.score",
                            _song_status_context(
                                item,
                                versions,
                                workflow,
                                sort_key=sort_key,
                                is_current=(audio_hash == current_hash),
                            ),
                        ),
                        unsafe_allow_html=True,
                    )
                    secondary = catalog_secondary_text(item, sort_by=sort_key)
                    st.caption(secondary)

                with social_col:
                    _render_rating(
                        audio_hash,
                        summaries.get(
                            audio_hash,
                            {"average": None, "count": 0, "user_rating": None},
                        ),
                        user=user,
                        key_prefix=f"catalog_social_{audio_hash}",
                    )
                    _render_add_playlist(
                        audio_hash,
                        user=user,
                        key_prefix=f"catalog_social_{audio_hash}",
                    )

                version_col, editor_col, action_col = st.columns([2.0, 1.5, 3.0])

                selected_choice = None
                selected_version = None
                with version_col:
                    if version_choices:
                        keys = [choice["key"] for choice in version_choices]
                        selected_key = st.selectbox(
                            t("catalog.version"),
                            keys,
                            index=0,
                            format_func=lambda key, _choices=version_choices: next(
                                choice["label"] for choice in _choices
                                if choice["key"] == key
                            ),
                            key=f"catalog_social_version_{audio_hash}",
                            label_visibility="collapsed",
                        )
                        selected_choice = next(
                            choice for choice in version_choices
                            if choice["key"] == selected_key
                        )
                        selected_version = int(selected_choice["snapshot_no"])
                    else:
                        st.caption(t("catalog.no_version"))

                with editor_col:
                    version_data = next(
                        (
                            v for v in versions
                            if selected_version is not None
                            and int(v["version_no"]) == selected_version
                        ),
                        None,
                    )
                    editor_display = (
                        str(version_data.get("editor", "") or "").strip()
                        if version_data
                        else str(item.get("editor", "") or "").strip()
                    )
                    st.caption(
                        t(
                            "catalog.editor",
                            name=editor_display or t("common.no_editor"),
                        )
                    )

                with action_col:
                    if selected_version is None:
                        open_col, delete_col = st.columns([1.8, 0.7])
                        with open_col:
                            if st.button(
                                t("catalog.open"),
                                key=f"catalog_social_open_{audio_hash}",
                                width="stretch",
                            ):
                                _open_song(audio_hash)
                        with delete_col:
                            if auth_allowed("song.delete"):
                                with st.popover("🗑"):
                                    render_delete_song_controls(
                                        audio_hash=audio_hash,
                                        display_name=catalog_display_name(
                                            item,
                                            sort_by="title",
                                        ),
                                        key_suffix=f"social_{audio_hash}_noversion",
                                    )
                    else:
                        view_col, edit_col, delete_col = st.columns([1, 1, .55])
                        with view_col:
                            if st.button(
                                t("catalog.view"),
                                key=f"catalog_social_view_{audio_hash}_{selected_version}",
                                width="stretch",
                            ):
                                _open_song(
                                    audio_hash,
                                    selected_version=selected_version,
                                    mode="Vue",
                                    view="Paroles + accords",
                                )
                        with edit_col:
                            if auth_allowed("song.edit"):
                                if st.button(
                                    t("catalog.edit"),
                                    key=f"catalog_social_edit_{audio_hash}_{selected_version}",
                                    width="stretch",
                                ):
                                    auth_require("song.edit")
                                    if (
                                        selected_choice is not None
                                        and selected_choice.get("kind") == "published"
                                    ):
                                        resume_song_modifications(audio_hash)
                                    _open_song(
                                        audio_hash,
                                        selected_version=selected_version,
                                        mode="Édition",
                                        view="Grille",
                                    )
                        with delete_col:
                            if auth_allowed("song.delete"):
                                with st.popover("🗑"):
                                    render_delete_song_controls(
                                        audio_hash=audio_hash,
                                        display_name=catalog_display_name(
                                            item,
                                            sort_by="title",
                                        ),
                                        key_suffix=f"social_{audio_hash}_{selected_version}",
                                    )


def _render_share_controls(
    uid: int,
    playlist: dict[str, Any],
    *,
    users_by_id: dict[int, dict[str, Any]],
    key_prefix: str,
) -> None:
    if not playlist.get("can_manage"):
        return

    with st.popover("↗ " + t("playlist.share")):
        candidates = [
            user
            for user_id, user in users_by_id.items()
            if user_id != uid
        ]
        if candidates:
            user_ids = [int(user["user_id"]) for user in candidates]
            target = st.selectbox(
                t("playlist.share.user"),
                user_ids,
                format_func=lambda user_id: _user_label(users_by_id[user_id]),
                key=f"{key_prefix}_share_user",
            )
            permission_labels = {
                PLAYLIST_PERMISSION_READ: t("playlist.share.read"),
                PLAYLIST_PERMISSION_EDIT: t("playlist.share.edit"),
            }
            permission = st.selectbox(
                t("playlist.share.permission"),
                [PLAYLIST_PERMISSION_READ, PLAYLIST_PERMISSION_EDIT],
                format_func=lambda value: permission_labels[value],
                key=f"{key_prefix}_share_permission",
            )
            if st.button(
                t("playlist.share.action"),
                key=f"{key_prefix}_share_action",
                width="stretch",
            ):
                share_playlist(
                    uid,
                    int(playlist["playlist_id"]),
                    int(target),
                    permission,
                )
                st.rerun()

        shares = list_playlist_shares(uid, int(playlist["playlist_id"]))
        if not shares:
            st.caption(t("playlist.share.none"))
        for share in shares:
            target_id = int(share["user_id"])
            target_user = users_by_id.get(target_id, {"user_id": target_id})
            label = _user_label(target_user)
            permission_label = (
                t("playlist.share.edit")
                if share["permission"] == PLAYLIST_PERMISSION_EDIT
                else t("playlist.share.read")
            )
            row_col, remove_col = st.columns([4, 1])
            with row_col:
                st.caption(f"{label} · {permission_label}")
            with remove_col:
                if st.button(
                    "×",
                    key=f"{key_prefix}_unshare_{target_id}",
                    help=t("playlist.share.remove"),
                ):
                    unshare_playlist(
                        uid,
                        int(playlist["playlist_id"]),
                        target_id,
                    )
                    st.rerun()


def _render_playlist_cards(
    catalog: list[dict[str, Any]],
    *,
    uid: int,
) -> None:
    playlists = list_accessible_playlists(uid)
    if not playlists:
        st.info(t("playlist.empty"))
        return

    groups = list_user_groups(uid)
    groups_by_id = {int(g["group_id"]): g for g in groups}
    users_by_id = _user_map()
    visible_by_hash = {str(item["audio_hash"]): item for item in catalog}

    for playlist in playlists:
        pid = int(playlist["playlist_id"])
        songs = [
            item for item in list_playlist_songs(uid, pid)
            if str(item["audio_hash"]) in visible_by_hash
        ]
        owner_label, owner_class = _playlist_owner_label(
            playlist,
            groups_by_id,
        )

        with st.container(border=True):
            st.markdown(
                _render_score(
                    "catalog-playlist.score",
                    {
                        "name": playlist["name"],
                        "count": len(songs),
                        "count_label": (
                            t("playlist.song")
                            if len(songs) == 1
                            else t("playlist.songs")
                        ),
                        "owner_label": owner_label,
                        "owner_class": owner_class,
                    },
                ),
                unsafe_allow_html=True,
            )

            control_cols = st.columns([1.2, 1.2, 5])
            with control_cols[0]:
                _render_share_controls(
                    uid,
                    playlist,
                    users_by_id=users_by_id,
                    key_prefix=f"playlist_{pid}",
                )
            with control_cols[1]:
                if playlist.get("can_manage"):
                    with st.popover("🗑 " + t("playlist.delete")):
                        st.warning(t("playlist.delete.warning"))
                        if st.button(
                            t("playlist.confirm"),
                            key=f"catalog_playlist_delete_{pid}",
                            type="primary",
                        ):
                            delete_user_playlist(uid, pid)
                            st.rerun()

            if not songs:
                st.caption(t("playlist.empty.content"))
                continue

            summaries = rating_summaries(
                [song["audio_hash"] for song in songs],
                uid,
            )

            for position, song in enumerate(songs, start=1):
                audio_hash = str(song["audio_hash"])
                title = str(song.get("title", "") or "").strip()
                if not title:
                    title = (
                        Path(str(song.get("original_filename", "") or "")).stem
                        or "Sans titre"
                    )
                artist = (
                    str(song.get("artist", "") or "").strip()
                    or t("common.unknown_artist")
                )

                pos_col, title_col, rating_col, open_col, remove_col = st.columns(
                    [0.35, 3.4, 1.3, 0.9, 0.9]
                )
                with pos_col:
                    st.markdown(
                        _render_score(
                            "catalog-position.score",
                            {"position": position},
                        ),
                        unsafe_allow_html=True,
                    )
                with title_col:
                    st.markdown(
                        _render_score(
                            "catalog-playlist-song.score",
                            {"title": title, "artist": artist},
                        ),
                        unsafe_allow_html=True,
                    )
                with rating_col:
                    st.markdown(
                        _render_score(
                            "catalog-rating.score",
                            _rating_context(
                                summaries.get(
                                    audio_hash,
                                    {"average": None, "count": 0},
                                )
                            ),
                        ),
                        unsafe_allow_html=True,
                    )
                with open_col:
                    if st.button(
                        t("catalog.open"),
                        key=f"catalog_playlist_open_{pid}_{audio_hash}",
                        width="stretch",
                    ):
                        versions = list_analysis_versions(audio_hash)
                        if versions:
                            _open_song(
                                audio_hash,
                                selected_version=int(versions[0]["version_no"]),
                                mode="Vue",
                                view="Paroles + accords",
                            )
                        else:
                            _open_song(audio_hash)
                with remove_col:
                    if playlist.get("can_edit"):
                        if st.button(
                            t("playlist.remove"),
                            key=f"catalog_playlist_remove_{pid}_{audio_hash}",
                            width="stretch",
                        ):
                            remove_song_from_playlist(uid, pid, audio_hash)
                            st.rerun()


def _render_groups(uid: int) -> None:
    users_by_id = _user_map()
    groups = list_user_groups(uid)

    with st.container(border=True):
        st.markdown(
            _render_score(
                "catalog-section.score",
                {
                    "icon": "👥",
                    "title": t("group.create"),
                    "subtitle": "",
                },
            ),
            unsafe_allow_html=True,
        )
        name_col, action_col = st.columns([4, 1])
        with name_col:
            new_group = st.text_input(
                t("group.create"),
                key="catalog_group_new_name",
                placeholder=t("group.create.placeholder"),
                label_visibility="collapsed",
            )
        with action_col:
            if st.button(
                t("group.create.action"),
                key="catalog_group_create",
                disabled=not str(new_group or "").strip(),
                width="stretch",
            ):
                create_user_group(uid, new_group)
                st.rerun()

    if not groups:
        st.info(t("group.empty"))
        return

    for group in groups:
        gid = int(group["group_id"])
        is_admin = str(group.get("role")) == GROUP_ROLE_ADMIN
        members = list_group_members(uid, gid)

        with st.container(border=True):
            st.markdown(
                _render_score(
                    "catalog-group.score",
                    {
                        "name": group["name"],
                        "member_count": int(group.get("member_count", 0) or 0),
                        "member_label": t("group.members"),
                        "playlist_count": int(group.get("playlist_count", 0) or 0),
                        "playlist_label": t("group.playlists"),
                        "role": (
                            t("group.admin")
                            if is_admin
                            else t("group.member")
                        ),
                    },
                ),
                unsafe_allow_html=True,
            )

            if is_admin:
                with st.expander("＋ " + t("group.add_member")):
                    existing_ids = {int(item["user_id"]) for item in members}
                    candidates = [
                        user_id
                        for user_id in users_by_id
                        if user_id not in existing_ids
                    ]
                    if candidates:
                        target = st.selectbox(
                            t("group.select_user"),
                            candidates,
                            format_func=lambda user_id: _user_label(users_by_id[user_id]),
                            key=f"group_{gid}_member_user",
                        )
                        role = st.selectbox(
                            t("group.role"),
                            [GROUP_ROLE_MEMBER, GROUP_ROLE_ADMIN],
                            format_func=lambda value: (
                                t("group.member")
                                if value == GROUP_ROLE_MEMBER
                                else t("group.admin")
                            ),
                            key=f"group_{gid}_member_role",
                        )
                        if st.button(
                            t("group.add"),
                            key=f"group_{gid}_member_add",
                        ):
                            add_group_member(uid, gid, target, role)
                            st.rerun()

            st.markdown(f"**{t('group.members')}**")
            for member in members:
                member_id = int(member["user_id"])
                user = users_by_id.get(member_id, {"user_id": member_id})
                role_label = (
                    t("group.admin")
                    if member["role"] == GROUP_ROLE_ADMIN
                    else t("group.member")
                )
                member_col, action_col = st.columns([5, 1])
                with member_col:
                    suffix = f" · {t('group.me')}" if member_id == uid else ""
                    st.caption(f"{_user_label(user)} · {role_label}{suffix}")
                with action_col:
                    if is_admin and member_id != uid:
                        if st.button(
                            "×",
                            key=f"group_{gid}_remove_{member_id}",
                            help=t("group.remove"),
                        ):
                            remove_group_member(uid, gid, member_id)
                            st.rerun()

            st.markdown(f"**{t('group.create_playlist')}**")
            p_name_col, p_action_col = st.columns([4, 1])
            with p_name_col:
                playlist_name = st.text_input(
                    t("group.create_playlist"),
                    key=f"group_{gid}_playlist_name",
                    placeholder=t("group.playlist.placeholder"),
                    label_visibility="collapsed",
                )
            with p_action_col:
                if st.button(
                    t("playlist.create"),
                    key=f"group_{gid}_playlist_create",
                    disabled=not str(playlist_name or "").strip(),
                    width="stretch",
                ):
                    create_playlist(
                        uid,
                        playlist_name,
                        owner_type=PLAYLIST_OWNER_GROUP,
                        owner_id=gid,
                    )
                    st.rerun()

            if is_admin:
                with st.popover("🗑 " + t("group.delete")):
                    st.warning(t("group.delete.warning"))
                    if st.button(
                        t("playlist.confirm"),
                        key=f"group_{gid}_delete",
                        type="primary",
                    ):
                        delete_user_group(uid, gid)
                        st.rerun()


def _render_playlists(
    catalog: list[dict[str, Any]],
    *,
    user: dict[str, Any] | None,
) -> None:
    uid = _user_id(user)
    if uid is None:
        st.info(t("playlist.login"))
        return

    section = st.radio(
        "Playlist mode",
        [t("playlist.section.mine"), t("playlist.section.groups")],
        horizontal=True,
        key="catalog_playlist_section",
        label_visibility="collapsed",
    )

    if section == t("playlist.section.groups"):
        _render_groups(uid)
        return

    with st.container(border=True):
        create_col, button_col = st.columns([4, 1])
        with create_col:
            new_name = st.text_input(
                t("catalog.new_playlist"),
                key="catalog_playlist_new_name",
                placeholder=t("playlist.create.placeholder"),
                label_visibility="collapsed",
            )
        with button_col:
            if st.button(
                t("playlist.create"),
                key="catalog_playlist_create",
                disabled=not str(new_name or "").strip(),
                width="stretch",
            ):
                create_user_playlist(uid, new_name)
                st.rerun()

    _render_playlist_cards(catalog, uid=uid)


def render_catalog_home() -> None:
    ensure_catalog_social_schema()
    user = auth_current_user()

    # I18n OPUS-like : browser language first, explicit override second.
    lang_col, spacer = st.columns([1.25, 5])
    with lang_col:
        language = current_language()
        selected = st.selectbox(
            t("home.language"),
            ["fr", "en"],
            index=0 if language == "fr" else 1,
            format_func=lambda value: "FR" if value == "fr" else "EN",
            key="catalog_language_selector",
            label_visibility="collapsed",
        )
        if selected != language:
            set_language(selected)
            st.rerun()

    st.markdown(
        _render_score(
            "catalog-home.score",
            {"title": t("home.title")},
        ),
        unsafe_allow_html=True,
    )

    mode = st.radio(
        "Catalog home",
        [t("home.general"), t("home.playlists")],
        horizontal=True,
        key="catalog_home_mode",
        label_visibility="collapsed",
    )

    catalog = list_song_catalog(sort_by="title")
    if not auth_allowed("song.read_private"):
        catalog = [
            item for item in catalog
            if str(
                get_song_workflow(item["audio_hash"]).get("state", "working")
            ) == "published"
        ]

    if mode == t("home.playlists"):
        _render_playlists(catalog, user=user)
    else:
        _render_general_catalog(catalog, user=user)
