"""EZScore UI helpers.

Integration hook for the validated unified STEM/karaoke player.
Unified karaoke player integration.
"""


def _install_karaoke_patch() -> None:
    try:
        from ezscore.ui import stem_lab_analysis as _stem_lab
        from ezscore.player.karaoke_stem_webaudio_r12c import (
            render_player as _karaoke_player,
        )
        _stem_lab._render_stem_player = _karaoke_player
    except Exception as exc:
        try:
            import streamlit as st
            st.error(f"Lecteur karaoké R12c indisponible : {exc}")
        except Exception:
            pass


def _install_lyrics_editor_patch() -> None:
    try:
        from ezscore.ui import stem_lab_analysis as _stem_lab
        from ezscore.ui.lyrics_word_anchor_editor import install
        install(_stem_lab)
    except Exception as exc:
        try:
            import streamlit as st
            st.error(f"Éditeur Paroles indisponible : {exc}")
        except Exception:
            pass


_install_karaoke_patch()
_install_lyrics_editor_patch()
