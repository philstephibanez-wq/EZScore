from __future__ import annotations

"""Restored R5.10 chords + lyrics editor surface for Analyse.

R2 timing rule:
- first consume historical/canonical timing via legacy loader;
- if absent, directly load/build technical_timeline.json;
- never depend on monkey-patch installation order;
- never synthesize fake beats.
"""

import json
from pathlib import Path
from typing import Any

import streamlit as st

from ezscore.analysis.technical_timeline import (
    ensure_from_stem_module,
    load as load_technical_timeline,
)
from ezscore.ui import lyrics_inline_editor as legacy
from ezscore.ui.editorial_timeline import (
    empty_payload,
    load as load_editorial,
    normalize_beats,
    normalize_words,
    save as save_editorial,
)


def _safe_editorial(
    *,
    work_dir: Path,
    lead: list[dict[str, Any]],
    backing: list[dict[str, Any]],
    beats: list[dict[str, Any]],
) -> tuple[dict[str, Any], str]:
    try:
        return load_editorial(work_dir, lead, backing, beats), ""
    except RuntimeError as exc:
        message = str(exc)
        if "timeline technique a changé" not in message:
            raise
        return (
            empty_payload(lead, backing, beats),
            (
                "La mise en page éditoriale enregistrée appartient à une ancienne "
                "timeline technique. Elle est conservée sur disque mais n'est pas "
                "appliquée automatiquement à cette nouvelle analyse."
            ),
        )


def _load_editor_timing(
    *,
    stem_module,
    audio_hash: str,
) -> tuple[list[dict[str, Any]], str, str]:
    """Load real timing without relying on installation order."""
    beats, meter, source = legacy._load_timing(
        stem_module,
        audio_hash,
    )
    if beats:
        return beats, meter, source

    work_dir = stem_module._work_dir(audio_hash)
    technical = load_technical_timeline(work_dir)

    if technical is None:
        technical = ensure_from_stem_module(
            stem_module,
            audio_hash,
        )

    raw = list(technical.get("beat_timeline", []) or [])
    if not raw:
        raise RuntimeError(
            "technical_timeline.json ne contient aucun beat canonique."
        )

    normalized = normalize_beats(raw)
    if not normalized:
        raise RuntimeError(
            "La timeline technique existe mais sa normalisation est vide."
        )

    return normalized, meter or "4/4", "technical_timeline"


def render_chords_lyrics_editor(
    *,
    stem_module,
    audio_hash: str,
) -> None:
    speech = stem_module._load_speech(audio_hash)
    if speech is None:
        st.info("Paroles alignées absentes.")
        return

    lead_raw = list(speech.get("words", []) or [])
    lead = normalize_words(lead_raw)
    backing = legacy._load_backing_words(
        stem_module,
        audio_hash,
        lead_raw,
    )

    try:
        beats, detected_meter, meter_source = _load_editor_timing(
            stem_module=stem_module,
            audio_hash=audio_hash,
        )
    except Exception as exc:
        st.error(
            "Timeline beats + accords indisponible : "
            f"{type(exc).__name__}: {exc}"
        )
        st.caption(
            "Aucun beat artificiel n'est créé. "
            "La cause technique exacte est affichée ci-dessus."
        )
        return

    work_dir = stem_module._work_dir(audio_hash)
    persisted, compatibility_warning = _safe_editorial(
        work_dir=work_dir,
        lead=lead,
        backing=backing,
        beats=beats,
    )

    if compatibility_warning:
        st.warning(compatibility_warning)

    result = legacy._COMPONENT(
        data={
            "lead": lead,
            "backing": backing,
            "beats": beats,
            "detected_meter": detected_meter,
            "meter_source": meter_source,
            "analysis_meter_storage_key": (
                "ezscore-karaoke-meter:"
                f"ezstem_player_{audio_hash[:12]}_{len(lead_raw)}"
            ),
            "editorial": persisted,
        },
        default={
            "snapshot": json.dumps(
                persisted,
                ensure_ascii=False,
            )
        },
        key=f"ez_chords_lyrics_editor_r5_{audio_hash[:12]}",
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
            key=f"ez_chords_lyrics_save_{audio_hash[:12]}",
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
        "Éditeur visuel R5.10 · timeline technique canonique · "
        "double-clic = modifier · clic long sur un mot = insérer ↵."
    )
