from __future__ import annotations

"""UI for destructive analysis lifecycle actions."""

from pathlib import Path

import streamlit as st

from EZScoreTemplate import ScoreTemplateRenderer
from ezscore.analysis_lifecycle import full_reanalysis_reset


APP_DIR = Path(__file__).resolve().parents[2]
SCORE = ScoreTemplateRenderer(APP_DIR)


def _clear_analysis_session_state(audio_hash: str) -> None:
    value = str(audio_hash or "").strip()
    short_hash = value[:12]

    # Remove all analysis/editorial widget state associated with this song.
    for key in list(st.session_state.keys()):
        key_text = str(key)
        if (
            (value and value in key_text)
            or (short_hash and short_hash in key_text)
        ):
            st.session_state.pop(key, None)

    # Re-enter the same song explicitly in Analyse after the purge.
    st.session_state["active_song_hash"] = value
    st.session_state["active_analysis_version_no"] = None
    st.session_state[f"song_mode_{short_hash}"] = "Vue"
    st.session_state[f"song_view_{short_hash}"] = "Analyse"
    st.session_state["_pending_main_menu"] = "Chanson"


def render_full_reanalysis_control(
    *,
    audio_hash: str,
    db_path,
) -> None:
    """Render a guarded full-reset control above the existing Analyse tabs."""
    short_hash = str(audio_hash)[:12]

    with st.expander("♻ Réanalyse complète", expanded=False):
        st.markdown(
            SCORE.render(
                "templates/views/analysis-lifecycle.score",
                {},
            ),
            unsafe_allow_html=True,
        )

        confirmed = st.checkbox(
            "Je confirme la remise à zéro complète de l’analyse",
            key=f"full_reanalysis_confirm_{short_hash}",
        )

        if st.button(
            "♻ Remettre à zéro et réanalyser",
            key=f"full_reanalysis_{short_hash}",
            type="primary",
            disabled=not confirmed,
            width="stretch",
        ):
            with st.spinner(
                "Purge complète des analyses, éditions et caches techniques…"
            ):
                result = full_reanalysis_reset(
                    app_dir=APP_DIR,
                    db_path=db_path,
                    audio_hash=audio_hash,
                )

            _clear_analysis_session_state(audio_hash)

            st.toast(
                "Analyse remise à zéro : "
                f"{result.deleted_rows} lignes supprimées, "
                f"{len(result.deleted_cache_dirs)} cache(s) technique(s)."
            )
            st.rerun()
