"""Lead-only manual-lyrics integration for EZScore.

Historical module name retained because ezscore.ui.__init__ already installs it.

Active policy:
- audio stems Chant/Chœurs remain available in the mixer;
- Chœurs text analysis is disabled;
- free Whisper lyric transcription is disabled;
- user-supplied lyrics are force-aligned against lead_vocals.wav;
- all resulting timestamps use original-audio seconds.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import streamlit as st

from ezscore.analysis.forced_lyrics import (
    ENGINE as FORCED_ENGINE,
    align_user_lyrics,
    alignment_is_current,
    cache_path as forced_cache_path,
    load_alignment,
    load_draft,
    save_draft,
)
from ezscore.analysis.technical_timeline import (
    ensure as ensure_technical_timeline,
    invalidate as invalidate_technical_timeline,
    load as load_technical_timeline,
)


LEAD_ONLY_LYRICS = True
MANUAL_LYRICS = True


def _speech_ready(stem_lab, audio_hash: str) -> bool:
    return alignment_is_current(audio_hash)


def _legacy_supplement_sentinel(stem_lab, audio_hash: str) -> None:
    """Prevent the old STEM surface from launching Whisper vocals supplement."""
    try:
        work = Path(stem_lab._work_dir(audio_hash))
    except Exception:
        return

    path = work / "whisper_vocals_small.json"
    payload = {
        "engine": "disabled",
        "mode": "manual-lyrics-lead-only",
        "words": [],
    }
    try:
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError:
        pass


def _purge_legacy_choir_text_cache(stem_lab, audio_hash: str) -> None:
    try:
        work = Path(stem_lab._work_dir(audio_hash))
    except Exception:
        return

    for name in (
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

    _legacy_supplement_sentinel(stem_lab, audio_hash)


def _install_manual_lyrics_ui(stem_lab, audio_hash: str, original_render) -> None:
    """Render the existing analysis surface with a targeted Paroles replacement."""
    short_hash = str(audio_hash)[:12]
    text_key = f"ezscore_manual_lyrics_{short_hash}"
    old_payload = load_alignment(audio_hash) or {}

    if text_key not in st.session_state:
        st.session_state[text_key] = (
            load_draft(audio_hash)
            or str(old_payload.get("source_text", "") or "")
        )

    original_caption = st.caption
    original_button = st.button
    original_success = st.success

    def caption_proxy(*args, **kwargs):
        value = str(args[0] if args else "").strip()

        if value.startswith("Whisper small sur l'audio original."):
            original_caption(
                "Texte fourni par l'utilisateur → alignement forcé multilingue "
                "sur le STEM Chant. Aucune transcription libre et aucune "
                "détection de langue audio."
            )

            current_text = st.text_area(
                "Texte exact du chant",
                key=text_key,
                height=300,
                placeholder=(
                    "Collez ici les paroles exactes. "
                    "Conservez les retours à la ligne : ils seront mémorisés."
                ),
            )
            save_draft(audio_hash, current_text)

            aligned_text = str(
                old_payload.get("source_text", "") or ""
            ).strip()
            changed = bool(
                aligned_text
                and current_text.strip()
                and current_text.strip() != aligned_text
            )
            if changed:
                st.warning(
                    "Le texte a été modifié depuis le dernier alignement. "
                    "Relancez l'alignement pour mettre à jour les timestamps."
                )

            try:
                from ezscore.analysis.vocal_stems import vocal_stem_paths
                lead = vocal_stem_paths(audio_hash).get("lead_vocals")
                lead_ready = bool(lead and Path(lead).is_file())
            except Exception:
                lead_ready = False

            label = (
                "Réaligner le texte sur le Chant"
                if old_payload
                else "Aligner le texte sur le Chant"
            )
            if original_button(
                label,
                key=f"ezscore_force_align_{short_hash}",
                type="primary",
                width="stretch",
                disabled=(not current_text.strip() or not lead_ready),
            ):
                try:
                    with st.spinner(
                        "Alignement acoustique du texte sur lead_vocals.wav…"
                    ):
                        align_user_lyrics(audio_hash, current_text)
                except Exception as exc:
                    st.error(f"Alignement des paroles impossible : {exc}")
                else:
                    st.rerun()

            if not lead_ready:
                st.info("Le STEM Chant doit être extrait avant l'alignement.")
            return None

        return original_caption(*args, **kwargs)

    def button_proxy(*args, **kwargs):
        # Suppress the legacy Whisper action.
        key = str(kwargs.get("key", "") or "")
        if key == f"ezstem_speech_{short_hash}":
            return False
        return original_button(*args, **kwargs)

    def success_proxy(*args, **kwargs):
        value = str(args[0] if args else "")
        if value.startswith("✓ Paroles prêtes"):
            payload = load_alignment(audio_hash) or {}
            count = len(list(payload.get("words", []) or []))
            return original_success(
                f"✓ Paroles alignées · {count} mots horodatés · "
                f"moteur `{FORCED_ENGINE}` · texte utilisateur."
            )
        return original_success(*args, **kwargs)

    st.caption = caption_proxy
    st.button = button_proxy
    st.success = success_proxy
    try:
        original_render(audio_hash)
    finally:
        st.caption = original_caption
        st.button = original_button
        st.success = original_success


def install(stem_lab) -> None:
    from ezscore.player import karaoke_stem_webaudio as base
    from ezscore.player import karaoke_stem_webaudio_r12c as r12c
    from ezscore.player.stem_analysis_conductor import (
        render_player as render_stem_analysis_player,
    )

    # Analysis STEM player != final karaoke player.
    stem_lab._render_stem_player = render_stem_analysis_player

    def _ensure_timing(audio_hash: str):
        song = stem_lab._song_for_hash(audio_hash)
        source = stem_lab._source_path(audio_hash, song)
        stems = stem_lab.cached_stem_paths(audio_hash)
        drums = stems.get("drums")
        if source is None or not Path(source).is_file():
            raise RuntimeError("Audio original introuvable pour la timeline technique.")
        if drums is None or not Path(drums).is_file():
            raise RuntimeError("STEM Batterie absent pour la timeline technique.")

        return ensure_technical_timeline(
            work_dir=stem_lab._work_dir(audio_hash),
            source=Path(source),
            drums=Path(drums),
            chord_cache_path=stem_lab._chord_cache_path(audio_hash),
            existing_structure=stem_lab._load_structure(audio_hash),
        )

    # The technical timeline is independent from Step 3 block segmentation.
    from ezscore.ui import lyrics_inline_editor as _lyrics_editor

    _original_load_timing = _lyrics_editor._load_timing

    def _load_timing_with_technical(stem_module, audio_hash: str):
        beats, meter, source = _original_load_timing(
            stem_module,
            audio_hash,
        )
        if beats:
            return beats, meter, source

        technical = load_technical_timeline(
            stem_module._work_dir(audio_hash)
        )
        if technical is None:
            try:
                technical = _ensure_timing(audio_hash)
            except Exception:
                return beats, meter, source

        raw = list(technical.get("beat_timeline", []) or [])
        if not raw:
            return beats, meter, source

        return (
            _lyrics_editor.normalize_beats(raw),
            meter or "4/4",
            "technical_timeline",
        )

    _lyrics_editor._load_timing = _load_timing_with_technical

    # Step 3 now segments blocks from the existing technical timeline instead
    # of rerunning rhythm + harmony.
    def _analyze_blocks_from_timeline(*, audio_hash, stems, meter):
        technical = _ensure_timing(audio_hash)
        return stem_lab._structure_from_beat_timeline(
            audio_hash=audio_hash,
            beat_timeline=list(technical.get("beat_timeline", []) or []),
            tempo=float(technical.get("tempo", 120.0) or 120.0),
            meter=dict(meter),
        )

    stem_lab._analyze_structure = _analyze_blocks_from_timeline

    _original_invalidate_after_stem = stem_lab._invalidate_after_stem_regeneration

    def _invalidate_after_stem(audio_hash: str, *, full: bool):
        _original_invalidate_after_stem(audio_hash, full=full)
        if full:
            invalidate_technical_timeline(stem_lab._work_dir(audio_hash))

    stem_lab._invalidate_after_stem_regeneration = _invalidate_after_stem

    # Canonical speech cache is now forced alignment, not Whisper.
    stem_lab._speech_cache_path = forced_cache_path

    def load_forced(audio_hash: str):
        return load_alignment(audio_hash)

    def align_from_saved_text(source: Path, audio_hash: str):
        text = load_draft(audio_hash)
        if not text.strip():
            raise RuntimeError(
                "Aucun texte utilisateur fourni. "
                "Ouvrez Analyse > Paroles et collez les paroles."
            )
        return align_user_lyrics(audio_hash, text)

    stem_lab._load_speech = load_forced
    stem_lab._transcribe_original = align_from_saved_text

    original_render = stem_lab.render_stem_lab_fresh_analysis
    if not getattr(original_render, "_ezscore_manual_forced_lyrics", False):
        def render_manual(audio_hash: str) -> None:
            _purge_legacy_choir_text_cache(stem_lab, audio_hash)

            if (
                stem_lab._load_speech(audio_hash) is not None
                and stem_lab.stems_cache_complete(audio_hash)
            ):
                technical = load_technical_timeline(
                    stem_lab._work_dir(audio_hash)
                )
                if technical is None:
                    try:
                        with st.spinner(
                            "Construction de la timeline beats + accords…"
                        ):
                            _ensure_timing(audio_hash)
                    except Exception as exc:
                        st.warning(
                            "Timeline technique indisponible : "
                            + str(exc)
                        )

            _install_manual_lyrics_ui(
                stem_lab,
                audio_hash,
                original_render,
            )

        render_manual._ezscore_manual_forced_lyrics = True
        stem_lab.render_stem_lab_fresh_analysis = render_manual

    # No Whisper supplementation and no textual choir lane.
    def lead_words_passthrough(source, stems, preview_dir, original_words):
        return list(original_words or [])

    def no_choir_words(stems, preview_dir, lead_words, player_words):
        return []

    def no_supplement_words(original_words, merged_words):
        return []

    base._ensure_vocal_whisper_supplement = lead_words_passthrough
    base._derive_choir_words_from_vocals = no_choir_words
    base._supplement_only_words = no_supplement_words

    original_base_render = base.render_player
    if not getattr(
        original_base_render,
        "_ezscore_manual_alignment_guard",
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
                    "Paroles non alignées. "
                    "Ouvrez l'onglet Paroles, collez le texte exact du chant "
                    "puis lancez l'alignement."
                )
                return None
            return original_base_render(
                source,
                stems,
                preview_dir=preview_dir,
                key=key,
                words=words,
            )

        guarded_base_render._ezscore_manual_alignment_guard = True
        base.render_player = guarded_base_render

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

        if audio_hash:
            beats = list(payload.get("beats", []) or [])
            try:
                payload["chord_diagrams"] = (
                    r12c._build_chord_diagrams(audio_hash, beats)
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

    base._COMPONENT = lead_only_component
