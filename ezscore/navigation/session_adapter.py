from __future__ import annotations
from typing import Any
import streamlit as st
from ezscore.auth import current_user
from ezscore.acl import actions as acl_actions
from ezscore.acl.guards import require as acl_require

from ezscore.persistence import prepare_analysis_version_for_open, prepare_song_preferences_for_open, set_app_state
from .events import OPEN_REPERTOIRE, OPEN_PLAYLISTS, OPEN_GROUPS, OPEN_GROUP, OPEN_PLAYLIST, OPEN_SONG
from .machine import initial_route, normalize_route, transition
from .states import REPERTOIRE_LIST, PLAYLISTS_LIST, GROUPS_LIST, GROUP_DETAIL, PLAYLIST_DETAIL, SONG_DETAIL, SONG_ANALYSIS

_ROUTE_KEY = "_ez_nav_route_v1"
_HISTORY_KEY = "_ez_nav_history_v1"
_MAX_HISTORY = 32

def _current_user_id() -> int | None:
    user = current_user() or {}
    try:
        value = int(user.get("user_id"))
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def current_route() -> dict[str, Any]:
    route = normalize_route(st.session_state.get(_ROUTE_KEY))
    st.session_state[_ROUTE_KEY] = route
    return route


def current_state() -> str:
    return str(current_route()["state"])


def current_context() -> dict[str, Any]:
    return dict(current_route()["context"])


def history() -> list[dict[str, Any]]:
    raw = st.session_state.get(_HISTORY_KEY, [])
    if not isinstance(raw, list):
        raw = []
    result = [normalize_route(item) for item in raw]
    st.session_state[_HISTORY_KEY] = result[-_MAX_HISTORY:]
    return list(st.session_state[_HISTORY_KEY])


def can_back() -> bool:
    return bool(history())


def previous_route() -> dict[str, Any] | None:
    stack = history()
    return dict(stack[-1]) if stack else None


def _same_route(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return left.get("state") == right.get("state") and left.get("context") == right.get("context")


def _apply_legacy_bridge(route: dict[str, Any]) -> None:
    state = str(route["state"])
    context = dict(route["context"])

    if state in {REPERTOIRE_LIST, PLAYLISTS_LIST, GROUPS_LIST, GROUP_DETAIL, PLAYLIST_DETAIL}:
        st.session_state["_pending_main_menu"] = "Répertoire"

    if state in {SONG_DETAIL, SONG_ANALYSIS}:
        audio_hash = str(context.get("audio_hash") or "").strip()
        if audio_hash:
            st.session_state["active_song_hash"] = audio_hash
            st.session_state["_pending_main_menu"] = "Chanson"
            view = str(context.get("view") or "").strip()
            mode = str(context.get("mode") or "").strip()
            if view:
                st.session_state[f"song_view_{audio_hash[:12]}"] = view
            if mode:
                st.session_state[f"song_mode_{audio_hash[:12]}"] = mode
            version = context.get("analysis_version_no")
            if version not in (None, ""):
                st.session_state["active_analysis_version_no"] = int(version)
            else:
                st.session_state.pop("active_analysis_version_no", None)

    st.session_state.pop("_ez_groups_open", None)
    st.session_state.pop("_ez_catalog_open_playlists", None)
    st.session_state.pop("_ez_open_playlist_id", None)


def _commit(next_route: dict[str, Any], *, push_history: bool, clear_history: bool = False, rerun: bool = True) -> dict[str, Any]:
    current = current_route()
    if clear_history:
        st.session_state[_HISTORY_KEY] = []
    elif push_history and not _same_route(current, next_route):
        stack = history()
        stack.append(current)
        st.session_state[_HISTORY_KEY] = stack[-_MAX_HISTORY:]
    st.session_state[_ROUTE_KEY] = normalize_route(next_route)
    _apply_legacy_bridge(st.session_state[_ROUTE_KEY])
    if rerun:
        st.rerun()
    return dict(st.session_state[_ROUTE_KEY])


def dispatch(event: str, payload: dict[str, Any] | None = None, *, push_history: bool = True, clear_history: bool = False, rerun: bool = True) -> dict[str, Any]:
    return _commit(
        transition(current_route(), event, payload),
        push_history=push_history,
        clear_history=clear_history,
        rerun=rerun,
    )


def open_repertoire(*, rerun: bool = True) -> dict[str, Any]:
    return dispatch(OPEN_REPERTOIRE, push_history=False, clear_history=True, rerun=rerun)


def open_playlists(*, rerun: bool = True) -> dict[str, Any]:
    acl_require(_current_user_id(), acl_actions.PLAYLIST_LIST)
    return dispatch(OPEN_PLAYLISTS, push_history=True, rerun=rerun)


def open_groups(*, rerun: bool = True) -> dict[str, Any]:
    acl_require(_current_user_id(), acl_actions.GROUP_LIST)
    return dispatch(OPEN_GROUPS, push_history=True, rerun=rerun)


def open_group(group_id: int, *, rerun: bool = True) -> dict[str, Any]:
    gid = int(group_id)
    acl_require(_current_user_id(), acl_actions.GROUP_READ, group_id=gid)
    return dispatch(OPEN_GROUP, {"group_id": gid}, push_history=True, rerun=rerun)


def open_playlist(playlist_id: int, *, group_id: int | None = None, rerun: bool = True) -> dict[str, Any]:
    pid = int(playlist_id)
    gid = int(group_id) if group_id is not None else None
    acl_require(_current_user_id(), acl_actions.PLAYLIST_READ, playlist_id=pid, group_id=gid)
    payload: dict[str, Any] = {"playlist_id": pid}
    if gid is not None:
        payload["group_id"] = gid
    return dispatch(OPEN_PLAYLIST, payload, push_history=True, rerun=rerun)


def open_song(audio_hash: str, *, selected_version: int | None = None, mode: str = "Vue", view: str = "Paroles + accords", rerun: bool = True) -> dict[str, Any]:
    song = str(audio_hash or "").strip()
    if not song:
        raise ValueError("audio_hash vide")
    acl_require(
        _current_user_id(),
        acl_actions.SONG_EDIT if mode == "Édition" else acl_actions.SONG_READ,
    )
    set_app_state("last_song_hash", song)
    prepare_song_preferences_for_open(song)
    if selected_version is None:
        st.session_state.pop("active_analysis_version_no", None)
    else:
        prepare_analysis_version_for_open(song, int(selected_version))
    return dispatch(
        OPEN_SONG,
        {
            "audio_hash": song,
            "analysis_version_no": selected_version,
            "mode": mode,
            "view": view,
        },
        push_history=True,
        rerun=rerun,
    )


def open_song_from_repertoire(
    audio_hash: str,
    *,
    selected_version: int | None = None,
    mode: str = "Vue",
    view: str = "Paroles + accords",
    rerun: bool = True,
) -> dict[str, Any]:
    # Répertoire général est une racine : on supprime tout ancien parent
    # Groupe/Playlist avant d'ouvrir la chanson.
    open_repertoire(rerun=False)
    return open_song(
        audio_hash,
        selected_version=selected_version,
        mode=mode,
        view=view,
        rerun=rerun,
    )


def open_song_from_playlist(
    audio_hash: str,
    *,
    selected_version: int | None = None,
    mode: str = "Vue",
    view: str = "Analyse",
    rerun: bool = True,
) -> dict[str, Any]:
    # Ici on conserve volontairement playlist_id/group_id dans l'historique.
    return open_song(
        audio_hash,
        selected_version=selected_version,
        mode=mode,
        view=view,
        rerun=rerun,
    )


def open_song_analysis(audio_hash: str, *, selected_version: int | None = None, mode: str = "Vue", rerun: bool = True) -> dict[str, Any]:
    return open_song(audio_hash, selected_version=selected_version, mode=mode, view="Analyse", rerun=rerun)


def back(*, rerun: bool = True) -> dict[str, Any]:
    stack = history()
    if not stack:
        return open_repertoire(rerun=rerun)
    target = normalize_route(stack.pop())
    st.session_state[_HISTORY_KEY] = stack
    st.session_state[_ROUTE_KEY] = target
    _apply_legacy_bridge(target)
    if rerun:
        st.rerun()
    return dict(target)


def bootstrap_from_legacy() -> dict[str, Any]:
    if _ROUTE_KEY in st.session_state:
        return current_route()

    if bool(st.session_state.get("_ez_groups_open", False)):
        route = transition(initial_route(), OPEN_GROUPS, {})
    else:
        focused = st.session_state.get("_ez_open_playlist_id")
        if focused not in (None, ""):
            try:
                playlist_id = int(focused)
            except (TypeError, ValueError):
                route = initial_route()
            else:
                route = transition(initial_route(), OPEN_PLAYLIST, {"playlist_id": playlist_id})
        elif bool(st.session_state.get("_ez_catalog_open_playlists", False)):
            route = transition(initial_route(), OPEN_PLAYLISTS, {})
        else:
            route = initial_route()

    st.session_state[_ROUTE_KEY] = route
    st.session_state[_HISTORY_KEY] = []
    _apply_legacy_bridge(route)
    return dict(route)
