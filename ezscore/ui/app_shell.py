"""Application shell: header, profile sidebar and contextual navigation."""

from __future__ import annotations

import html

import streamlit as st

from ezscore.auth import allowed, current_user, logout
from ezscore.auth.storage import avatar_value
import ezscore.persistence as _persistence
from ezscore.persistence import load_latest_persisted_analysis
from ezscore.midi import build_midi_file as _build_midi_file


# ---------------------------------------------------------------------------
# R30 MIDI symbol bridge.
#
# EZScore.py imports app_shell BEFORE:
#     from ezscore.persistence import *
#
# The current monolith later calls build_midi_file(...) but imports only
# MIDI_INSTRUMENTS from ezscore.midi. Expose the already-existing MIDI builder
# through persistence.__all__, so the later star import resolves the symbol.
#
# Important:
# - no builtins mutation;
# - no MIDI work is performed here;
# - build_midi_file still runs only when the Analyse view asks for it.
# ---------------------------------------------------------------------------

_persistence.build_midi_file = _build_midi_file
if "build_midi_file" not in _persistence.__all__:
    _persistence.__all__.append("build_midi_file")

print("[EZTRACE][MIDI_SYMBOL] build_midi_file exported=true")


# ---------------------------------------------------------------------------
# R30 compatibility shim — structure detection is mandatory.
#
# EZScore.py R30 still instantiates two legacy widgets:
# - setting_sections_enabled
# - setting_section_block_measures
#
# We neutralize those exact widget keys before rendering:
# - structure detection is always enabled;
# - the internal observation window is fixed at 4 measures.
#
# This keeps the R30 SSO/auth/application shell intact while removing the two
# obsolete choices from the UI. Only the similarity sensitivity remains user-
# adjustable.
# ---------------------------------------------------------------------------

_ORIGINAL_ST_CHECKBOX = st.checkbox
_ORIGINAL_ST_SELECTBOX = st.selectbox


def _ezscore_checkbox(*args, **kwargs):
    key = kwargs.get("key")
    if key == "setting_sections_enabled":
        st.session_state[key] = True
        return True
    return _ORIGINAL_ST_CHECKBOX(*args, **kwargs)


def _ezscore_selectbox(*args, **kwargs):
    key = kwargs.get("key")
    if key == "setting_section_block_measures":
        st.session_state[key] = 4
        return 4
    return _ORIGINAL_ST_SELECTBOX(*args, **kwargs)


st.checkbox = _ezscore_checkbox
st.selectbox = _ezscore_selectbox


# ---------------------------------------------------------------------------
# R33 compatibility bridge — vocal pre-roll / post-roll.
#
# Primary timelines remain authoritative. Structural blocks are visual only.
# The legacy R30 orchestration still rebuilds block time_start/time_end from
# measure boundaries, which cuts lyrics sung before measure 1 (and potentially
# after the last detected measure).
#
# R33's structure engine already carries the correct visual envelope in
# detected_sections. We preserve it here without moving a single timestamp:
# - materialized first/last block inherit the wider detected envelope;
# - the block editor preview, which still queries raw measure boundaries,
#   transparently receives the same envelope through _source_words_for_interval.
#
# This bridge can disappear when EZScore.py is fully migrated to the canonical
# timeline API.
# ---------------------------------------------------------------------------

_ORIGINAL_MATERIALISER_STRUCTURE_BLOCKS = (
    _persistence.materialiser_structure_blocks
)
_ORIGINAL_SOURCE_WORDS_FOR_INTERVAL = (
    _persistence._source_words_for_interval
)

_LYRICS_ENVELOPE_STATE_KEY = "_ezscore_lyrics_visual_envelope"


def _ezscore_materialiser_structure_blocks(
    blocks,
    mesures,
    detected_sections,
):
    result = _ORIGINAL_MATERIALISER_STRUCTURE_BLOCKS(
        blocks=blocks,
        mesures=mesures,
        detected_sections=detected_sections,
    )

    if not result:
        st.session_state.pop(_LYRICS_ENVELOPE_STATE_KEY, None)
        return result

    raw_start = float(result[0].get("time_start", 0.0) or 0.0)
    raw_end = float(result[-1].get("time_end", raw_start) or raw_start)

    visual_start = raw_start
    visual_end = raw_end

    detected = [
        section
        for section in (detected_sections or [])
        if isinstance(section, dict)
    ]

    if detected:
        first_detected = min(
            detected,
            key=lambda section: int(
                section.get("measure_start", 10**9) or 10**9
            ),
        )
        last_detected = max(
            detected,
            key=lambda section: int(
                section.get("measure_end", 0) or 0
            ),
        )

        try:
            visual_start = min(
                raw_start,
                float(first_detected.get("time_start", raw_start)),
            )
        except (TypeError, ValueError):
            visual_start = raw_start

        try:
            visual_end = max(
                raw_end,
                float(last_detected.get("time_end", raw_end)),
            )
        except (TypeError, ValueError):
            visual_end = raw_end

    result[0]["time_start"] = visual_start
    result[-1]["time_end"] = visual_end

    st.session_state[_LYRICS_ENVELOPE_STATE_KEY] = {
        "measure_time_start": raw_start,
        "measure_time_end": raw_end,
        "visual_time_start": visual_start,
        "visual_time_end": visual_end,
    }

    if visual_start < raw_start or visual_end > raw_end:
        print(
            "[EZTRACE][LYRICS_ENVELOPE] "
            f"measure={raw_start:.3f}-{raw_end:.3f} "
            f"visual={visual_start:.3f}-{visual_end:.3f}"
        )

    return result


def _ezscore_source_words_for_interval(resultat, t0, t1):
    query_start = float(t0)
    query_end = float(t1)

    envelope = st.session_state.get(_LYRICS_ENVELOPE_STATE_KEY)
    if isinstance(envelope, dict):
        measure_start = float(
            envelope.get("measure_time_start", query_start)
        )
        measure_end = float(
            envelope.get("measure_time_end", query_end)
        )
        visual_start = float(
            envelope.get("visual_time_start", measure_start)
        )
        visual_end = float(
            envelope.get("visual_time_end", measure_end)
        )

        # Only the true first/last measure boundaries are expanded.
        # Middle block boundaries are never touched.
        if abs(query_start - measure_start) <= 0.010:
            query_start = min(query_start, visual_start)

        if abs(query_end - measure_end) <= 0.010:
            query_end = max(query_end, visual_end)

    return _ORIGINAL_SOURCE_WORDS_FOR_INTERVAL(
        resultat,
        query_start,
        query_end,
    )


# Patch the already imported persistence module BEFORE EZScore.py later performs
# `from ezscore.persistence import *`. The orchestration therefore receives the
# corrected functions without any change to auth/SSO, timelines or R33.
_persistence.materialiser_structure_blocks = (
    _ezscore_materialiser_structure_blocks
)
_persistence._source_words_for_interval = (
    _ezscore_source_words_for_interval
)


_SHELL_CSS = r"""
<style>
.ez-topbar {
    display:flex;
    align-items:center;
    gap:1rem;
    padding:.65rem .9rem;
    margin:0 0 .85rem 0;
    border:1px solid rgba(120,130,145,.24);
    border-radius:14px;
    background:linear-gradient(90deg, rgba(20,92,86,.24), rgba(18,25,34,.12));
}
.ez-topbar-logo {
    font-size:1.65rem;
    font-weight:900;
    white-space:nowrap;
}
.ez-topbar-search {
    flex:1;
    min-width:8rem;
    opacity:.8;
    border:1px solid rgba(120,130,145,.26);
    border-radius:999px;
    padding:.55rem .9rem;
}
.ez-topbar-user {
    font-weight:750;
    white-space:nowrap;
}
.ez-side-profile {
    text-align:center;
    padding:.7rem .25rem 1rem;
}
.ez-side-avatar {
    width:76px;
    height:76px;
    border-radius:50%;
    margin:0 auto .55rem;
    display:flex;
    align-items:center;
    justify-content:center;
    font-size:1.65rem;
    font-weight:900;
    background:rgba(45,180,160,.18);
    border:2px solid rgba(45,180,160,.55);
}
.ez-side-name {
    font-weight:850;
    line-height:1.2;
}
.ez-side-role {
    opacity:.68;
    font-size:.82rem;
    margin-top:.2rem;
}
.ez-side-profile-compact {
    display:flex;
    align-items:center;
    gap:.65rem;
    padding:.35rem .2rem .55rem;
}
.ez-side-avatar-compact {
    width:38px;
    height:38px;
    flex:0 0 38px;
    border-radius:50%;
    display:flex;
    align-items:center;
    justify-content:center;
    font-size:1rem;
    font-weight:900;
    background:rgba(45,180,160,.18);
    border:1px solid rgba(45,180,160,.65);
}
.ez-side-profile-compact .ez-side-name {
    font-size:.94rem;
}
.ez-side-profile-compact .ez-side-role {
    margin-top:.05rem;
    font-size:.72rem;
}
@media(max-width:900px) {
    .ez-topbar {flex-wrap:wrap}
    .ez-topbar-search {order:3; width:100%}
}
</style>
"""


def current_section() -> str:
    pending = st.session_state.get("_pending_main_menu")
    if pending:
        return str(pending)
    return str(st.session_state.get("main_menu", "Répertoire"))


def analysis_sidebar_active() -> bool:
    """Show analysis controls for imports, fresh songs, or explicit edit mode."""
    # Structural analysis is a permanent EZScore invariant.
    st.session_state["setting_sections_enabled"] = True
    st.session_state["setting_section_block_measures"] = 4
    section = current_section()

    if section == "Import":
        return allowed("song.edit")

    if section != "Chanson" or not allowed("song.edit"):
        return False

    active_hash = str(
        st.session_state.get("active_song_hash", "") or ""
    )
    if not active_hash:
        return False

    # R30 baseline fix:
    # a freshly imported song has no persisted analysis yet. It must expose
    # the analysis settings even though the song is opened in Vue mode.
    try:
        latest = load_latest_persisted_analysis(active_hash)
    except Exception as exc:
        print(
            "[EZTRACE][ANALYSIS_UI] "
            f"hash={active_hash[:12]} persistence_error={exc!r}"
        )
        latest = None

    if latest is None:
        print(
            "[EZTRACE][ANALYSIS_UI] "
            f"hash={active_hash[:12]} "
            "fresh_song=true show_settings=true"
        )
        return True

    mode_key = "song_mode_" + active_hash[:12]
    editing = st.session_state.get(mode_key) == "Édition"

    print(
        "[EZTRACE][ANALYSIS_UI] "
        f"hash={active_hash[:12]} "
        f"fresh_song=false edit_mode={editing}"
    )
    return editing


def render_app_header() -> None:
    st.markdown(_SHELL_CSS, unsafe_allow_html=True)
    user = current_user()
    if user:
        name = html.escape(str(user.get("display_name") or user.get("email") or "Compte"))
        role = html.escape(str(user.get("role") or "reader"))
        user_label = f"{name} · {role}"
    else:
        user_label = "Visiteur"

    st.markdown(
        f"""
        <div class="ez-topbar">
          <div class="ez-topbar-logo">🎸 EZScore</div>
          <div class="ez-topbar-search">🔎 Rechercher dans le répertoire</div>
          <div class="ez-topbar-user">👤 {user_label}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _goto(section: str) -> None:
    st.session_state["_pending_main_menu"] = section
    st.rerun()


def render_profile_sidebar() -> None:
    """Render global navigation without stealing space from song controls.

    Répertoire / Compte keep the richer profile presentation. Chanson / Import
    use a compact identity plus a collapsed secondary menu so the contextual
    song controls remain immediately reachable.
    """
    section = current_section()
    compact = section in ("Chanson", "Import")
    user = current_user()

    if user:
        name = str(user.get("display_name") or user.get("email") or "Compte")
        role = str(user.get("role") or "reader")
        initial = html.escape(name[:1].upper() if name else "?")
        avatar = avatar_value(user)

        if compact:
            if avatar:
                av_col, name_col = st.sidebar.columns([0.28, 0.72])
                with av_col:
                    st.image(avatar, width=42)
                with name_col:
                    st.markdown(
                        f"**{html.escape(name)}**  \n"
                        f"<small>{html.escape(role)}</small>",
                        unsafe_allow_html=True,
                    )
            else:
                st.sidebar.markdown(
                    f"""
                    <div class="ez-side-profile-compact">
                      <div class="ez-side-avatar-compact">{initial}</div>
                      <div>
                        <div class="ez-side-name">{html.escape(name)}</div>
                        <div class="ez-side-role">{html.escape(role)}</div>
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            if avatar:
                st.sidebar.image(avatar, width=76)
                st.sidebar.markdown(
                    f"<div style='text-align:center'>"
                    f"<div class='ez-side-name'>{html.escape(name)}</div>"
                    f"<div class='ez-side-role'>{html.escape(role)}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.sidebar.markdown(
                    f"""
                    <div class="ez-side-profile">
                      <div class="ez-side-avatar">{initial}</div>
                      <div class="ez-side-name">{html.escape(name)}</div>
                      <div class="ez-side-role">{html.escape(role)}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
    else:
        if compact:
            st.sidebar.markdown(
                """
                <div class="ez-side-profile-compact">
                  <div class="ez-side-avatar-compact">?</div>
                  <div>
                    <div class="ez-side-name">Visiteur</div>
                    <div class="ez-side-role">accès public</div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.sidebar.markdown(
                """
                <div class="ez-side-profile">
                  <div class="ez-side-avatar">?</div>
                  <div>
                    <div class="ez-side-name">Visiteur</div>
                    <div class="ez-side-role">accès public</div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    if compact:
        quick_col1, quick_col2 = st.sidebar.columns(2)
        with quick_col1:
            if st.button("🎵 Répertoire", key="shell_repertoire", width="stretch"):
                _goto("Répertoire")
        with quick_col2:
            if user:
                if st.button("👤 Profil", key="shell_profile", width="stretch"):
                    _goto("Compte")
            else:
                if st.button("🔐 Connexion", key="shell_login", width="stretch"):
                    _goto("Compte")

        if user:
            with st.sidebar.expander("☰ Navigation", expanded=False):
                if allowed("song.edit"):
                    if st.button(
                        "✏️ Mes éditions",
                        key="shell_edits",
                        width="stretch",
                    ):
                        _goto("Répertoire")
                    if st.button(
                        "⬆️ Importer",
                        key="shell_import",
                        width="stretch",
                    ):
                        _goto("Import")

                if allowed("admin.users"):
                    if st.button(
                        "👥 Utilisateurs & droits",
                        key="shell_admin_users",
                        width="stretch",
                    ):
                        st.session_state["_open_admin_users"] = True
                        _goto("Compte")

                if st.button(
                    "🚪 Déconnexion",
                    key="shell_logout",
                    width="stretch",
                ):
                    logout()
                    _goto("Répertoire")
        return

    if st.sidebar.button("🎵 Répertoire", key="shell_repertoire", width="stretch"):
        _goto("Répertoire")

    if user:
        if st.sidebar.button("👤 Mon profil", key="shell_profile", width="stretch"):
            _goto("Compte")

        if allowed("song.edit"):
            if st.sidebar.button("✏️ Mes éditions", key="shell_edits", width="stretch"):
                _goto("Répertoire")
            if st.sidebar.button("⬆️ Importer", key="shell_import", width="stretch"):
                _goto("Import")

        if allowed("admin.users"):
            st.sidebar.markdown("---")
            st.sidebar.caption("Administration")
            if st.sidebar.button(
                "👥 Utilisateurs & droits",
                key="shell_admin_users",
                width="stretch",
            ):
                st.session_state["_open_admin_users"] = True
                _goto("Compte")

        st.sidebar.markdown("---")
        if st.sidebar.button("🚪 Déconnexion", key="shell_logout", width="stretch"):
            logout()
            _goto("Répertoire")
    else:
        if st.sidebar.button(
            "🔐 Connexion / inscription",
            key="shell_login",
            width="stretch",
        ):
            _goto("Compte")
