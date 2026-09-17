"""EZScore UI helpers.

Integration hook for the validated unified STEM/karaoke player.
R11 keeps the R10 audio engine and replaces only the conductor presentation.
"""

def _install_karaoke_patch() -> None:
    try:
        from ezscore.ui import stem_lab_analysis as _stem_lab
        from ezscore.player.karaoke_stem_webaudio_r11 import (
            render_player as _karaoke_player,
        )
        _stem_lab._render_stem_player = _karaoke_player
    except Exception as exc:
        try:
            import streamlit as st
            st.error(f"Lecteur karaoké R11 indisponible : {exc}")
        except Exception:
            pass

_install_karaoke_patch()
