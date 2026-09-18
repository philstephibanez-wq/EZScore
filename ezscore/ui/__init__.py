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


def _install_persisted_analysis_r5_10_patch() -> None:
    """Restore the validated R5.10 Analyse > Paroles surface for saved songs.

    R5.10 is implemented inside stem_lab_analysis and its inline editor hook.
    Historically this surface was injected only when EZScore displayed the
    fresh-song message. Once the same song was reopened from the catalogue,
    EZScore.py fell back to its legacy Analyse branch.

    We intercept the exact legacy Analyse heading at render time, after the
    song sidebar controls already exist, render the validated STEM/Paroles/
    Structure/MIDI surface, then stop the legacy branch for this rerun only.
    """
    try:
        import streamlit as st
        from ezscore.ui import app_shell as _shell
        from ezscore.ui import stem_lab_analysis as _stem_lab

        original_markdown = st.markdown

        if getattr(
            original_markdown,
            "_ezscore_persisted_analysis_r5_10_patch",
            False,
        ):
            return

        rendering = False

        def markdown_with_persisted_analysis(*args, **kwargs):
            nonlocal rendering

            if (
                not rendering
                and args
                and _shell.current_section() == "Chanson"
            ):
                value = str(args[0] or "")
                active_hash = str(
                    st.session_state.get("active_song_hash", "") or ""
                ).strip()
                current_view = (
                    str(
                        st.session_state.get(
                            f"song_view_{active_hash[:12]}",
                            "",
                        )
                    )
                    if active_hash
                    else ""
                )

                if (
                    active_hash
                    and current_view == "Analyse"
                    and "ez-view-analytic-heading" in value
                ):
                    rendering = True
                    try:
                        _stem_lab.render_stem_lab_fresh_analysis(active_hash)
                    finally:
                        rendering = False

                    # The validated Analyse surface has been rendered. Do not
                    # continue into the obsolete Analyse implementation below.
                    st.stop()

            return original_markdown(*args, **kwargs)

        markdown_with_persisted_analysis._ezscore_persisted_analysis_r5_10_patch = True
        st.markdown = markdown_with_persisted_analysis

    except Exception as exc:
        try:
            import streamlit as st
            st.error(
                "Restauration Analyse > Paroles R5.10 indisponible : "
                + str(exc)
            )
        except Exception:
            pass


_install_karaoke_patch()
_install_inline_editor_patch()
_install_catalog_home_patch()
_install_persisted_analysis_r5_10_patch()
