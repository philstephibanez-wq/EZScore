"""Silent inline timeline editor for EZScore > Analyse > Paroles.

The browser component contains no audio/media/WebAudio code. It only renders
and edits the shared visual timeline.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import streamlit as st

from ezscore.player import karaoke_stem_webaudio as _karaoke_base
from ezscore.ui.editorial_timeline import (
    load as load_editorial,
    normalize_beats,
    normalize_words,
    save as save_editorial,
)

_PATCH_INSTALLED = False
_TEMPLATE_DIR = Path(__file__).resolve().parents[2] / "templates" / "views"


def _template(name: str) -> str:
    path = _TEMPLATE_DIR / name
    if not path.is_file():
        raise RuntimeError(f"Template EZScore manquant : {path}")
    return path.read_text(encoding="utf-8")


_COMPONENT = st.components.v2.component(
    "ezscore_inline_timeline_editor_r5",
    html=_template("lyrics-editor.html"),
    css=_template("lyrics-editor.css"),
    js=_template("lyrics-editor.js"),
    isolate_styles=True,
)


def _load_backing_words(
    stem_module,
    audio_hash: str,
    lead_raw: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    path = stem_module._work_dir(audio_hash) / "whisper_vocals_small.json"
    if not path.is_file():
        return []

    try:
        vocal_payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError(f"Impossible de lire {path.name}: {exc}") from exc

    merged = _karaoke_base._merge_vocal_gap_words(
        list(lead_raw),
        list(vocal_payload.get("words", []) or []),
    )
    supplement = _karaoke_base._supplement_only_words(
        list(lead_raw),
        merged,
    )
    return normalize_words(supplement)


def _coerce_time_signature(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, str):
        match = re.search(r"\b([1-9][0-9]?)/(1|2|4|8|16|32)\b", value)
        return f"{match.group(1)}/{match.group(2)}" if match else ""

    if isinstance(value, (list, tuple)) and len(value) >= 2:
        try:
            numerator = int(value[0])
            denominator = int(value[1])
        except (TypeError, ValueError):
            return ""
        if 1 <= numerator <= 99 and denominator in {1, 2, 4, 8, 16, 32}:
            return f"{numerator}/{denominator}"
        return ""

    if isinstance(value, dict):
        numerator = (
            value.get("numerator")
            or value.get("beats_per_bar")
            or value.get("beats_per_measure")
            or value.get("beats")
        )
        denominator = (
            value.get("denominator")
            or value.get("beat_unit")
            or value.get("unit")
        )
        if numerator is not None and denominator is not None:
            return _coerce_time_signature([numerator, denominator])

    return ""


def _find_time_signature(payload: Any) -> str:
    if not isinstance(payload, dict):
        return ""

    priority_keys = (
        "time_signature",
        "timeSignature",
        "detected_time_signature",
        "detectedTimeSignature",
        "meter",
        "metre",
        "signature",
    )

    for key in priority_keys:
        if key in payload:
            meter = _coerce_time_signature(payload.get(key))
            if meter:
                return meter

    beats_per_bar = payload.get("beats_per_bar", payload.get("beats_per_measure"))
    beat_unit = payload.get("beat_unit", payload.get("denominator"))
    if beats_per_bar is not None and beat_unit is not None:
        meter = _coerce_time_signature([beats_per_bar, beat_unit])
        if meter:
            return meter

    for value in payload.values():
        if isinstance(value, dict):
            meter = _find_time_signature(value)
            if meter:
                return meter

    return ""


def _load_timing(
    stem_module,
    audio_hash: str,
) -> tuple[list[dict[str, Any]], str, str]:
    structure = stem_module._load_structure(audio_hash)
    detected_meter = _find_time_signature(structure)
    meter_source = "detected" if detected_meter else ""

    if structure:
        source = (
            list(structure.get("beat_timeline", []) or [])
            or list(structure.get("beats", []) or [])
        )
        if source:
            return (
                normalize_beats(source),
                detected_meter or "4/4",
                meter_source or "default",
            )

    conductor_path = (
        stem_module._work_dir(audio_hash)
        / "karaoke_conductor.json"
    )

    if conductor_path.is_file():
        try:
            conductor = json.loads(
                conductor_path.read_text(encoding="utf-8")
            )
        except Exception as exc:
            raise RuntimeError(
                f"Impossible de lire {conductor_path.name}: {exc}"
            ) from exc

        if not detected_meter:
            detected_meter = _find_time_signature(conductor)
            meter_source = "detected" if detected_meter else ""

        source = list(conductor.get("beats", []) or [])
        if source:
            return (
                normalize_beats(source),
                detected_meter or "4/4",
                meter_source or "default",
            )

    return [], detected_meter or "4/4", meter_source or "default"


def _render_editor(
    *,
    stem_module,
    audio_hash: str,
    original_textarea,
    label: str,
    args,
    kwargs,
) -> str:
    speech = stem_module._load_speech(audio_hash)
    if speech is None:
        raise RuntimeError("Transcription Whisper absente.")

    lead_raw = list(speech.get("words", []) or [])
    lead = normalize_words(lead_raw)
    backing = _load_backing_words(
        stem_module,
        audio_hash,
        lead_raw,
    )
    beats, detected_meter, meter_source = _load_timing(stem_module, audio_hash)

    if not beats:
        st.error(
            "Timeline de beats absente : l'éditeur synchronisé ne peut pas "
            "être affiché correctement. Aucun faux alignement n'est généré."
        )
        return original_textarea(label, *args, **kwargs)

    work_dir = stem_module._work_dir(audio_hash)
    persisted = load_editorial(
        work_dir,
        lead,
        backing,
        beats,
    )

    result = _COMPONENT(
        data={
            "lead": lead,
            "backing": backing,
            "beats": beats,
            "detected_meter": detected_meter,
            "meter_source": meter_source,
            "editorial": persisted,
        },
        default={
            "snapshot": json.dumps(
                persisted,
                ensure_ascii=False,
            )
        },
        key=f"ez_inline_timeline_r5_{audio_hash[:12]}",
        on_snapshot_change=lambda: None,
    )

    snapshot = str(getattr(result, "snapshot", "") or "")
    try:
        current = json.loads(snapshot) if snapshot else persisted
    except Exception as exc:
        st.error(f"État éditorial invalide : {exc}")
        current = persisted

    tracked_keys = (
        "lead_overrides",
        "backing_overrides",
        "line_break_after_lead",
        "chord_overrides",
        "time_signature_override",
        "anchors",
    )

    dirty = any(
        current.get(key) != persisted.get(key)
        for key in tracked_keys
    )

    status_col, save_col = st.columns([2.4, 1.0])

    with status_col:
        if dirty:
            st.warning("● Modifications non enregistrées.")
        else:
            st.success("✓ Enregistré.")

    with save_col:
        if st.button(
            "💾 Enregistrer",
            type="primary",
            width="stretch",
            key=f"ez_inline_timeline_save_{audio_hash[:12]}",
        ):
            save_editorial(
                work_dir,
                current,
                lead,
                backing,
                beats,
            )
            st.success("Édition enregistrée.")
            st.rerun()

    st.caption(
        "Cette vue est un éditeur visuel silencieux : aucun son, aucun moteur "
        "audio, aucun changement du player d'analyse."
    )

    return ""


def install(stem_module) -> None:
    global _PATCH_INSTALLED

    if _PATCH_INSTALLED:
        return

    original_render = stem_module.render_stem_lab_fresh_analysis

    def render_with_inline_editor(audio_hash: str) -> None:
        original_textarea = st.text_area

        def patched_text_area(label, *args, **kwargs):
            if str(label) != "Texte transcrit":
                return original_textarea(label, *args, **kwargs)

            return _render_editor(
                stem_module=stem_module,
                audio_hash=audio_hash,
                original_textarea=original_textarea,
                label=label,
                args=args,
                kwargs=kwargs,
            )

        st.text_area = patched_text_area
        try:
            original_render(audio_hash)
        finally:
            st.text_area = original_textarea

    stem_module.render_stem_lab_fresh_analysis = render_with_inline_editor
    _PATCH_INSTALLED = True
