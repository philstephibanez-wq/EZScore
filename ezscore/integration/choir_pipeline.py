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
import sqlite3
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
from ezscore.analysis.music_timeline import ensure_music_timeline


LEAD_ONLY_LYRICS = True
MANUAL_LYRICS = True

_DB_PATH = Path(__file__).resolve().parents[2] / "data" / "EZScore.sqlite3"


def _legacy_saved_lyrics(audio_hash: str) -> str:
    try:
        with sqlite3.connect(_DB_PATH) as conn:
            rows = conn.execute(
                "SELECT corrected_text, original_text, time_start FROM lyric_block_edits WHERE audio_hash = ? ORDER BY time_start",
                (str(audio_hash),),
            ).fetchall()
    except sqlite3.Error:
        return ""
    chunks = []
    for corrected, original, _ in rows:
        value = str(corrected or original or "").strip()
        if value and (not chunks or value != chunks[-1]):
            chunks.append(value)
    return "\n\n".join(chunks).strip()


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

            if not current_text.strip():
                legacy_text = _legacy_saved_lyrics(audio_hash)
                if legacy_text and original_button(
                    "↩ Récupérer les paroles enregistrées",
                    key=f"ezscore_recover_legacy_lyrics_{short_hash}",
                    width="stretch",
                ):
                    st.session_state[text_key] = legacy_text
                    save_draft(audio_hash, legacy_text)
                    st.rerun()

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
                    with st.status(
                        "Alignement des paroles en cours…",
                        expanded=True,
                    ) as status:
                        status.write("Initialisation MMS_FA…")
                        align_user_lyrics(
                            audio_hash,
                            current_text,
                            progress=status.write,
                        )
                        status.update(
                            label="Paroles alignées.",
                            state="complete",
                            expanded=False,
                        )
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
            result = original_success(
                f"✓ Paroles alignées · {count} mots horodatés · "
                f"moteur `{FORCED_ENGINE}` · texte utilisateur."
            )
            if original_button(
                "→ Étape 3 · Blocs / structure",
                key=f"ezscore_next_blocks_{short_hash}",
                width="stretch",
            ):
                st.session_state[f"ezstem_analysis_step_{short_hash}"] = "3 · Blocs / structure"
                st.rerun()
            return result
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

    # ------------------------------------------------------------
    # Music timeline: same structure_analysis.json, earlier in workflow.
    # No technical_timeline.json and no second analysis route.
    # ------------------------------------------------------------
    original_analyze_structure = stem_lab._analyze_structure

    def analyze_structure_from_existing_timeline(
        *,
        audio_hash: str,
        stems: dict[str, Path],
        meter: dict[str, Any],
    ):
        timeline = ensure_music_timeline(
            stem_lab,
            audio_hash,
        )
        structure = stem_lab._structure_from_beat_timeline(
            audio_hash=audio_hash,
            beat_timeline=list(timeline.get("beat_timeline", []) or []),
            tempo=float(timeline.get("tempo", 120.0) or 120.0),
            meter=dict(meter),
        )
        structure["analysis_engines"] = dict(
            timeline.get("analysis_engines", {}) or {}
        )
        structure["chord_segment_count"] = int(
            timeline.get("chord_segment_count", 0) or 0
        )
        stem_lab._structure_cache_path(audio_hash).write_text(
            json.dumps(structure, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return structure

    # Step 3 now only groups/segments the already-built timeline.
    stem_lab._analyze_structure = analyze_structure_from_existing_timeline

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

            # Build beats + chords exactly once, immediately after STEM + forced
            # lyrics are ready. Player STEM and Paroles+accords then consume the
            # same structure_analysis.json without waiting for Step 3.
            speech = stem_lab._load_speech(audio_hash)
            structure = stem_lab._load_structure(audio_hash)
            has_timeline = bool(
                structure
                and len(list(structure.get("beat_timeline", []) or [])) >= 2
            )

            if (
                speech is not None
                and stem_lab.stems_cache_complete(audio_hash)
                and not has_timeline
            ):
                try:
                    with st.status(
                        "Analyse musicale · beats + accords…",
                        expanded=True,
                    ) as status:
                        ensure_music_timeline(
                            stem_lab,
                            audio_hash,
                            progress=status.write,
                        )
                        status.update(
                            label="Timeline beats + accords prête.",
                            state="complete",
                            expanded=False,
                        )
                except Exception as exc:
                    st.error(
                        "Timeline beats + accords impossible : "
                        f"{type(exc).__name__}: {exc}"
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
