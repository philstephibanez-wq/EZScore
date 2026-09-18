from __future__ import annotations

"""Canonical re-analysis actions for the Analyse surface only.

This module deliberately does not touch the player or editorial overlays.
It invokes the existing canonical Analyse pipeline and persists its artifacts.
"""

from pathlib import Path

import streamlit as st


def _work_dir(stem_module, audio_hash: str) -> Path:
    return Path(stem_module._work_dir(audio_hash))


def _meter_for_reanalysis(stem_module, audio_hash: str) -> dict:
    structure = stem_module._load_structure(audio_hash) or {}
    meter = dict(structure.get("meter", {}) or {})

    signature = str(
        meter.get("signature")
        or structure.get("signature")
        or "4/4"
    )
    grouping = str(meter.get("grouping", "") or "")

    return dict(stem_module._meter_spec(signature, grouping))


def _unlink_if_exists(path: Path) -> None:
    try:
        if path.is_file():
            path.unlink()
    except OSError:
        pass


def reanalyze_lyrics(stem_module, audio_hash: str) -> None:
    song = stem_module._song_for_hash(audio_hash)
    source = stem_module._source_path(audio_hash, song)
    if source is None or not Path(source).is_file():
        raise RuntimeError("Audio original introuvable.")

    work_dir = _work_dir(stem_module, audio_hash)

    # Only lyrics truth is invalidated here.
    _unlink_if_exists(work_dir / "whisper_original_small.json")
    _unlink_if_exists(work_dir / "whisper_vocals_small.json")

    stem_module._transcribe_original(Path(source), audio_hash)


def reanalyze_chords(stem_module, audio_hash: str) -> None:
    if not stem_module.stems_cache_complete(audio_hash):
        raise RuntimeError("Les STEM doivent être disponibles avant l'analyse accords.")

    work_dir = _work_dir(stem_module, audio_hash)
    meter = _meter_for_reanalysis(stem_module, audio_hash)

    # Invalidate canonical harmony/structure only.
    _unlink_if_exists(work_dir / "chord_analysis_lv_chordia.json")
    _unlink_if_exists(work_dir / "structure_analysis.json")

    # Legacy player-derived cache is removed because it must never become a
    # competing technical source of truth again.
    _unlink_if_exists(work_dir / "karaoke_conductor.json")

    stem_module._analyze_structure(
        audio_hash=audio_hash,
        stems=stem_module.cached_stem_paths(audio_hash),
        meter=meter,
    )
    stem_module._invalidate_metric_midi(audio_hash)


def reanalyze_all(stem_module, audio_hash: str) -> None:
    """Recompute lyrics + rhythm/harmony from existing audio/STEMs.

    This is NOT "Réanalyse complète" (which purges STEMs and all analysis).
    It is the historical quick Analyse action, but now located in the correct
    responsibility layer.
    """
    reanalyze_lyrics(stem_module, audio_hash)
    reanalyze_chords(stem_module, audio_hash)


def render(stem_module, audio_hash: str) -> None:
    """Render re-analysis commands on the Analyse page, never in the player."""
    work_dir = _work_dir(stem_module, audio_hash)

    from ezscore.analysis.technical_snapshot import status

    state = status(work_dir)

    st.markdown("### 🔄 Réanalyse technique")
    st.caption(
        "Ces actions appartiennent à Analyse. Le player STEM reste strictement "
        "en lecture seule et relit les artefacts persistés après recalcul."
    )

    cols = st.columns(3)

    with cols[0]:
        if st.button(
            "↻ Ré-analyser paroles",
            width="stretch",
            key=f"analysis_relyrics_{audio_hash[:12]}",
        ):
            with st.spinner("Whisper small sur l'audio original…"):
                reanalyze_lyrics(stem_module, audio_hash)
            st.rerun()

    with cols[1]:
        if st.button(
            "↻ Ré-analyser accords",
            width="stretch",
            key=f"analysis_rechords_{audio_hash[:12]}",
            disabled=not stem_module.stems_cache_complete(audio_hash),
        ):
            with st.spinner("Rythme + harmonie HQ…"):
                reanalyze_chords(stem_module, audio_hash)
            st.rerun()

    with cols[2]:
        if st.button(
            "↻ Ré-analyser tout",
            type="primary",
            width="stretch",
            key=f"analysis_reall_{audio_hash[:12]}",
            disabled=not stem_module.stems_cache_complete(audio_hash),
        ):
            with st.spinner("Paroles + rythme + accords…"):
                reanalyze_all(stem_module, audio_hash)
            st.rerun()

    st.caption(
        "État technique : "
        f"{state['word_count']} mots · "
        f"{state['beat_count']} beats · "
        f"{state['chord_count']} positions d'accord."
    )


def install(stem_module) -> None:
    original_render = stem_module.render_stem_lab_fresh_analysis

    if getattr(
        original_render,
        "_ezscore_analysis_reanalysis_controls",
        False,
    ):
        return

    def render_with_analysis_actions(audio_hash: str) -> None:
        # Commands are intentionally outside the player and inside Analyse.
        render(stem_module, audio_hash)
        original_render(audio_hash)

    render_with_analysis_actions._ezscore_analysis_reanalysis_controls = True
    stem_module.render_stem_lab_fresh_analysis = render_with_analysis_actions
