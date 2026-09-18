from __future__ import annotations

"""Drag/drop editor for an ordered EZScore playlist.

No audio and no song-analysis dependency. The component only returns an ordered
list of audio hashes; persistence remains server-side in catalog_social.
"""

import json
from pathlib import Path
from typing import Any

import streamlit as st


_TEMPLATE_DIR = Path(__file__).resolve().parents[2] / "templates" / "views"


def _template(name: str) -> str:
    path = _TEMPLATE_DIR / name
    if not path.is_file():
        raise RuntimeError(f"Template EZScore manquant : {path}")
    return path.read_text(encoding="utf-8")


_COMPONENT = st.components.v2.component(
    "ezscore_playlist_order_editor_r1",
    html=_template("playlist-order-editor.html"),
    css=_template("playlist-order-editor.css"),
    js=_template("playlist-order-editor.js"),
    isolate_styles=True,
)


def render_playlist_order_editor(
    playlist_id: int,
    songs: list[dict[str, Any]],
    *,
    editable: bool,
    drag_label: str,
    readonly_label: str,
) -> list[str]:
    items = []
    for song in songs:
        audio_hash = str(song.get("audio_hash", "") or "").strip()
        if not audio_hash:
            continue
        title = str(song.get("title", "") or "").strip()
        if not title:
            title = Path(str(song.get("original_filename", "") or "")).stem
        artist = str(song.get("artist", "") or "").strip()
        items.append(
            {
                "audio_hash": audio_hash,
                "title": title or audio_hash[:12],
                "artist": artist,
            }
        )

    initial_order = [item["audio_hash"] for item in items]

    result = _COMPONENT(
        data={
            "items": items,
            "editable": bool(editable),
            "drag_label": drag_label,
            "readonly_label": readonly_label,
        },
        default={"order": json.dumps(initial_order)},
        key=f"ez_playlist_order_{int(playlist_id)}",
        on_order_change=lambda: None,
    )

    raw = str(getattr(result, "order", "") or "")
    if not raw:
        return initial_order

    try:
        order = json.loads(raw)
    except Exception:
        return initial_order

    if not isinstance(order, list):
        return initial_order

    clean = [str(value) for value in order]
    if len(clean) != len(initial_order) or set(clean) != set(initial_order):
        return initial_order

    return clean
