"""Integration of the canonical choir analyzer into EZScore Analyse + Player.

Rules:
- Analyse owns computation and persistence.
- Player reads choir_analysis.json only.
- Lead analysis is untouched.
- No fallback to whisper_vocals_small.json / whisper_backing_small.json.
- No choir inference is performed in the player.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit as st

from ezscore.analysis.choirs import (
    analyze_choirs,
    choir_analysis_is_current,
    load_choir_analysis,
)
from ezscore.analysis.vocal_stems import vocal_stem_paths
from ezscore.player.choir_vocalises import refine_backing_words_for_display


def _artifact_words(audio_hash: str) -> list[dict[str, Any]]:
    payload = load_choir_analysis(audio_hash) or {}
    return list(payload.get("words", []) or [])


def _analysis_ready(stem_lab, audio_hash: str) -> bool:
    speech_path = stem_lab._speech_cache_path(audio_hash)
    if not speech_path.is_file():
        return False

    backing = vocal_stem_paths(audio_hash).get("backing_vocals")
    return bool(backing and Path(backing).is_file())


def _ensure_analysis(stem_lab, audio_hash: str) -> None:
    if not _analysis_ready(stem_lab, audio_hash):
        return
    if choir_analysis_is_current(audio_hash):
        return

    with st.spinner("Analyse Chœurs dédiée…"):
        analyze_choirs(audio_hash=audio_hash, force=False)


def _display_words(audio_hash: str) -> list[dict[str, Any]]:
    """Canonical artifact + presentation-only acoustic vocalise refinement."""
    words = _artifact_words(audio_hash)
    backing = vocal_stem_paths(audio_hash).get("backing_vocals")
    if not backing:
        return words

    try:
        return refine_backing_words_for_display(
            words,
            Path(backing),
            audio_hash=audio_hash,
            source="choir_analysis.json",
        )
    except Exception:
        # Canonical analysis artifact is always the safe fallback.
        return words


def install(stem_lab) -> None:
    """Install one modular Analyse hook and one read-only Player bridge."""
    from ezscore.player import karaoke_stem_webaudio as base
    from ezscore.player import karaoke_stem_webaudio_r12c as r12c

    original_render = stem_lab.render_stem_lab_fresh_analysis

    if not getattr(original_render, "_ezscore_choir_pipeline", False):
        def render_with_choir_analysis(audio_hash: str) -> None:
            try:
                _ensure_analysis(stem_lab, audio_hash)
            except Exception as exc:
                st.error("Analyse Chœurs indisponible : " + str(exc))
            original_render(audio_hash)

        render_with_choir_analysis._ezscore_choir_pipeline = True
        stem_lab.render_stem_lab_fresh_analysis = render_with_choir_analysis

    def lead_words_passthrough(source, stems, preview_dir, original_words):
        return list(original_words or [])

    def choir_words_from_artifact(stems, preview_dir, lead_words, player_words):
        audio_hash = Path(preview_dir).parent.name
        return _display_words(audio_hash)

    def no_supplement_words(original_words, merged_words):
        return []

    base._ensure_vocal_whisper_supplement = lead_words_passthrough
    base._derive_choir_words_from_vocals = choir_words_from_artifact
    base._supplement_only_words = no_supplement_words

    def canonical_component(*, data: dict[str, Any], **kwargs):
        payload = dict(data or {})
        storage_key = str(payload.get("storage_key", "") or "")
        audio_hash = str(
            r12c._AUDIO_HASH_BY_STORAGE_KEY.get(storage_key, "") or ""
        )

        payload["media_duration"] = float(
            r12c._MEDIA_DURATION_BY_STORAGE_KEY.get(storage_key, 0.0) or 0.0
        )
        payload["backing_words"] = (
            _display_words(audio_hash) if audio_hash else []
        )
        payload["backing_word_count"] = len(
            list(payload.get("backing_words", []) or [])
        )

        if audio_hash:
            beats = list(payload.get("beats", []) or [])
            try:
                payload["chord_diagrams"] = r12c._build_chord_diagrams(
                    audio_hash,
                    beats,
                )
            except Exception:
                payload["chord_diagrams"] = {}

            try:
                payload["show_diagrams_default"] = bool(
                    r12c.load_show_diagrams(audio_hash)
                )
            except Exception:
                payload["show_diagrams_default"] = False
        else:
            payload["chord_diagrams"] = {}
            payload["show_diagrams_default"] = False

        return r12c._COMPONENT_R12C(data=payload, **kwargs)

    base._COMPONENT = canonical_component
