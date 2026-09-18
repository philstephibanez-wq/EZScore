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


def _install_catalog_home_patch() -> None:
    """Déporte le Répertoire vers une surface modulaire sans toucher EZScore.py.

    Le projet utilise déjà ce module comme point d'installation des surfaces
    R12c / éditeur inline. On conserve donc le même mécanisme : le shell garde
    la navigation globale, puis la nouvelle page Répertoire est rendue avant
    que le bloc historique de EZScore.py ne soit atteint.
    """
    try:
        import streamlit as st
        from ezscore.ui import app_shell as _shell

        original = _shell.render_profile_sidebar
        if getattr(original, "_ezscore_catalog_home_patch", False):
            return

        def render_profile_sidebar_with_catalog() -> None:
            original()

            if _shell.current_section() != "Répertoire":
                return

            try:
                from ezscore.ui.catalog_home import render_catalog_home
                render_catalog_home()
            except Exception as exc:
                st.error(f"Répertoire enrichi indisponible : {exc}")
                return

            # Le Répertoire complet vient d'être rendu. Ne pas exécuter ensuite
            # l'ancien bloc monolithique de EZScore.py.
            st.stop()

        render_profile_sidebar_with_catalog._ezscore_catalog_home_patch = True
        _shell.render_profile_sidebar = render_profile_sidebar_with_catalog
    except Exception as exc:
        try:
            import streamlit as st
            st.error(f"Répertoire enrichi indisponible : {exc}")
        except Exception:
            pass


_install_karaoke_patch()
_install_inline_editor_patch()
_install_catalog_home_patch()
