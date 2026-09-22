from __future__ import annotations

"""Restored R5.10 chords + lyrics editor surface for Analyse.

This is deliberately a dedicated module. It reuses the exact validated R5.10
component/templates already present in the repository:
- Sections
- Accords
- Chant
- Chœurs
- word editing
- chord editing
- section anchors
- long-click line-break insertion
- line-break drag/delete
- one shared horizontal timeline / scrollbar

No audio engine is created here.
"""

import json
from pathlib import Path
from typing import Any

import streamlit as st

from ezscore.ui import lyrics_inline_editor as legacy
from ezscore.ui.editorial_timeline import (
    empty_payload,
    load as load_editorial,
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
    """Load the saved overlay without allowing a stale fingerprint to crash Analyse.

    The old file is never deleted or rewritten automatically. If the technical
    timeline changed after a reanalysis, the editor opens on a clean overlay and
    reports the mismatch. A later explicit Save is the only operation that may
    replace the editorial overlay.
    """
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


def render_chords_lyrics_editor(
    *,
    stem_module,
    audio_hash: str,
) -> None:
    speech = stem_module._load_speech(audio_hash)
    if speech is None:
        st.info("Transcription Whisper absente.")
        return

    lead_raw = list(speech.get("words", []) or [])
    lead = normalize_words(lead_raw)
    backing = legacy._load_backing_words(
        stem_module,
        audio_hash,
        lead_raw,
    )
    beats, detected_meter, meter_source = legacy._load_timing(
        stem_module,
        audio_hash,
    )

    if not beats:
        st.error(
            "Timeline de beats absente : l'éditeur synchronisé ne peut pas "
            "être affiché correctement. Aucun faux alignement n'est généré."
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
        "Éditeur visuel R5.10 : Sections / Accords / Chant · "
        "double-clic = modifier · clic long sur un mot = insérer ↵ · "
        "une seule timeline et une seule scrollbar. Aucun moteur audio ici."
    )
