"""EZScore UI integration hooks."""

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


def _install_inline_editor_patch() -> None:
    try:
        from ezscore.ui import stem_lab_analysis as _stem_lab
        from ezscore.ui.lyrics_inline_editor import install
        install(_stem_lab)
    except Exception as exc:
        try:
            import streamlit as st
            st.error(f"Éditeur timeline indisponible : {exc}")
        except Exception:
            pass


_install_karaoke_patch()
_install_inline_editor_patch()
