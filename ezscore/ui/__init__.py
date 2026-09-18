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
                if bool(st.session_state.get("_ez_groups_open", False)):
                    from ezscore.ui.groups_home import render_groups_home
                    render_groups_home()
                else:
                    from ezscore.ui.catalog_home import render_catalog_home

                    if bool(
                        st.session_state.pop(
                            "_ez_catalog_open_playlists",
                            False,
                        )
                    ):
                        from ezscore.i18n import t
                        st.session_state["catalog_home_mode"] = t(
                            "home.playlists",
                            domain="catalog",
                        )

                    render_catalog_home()
            except Exception as exc:
                st.error(f"Surface Répertoire/Groupes indisponible : {exc}")
                return

            # La surface modulaire vient d'être rendue. Ne pas exécuter ensuite
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




def _install_groups_navigation_patch() -> None:
    """Expose a dedicated Groups surface without changing EZScore.py/app_shell.

    EZScore.py currently knows only Répertoire / Chanson / Compte / Import.
    We therefore keep the shell's stable main-menu contract and route Groups
    as a dedicated sub-surface of Répertoire, selected by a private session
    flag. The sidebar button is injected immediately after Profile.

    This avoids widening the legacy global navigation enum and keeps the patch
    modular until the shell itself is migrated to the i18n navigation model.
    """
    try:
        import streamlit as st
        from ezscore.ui import app_shell as _shell
        from ezscore.i18n import t

        original_render = _shell.render_profile_sidebar
        if getattr(
            original_render,
            "_ezscore_groups_navigation_patch",
            False,
        ):
            return

        def render_profile_sidebar_with_groups() -> None:
            original_button = st.button
            original_sidebar_button = st.sidebar.button

            def open_groups() -> None:
                st.session_state["_ez_groups_open"] = True
                st.session_state["_pending_main_menu"] = "Répertoire"
                st.rerun()

            def clear_groups_if_navigation(key, clicked) -> None:
                if (
                    clicked
                    and key
                    in {
                        "shell_repertoire",
                        "shell_profile",
                        "shell_login",
                        "shell_edits",
                        "shell_import",
                        "shell_admin_users",
                        "shell_logout",
                    }
                ):
                    st.session_state["_ez_groups_open"] = False

            def patched_sidebar_button(*args, **kwargs):
                key = kwargs.get("key")
                clicked = original_sidebar_button(*args, **kwargs)
                clear_groups_if_navigation(key, clicked)

                # Full sidebar: requested placement is directly below Profile.
                if key == "shell_profile":
                    if original_sidebar_button(
                        t(
                            "nav.groups",
                            domain="groups",
                        ),
                        key="shell_groups",
                        width="stretch",
                    ):
                        open_groups()
                return clicked

            def patched_button(*args, **kwargs):
                key = kwargs.get("key")
                clicked = original_button(*args, **kwargs)
                clear_groups_if_navigation(key, clicked)

                # Compact song/import sidebar: Profile lives in a column, so
                # keep Groups immediately underneath it in that same quick area.
                if key == "shell_profile":
                    if original_button(
                        t(
                            "nav.groups",
                            domain="groups",
                        ),
                        key="shell_groups_compact",
                        width="stretch",
                    ):
                        open_groups()
                return clicked

            st.sidebar.button = patched_sidebar_button
            st.button = patched_button
            try:
                original_render()
            finally:
                st.sidebar.button = original_sidebar_button
                st.button = original_button

        render_profile_sidebar_with_groups._ezscore_groups_navigation_patch = True
        _shell.render_profile_sidebar = render_profile_sidebar_with_groups

    except Exception as exc:
        try:
            import streamlit as st
            st.error(f"Navigation groupes indisponible : {exc}")
        except Exception:
            pass


_install_karaoke_patch()
_install_inline_editor_patch()
_install_catalog_home_patch()
_install_groups_navigation_patch()
_install_persisted_analysis_r5_10_patch()
