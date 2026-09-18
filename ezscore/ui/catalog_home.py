from __future__ import annotations

"""Accueil Répertoire / Playlists.

Cette surface remplace le bloc Répertoire historique uniquement lorsque
``ezscore.ui`` installe le hook correspondant. Les éléments visuels HTML/CSS
sont externalisés dans ``templates/views/*.score`` pour permettre de refaire
l'UI sans déplacer la logique métier.
"""

from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st

from EZScoreTemplate import ScoreTemplateRenderer
from ezscore.auth import allowed as auth_allowed
from ezscore.auth import current_user as auth_current_user
from ezscore.auth import require as auth_require
from ezscore.catalog_social import (
    add_song_to_playlist,
    create_user_playlist,
    delete_user_playlist,
    ensure_catalog_social_schema,
    list_playlist_songs,
    list_user_playlists,
    rating_summaries,
    remove_song_from_playlist,
    set_song_rating,
)
from ezscore.persistence import (
    catalog_display_name,
    catalog_letter_for_song,
    catalog_primary_text,
    catalog_secondary_text,
    clear_deleted_song_session_state,
    filter_catalog,
    get_app_state,
    get_song_editorial_version,
    get_song_workflow,
    latest_song_editorial_version,
    list_analysis_versions,
    list_song_catalog,
    list_song_editorial_versions,
    prepare_analysis_version_for_open,
    prepare_song_preferences_for_open,
    render_delete_song_controls,
    resume_song_modifications,
    set_app_state,
    song_cover_path,
)


APP_DIR = Path(__file__).resolve().parents[2]
SCORE = ScoreTemplateRenderer(APP_DIR)


def _render_score(template: str, context: dict[str, Any]) -> str:
    return SCORE.render(f"templates/views/{template}", context)


def _user_id(user: dict[str, Any] | None) -> int | None:
    if not user:
        return None
    try:
        value = int(user.get("user_id"))
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def _format_date(value: Any, *, with_time: bool = False) -> str:
    text = str(value or "").strip()
    if not text:
        return "—"
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return text[:16] if with_time else text[:10]
    return dt.strftime("%d/%m/%Y %H:%M" if with_time else "%d/%m/%Y")


def _rating_context(summary: dict[str, Any]) -> dict[str, Any]:
    average = summary.get("average")
    count = int(summary.get("count", 0) or 0)
    if average is None or count <= 0:
        return {
            "stars": "☆☆☆☆☆",
            "average": "—",
            "votes": "0 vote",
            "has_rating": False,
        }

    rounded = max(0, min(5, int(float(average) + 0.5)))
    return {
        "stars": ("★" * rounded) + ("☆" * (5 - rounded)),
        "average": f"{float(average):.1f}".replace(".", ","),
        "votes": f"{count} vote" + ("s" if count != 1 else ""),
        "has_rating": True,
    }


def _render_rating(
    audio_hash: str,
    summary: dict[str, Any],
    *,
    user: dict[str, Any] | None,
    key_prefix: str,
) -> None:
    st.markdown(
        _render_score("catalog-rating.score", _rating_context(summary)),
        unsafe_allow_html=True,
    )

    uid = _user_id(user)
    if uid is None:
        return

    own = summary.get("user_rating")
    label = "★ Noter" if own is None else f"★ {int(own)}/5"
    with st.popover(label):
        st.caption("Votre note contribue à la moyenne collective.")
        cols = st.columns(5)
        for score, col in enumerate(cols, start=1):
            selected = own is not None and score <= int(own)
            with col:
                if st.button(
                    "★" if selected else "☆",
                    key=f"{key_prefix}_rate_{score}",
                    help=f"Noter {score}/5",
                    width="stretch",
                ):
                    set_song_rating(uid, audio_hash, score)
                    st.rerun()


def _render_add_playlist(
    audio_hash: str,
    *,
    user: dict[str, Any] | None,
    key_prefix: str,
) -> None:
    uid = _user_id(user)

    with st.popover("＋"):
        st.markdown("**Ajouter à une playlist**")
        if uid is None:
            st.info("Connectez-vous pour utiliser vos playlists.")
            return

        playlists = list_user_playlists(uid, audio_hash=audio_hash)
        if playlists:
            for playlist in playlists:
                pid = int(playlist["playlist_id"])
                contains = bool(playlist.get("contains_song"))
                if st.button(
                    ("✓ " if contains else "") + str(playlist["name"]),
                    disabled=contains,
                    key=f"{key_prefix}_add_playlist_{pid}",
                    width="stretch",
                ):
                    add_song_to_playlist(uid, pid, audio_hash)
                    st.rerun()
        else:
            st.caption("Aucune playlist pour le moment.")

        st.markdown("---")
        new_name = st.text_input(
            "Nouvelle playlist",
            key=f"{key_prefix}_new_playlist_name",
            placeholder="Nom de la playlist",
        )
        if st.button(
            "＋ Créer et ajouter",
            key=f"{key_prefix}_create_playlist",
            disabled=not str(new_name or "").strip(),
            width="stretch",
        ):
            playlist = create_user_playlist(uid, new_name)
            add_song_to_playlist(
                uid,
                int(playlist["playlist_id"]),
                audio_hash,
            )
            st.rerun()


def _open_song(
    audio_hash: str,
    *,
    selected_version: int | None = None,
    mode: str = "Vue",
    view: str = "Paroles + accords",
) -> None:
    st.session_state["active_song_hash"] = audio_hash
    set_app_state("last_song_hash", audio_hash)
    prepare_song_preferences_for_open(audio_hash)

    if selected_version is None:
        st.session_state.pop("active_analysis_version_no", None)
    else:
        prepare_analysis_version_for_open(audio_hash, selected_version)
        st.session_state[f"song_view_{audio_hash[:12]}"] = view
        st.session_state[f"song_mode_{audio_hash[:12]}"] = mode

    st.session_state["_pending_main_menu"] = "Chanson"
    st.rerun()


def _catalog_choices(
    audio_hash: str,
    versions: list[dict[str, Any]],
    workflow: dict[str, Any],
) -> list[dict[str, Any]]:
    version_numbers = [int(v["version_no"]) for v in versions]
    if not version_numbers:
        return []

    choices: list[dict[str, Any]] = []
    latest_snapshot_no = int(version_numbers[0])
    state = str(workflow.get("state", "working") or "working")

    if state != "published":
        choices.append(
            {
                "key": "working",
                "kind": "working",
                "snapshot_no": latest_snapshot_no,
                "label": (
                    f"V{workflow.get('target_version_label', '1.0')} · "
                    f"{workflow.get('target_edition_label', 'Standard')} · Travail"
                ),
            }
        )

    known = set(version_numbers)
    history = list_song_editorial_versions(audio_hash)
    for publication in history:
        if publication.get("status") != "published":
            continue
        source = publication.get("source_analysis_version_no")
        if source is None or int(source) not in known:
            continue
        choices.append(
            {
                "key": f"published:{publication['version_no']}",
                "kind": "published",
                "snapshot_no": int(source),
                "editorial": publication,
                "label": (
                    f"V{publication['version_label']} · "
                    f"{publication['edition_label']} · "
                    f"R{publication['release_no']}"
                ),
            }
        )

    current = get_song_editorial_version(
        audio_hash,
        workflow.get("current_version_no"),
    )
    if current is None:
        current = latest_song_editorial_version(audio_hash)

    if not choices and state == "published" and current is not None:
        source = current.get("source_analysis_version_no")
        if source is not None and int(source) in known:
            choices.append(
                {
                    "key": "published-current",
                    "kind": "published",
                    "snapshot_no": int(source),
                    "editorial": current,
                    "label": (
                        f"V{current['version_label']} · "
                        f"{current['edition_label']} · "
                        f"R{current['release_no']}"
                    ),
                }
            )

    return choices


def _song_status_context(
    item: dict[str, Any],
    versions: list[dict[str, Any]],
    workflow: dict[str, Any],
    *,
    sort_key: str,
    is_current: bool,
) -> dict[str, Any]:
    state = str(workflow.get("state", "working") or "working")
    primary = catalog_primary_text(item, sort_by=sort_key)
    note = str(workflow.get("working_note", "") or "").strip()

    current = get_song_editorial_version(
        item["audio_hash"],
        workflow.get("current_version_no"),
    )
    if current is None:
        current = latest_song_editorial_version(item["audio_hash"])

    if state in ("validated", "published") and current is not None:
        note = str(current.get("note", "") or "").strip()

    if not versions:
        status = "○ À analyser"
        status_class = "pending"
    elif state == "published" and current is not None:
        status = (
            f"🌍 Publiée · V{current['version_label']} · "
            f"{current['edition_label']} · R{current['release_no']}"
        )
        status_class = "published"
    elif state == "validated" and current is not None:
        status = f"✓ Validée · V{current['version_label']}"
        status_class = "validated"
    else:
        status = "● Modification en cours"
        status_class = "working"

    modified_candidates = [
        str(item.get("updated_at", "") or ""),
        str(workflow.get("updated_at", "") or ""),
    ]
    if current is not None:
        modified_candidates.append(str(current.get("updated_at", "") or ""))

    modified = max((x for x in modified_candidates if x), default="")

    return {
        "primary": ("▶ " if is_current else "") + primary,
        "status": status,
        "status_class": status_class,
        "modified": _format_date(modified, with_time=True),
        "note": note,
        "has_note": bool(note),
    }


def _render_general_catalog(
    catalog: list[dict[str, Any]],
    *,
    user: dict[str, Any] | None,
) -> None:
    last_sort = get_app_state("catalog_sort", "title")
    sort_choice = st.radio(
        "Classer par",
        ["Titre", "Auteur / Interprète"],
        index=1 if last_sort == "artist" else 0,
        horizontal=True,
        key="catalog_social_sort_choice",
    )
    sort_key = "artist" if sort_choice == "Auteur / Interprète" else "title"
    set_app_state("catalog_sort", sort_key)

    catalog = sorted(
        catalog,
        key=lambda item: catalog_primary_text(item, sort_by=sort_key).casefold(),
    )

    st.caption(f"{len(catalog)} chanson(s) dans le répertoire")
    search_query = st.text_input(
        "Rechercher",
        value="",
        placeholder="Titre, auteur ou nom de fichier…",
        key="catalog_social_search",
    )

    letters = ["Tous", "#"] + [chr(c) for c in range(ord("A"), ord("Z") + 1)]
    default_letter = get_app_state("catalog_letter", "Tous")
    if default_letter not in letters:
        default_letter = "Tous"

    selected_letter = st.radio(
        "Index",
        letters,
        index=letters.index(default_letter),
        horizontal=True,
        key="catalog_social_letter",
    )
    set_app_state("catalog_letter", selected_letter)

    filtered = filter_catalog(
        catalog,
        sort_by=sort_key,
        letter=selected_letter,
        query=search_query,
    )

    if not catalog:
        st.info("Le répertoire est vide. Utilisez Import pour ajouter une chanson.")
        return
    if not filtered:
        st.info("Aucune chanson ne correspond à ce filtre.")
        return

    uid = _user_id(user)
    summaries = rating_summaries(
        [item["audio_hash"] for item in filtered],
        uid,
    )
    current_hash = str(st.session_state.get("active_song_hash", "") or "")

    groups: dict[str, list[dict[str, Any]]] = {}
    for item in filtered:
        letter = catalog_letter_for_song(item, sort_by=sort_key)
        groups.setdefault(letter, []).append(item)

    ordered_letters = ["#"] + [chr(c) for c in range(ord("A"), ord("Z") + 1)]
    for letter in ordered_letters:
        items = groups.get(letter, [])
        if not items:
            continue

        st.markdown(
            f'<div class="ez-catalog-letter">{letter}</div>',
            unsafe_allow_html=True,
        )

        for item in items:
            audio_hash = str(item["audio_hash"])
            versions = list_analysis_versions(audio_hash)
            workflow = get_song_workflow(audio_hash)
            choices = _catalog_choices(audio_hash, versions, workflow)

            cover_col, info_col, artist_col, version_col, editor_col, social_col, action_col = st.columns(
                [0.55, 2.05, 1.05, 1.15, 0.95, 1.2, 2.2]
            )

            with cover_col:
                cover = song_cover_path(item)
                if cover is not None:
                    st.image(str(cover), width=64)
                else:
                    st.caption("🎵")

            with info_col:
                st.markdown(
                    _render_score(
                        "catalog-song.score",
                        _song_status_context(
                            item,
                            versions,
                            workflow,
                            sort_key=sort_key,
                            is_current=(audio_hash == current_hash),
                        ),
                    ),
                    unsafe_allow_html=True,
                )

            with artist_col:
                st.caption(catalog_secondary_text(item, sort_by=sort_key))

            selected_choice = None
            selected_version = None
            with version_col:
                if choices:
                    keys = [choice["key"] for choice in choices]
                    selected_key = st.selectbox(
                        "Version",
                        keys,
                        index=0,
                        format_func=lambda key, _choices=choices: next(
                            choice["label"] for choice in _choices
                            if choice["key"] == key
                        ),
                        key=f"catalog_social_version_{audio_hash}",
                        label_visibility="collapsed",
                    )
                    selected_choice = next(
                        choice for choice in choices
                        if choice["key"] == selected_key
                    )
                    selected_version = int(selected_choice["snapshot_no"])
                else:
                    st.caption("Sans version")

            with editor_col:
                version_data = next(
                    (
                        v for v in versions
                        if selected_version is not None
                        and int(v["version_no"]) == selected_version
                    ),
                    None,
                )
                editor_display = (
                    str(version_data.get("editor", "") or "").strip()
                    if version_data
                    else str(item.get("editor", "") or "").strip()
                )
                st.caption(f"Éditeur : {editor_display or '—'}")

            with social_col:
                _render_rating(
                    audio_hash,
                    summaries.get(
                        audio_hash,
                        {"average": None, "count": 0, "user_rating": None},
                    ),
                    user=user,
                    key_prefix=f"catalog_social_{audio_hash}",
                )
                _render_add_playlist(
                    audio_hash,
                    user=user,
                    key_prefix=f"catalog_social_{audio_hash}",
                )

            with action_col:
                if selected_version is None:
                    open_col, delete_col = st.columns([1.5, 0.6])
                    with open_col:
                        if st.button(
                            "Ouvrir",
                            key=f"catalog_social_open_{audio_hash}",
                        ):
                            _open_song(audio_hash)
                    with delete_col:
                        if auth_allowed("song.delete"):
                            with st.popover("🗑"):
                                render_delete_song_controls(
                                    audio_hash=audio_hash,
                                    display_name=catalog_display_name(item, sort_by="title"),
                                    key_suffix=f"social_{audio_hash}_noversion",
                                )
                else:
                    view_col, edit_col, delete_col = st.columns([1, 1, 1])
                    with view_col:
                        if st.button(
                            "👁 Voir",
                            key=f"catalog_social_view_{audio_hash}_{selected_version}",
                        ):
                            _open_song(
                                audio_hash,
                                selected_version=selected_version,
                                mode="Vue",
                                view="Paroles + accords",
                            )
                    with edit_col:
                        if auth_allowed("song.edit"):
                            if st.button(
                                "✏ Modifier",
                                key=f"catalog_social_edit_{audio_hash}_{selected_version}",
                            ):
                                auth_require("song.edit")
                                if (
                                    selected_choice is not None
                                    and selected_choice.get("kind") == "published"
                                ):
                                    resume_song_modifications(audio_hash)
                                _open_song(
                                    audio_hash,
                                    selected_version=selected_version,
                                    mode="Édition",
                                    view="Grille",
                                )
                    with delete_col:
                        if auth_allowed("song.delete"):
                            with st.popover("🗑"):
                                render_delete_song_controls(
                                    audio_hash=audio_hash,
                                    display_name=catalog_display_name(item, sort_by="title"),
                                    key_suffix=f"social_{audio_hash}_{selected_version}",
                                )


def _render_playlists(
    catalog: list[dict[str, Any]],
    *,
    user: dict[str, Any] | None,
) -> None:
    uid = _user_id(user)
    if uid is None:
        st.info("Connectez-vous pour créer et gérer vos playlists.")
        return

    create_col, button_col = st.columns([3, 1])
    with create_col:
        new_name = st.text_input(
            "Nouvelle playlist",
            key="catalog_playlist_new_name",
            placeholder="Nom de la playlist",
            label_visibility="collapsed",
        )
    with button_col:
        if st.button(
            "＋ Créer",
            key="catalog_playlist_create",
            disabled=not str(new_name or "").strip(),
            width="stretch",
        ):
            create_user_playlist(uid, new_name)
            st.rerun()

    playlists = list_user_playlists(uid)
    if not playlists:
        st.info("Aucune playlist. Créez-en une ci-dessus ou depuis le bouton ＋ d'une chanson.")
        return

    visible_by_hash = {str(item["audio_hash"]): item for item in catalog}

    for playlist in playlists:
        pid = int(playlist["playlist_id"])
        songs = [
            item for item in list_playlist_songs(uid, pid)
            if str(item["audio_hash"]) in visible_by_hash
        ]

        st.markdown(
            _render_score(
                "catalog-playlist.score",
                {
                    "name": playlist["name"],
                    "count": len(songs),
                    "count_label": "chanson" if len(songs) == 1 else "chansons",
                },
            ),
            unsafe_allow_html=True,
        )

        delete_col, _ = st.columns([1, 5])
        with delete_col:
            with st.popover("🗑 Supprimer"):
                st.warning(
                    "La playlist sera supprimée. Les chansons restent dans le répertoire."
                )
                if st.button(
                    "Confirmer",
                    key=f"catalog_playlist_delete_{pid}",
                    type="primary",
                ):
                    delete_user_playlist(uid, pid)
                    st.rerun()

        if not songs:
            st.caption("Playlist vide.")
            continue

        summaries = rating_summaries(
            [song["audio_hash"] for song in songs],
            uid,
        )

        for position, song in enumerate(songs, start=1):
            audio_hash = str(song["audio_hash"])
            title = str(song.get("title", "") or "").strip()
            if not title:
                title = Path(str(song.get("original_filename", "") or "")).stem or "Sans titre"
            artist = str(song.get("artist", "") or "").strip() or "Auteur inconnu"

            pos_col, title_col, rating_col, open_col, remove_col = st.columns(
                [0.35, 3.2, 1.35, 0.8, 0.8]
            )
            with pos_col:
                st.caption(str(position))
            with title_col:
                st.markdown(
                    _render_score(
                        "catalog-playlist-song.score",
                        {"title": title, "artist": artist},
                    ),
                    unsafe_allow_html=True,
                )
            with rating_col:
                st.markdown(
                    _render_score(
                        "catalog-rating.score",
                        _rating_context(
                            summaries.get(
                                audio_hash,
                                {"average": None, "count": 0},
                            )
                        ),
                    ),
                    unsafe_allow_html=True,
                )
            with open_col:
                if st.button(
                    "Ouvrir",
                    key=f"catalog_playlist_open_{pid}_{audio_hash}",
                ):
                    versions = list_analysis_versions(audio_hash)
                    if versions:
                        _open_song(
                            audio_hash,
                            selected_version=int(versions[0]["version_no"]),
                            mode="Vue",
                            view="Paroles + accords",
                        )
                    else:
                        _open_song(audio_hash)
            with remove_col:
                if st.button(
                    "Retirer",
                    key=f"catalog_playlist_remove_{pid}_{audio_hash}",
                ):
                    remove_song_from_playlist(uid, pid, audio_hash)
                    st.rerun()

        st.markdown("---")


def render_catalog_home() -> None:
    """Rend la totalité de l'accueil Répertoire puis laisse le hook stopper le script."""
    ensure_catalog_social_schema()
    user = auth_current_user()

    st.markdown(
        _render_score(
            "catalog-home.score",
            {"title": "Répertoire"},
        ),
        unsafe_allow_html=True,
    )

    mode = st.radio(
        "Accueil Répertoire",
        ["Répertoire général", "Playlists"],
        horizontal=True,
        key="catalog_home_mode",
        label_visibility="collapsed",
    )

    catalog = list_song_catalog(sort_by="title")
    if not auth_allowed("song.read_private"):
        catalog = [
            item for item in catalog
            if str(get_song_workflow(item["audio_hash"]).get("state", "working"))
            == "published"
        ]

    if mode == "Playlists":
        _render_playlists(catalog, user=user)
    else:
        _render_general_catalog(catalog, user=user)
