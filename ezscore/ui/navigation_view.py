from __future__ import annotations

from pathlib import Path
from typing import Any
import html

import streamlit as st

from EZScoreTemplate import ScoreTemplateRenderer
from ezscore.navigation.session_adapter import current_route
from ezscore.navigation.states import (
    REPERTOIRE_LIST, PLAYLISTS_LIST, GROUPS_LIST, GROUP_DETAIL,
    PLAYLIST_DETAIL, SONG_DETAIL, SONG_ANALYSIS,
)

APP_DIR = Path(__file__).resolve().parents[2]
SCORE = ScoreTemplateRenderer(APP_DIR)


def render_navigation_path(
    *,
    group_name: str = "",
    playlist_name: str = "",
    song_name: str = "",
) -> None:
    route = current_route()
    state = str(route["state"])
    context = dict(route.get("context") or {})

    items: list[dict[str, Any]] = [
        {"label": "Répertoire", "active": state == REPERTOIRE_LIST},
    ]

    if state in {PLAYLISTS_LIST, PLAYLIST_DETAIL}:
        items.append({"label": "Playlists", "active": state == PLAYLISTS_LIST})

    if state in {GROUPS_LIST, GROUP_DETAIL}:
        items.append({"label": "Groupes", "active": state == GROUPS_LIST})

    if state == GROUP_DETAIL:
        items.append({"label": group_name or "Groupe", "active": True})

    if state == PLAYLIST_DETAIL:
        if context.get("group_id") and group_name:
            items.append({"label": group_name, "active": False})
        items.append({"label": playlist_name or "Playlist", "active": True})

    if state in {SONG_DETAIL, SONG_ANALYSIS}:
        if context.get("group_id") and group_name:
            items.append({"label": group_name, "active": False})
        if context.get("playlist_id") and playlist_name:
            items.append({"label": playlist_name, "active": False})
        items.append({
            "label": song_name or "Chanson",
            "active": state == SONG_DETAIL,
        })
        if state == SONG_ANALYSIS:
            items.append({"label": "Analyse", "active": True})

    chunks = []
    for index, item in enumerate(items):
        cls = "eznav-item active" if item["active"] else "eznav-item"
        chunks.append(
            f'<span class="{cls}">{html.escape(str(item["label"]))}</span>'
        )
        if index < len(items) - 1:
            chunks.append('<span class="eznav-sep">›</span>')

    st.markdown(
        SCORE.render(
            "templates/views/navigation-breadcrumb.score",
            {"items_html": "".join(chunks)},
        ),
        unsafe_allow_html=True,
    )
