from __future__ import annotations

"""Template-driven Riffstation/STEM player used by Analyse Step 1 and Step 2.

The existing STEM_LAB orchestration remains authoritative.  This module only
prepares the shared player ViewModel and renders the existing Streamlit v2
component from SCORE/CSS/JS templates.
"""

import json
from pathlib import Path
from typing import Any

import streamlit as st

from EZScoreTemplate import ScoreTemplateRenderer
from ezscore.analysis.riffstation_step1 import (
    SUPPORTED_SIGNATURES,
    analyze as analyze_step1,
    effective_signature,
    load as load_step1,
    timeline_beats_per_measure,
)
from ezscore.analysis.stems import STEM_NAMES
from ezscore.auth import current_user
from ezscore.auth.storage import list_users
from ezscore.guitar import (
    choices as guitar_choices,
    get_voicing,
    load_show_diagrams,
    load_voicings,
    save_show_diagrams,
    svg as guitar_svg,
)
from ezscore.notation import accord_forme_capo
from ezscore.persistence import (
    assign_song_editor,
    get_song_editor_assignment,
    list_song_catalog,
    load_latest_persisted_analysis,
    load_song_preferences,
    save_song_preferences,
    update_song_metadata,
)
from ezscore.player.karaoke_stem_webaudio import prepare_browser_previews
from ezscore.player.media_metadata import duration_seconds
from ezscore.player.media_url import register_media_url

APP_DIR = Path(__file__).resolve().parents[2]
TEMPLATE_DIR = APP_DIR / "templates" / "views"
SCORE = ScoreTemplateRenderer(APP_DIR)

_HTML = SCORE.render(
    "templates/views/riffstation-workspace.score",
    {"view": {"name": "Riffstation + STEM"}},
)
_CSS = (TEMPLATE_DIR / "riffstation-workspace.css").read_text(encoding="utf-8")
_JS = (TEMPLATE_DIR / "riffstation-workspace.js").read_text(encoding="utf-8")

_COMPONENT = st.components.v2.component(
    "ezscore_karaoke_stem_player_r13",
    html=_HTML,
    css=_CSS,
    js=_JS,
    isolate_styles=True,
)

_SIGNATURE_OPTIONS = ["Auto", *SUPPORTED_SIGNATURES]


def _song(audio_hash: str) -> dict[str, Any]:
    for item in list_song_catalog(sort_by="title"):
        if str(item.get("audio_hash", "")) == str(audio_hash):
            return dict(item)
    return {}


def _editor_context(audio_hash: str, song: dict[str, Any]) -> tuple[list[dict[str, str]], str, int | None, bool]:
    assignment = get_song_editor_assignment(audio_hash)
    editor_id = (
        int(assignment["user_id"])
        if assignment and assignment.get("user_id") is not None
        else None
    )
    editor_name = str(
        (assignment or {}).get("display_name")
        or song.get("editor")
        or ""
    ).strip()

    editors: list[dict[str, str]] = []
    for user in list_users():
        if not bool(user.get("active")):
            continue
        if str(user.get("role") or "") not in {"editor", "admin"}:
            continue
        uid = int(user["user_id"])
        label = str(user.get("display_name") or user.get("email") or uid)
        editors.append({"value": str(uid), "label": label})
    editors.sort(key=lambda item: item["label"].casefold())

    auth_user = current_user() or {}
    is_admin = str(auth_user.get("role") or "") == "admin"
    return editors, editor_name, editor_id, is_admin


def _timeline_from_structure(work_dir: Path) -> dict[str, Any] | None:
    path = Path(work_dir) / "structure_analysis.json"
    if not path.is_file():
        return None
    try:
        structure = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

    raw = list(structure.get("beat_timeline", []) or [])
    if len(raw) < 2:
        return None

    tempo = float(structure.get("tempo", 0.0) or 0.0)
    starts = [float(item.get("time", 0.0) or 0.0) for item in raw]
    intervals = [b - a for a, b in zip(starts[:-1], starts[1:]) if b > a]
    if tempo <= 1.0 and intervals:
        ordered = sorted(intervals)
        tempo = 60.0 / ordered[len(ordered) // 2]
    if tempo <= 1.0:
        return None

    beats: list[dict[str, Any]] = []
    default_interval = 60.0 / tempo
    for index, item in enumerate(raw):
        start = float(item.get("time", 0.0) or 0.0)
        end = (
            float(raw[index + 1].get("time", start + default_interval) or start + default_interval)
            if index + 1 < len(raw)
            else start + default_interval
        )
        chord = str(item.get("chord", ".") or ".").strip() or "."
        if chord.upper() in {"N", "NC", "N.C."}:
            chord = "."
        beats.append(
            {
                "index": index,
                "start": start,
                "end": max(start + 0.001, end),
                "chord": chord,
            }
        )

    meter = dict(structure.get("meter", {}) or {})
    detected = str(structure.get("signature") or meter.get("signature") or "").strip()
    if not detected:
        return None

    return {
        "version": "structure-analysis-bridge",
        "timebase": "original_audio_seconds",
        "tempo": tempo,
        "detected_signature": detected,
        "meter_detection": {"signature": detected, "confidence": 1.0, "engine": "structure-cache"},
        "beats": beats,
        "analysis_engines": dict(structure.get("analysis_engines", {}) or {}),
    }



def _timeline_from_persisted_analysis(audio_hash: str) -> dict[str, Any] | None:
    """Bridge the already persisted EZScore analysis into the Riffstation view.

    This is a pure read of the canonical persisted analysis.  It prevents an
    already analysed song from launching a second madmom/lv-chordia analysis
    merely because the newer Step-1 cache file does not exist yet.
    """
    payload = load_latest_persisted_analysis(audio_hash)
    if not payload:
        return None

    music = dict(payload.get("musique", {}) or {})
    raw_beats = list(music.get("beats", []) or [])
    detected = str(music.get("signature", "") or "").strip()
    tempo = float(music.get("tempo", 0.0) or 0.0)

    if len(raw_beats) < 2 or not detected:
        return None

    beats: list[dict[str, Any]] = []
    for index, item in enumerate(raw_beats):
        start = float(item.get("temps", item.get("start", 0.0)) or 0.0)
        end = float(item.get("fin", item.get("end", start)) or start)
        if end <= start:
            if index + 1 < len(raw_beats):
                end = float(
                    raw_beats[index + 1].get(
                        "temps",
                        raw_beats[index + 1].get("start", start),
                    )
                    or start
                )
            if end <= start and tempo > 1.0:
                end = start + 60.0 / tempo
        chord = str(item.get("accord", item.get("chord", ".")) or ".").strip() or "."
        if chord.upper() in {"N", "NC", "N.C."}:
            chord = "."
        beats.append(
            {
                "index": int(item.get("index", index) or index),
                "start": start,
                "end": max(start + 0.001, end),
                "chord": chord,
            }
        )

    if tempo <= 1.0:
        intervals = [
            b["start"] - a["start"]
            for a, b in zip(beats[:-1], beats[1:])
            if b["start"] > a["start"]
        ]
        if intervals:
            ordered = sorted(intervals)
            tempo = 60.0 / ordered[len(ordered) // 2]

    if tempo <= 1.0:
        return None

    return {
        "version": "ezscore-persisted-analysis-bridge-v1",
        "timebase": "original_audio_seconds",
        "tempo": tempo,
        "detected_signature": detected,
        "meter_detection": {
            "signature": detected,
            "confidence": float(
                dict(music.get("signature_auto", {}) or {}).get(
                    "confiance", 1.0
                )
                or 1.0
            ),
            "engine": "ezscore-persisted-analysis",
        },
        "beats": beats,
        "beat_count": len(beats),
        "analysis_engines": {"bridge": "ezscore-persisted-analysis"},
    }

def _load_timeline(
    source: Path,
    stems: dict[str, Path],
    work_dir: Path,
    audio_hash: str,
    *,
    status=None,
) -> dict[str, Any]:
    if status is not None:
        status.write("Recherche de la timeline Step 1 persistée…")
    timeline = load_step1(work_dir)
    if timeline is not None:
        if status is not None:
            status.write("✓ Timeline Riffstation Step 1 chargée depuis le cache.")
        return timeline

    if status is not None:
        status.write("Recherche de la structure musicale persistée…")
    timeline = _timeline_from_structure(work_dir)
    if timeline is not None:
        if status is not None:
            status.write("✓ Timeline chargée depuis structure_analysis.json.")
        return timeline

    if status is not None:
        status.write("Recherche de l'analyse EZScore persistée en base…")
    timeline = _timeline_from_persisted_analysis(audio_hash)
    if timeline is not None:
        if status is not None:
            status.write("✓ Timeline chargée depuis l'analyse EZScore existante.")
        return timeline

    drums = stems.get("drums")
    if drums is None or not Path(drums).is_file():
        raise RuntimeError("Step 1 impossible : stem Batterie absent.")

    # Only a genuinely new/unanalysed song reaches this point.
    if status is not None:
        status.write(
            "Aucune timeline persistée : calcul HQ Step 1 en cours "
            "(beats, time signature, accords)."
        )
        status.write(
            "Cette étape peut durer : madmom-infer puis lv-chordia analysent "
            "le morceau avant l'affichage du conducteur."
        )
        # Give Streamlit a short flush window so the user sees the status before
        # the synchronous native inference occupies the Python thread.
        import time as _time
        _time.sleep(0.20)
    return analyze_step1(
        source=Path(source),
        drums_path=Path(drums),
        work_dir=Path(work_dir),
        force=False,
    )


def _display_beats(raw: list[dict[str, Any]], capo: int) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for index, beat in enumerate(raw):
        item = dict(beat)
        item["index"] = int(item.get("index", index) or index)
        real = str(item.get("chord", ".") or ".").strip() or "."
        item["real_chord"] = real
        item["chord"] = accord_forme_capo(real, capo)
        result.append(item)
    return result


def _build_diagrams(audio_hash: str, beats: list[dict[str, Any]]) -> dict[str, str]:
    saved = load_voicings(audio_hash)
    diagrams: dict[str, str] = {}
    for beat in beats:
        symbol = str(beat.get("chord", "") or "").strip()
        if not symbol or symbol in {".", "-", "?", "^"} or symbol in diagrams:
            continue
        candidates = [symbol]
        if "/" in symbol:
            base = symbol.split("/", 1)[0].strip()
            if base and base not in candidates:
                candidates.append(base)
        for candidate in candidates:
            available = guitar_choices(candidate)
            if not available:
                continue
            selected_name = saved.get(symbol) or saved.get(candidate) or available[0].name
            voicing = get_voicing(candidate, selected_name)
            if voicing is None:
                continue
            diagrams[symbol] = guitar_svg(symbol, voicing, width=92, height=118)
            break
    return diagrams


def _pack_tracks(source: Path, stems: dict[str, Path], preview_dir: Path, key: str) -> list[dict[str, Any]]:
    previews = prepare_browser_previews(source, stems, preview_dir)
    tracks: list[dict[str, Any]] = []

    def add(name: str, label: str, enabled: bool, volume: float) -> None:
        if name == "original":
            path = source
        else:
            path = stems.get(name)
            if path is None:
                return
        preview = previews.get(name)
        if preview is None:
            return
        tracks.append(
            {
                "name": name,
                "label": label,
                "url": register_media_url(
                    preview,
                    coordinates=f"{key}:riff:{name}",
                    mimetype="audio/mpeg",
                ),
                "enabled": bool(enabled),
                "volume": float(volume),
                "low": 0.0,
                "mid": 0.0,
                "high": 0.0,
            }
        )

    add("original", "Original", True, 0.78)
    labels = {
        "vocals": "Voix",
        "drums": "Batterie",
        "bass": "Basse",
        "guitar": "Guitare",
        "piano": "Piano",
        "other": "Other",
        "lead_vocals": "Chant principal",
        "backing_vocals": "Chœurs",
    }
    defaults = {
        "vocals": (True, 0.82),
        "drums": (False, 0.72),
        "bass": (False, 0.72),
        "guitar": (False, 0.72),
        "piano": (False, 0.72),
        "other": (False, 0.72),
        "lead_vocals": (False, 0.82),
        "backing_vocals": (False, 0.72),
    }
    ordered = list(STEM_NAMES) + ["lead_vocals", "backing_vocals"]
    seen: set[str] = set()
    for name in ordered:
        if name in seen:
            continue
        seen.add(name)
        if name not in stems:
            continue
        enabled, volume = defaults.get(name, (False, 0.72))
        add(name, labels.get(name, name), enabled, volume)
    return tracks


def _persist_header(
    *,
    audio_hash: str,
    song: dict[str, Any],
    editor_name: str,
    editor_id: int | None,
    is_admin: bool,
    stored_settings: dict[str, Any],
    payload_text: str,
) -> bool:
    try:
        payload = dict(json.loads(payload_text or "{}") or {})
    except Exception:
        return False
    token = str(payload.get("token", "") or "")
    if not token:
        return False
    token_key = f"_riff_header_token_{audio_hash[:12]}"
    if token == str(st.session_state.get(token_key, "") or ""):
        return False

    title = str(payload.get("title", song.get("title", "")) or "").strip()
    artist = str(payload.get("artist", song.get("artist", "")) or "").strip()
    strum = str(payload.get("strumming_primary", song.get("strumming_primary", "")) or "").strip()
    strum_alt = str(payload.get("strumming_secondary", song.get("strumming_secondary", "")) or "").strip()

    new_editor_id = editor_id
    new_editor_name = editor_name
    if is_admin:
        raw_editor = str(payload.get("editor_user_id", "") or "").strip()
        new_editor_id = int(raw_editor) if raw_editor.isdigit() else None
        by_id = {
            int(user["user_id"]): str(user.get("display_name") or user.get("email") or "")
            for user in list_users()
            if bool(user.get("active")) and str(user.get("role") or "") in {"editor", "admin"}
        }
        new_editor_name = by_id.get(new_editor_id, "") if new_editor_id is not None else ""

    update_song_metadata(
        audio_hash,
        title,
        artist,
        new_editor_name,
        strum,
        strum_alt,
    )
    if is_admin:
        assign_song_editor(audio_hash, new_editor_id, new_editor_name)

    signature_mode = str(payload.get("signature_mode", stored_settings.get("signature_mode", "Auto")) or "Auto").strip()
    if signature_mode not in _SIGNATURE_OPTIONS:
        signature_mode = "Auto"
    capo = max(0, min(12, int(payload.get("capo", 0) or 0)))
    new_settings = dict(stored_settings)
    new_settings["signature_mode"] = signature_mode
    save_song_preferences(audio_hash=audio_hash, capo=capo, settings=new_settings)
    st.session_state["_pending_song_preferences"] = {
        "capo": capo,
        "settings": new_settings,
    }

    st.session_state[token_key] = token
    return True


def render_player(
    source,
    stems,
    *,
    preview_dir,
    key: str,
    words=None,
) -> None:
    source = Path(source)
    preview_dir = Path(preview_dir)
    work_dir = preview_dir.parent
    audio_hash = work_dir.name
    stems = {name: Path(path) for name, path in dict(stems).items()}

    step_key = f"ezstem_analysis_step_{audio_hash[:12]}"
    active_step = str(st.session_state.get(step_key, "1 · STEMS") or "1 · STEMS")
    lyrics_enabled = active_step.startswith("2")
    active_step_token = "2" if lyrics_enabled else "1"
    visible_words = list(words or []) if lyrics_enabled else []

    with st.status("Préparation de la timeline musicale…", expanded=True) as timeline_status:
        try:
            timeline = _load_timeline(
                source,
                stems,
                work_dir,
                audio_hash,
                status=timeline_status,
            )
        except Exception as exc:
            timeline_status.update(
                label="Timeline musicale indisponible.",
                state="error",
                expanded=True,
            )
            st.error(
                f"Timeline musicale Step 1 indisponible : "
                f"{type(exc).__name__}: {exc}"
            )
            return
        timeline_status.update(
            label="Timeline musicale prête.",
            state="complete",
            expanded=False,
        )

    detected = str(timeline.get("detected_signature", "") or "").strip()
    prefs = load_song_preferences(audio_hash) or {}
    stored_settings = dict(prefs.get("settings", {}) or {})
    selected_mode = str(stored_settings.get("signature_mode", "Auto") or "Auto").strip()
    capo = max(0, min(12, int(prefs.get("capo", 0) or 0)))

    try:
        effective = effective_signature(selected=selected_mode, detected=detected)
        beats_per_measure = timeline_beats_per_measure(effective)
    except Exception as exc:
        st.error(f"Time signature indisponible : {exc}")
        return

    display_beats = _display_beats(list(timeline.get("beats", []) or []), capo)
    if not display_beats:
        st.error("Timeline musicale Step 1 vide.")
        return

    song = _song(audio_hash)
    editors, editor_name, editor_id, is_admin = _editor_context(audio_hash, song)
    current = current_user() or {}
    header_readonly = str(current.get("role") or "") not in {"editor", "admin"}

    try:
        show_diagrams = bool(load_show_diagrams(audio_hash))
    except Exception:
        show_diagrams = False

    tracks = _pack_tracks(source, stems, preview_dir, key)
    diagrams = _build_diagrams(audio_hash, display_beats)
    duration = duration_seconds(source)
    if duration <= 0.0:
        duration = max(float(item.get("end", item.get("start", 0.0)) or 0.0) for item in display_beats)

    signature_label = effective if selected_mode != "Auto" else f"Auto · {effective}"
    initial_header = json.dumps(
        {
            "title": str(song.get("title", "") or ""),
            "artist": str(song.get("artist", "") or ""),
            "editor_user_id": "" if editor_id is None else str(editor_id),
            "signature_mode": selected_mode,
            "capo": capo,
            "strumming_primary": str(song.get("strumming_primary", "") or ""),
            "strumming_secondary": str(song.get("strumming_secondary", "") or ""),
            "token": "",
        },
        ensure_ascii=False,
        sort_keys=True,
    )

    result = _COMPONENT(
        data={
            "tracks": tracks,
            "beats": display_beats,
            "words": visible_words,
            "chord_diagrams": diagrams,
            "show_diagrams": show_diagrams,
            "duration_hint": duration,
            "beat_spacing": 112,
            "beats_per_measure": beats_per_measure,
            "step_label": "Step 2 · Paroles" if lyrics_enabled else "Step 1 · STEMS",
            "active_step": active_step_token,
            "song_title": str(song.get("title", "") or source.stem),
            "song_artist": str(song.get("artist", "") or ""),
            "song_editor": editor_name,
            "editor_user_id": "" if editor_id is None else str(editor_id),
            "editors": editors,
            "editor_selectable": bool(is_admin and not header_readonly),
            "header_readonly": bool(header_readonly),
            "signature_options": _SIGNATURE_OPTIONS,
            "signature_mode": selected_mode,
            "signature_label": signature_label,
            "detected_signature": detected,
            "capo": capo,
            "strumming_primary": str(song.get("strumming_primary", "") or ""),
            "strumming_secondary": str(song.get("strumming_secondary", "") or ""),
        },
        default={
            "header_payload": initial_header,
            "show_diagrams": show_diagrams,
            "step_request": "",
        },
        # Stable component instance. Step navigation is edge-triggered through
        # a tokenised request so stale component state can never re-activate
        # the previous tab on the next Streamlit rerun.
        key=f"riffstation_r13_{audio_hash[:12]}_{effective.replace('/', '_')}_capo{capo}",
        on_header_payload_change=lambda: None,
        on_show_diagrams_change=lambda: None,
        on_step_request_change=lambda: None,
        width="stretch",
        height=980 if lyrics_enabled else 900,
    )


    request_text = str(getattr(result, "step_request", "") or "").strip()
    if request_text:
        try:
            request = dict(json.loads(request_text) or {})
        except Exception:
            request = {}
        requested_step = str(request.get("step", "") or "")
        request_token = str(request.get("token", "") or "")
        consumed_key = f"_riff_step_request_{audio_hash[:12]}"
        consumed_token = str(st.session_state.get(consumed_key, "") or "")
        if (
            request_token
            and request_token != consumed_token
            and requested_step in {"1", "2"}
        ):
            st.session_state[consumed_key] = request_token
            target = "2 · PAROLES" if requested_step == "2" else "1 · STEMS"
            if target != active_step:
                st.session_state[step_key] = target
                st.rerun()

    payload_text = str(getattr(result, "header_payload", initial_header) or initial_header)
    if payload_text != initial_header:
        if _persist_header(
            audio_hash=audio_hash,
            song=song,
            editor_name=editor_name,
            editor_id=editor_id,
            is_admin=is_admin,
            stored_settings=stored_settings,
            payload_text=payload_text,
        ):
            st.rerun()

    current_show = bool(getattr(result, "show_diagrams", show_diagrams))
    if current_show != show_diagrams:
        save_show_diagrams(audio_hash, current_show)
