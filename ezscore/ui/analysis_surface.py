"""Canonical two-step Analyse workflow.

Step 1 = Riffstation + STEMS, no lyrics.
Step 2 = exactly the same template-driven workspace + anchored lyrics.

This module owns only the product workflow. It deliberately calls the existing
R12c template-driven Riffstation player directly so no historical monkey-patch
can silently replace the requested workspace with the legacy conductor.
"""

from __future__ import annotations

import traceback
from pathlib import Path

import streamlit as st

from EZScoreTemplate import ScoreTemplateRenderer

SCORE = ScoreTemplateRenderer(Path(__file__).resolve().parents[2])


def _render_analysis_shell() -> None:
    st.markdown(
        SCORE.render(
            "templates/views/analysis-workspace-shell.score",
            {"view": {"name": "Analyse Riffstation"}},
        ),
        unsafe_allow_html=True,
    )


def _all_stems(stem, audio_hash: str) -> dict:
    return {
        **stem.cached_stem_paths(audio_hash),
        **stem.vocal_stem_paths(audio_hash),
    }


def _extract_all_stems(stem, audio_hash: str, source) -> None:
    short_hash = str(audio_hash)[:12]
    with st.status("Extraction STEM HQ…", expanded=True) as status:
        try:
            status.write("1/2 · Instruments")
            stem.ensure_stems(
                audio_bytes=source.read_bytes(),
                extension=source.suffix.lower() or ".mp3",
                audio_hash=audio_hash,
            )
            current = stem.cached_stem_paths(audio_hash)
            status.write("2/2 · Chant / Chœurs")
            stem.ensure_vocal_stems(
                audio_hash=audio_hash,
                vocals_path=current["vocals"],
            )
        except Exception as exc:
            status.update(
                label="Extraction STEM en erreur.",
                state="error",
                expanded=True,
            )
            st.session_state[f"ezstem_error_{short_hash}"] = (
                f"Extraction STEM : {type(exc).__name__}: {exc}"
            )
            stem.perf_event(
                "analysis.stem.error",
                status="error",
                operation="Extraction STEM",
                error_type=type(exc).__name__,
                error=str(exc),
                traceback=traceback.format_exc(),
            )
            return

        st.session_state.pop(f"ezstem_error_{short_hash}", None)
        stem.perf_event(
            "analysis.stem.complete",
            status="ok",
            operation="Extraction STEM",
        )
        status.update(
            label="STEM HQ prêts.",
            state="complete",
            expanded=False,
        )
    st.rerun()


def _render_stem_maintenance(stem, audio_hash: str, source) -> None:
    """Technical STEM operations remain available outside the main workspace."""
    short_hash = str(audio_hash)[:12]
    with st.expander("Maintenance STEM", expanded=False):
        stems = stem.cached_stem_paths(audio_hash)
        vocal_parts = stem.vocal_stem_paths(audio_hash)
        all_stems = {**stems, **vocal_parts}

        if st.button(
            "⬇ Préparer les téléchargements STEM",
            key=f"ezstem_r10_downloads_{short_hash}",
            width="stretch",
        ):
            stem._download_stems(all_stems)

        c1, c2 = st.columns(2)
        with c1:
            if st.button(
                "↻ Régénérer tous les STEM",
                key=f"ezstem_r10_regen_all_{short_hash}",
                width="stretch",
            ):
                with st.status("Régénération complète…", expanded=True) as status:
                    try:
                        stem.ensure_stems(
                            audio_bytes=source.read_bytes(),
                            extension=source.suffix.lower() or ".mp3",
                            audio_hash=audio_hash,
                            force=True,
                            force_model_download=False,
                        )
                        refreshed = stem.cached_stem_paths(audio_hash)
                        stem.delete_vocal_stem_cache(audio_hash)
                        stem.ensure_vocal_stems(
                            audio_hash=audio_hash,
                            vocals_path=refreshed["vocals"],
                            force=True,
                            force_model_download=False,
                        )
                        stem._invalidate_after_stem_regeneration(
                            audio_hash,
                            full=True,
                        )
                    except Exception as exc:
                        status.update(
                            label="Régénération STEM en erreur.",
                            state="error",
                            expanded=True,
                        )
                        st.error(f"{type(exc).__name__}: {exc}")
                    else:
                        status.update(
                            label="STEM régénérés.",
                            state="complete",
                            expanded=False,
                        )
                        st.rerun()

        with c2:
            if st.button(
                "↻ Régénérer Chant / Chœurs",
                key=f"ezstem_r10_regen_vocals_{short_hash}",
                width="stretch",
            ):
                with st.status("Régénération Chant / Chœurs…", expanded=True) as status:
                    try:
                        stem.ensure_vocal_stems(
                            audio_hash=audio_hash,
                            vocals_path=stems["vocals"],
                            force=True,
                            force_model_download=False,
                        )
                        stem._invalidate_after_stem_regeneration(
                            audio_hash,
                            full=False,
                        )
                    except Exception as exc:
                        status.update(
                            label="Régénération Chant / Chœurs en erreur.",
                            state="error",
                            expanded=True,
                        )
                        st.error(f"{type(exc).__name__}: {exc}")
                    else:
                        status.update(
                            label="Chant / Chœurs régénérés.",
                            state="complete",
                            expanded=False,
                        )
                        st.rerun()


def _render_workspace(stem, *, audio_hash: str, source, words: list[dict]) -> None:
    if not stem._stem_ffmpeg_available():
        st.error("FFmpeg est requis pour le lecteur STEM.")
        return

    # IMPORTANT: direct call to the existing template-driven player.
    # Do not use stem._render_stem_player here: historical integration hooks can
    # replace that symbol with the old Structure/Accords/Chant conductor.
    from ezscore.player.karaoke_stem_webaudio_r12c import (
        render_player as render_riffstation_workspace,
    )

    all_stems = _all_stems(stem, audio_hash)
    render_riffstation_workspace(
        source,
        all_stems,
        preview_dir=stem._work_dir(audio_hash) / "browser_preview",
        key=(
            f"ezstem_riffstation_r9_{str(audio_hash)[:12]}_"
            f"{'lyrics' if words else 'stems'}"
        ),
        words=words,
    )


def render_analysis_surface(audio_hash: str) -> None:
    """Render exactly the two requested product steps."""
    from ezscore.ui import stem_lab_analysis as stem

    _render_analysis_shell()

    song = stem._song_for_hash(audio_hash)
    source = stem._source_path(audio_hash, song)
    if source is None or not source.is_file():
        st.error("Audio original introuvable dans le répertoire EZScore.")
        return

    short_hash = str(audio_hash)[:12]
    step_key = f"ezstem_analysis_step_{short_hash}"
    steps = ["1 · STEMS", "2 · PAROLES"]

    current = str(st.session_state.get(step_key, steps[0]) or steps[0])
    current = steps[1] if current.startswith("2") else steps[0]
    st.session_state[step_key] = current
    selected = current

    stem_error = str(
        st.session_state.get(f"ezstem_error_{short_hash}", "") or ""
    )
    if stem_error:
        st.error(stem_error)

    if not stem.demucs_available():
        st.error("BS-RoFormer-Infer n’est pas installé dans cet environnement Python.")
        return

    if not stem.stems_cache_complete(audio_hash):
        st.info(
            "Step 1 : extraire les STEM avant l'audit Riffstation. "
            "Aucune parole n'est analysée à cette étape."
        )
        if st.button(
            "Extraire les STEM HQ",
            type="primary",
            width="stretch",
            key=f"ezstem_r10_extract_{short_hash}",
        ):
            _extract_all_stems(stem, audio_hash, source)
        return

    if not stem.vocal_stems_cache_complete(audio_hash):
        with st.expander("Chant / Chœurs non séparés", expanded=False):
            if st.button(
                "Extraire Chant / Chœurs",
                type="primary",
                width="stretch",
                key=f"ezstem_r10_split_vocals_{short_hash}",
            ):
                stems = stem.cached_stem_paths(audio_hash)
                try:
                    stem.ensure_vocal_stems(
                        audio_hash=audio_hash,
                        vocals_path=stems["vocals"],
                    )
                except Exception as exc:
                    st.error(f"{type(exc).__name__}: {exc}")
                else:
                    st.rerun()

    if selected == steps[0]:
        # STEP 1 = Riffstation + STEMS. No lyrics object enters the component.
        _render_workspace(
            stem,
            audio_hash=audio_hash,
            source=source,
            words=[],
        )
        return

    # STEP 2 = same workspace, same musical timeline, plus anchored words.
    speech = stem._load_speech(audio_hash)
    words = list((speech or {}).get("words", []) or [])

    _render_workspace(
        stem,
        audio_hash=audio_hash,
        source=source,
        words=words,
    )

    if not words:
        st.info(
            "Step 2 ajoute les paroles au même conducteur. "
            "La timeline musicale du Step 1 n'est pas recalculée."
        )
        if st.button(
            "Analyser / ancrer les paroles",
            type="primary",
            width="stretch",
            key=f"ezstem_r10_speech_{short_hash}",
        ):
            with st.spinner("Reconnaissance et ancrage des mots…"):
                stem._transcribe_original(source, audio_hash)
            st.rerun()
