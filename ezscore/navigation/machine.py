from __future__ import annotations
from typing import Any

from .events import OPEN_REPERTOIRE, OPEN_PLAYLISTS, OPEN_GROUPS, OPEN_GROUP, OPEN_PLAYLIST, OPEN_SONG
from .states import ALL_STATES, REPERTOIRE_LIST, PLAYLISTS_LIST, GROUPS_LIST, GROUP_DETAIL, PLAYLIST_DETAIL, SONG_DETAIL, SONG_ANALYSIS


def initial_route() -> dict[str, Any]:
    return {"state": REPERTOIRE_LIST, "context": {}}


def normalize_route(route: Any) -> dict[str, Any]:
    if not isinstance(route, dict):
        return initial_route()
    state = str(route.get("state") or "")
    if state not in ALL_STATES:
        return initial_route()
    context = route.get("context")
    if not isinstance(context, dict):
        context = {}
    return {"state": state, "context": dict(context)}


def _required_int(payload: dict[str, Any], key: str) -> int:
    try:
        value = int(payload.get(key))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{key} invalide") from exc
    if value <= 0:
        raise ValueError(f"{key} invalide")
    return value


def _required_text(payload: dict[str, Any], key: str) -> str:
    value = str(payload.get(key) or "").strip()
    if not value:
        raise ValueError(f"{key} vide")
    return value


def transition(route: Any, event: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    current = normalize_route(route)
    context = dict(current["context"])
    data = dict(payload or {})

    if event == OPEN_REPERTOIRE:
        return {"state": REPERTOIRE_LIST, "context": {}}
    if event == OPEN_PLAYLISTS:
        return {"state": PLAYLISTS_LIST, "context": {}}
    if event == OPEN_GROUPS:
        return {"state": GROUPS_LIST, "context": {}}
    if event == OPEN_GROUP:
        return {"state": GROUP_DETAIL, "context": {"group_id": _required_int(data, "group_id")}}
    if event == OPEN_PLAYLIST:
        next_context: dict[str, Any] = {"playlist_id": _required_int(data, "playlist_id")}
        raw_group = data.get("group_id", context.get("group_id"))
        if raw_group not in (None, ""):
            try:
                gid = int(raw_group)
            except (TypeError, ValueError):
                gid = 0
            if gid > 0:
                next_context["group_id"] = gid
        return {"state": PLAYLIST_DETAIL, "context": next_context}
    if event == OPEN_SONG:
        audio_hash = _required_text(data, "audio_hash")
        view = str(data.get("view") or "Paroles + accords").strip()
        mode = str(data.get("mode") or "Vue").strip()
        next_context = dict(context)
        next_context.update({"audio_hash": audio_hash, "view": view, "mode": mode})
        version = data.get("analysis_version_no")
        if version not in (None, ""):
            try:
                version_no = int(version)
            except (TypeError, ValueError) as exc:
                raise ValueError("analysis_version_no invalide") from exc
            if version_no <= 0:
                raise ValueError("analysis_version_no invalide")
            next_context["analysis_version_no"] = version_no
        else:
            next_context.pop("analysis_version_no", None)
        return {
            "state": SONG_ANALYSIS if view == "Analyse" else SONG_DETAIL,
            "context": next_context,
        }
    raise ValueError(f"Transition de navigation inconnue : {current['state']} + {event}")
