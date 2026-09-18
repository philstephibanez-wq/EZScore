from __future__ import annotations

"""Canonical runtime for EZScore.

Disease addressed:
- work mode previously keyed by audio hash;
- old SQLite analysis could outrank STEM_LAB;
- two Analyse render paths could coexist.

Contract:
- one work mode for the application session;
- STEM_LAB is technical truth for modern Analyse/Edit/Player;
- Analyse always renders stem_lab_analysis;
- legacy per-song keys are compatibility mirrors only.
"""

from pathlib import Path
from typing import Any

import streamlit as st


GLOBAL_WORK_MODE_KEY = "ez_work_mode"


def _active_hash() -> str:
    return str(st.session_state.get("active_song_hash", "") or "").strip()


def _work_dir(app_shell, audio_hash: str) -> Path:
    return (
        Path(app_shell.APP_DIR)
        / "data"
        / "analysis"
        / "stem_lab"
        / str(audio_hash)
    )


def _canonical_analysis_ready(app_shell, audio_hash: str) -> bool:
    if not audio_hash:
        return False

    from ezscore.analysis.technical_snapshot import status

    state = status(_work_dir(app_shell, audio_hash))
    return bool(
        state.get("lyrics_ready")
        and state.get("structure_ready")
        and int(state.get("beat_count", 0) or 0) > 0
    )


def _install_work_mode_contract(app_shell) -> None:
    if getattr(app_shell, "_EZ_CANONICAL_WORK_MODE_R3", False):
        return

    historical_loader = app_shell._ORIGINAL_LOAD_LATEST_PERSISTED_ANALYSIS
    stem_bridge = app_shell._stem_lab_editor_bridge

    def global_work_mode_key(active_hash: str) -> str:
        return GLOBAL_WORK_MODE_KEY

    def canonical_analysis_exists(active_hash: str) -> bool:
        return _canonical_analysis_ready(
            app_shell,
            str(active_hash or ""),
        )

    def mirror_mode(active_hash: str) -> str:
        mode = str(
            st.session_state.get(GLOBAL_WORK_MODE_KEY, "") or ""
        ).strip()

        if mode and active_hash:
            st.session_state[
                f"ez_work_mode_{active_hash[:12]}"
            ] = mode

        return mode

    def canonical_bridge(audio_hash: str) -> dict[str, Any] | None:
        active_hash = str(audio_hash or "").strip()
        if not active_hash:
            return None

        mirror_mode(active_hash)
        return stem_bridge(active_hash)

    def canonical_loader(audio_hash):
        active_hash = str(audio_hash or "").strip()
        mode = str(
            st.session_state.get(GLOBAL_WORK_MODE_KEY, "") or ""
        ).strip()

        if mode in {"Édition", "Player"}:
            # Never adapt the UI to the age/history of the song.
            # Modern work modes consume STEM_LAB or nothing.
            return canonical_bridge(active_hash)

        # Catalogue/version metadata may still inspect historical analysis.
        return historical_loader(active_hash)

    app_shell._work_mode_key = global_work_mode_key
    app_shell._analysis_exists = canonical_analysis_exists
    app_shell._stem_lab_editor_bridge = canonical_bridge
    app_shell.load_latest_persisted_analysis = canonical_loader
    app_shell._persistence.load_latest_persisted_analysis = canonical_loader
    app_shell._EZ_CANONICAL_WORK_MODE_R3 = True


def _install_analysis_router(app_shell) -> None:
    current_markdown = st.markdown

    if getattr(
        current_markdown,
        "_ezscore_canonical_analysis_router_r3",
        False,
    ):
        return

    rendering = False

    def markdown_canonical(*args, **kwargs):
        nonlocal rendering

        if not rendering and args:
            value = str(args[0] or "")
            active_hash = _active_hash()
            mode = str(
                st.session_state.get(GLOBAL_WORK_MODE_KEY, "") or ""
            ).strip()

            if (
                active_hash
                and mode == "Analyse"
                and "ez-view-analytic-heading" in value
            ):
                from ezscore.ui import stem_lab_analysis

                rendering = True
                try:
                    stem_lab_analysis.render_stem_lab_fresh_analysis(
                        active_hash
                    )
                finally:
                    rendering = False

                # Never render the historical Analyse implementation below.
                st.stop()

        return current_markdown(*args, **kwargs)

    markdown_canonical._ezscore_canonical_analysis_router_r3 = True
    st.markdown = markdown_canonical


def install(app_shell) -> None:
    if getattr(app_shell, "_EZ_CANONICAL_RUNTIME_R3", False):
        return

    _install_work_mode_contract(app_shell)

    original_sidebar = app_shell.render_profile_sidebar

    def render_profile_sidebar_canonical() -> None:
        # app_shell installs Streamlit wrappers at import time.
        # Install the final Analyse router only now, over the final callable.
        _install_analysis_router(app_shell)

        active_hash = _active_hash()
        if active_hash:
            mode = str(
                st.session_state.get(GLOBAL_WORK_MODE_KEY, "") or ""
            ).strip()

            if mode:
                st.session_state[
                    f"ez_work_mode_{active_hash[:12]}"
                ] = mode

        original_sidebar()

    render_profile_sidebar_canonical._ezscore_canonical_runtime_r3 = True
    app_shell.render_profile_sidebar = render_profile_sidebar_canonical
    app_shell._EZ_CANONICAL_RUNTIME_R3 = True
