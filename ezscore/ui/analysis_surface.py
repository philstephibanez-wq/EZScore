"""Canonical Analyse surface.

The mature STEM_LAB engine remains untouched.  This module only constrains the
product workflow to Step 1 / Step 2 and routes Step 2 presentation through the
same template-driven STEM/Riffstation player used by Step 1.
"""

from __future__ import annotations

import streamlit as st


def render_analysis_surface(audio_hash: str) -> None:
    from ezscore.ui import stem_lab_analysis as stem

    # Analyse uses the main workspace; legacy song widgets must not occupy the
    # left panel. Global navigation/profile buttons remain available.
    st.markdown(
        """
        <style>
        section[data-testid="stSidebar"] div[data-testid="stRadio"],
        section[data-testid="stSidebar"] div[data-testid="stSelectbox"] {
            display:none !important;
        }
        section[data-testid="stSidebar"] h3 { display:none !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    original_segmented = st.segmented_control
    original_caption = st.caption
    original_editor = stem.render_chords_lyrics_editor

    def two_step_segmented(label, options, *args, **kwargs):
        if str(label) == "Étape d'analyse":
            allowed = ["1 · STEM", "2 · Paroles"]
            options = allowed
            key = str(kwargs.get("key", "") or "")
            if key and st.session_state.get(key) not in allowed:
                st.session_state[key] = allowed[0]
            default = kwargs.get("default")
            if default not in allowed:
                kwargs.pop("default", None)
        return original_segmented(label, options, *args, **kwargs)

    def render_step2_shared_player(*, stem_module, audio_hash: str, **_kwargs) -> None:
        song = stem_module._song_for_hash(audio_hash)
        source = stem_module._source_path(audio_hash, song)
        if source is None or not source.is_file():
            st.error("Audio original introuvable pour le Step 2.")
            return

        speech = stem_module._load_speech(audio_hash) or {}
        words = list(speech.get("words", []) or [])
        if not words:
            st.info("Aucun mot ancré. Lancer d'abord la reconnaissance du Step 2.")
            return

        stems = stem_module.cached_stem_paths(audio_hash)
        vocal_parts = stem_module.vocal_stem_paths(audio_hash)
        all_stems = {**stems, **vocal_parts}
        stem_module._render_stem_player(
            source,
            all_stems,
            preview_dir=stem_module._work_dir(audio_hash) / "browser_preview",
            key=f"ezstem_player_{str(audio_hash)[:12]}_step2",
            words=words,
        )

    def workflow_caption(body, *args, **kwargs):
        text = str(body or "")
        step_key = f"ezstem_analysis_step_{str(audio_hash)[:12]}"
        step = str(st.session_state.get(step_key, "1 · STEM") or "1 · STEM")
        if step.startswith("1") and "Paroles synchronisées" in text:
            body = "Original + STEMS + Chant + Chœurs · audit accords sans paroles."
        return original_caption(body, *args, **kwargs)

    st.segmented_control = two_step_segmented
    st.caption = workflow_caption
    stem.render_chords_lyrics_editor = render_step2_shared_player
    try:
        stem.render_stem_lab_fresh_analysis(audio_hash)
    finally:
        st.segmented_control = original_segmented
        st.caption = original_caption
        stem.render_chords_lyrics_editor = original_editor
