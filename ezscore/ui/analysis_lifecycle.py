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


def _widget_key_already_rendered(key: str) -> bool:
    """Return True when Streamlit already registered this user key this run.

    EZScore currently has two legacy routes that can reach the canonical
    Analyse surface during the same Streamlit script run.  The destructive
    full-reanalysis control is a singleton for one song and must therefore
    render only once.

    We use Streamlit's current ScriptRunContext only as a defensive duplicate
    guard.  Failure to inspect the context falls back to normal rendering.
    """
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx

        ctx = get_script_run_ctx(suppress_warning=True)
        if ctx is None:
            return False

        user_keys = getattr(ctx, "widget_user_keys_this_run", None)
        if user_keys is None:
            return False

        return str(key) in user_keys
    except Exception:
        return False


def render_full_reanalysis_control(
    *,
    audio_hash: str,
    db_path,
) -> None:
    """Render one guarded full-reset control above the Analyse surface."""
    short_hash = str(audio_hash)[:12]
    confirm_key = f"full_reanalysis_confirm_{short_hash}"
    action_key = f"full_reanalysis_{short_hash}"

    # Singleton contract: if another legacy route already rendered this
    # control during the current Streamlit run, do not render it a second time.
    # This prevents StreamlitDuplicateElementKey without changing the reset
    # semantics or inventing multiple suffixed widget keys.
    if (
        _widget_key_already_rendered(confirm_key)
        or _widget_key_already_rendered(action_key)
    ):
        return

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
            key=confirm_key,
        )

        if st.button(
            "♻ Remettre à zéro et réanalyser",
            key=action_key,
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
