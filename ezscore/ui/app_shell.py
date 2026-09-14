"""Application shell: header, profile sidebar and contextual navigation."""

from __future__ import annotations

import html

import streamlit as st

from ezscore.auth import allowed, current_user, logout
from ezscore.auth.storage import avatar_value
from ezscore.ui.song_fsm import (
    is_analysis_phase,
    workflow_state,
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
    """Analysis settings visibility driven by workflow FSM."""
    section = current_section()

    if section == "Import":
        active = allowed("song.edit")
        print(
            "[EZTRACE][ANALYSIS_UI] "
            f"section=Import active={active}"
        )
        return active

    if section != "Chanson" or not allowed("song.edit"):
        return False

    active_hash = str(
        st.session_state.get("active_song_hash", "") or ""
    )
    if not active_hash:
        return False

    phase = workflow_state(active_hash)
    if is_analysis_phase(phase):
        print(
            "[EZTRACE][ANALYSIS_UI] "
            f"hash={active_hash[:12]} workflow={phase} active=True"
        )
        return True

    view_key = "song_view_" + active_hash[:12]
    mode_key = "song_mode_" + active_hash[:12]

    view = str(st.session_state.get(view_key, "") or "")
    mode = str(st.session_state.get(mode_key, "") or "")

    active = view == "Analyse" or mode == "Édition"

    print(
        "[EZTRACE][ANALYSIS_UI] "
        f"hash={active_hash[:12]} workflow={phase} "
        f"view={view or '-'} mode={mode or '-'} active={active}"
    )

    return active

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
    """Render global navigation unless analysis owns the sidebar."""
    active_hash = str(
        st.session_state.get("active_song_hash", "") or ""
    )
    if active_hash:
        phase = workflow_state(active_hash)
        if is_analysis_phase(phase):
            print(
                "[EZTRACE][SIDEBAR] "
                f"hash={active_hash[:12]} workflow={phase} shell=hidden"
            )
            return

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
                  <div class="ez-side-name">Visiteur</div>
                  <div class="ez-side-role">accès public</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # On a song/import page, keep global navigation secondary and collapsed.
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

    # Home/account: full navigation is useful and there is no song toolbar.
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
