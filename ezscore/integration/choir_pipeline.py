"""Canonical choir integration for EZScore.

Analyse owns computation. Player is a read-only projection of the one timeline.

Cache-coherence invariant:
no choir/conductor projection is exposed unless the current canonical lead
transcript is complete and every derived choir artifact matches it.
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
from ezscore.analysis.choir_timeline import (
    align_choir_timeline,
    timeline_alignment_is_current,
)
from ezscore.analysis.vocal_stems import vocal_stem_paths


def _speech_ready(stem_lab, audio_hash: str) -> bool:
    try:
        from ezscore.integration.language_pipeline import (
            speech_cache_is_current,
        )
        return bool(speech_cache_is_current(stem_lab, audio_hash))
    except Exception:
        return False


def _artifact_words(
    audio_hash: str,
    *,
    stem_lab=None,
) -> list[dict[str, Any]]:
    if stem_lab is not None and not _speech_ready(stem_lab, audio_hash):
        return []
    if not choir_analysis_is_current(audio_hash):
        return []
    if not timeline_alignment_is_current(audio_hash):
        return []

    payload = load_choir_analysis(audio_hash) or {}
    return list(payload.get("words", []) or [])


def _analysis_ready(stem_lab, audio_hash: str) -> bool:
    # A file merely existing is not enough.  It must satisfy the canonical
    # speech schema/policy/status contract.
    if not _speech_ready(stem_lab, audio_hash):
        return False

    backing = vocal_stem_paths(audio_hash).get("backing_vocals")
    return bool(backing and Path(backing).is_file())


def _ensure_analysis(stem_lab, audio_hash: str) -> None:
    if not _analysis_ready(stem_lab, audio_hash):
        return

    if not choir_analysis_is_current(audio_hash):
        with st.spinner("Analyse Chœurs dédiée…"):
            analyze_choirs(audio_hash=audio_hash, force=False)

    if not timeline_alignment_is_current(audio_hash):
        with st.spinner("Timeline Chœurs / contre-chant…"):
            align_choir_timeline(audio_hash, force=True)


def install(stem_lab) -> None:
    from ezscore.integration.language_pipeline import (
        install as install_language_pipeline,
    )
    install_language_pipeline(stem_lab)

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

    # Prevent the enriched karaoke/conductor player from mounting at all while
    # the canonical master transcript is absent/stale/incomplete.
    original_base_render = base.render_player
    if not getattr(original_base_render, "_ezscore_canonical_cache_guard", False):
        def guarded_base_render(
            source,
            stems,
            *,
            preview_dir,
            key,
            words=None,
        ):
            audio_hash = Path(preview_dir).parent.name

            if not _speech_ready(stem_lab, audio_hash):
                st.info(
                    "Analyse des paroles requise. "
                    "Le conducteur Chant / Chœurs / Accords n'est affiché "
                    "qu'après validation complète de la transcription canonique."
                )
                if st.button(
                    "Analyser les paroles maintenant",
                    type="primary",
                    width="stretch",
                    key=f"{key}_canonical_lyrics",
                ):
                    with st.spinner("Analyse canonique des paroles…"):
                        stem_lab._transcribe_original(
                            Path(source),
                            audio_hash,
                        )
                    st.rerun()
                return None

            return original_base_render(
                source,
                stems,
                preview_dir=preview_dir,
                key=key,
                words=words,
            )

        guarded_base_render._ezscore_canonical_cache_guard = True
        base.render_player = guarded_base_render

    def lead_words_passthrough(source, stems, preview_dir, original_words):
        audio_hash = Path(preview_dir).parent.name
        if not _speech_ready(stem_lab, audio_hash):
            return []
        return list(original_words or [])

    def choir_words_from_artifact(stems, preview_dir, lead_words, player_words):
        audio_hash = Path(preview_dir).parent.name
        return _artifact_words(audio_hash, stem_lab=stem_lab)

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

        if audio_hash and not _speech_ready(stem_lab, audio_hash):
            payload["words"] = []
            payload["lead_words"] = []
            payload["backing_words"] = []
            payload["backing_word_count"] = 0
            payload["beats"] = []
            payload["chord_diagrams"] = {}
            payload["show_diagrams_default"] = False
            return r12c._COMPONENT_R12C(data=payload, **kwargs)

        payload["media_duration"] = float(
            r12c._MEDIA_DURATION_BY_STORAGE_KEY.get(storage_key, 0.0) or 0.0
        )
        payload["backing_words"] = (
            _artifact_words(audio_hash, stem_lab=stem_lab)
            if audio_hash else []
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
