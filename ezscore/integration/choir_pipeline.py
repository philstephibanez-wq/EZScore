"""Lead-only lyrics integration for EZScore.

Temporary stabilization mode:
- keep lead_vocals.wav and backing_vocals.wav as audio stems;
- transcribe/display lead lyrics only;
- do not analyze, transcribe or render backing/choir lyrics;
- keep one canonical original-audio timeline.

This module keeps its historical name for compatibility with the current
installer in ezscore.ui.__init__.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit as st


LEAD_ONLY_LYRICS = True


def _speech_ready(stem_lab, audio_hash: str) -> bool:
    try:
        from ezscore.integration.language_pipeline import (
            speech_cache_is_current,
        )
        return bool(speech_cache_is_current(stem_lab, audio_hash))
    except Exception:
        return False


def _purge_legacy_choir_text_cache(stem_lab, audio_hash: str) -> None:
    """Delete only text/timeline artifacts for the disabled choir layer.

    Audio stems are intentionally untouched:
        lead_vocals.wav
        backing_vocals.wav
    """
    try:
        work = Path(stem_lab._speech_cache_path(audio_hash)).parent
    except Exception:
        return

    for name in (
        "whisper_vocals_small.json",
        "whisper_backing_small.json",
        "choir_words_from_vocals.json",
        "choir_analysis.json",
    ):
        try:
            (work / name).unlink()
        except FileNotFoundError:
            pass
        except OSError:
            pass


def install(stem_lab) -> None:
    """Install the canonical lead-only lyrics surface."""
    from ezscore.integration.language_pipeline import (
        install as install_language_pipeline,
    )
    install_language_pipeline(stem_lab)

    from ezscore.player import karaoke_stem_webaudio as base
    from ezscore.player import karaoke_stem_webaudio_r12c as r12c

    original_render = stem_lab.render_stem_lab_fresh_analysis

    if not getattr(original_render, "_ezscore_lead_only_lyrics", False):
        def render_lead_only(audio_hash: str) -> None:
            _purge_legacy_choir_text_cache(stem_lab, audio_hash)
            original_render(audio_hash)

        render_lead_only._ezscore_lead_only_lyrics = True
        stem_lab.render_stem_lab_fresh_analysis = render_lead_only

    original_base_render = base.render_player
    if not getattr(
        original_base_render,
        "_ezscore_canonical_cache_guard",
        False,
    ):
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
                    "Le conducteur Accords + Chant n'est affiché "
                    "qu'après validation complète de la transcription "
                    "canonique."
                )
                if st.button(
                    "Analyser les paroles maintenant",
                    type="primary",
                    width="stretch",
                    key=f"{key}_canonical_lyrics",
                ):
                    with st.spinner("Analyse canonique du Chant…"):
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

    def lead_words_passthrough(
        source,
        stems,
        preview_dir,
        original_words,
    ):
        audio_hash = Path(preview_dir).parent.name
        if not _speech_ready(stem_lab, audio_hash):
            return []
        return list(original_words or [])

    def no_choir_words(
        stems,
        preview_dir,
        lead_words,
        player_words,
    ):
        return []

    def no_supplement_words(original_words, merged_words):
        return []

    base._ensure_vocal_whisper_supplement = lead_words_passthrough
    base._derive_choir_words_from_vocals = no_choir_words
    base._supplement_only_words = no_supplement_words

    def lead_only_component(*, data: dict[str, Any], **kwargs):
        payload = dict(data or {})
        storage_key = str(payload.get("storage_key", "") or "")
        audio_hash = str(
            r12c._AUDIO_HASH_BY_STORAGE_KEY.get(storage_key, "") or ""
        )

        payload["media_duration"] = float(
            r12c._MEDIA_DURATION_BY_STORAGE_KEY.get(
                storage_key,
                0.0,
            ) or 0.0
        )

        payload["backing_words"] = []
        payload["backing_word_count"] = 0

        if audio_hash and not _speech_ready(stem_lab, audio_hash):
            payload["words"] = []
            payload["lead_words"] = []
            payload["beats"] = []
            payload["chord_diagrams"] = {}
            payload["show_diagrams_default"] = False
            return r12c._COMPONENT_R12C(
                data=payload,
                **kwargs,
            )

        if audio_hash:
            beats = list(payload.get("beats", []) or [])
            try:
                payload["chord_diagrams"] = (
                    r12c._build_chord_diagrams(
                        audio_hash,
                        beats,
                    )
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

        return r12c._COMPONENT_R12C(
            data=payload,
            **kwargs,
        )

    base._COMPONENT = lead_only_component
