"""EZScore UI integration hooks."""


def _install_karaoke_patch() -> None:
    try:
        from ezscore.ui import stem_lab_analysis as _stem_lab
        from pathlib import Path
        import shutil
        import subprocess

        from ezscore.player.karaoke_stem_webaudio_r12c import (
            render_player as _karaoke_player,
        )

        _preview_probe_cache = {}

        def _preview_signature(path: Path):
            try:
                stat = path.stat()
                return (str(path), int(stat.st_size), int(stat.st_mtime_ns))
            except OSError:
                return None

        def _preview_is_valid(path: Path) -> bool:
            signature = _preview_signature(path)
            if signature is None:
                return False
            if signature in _preview_probe_cache:
                return bool(_preview_probe_cache[signature])

            ffprobe = shutil.which("ffprobe")
            if not ffprobe:
                # No new hard dependency: let the already validated player run.
                _preview_probe_cache[signature] = True
                return True

            result = subprocess.run(
                [
                    ffprobe,
                    "-v", "error",
                    "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    str(path),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
                timeout=8,
            )
            try:
                duration = float((result.stdout or "").strip())
            except (TypeError, ValueError):
                duration = 0.0

            valid = result.returncode == 0 and duration > 0.05
            _preview_probe_cache[signature] = valid
            return valid

        def _karaoke_player_guarded(
            source,
            stems,
            *,
            preview_dir,
            key,
            words=None,
        ):
            preview_path = Path(preview_dir)
            repaired = []

            if preview_path.is_dir():
                for preview in preview_path.glob("*.browser64.mp3"):
                    try:
                        if preview.is_file() and not _preview_is_valid(preview):
                            repaired.append(preview.name)
                            preview.unlink()
                    except (OSError, subprocess.SubprocessError):
                        # Never break the validated player for a diagnostic probe.
                        pass

            if repaired:
                st.warning(
                    "Pré-écoute navigateur invalide détectée et reconstruite : "
                    + ", ".join(repaired)
                )

            return _karaoke_player(
                source,
                stems,
                preview_dir=preview_dir,
                key=key,
                words=words,
            )

        _stem_lab._render_stem_player = _karaoke_player_guarded
    except Exception as exc:
        try:
            import streamlit as st
            st.error(f"Lecteur karaoké R12c indisponible : {exc}")
        except Exception:
            pass


def _install_analysis_lifecycle_patch() -> None:
    """Add complete analysis reset and make full song deletion really total."""
    try:
        from ezscore import persistence as _persistence
        from ezscore.analysis_lifecycle import purge_analysis_cache
        from ezscore.ui import stem_lab_analysis as _stem_lab
        from ezscore.ui.analysis_lifecycle import render_full_reanalysis_control

        # --------------------------------------------------------------
        # Full delete: current persistence already removes audio, covers
        # and every DB row keyed by audio_hash. Add the missing technical
        # cache purge without changing persistence.py.
        # --------------------------------------------------------------
        original_delete = _persistence.delete_song_completely
        if not getattr(original_delete, "_ezscore_total_delete_patch", False):
            def delete_song_completely_total(audio_hash):
                purge_analysis_cache(
                    _persistence.APP_DIR,
                    audio_hash,
                )
                return original_delete(audio_hash)

            delete_song_completely_total._ezscore_total_delete_patch = True
            _persistence.delete_song_completely = delete_song_completely_total

        # --------------------------------------------------------------
        # Analyse UI: wrap the validated surface; do not alter its STEM /
        # Paroles / Structure / MIDI implementation.
        # --------------------------------------------------------------
        original_render = _stem_lab.render_stem_lab_fresh_analysis
        if not getattr(original_render, "_ezscore_full_reanalysis_patch", False):
            def render_with_full_reanalysis(audio_hash: str) -> None:
                render_full_reanalysis_control(
                    audio_hash=audio_hash,
                    db_path=_persistence.DB_PATH,
                )
                original_render(audio_hash)

            render_with_full_reanalysis._ezscore_full_reanalysis_patch = True
            _stem_lab.render_stem_lab_fresh_analysis = render_with_full_reanalysis

    except Exception as exc:
        try:
            import streamlit as st
            st.error("Cycle de réanalyse complète indisponible : " + str(exc))
        except Exception:
            pass


def _install_karaoke_word_layout_patch() -> None:
    try:
        from ezscore.player.karaoke_word_layout import install
        install()
    except Exception as exc:
        try:
            import streamlit as st
            st.error("Layout paroles du player indisponible : " + str(exc))
        except Exception:
            pass


def _install_intro_rhythm_fusion_patch() -> None:
    try:
        from ezscore.ui import stem_lab_analysis as _stem_lab
        from ezscore.ui.analysis_rhythm_patch import install
        install(_stem_lab)
    except Exception as exc:
        try:
            import streamlit as st
            st.error("Fusion rythmique d'intro indisponible : " + str(exc))
        except Exception:
            pass


def _install_editorial_recovery_patch() -> None:
    """Recover safely from intentional editorial fingerprint changes."""
    try:
        from ezscore.ui.editorial_compat_patch import install
        install()
    except Exception as exc:
        try:
            import streamlit as st
            st.error("Compatibilité éditoriale indisponible : " + str(exc))
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
                from ezscore.navigation.session_adapter import (
                    bootstrap_from_legacy,
                    current_state,
                )
                from ezscore.navigation.states import (
                    GROUPS_LIST,
                    GROUP_DETAIL,
                )

                bootstrap_from_legacy()

                if current_state() in {GROUPS_LIST, GROUP_DETAIL}:
                    from ezscore.ui.groups_home import render_groups_home
                    render_groups_home()
                else:
                    from ezscore.ui.catalog_home import render_catalog_home
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

            from ezscore.navigation.session_adapter import (
                back as nav_back,
                can_back as nav_can_back,
                current_state as nav_current_state,
                open_groups as nav_open_groups,
                open_playlists as nav_open_playlists,
                open_repertoire as nav_open_repertoire,
                previous_route as nav_previous_route,
            )
            from ezscore.navigation.states import SONG_DETAIL, SONG_ANALYSIS

            def open_groups() -> None:
                nav_open_groups()

            def clear_groups_if_navigation(key, clicked) -> None:
                if clicked and key == "shell_repertoire":
                    nav_open_repertoire(rerun=False)

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
                    if original_sidebar_button(
                        t(
                            "nav.playlists",
                            domain="catalog",
                        ),
                        key="shell_playlists",
                        width="stretch",
                    ):
                        nav_open_playlists()
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
                    if original_button(
                        t(
                            "nav.playlists",
                            domain="catalog",
                        ),
                        key="shell_playlists_compact",
                        width="stretch",
                    ):
                        nav_open_playlists()
                return clicked

            st.sidebar.button = patched_sidebar_button
            st.button = patched_button
            try:
                original_render()

                if (
                    nav_current_state() in {SONG_DETAIL, SONG_ANALYSIS}
                    and nav_can_back()
                ):
                    previous = nav_previous_route() or {}
                    previous_state = str(previous.get("state") or "")
                    label = (
                        "← Retour à la playlist"
                        if previous_state == "playlist.detail"
                        else "← Retour"
                    )
                    if original_sidebar_button(
                        label,
                        key="shell_efsm_back",
                        width="stretch",
                    ):
                        nav_back()
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
_install_karaoke_word_layout_patch()
_install_intro_rhythm_fusion_patch()
_install_analysis_lifecycle_patch()
_install_editorial_recovery_patch()
_install_inline_editor_patch()
_install_catalog_home_patch()
_install_groups_navigation_patch()
_install_persisted_analysis_r5_10_patch()
