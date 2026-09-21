"""Authentication, registration, profile and account administration UI."""

from __future__ import annotations

import importlib.util
import streamlit as st

from .roles import Role
from .session import (
    allowed,
    current_auth_method,
    current_user,
    login,
    login_oidc,
    logout,
    oidc_provider_status,
    register_and_login,
)
from .storage import (
    active_admin_count,
    avatar_value,
    create_initial_admin,
    create_user,
    delete_user,
    list_identities,
    list_users,
    reset_local_password,
    restore_provider_avatar,
    save_user_avatar,
    set_local_password,
    update_profile,
    update_user_access,
    user_count,
)

_AUTH_CSS = r"""
<style>
.ez-auth-hero {
  border:1px solid rgba(140,150,165,.28);
  border-radius:18px;
  padding:1.2rem;
  min-height:440px;
  background:
    radial-gradient(circle at 22% 28%, rgba(67,180,170,.18), transparent 34%),
    linear-gradient(145deg, rgba(38,120,216,.08), rgba(255,255,255,.02));
}
.ez-auth-logo {font-size:2rem;font-weight:900;margin-bottom:.65rem}
.ez-auth-tagline {font-size:1.35rem;font-weight:800;margin-top:1.3rem}
.ez-auth-sub {opacity:.72;line-height:1.45}
.ez-auth-or {text-align:center;opacity:.55;margin:.55rem 0}
.ez-profile-avatar {
  width:92px;height:92px;border-radius:50%;
  display:flex;align-items:center;justify-content:center;
  font-size:2rem;font-weight:900;
  background:rgba(60,180,165,.18);
  border:2px solid rgba(60,180,165,.55);
  margin-bottom:.7rem;
}
@media(max-width:640px){
  .ez-auth-hero{min-height:auto}
  .ez-auth-logo{font-size:1.6rem}
}
</style>
"""


def _provider_button(provider: str, label: str, key: str) -> None:
    ready, reason = oidc_provider_status(provider)
    authlib_available = importlib.util.find_spec("authlib") is not None
    enabled = bool(ready and authlib_available)

    if st.button(
        label if ready else label + " · à configurer",
        key=key,
        width="stretch",
        disabled=not enabled,
    ):
        try:
            login_oidc(provider)
        except Exception as exc:
            st.error(str(exc))

    if not ready:
        st.caption(reason)
    elif not authlib_available:
        st.caption(
            "Bibliothèque Authlib absente de l'environnement Python actif."
        )


def render_account_header() -> None:
    user = current_user()
    with st.container(border=True):
        c1, c2, c3 = st.columns([3.2, 1.2, 1.0])
        with c1:
            if user:
                name = str(user.get("display_name") or user.get("email") or "Compte")
                st.markdown("**👤 " + name + "** · rôle " + str(user.get("role") or "reader"))
            else:
                st.markdown("**👤 Visiteur** · accès public")
        with c2:
            if st.button(
                "Mon profil" if user else "Connexion / S'inscrire",
                key="auth_open_account",
                width="stretch",
            ):
                st.session_state["_pending_main_menu"] = "Compte"
                st.rerun()
        with c3:
            if user and st.button(
                "Déconnexion",
                key="auth_logout_header",
                width="stretch",
            ):
                logout()
                st.rerun()


def _render_login_panel() -> None:
    st.subheader("Connexion")
    c1, c2, c3 = st.columns(3)
    with c1:
        _provider_button("google", "Google", "auth_google")
    with c2:
        _provider_button("auth0", "Réseaux sociaux", "auth_social")
    with c3:
        _provider_button("apple", "Apple", "auth_apple")

    st.markdown('<div class="ez-auth-or">ou</div>', unsafe_allow_html=True)

    with st.form("auth_login_form", clear_on_submit=False):
        identifier = st.text_input("Nom affiché ou e-mail", key="auth_login_email")
        password = st.text_input(
            "Mot de passe",
            type="password",
            key="auth_login_password",
        )
        remember = st.checkbox(
            "Rester connecté 30 jours",
            value=True,
            help="La session locale est restaurée après un redémarrage de Streamlit.",
        )
        submitted = st.form_submit_button(
            "Se connecter",
            type="primary",
            width="stretch",
        )

    if submitted:
        if login(identifier, password, remember=remember):
            st.session_state["_pending_main_menu"] = "Répertoire"
            st.rerun()
        st.error("Identifiants invalides.")


def _render_registration_panel() -> None:
    st.subheader("Créer un compte")
    st.caption("Les nouveaux comptes sont créés avec le rôle reader.")

    with st.form("auth_register_form", clear_on_submit=False):
        display_name = st.text_input(
            "Nom affiché / login",
            help="Unique dans EZScore. Utilisable à la place de l'e-mail pour se connecter.",
        )
        email = st.text_input("E-mail", key="auth_register_email")
        password = st.text_input(
            "Mot de passe",
            type="password",
            key="auth_register_password",
        )
        confirm = st.text_input(
            "Confirmer le mot de passe",
            type="password",
            key="auth_register_confirm",
        )
        remember = st.checkbox(
            "Rester connecté 30 jours",
            value=True,
            key="auth_register_remember",
        )
        submitted = st.form_submit_button(
            "Créer mon compte",
            type="primary",
            width="stretch",
        )

    if submitted:
        if password != confirm:
            st.error("Les deux mots de passe sont différents.")
            return
        try:
            register_and_login(
                email=email,
                password=password,
                display_name=display_name,
                remember=remember,
            )
            st.session_state["_pending_main_menu"] = "Répertoire"
            st.rerun()
        except Exception as exc:
            st.error(str(exc))


def _render_initial_admin_setup() -> None:
    st.subheader("Initialisation d'EZScore")
    st.info(
        "Aucun administrateur n'existe dans cette nouvelle base. "
        "Créez le premier compte administrateur."
    )

    with st.form("auth_initial_admin_form", clear_on_submit=False):
        display_name = st.text_input(
            "Nom affiché / login",
            value="",
            help="Nom unique utilisé également pour la connexion locale.",
        )
        email = st.text_input(
            "E-mail administrateur",
            value="",
        )
        password = st.text_input(
            "Mot de passe",
            type="password",
            help="Au moins 8 caractères.",
        )
        confirm = st.text_input(
            "Confirmer le mot de passe",
            type="password",
        )
        submitted = st.form_submit_button(
            "Créer l'administrateur",
            type="primary",
            width="stretch",
        )

    if not submitted:
        return

    if password != confirm:
        st.error("Les deux mots de passe sont différents.")
        return

    try:
        create_initial_admin(
            email=email,
            password=password,
            display_name=display_name,
        )
        if not login(email, password, remember=True):
            raise RuntimeError(
                "Le compte administrateur a été créé mais la connexion "
                "automatique a échoué."
            )
        st.session_state["_pending_main_menu"] = "Répertoire"
        st.success("Administrateur créé.")
        st.rerun()
    except Exception as exc:
        st.error(str(exc))


def _render_profile(user: dict) -> None:
    name = str(user.get("display_name") or user.get("email") or "?")
    initial = name[:1].upper()
    avatar = avatar_value(user)

    c1, c2 = st.columns([1.0, 3.2])
    with c1:
        if avatar:
            st.image(avatar, width=96)
        else:
            st.markdown(
                '<div class="ez-profile-avatar">' + initial + '</div>',
                unsafe_allow_html=True,
            )
    with c2:
        st.subheader(name)
        st.write(str(user.get("email") or ""))
        st.caption(
            "Rôle : " + str(user.get("role") or "reader")
            + " · connexion : " + current_auth_method()
        )

    with st.form("profile_identity_form"):
        display_name = st.text_input(
            "Nom affiché / login",
            value=str(user.get("display_name") or ""),
            help="Ce nom est unique et peut être utilisé pour la connexion locale.",
        )
        save = st.form_submit_button(
            "Enregistrer le profil",
            type="primary",
            width="stretch",
        )
    if save:
        try:
            update_profile(int(user["user_id"]), display_name=display_name)
            st.success("Profil enregistré.")
            st.rerun()
        except Exception as exc:
            st.error(str(exc))

    st.markdown("#### Photo de profil")
    avatar_upload = st.file_uploader(
        "Importer / remplacer la photo",
        type=["jpg", "jpeg", "png", "webp"],
        key="profile_avatar_upload",
    )
    av1, av2 = st.columns(2)
    with av1:
        if st.button(
            "Enregistrer la photo",
            key="profile_avatar_save",
            width="stretch",
            disabled=avatar_upload is None,
        ):
            try:
                save_user_avatar(int(user["user_id"]), avatar_upload)
                st.rerun()
            except Exception as exc:
                st.error(str(exc))
    with av2:
        identities = list_identities(int(user["user_id"]))
        has_provider_picture = any(
            str(identity.get("picture_url") or "").strip()
            for identity in identities
        )
        if st.button(
            "Reprendre la photo Google / SSO",
            key="profile_avatar_provider",
            width="stretch",
            disabled=not has_provider_picture,
        ):
            try:
                restore_provider_avatar(int(user["user_id"]))
                st.rerun()
            except Exception as exc:
                st.error(str(exc))

    st.markdown("#### Sécurité")
    has_password = bool(user.get("has_local_password"))
    with st.form("profile_password_form"):
        current_password = st.text_input(
            "Mot de passe actuel",
            type="password",
            disabled=not has_password,
        )
        new_password = st.text_input("Nouveau mot de passe", type="password")
        confirm_password = st.text_input(
            "Confirmer le nouveau mot de passe",
            type="password",
        )
        change = st.form_submit_button("Changer le mot de passe", width="stretch")
    if change:
        if new_password != confirm_password:
            st.error("Les deux nouveaux mots de passe sont différents.")
        else:
            try:
                set_local_password(
                    int(user["user_id"]),
                    new_password=new_password,
                    current_password=current_password if has_password else None,
                )
                st.success("Mot de passe modifié.")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))

    identities = list_identities(int(user["user_id"]))
    if identities:
        st.markdown("#### Identités liées")
        for identity in identities:
            provider = str(identity.get("provider") or "oidc")
            email = str(identity.get("email") or "")
            has_picture = bool(str(identity.get("picture_url") or "").strip())
            st.caption(
                provider + " · " + email
                + (" · photo disponible" if has_picture else "")
            )

    if st.button("Se déconnecter", key="profile_logout", width="stretch"):
        logout()
        st.session_state["_pending_main_menu"] = "Répertoire"
        st.rerun()


def render_admin_users() -> None:
    if not allowed("admin.users"):
        return

    with st.expander(
        "Administration des utilisateurs",
        expanded=bool(st.session_state.pop("_open_admin_users", False)),
    ):
        with st.form("admin_create_user", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                email = st.text_input("E-mail du nouvel utilisateur")
                display_name = st.text_input(
                    "Nom affiché / login",
                    help="Unique. L'utilisateur pourra se connecter avec ce nom ou son e-mail.",
                )
            with c2:
                role = st.selectbox(
                    "Rôle",
                    [Role.READER.value, Role.EDITOR.value, Role.ADMIN.value],
                )
                password = st.text_input("Mot de passe initial", type="password")
            create = st.form_submit_button(
                "Créer le compte",
                type="primary",
                width="stretch",
            )

        if create:
            try:
                create_user(
                    email=email,
                    password=password,
                    display_name=display_name,
                    role=role,
                )
                st.rerun()
            except Exception as exc:
                st.error(str(exc))

        role_values = [Role.READER.value, Role.EDITOR.value, Role.ADMIN.value]

        for item in list_users():
            with st.container(border=True):
                st.markdown(
                    "**" + str(item["display_name"] or item["email"]) + "**  \n"
                    + str(item["email"])
                )
                st.caption(
                    "Morceaux assignés : " + str(int(item.get("assigned_songs") or 0))
                )

                login_name = st.text_input(
                    "Nom affiché / login",
                    value=str(item.get("display_name") or ""),
                    key="admin_display_" + str(item["user_id"]),
                )

                c1, c2, c3 = st.columns([1.0, .8, 1.4])
                with c1:
                    role = st.selectbox(
                        "Rôle",
                        role_values,
                        index=role_values.index(item["role"])
                        if item["role"] in role_values else 0,
                        key="admin_role_" + str(item["user_id"]),
                    )
                with c2:
                    active = st.toggle(
                        "Actif",
                        value=bool(item["active"]),
                        key="admin_active_" + str(item["user_id"]),
                    )
                with c3:
                    reset = st.text_input(
                        "Nouveau mot de passe",
                        type="password",
                        key="admin_password_" + str(item["user_id"]),
                    )

                b1, b2, b3 = st.columns(3)
                with b1:
                    if st.button(
                        "Enregistrer les droits",
                        key="admin_access_" + str(item["user_id"]),
                        width="stretch",
                    ):
                        try:
                            update_profile(
                                int(item["user_id"]),
                                display_name=login_name,
                            )
                            update_user_access(
                                int(item["user_id"]),
                                role=role,
                                active=active,
                            )
                            st.rerun()
                        except Exception as exc:
                            st.error(str(exc))
                with b2:
                    if st.button(
                        "Réinitialiser le mot de passe",
                        key="admin_reset_" + str(item["user_id"]),
                        width="stretch",
                        disabled=not bool(reset),
                    ):
                        try:
                            reset_local_password(int(item["user_id"]), reset)
                            st.success("Mot de passe modifié.")
                        except Exception as exc:
                            st.error(str(exc))
                with b3:
                    with st.popover("Supprimer", use_container_width=True):
                        st.warning("Cette suppression retire aussi les identités SSO liées.")
                        if st.button(
                            "Confirmer la suppression",
                            key="admin_delete_" + str(item["user_id"]),
                            type="primary",
                            width="stretch",
                        ):
                            try:
                                delete_user(int(item["user_id"]))
                                st.rerun()
                            except Exception as exc:
                                st.error(str(exc))


def render_account_page() -> None:
    st.markdown(_AUTH_CSS, unsafe_allow_html=True)
    st.header("Compte EZScore")

    users = user_count()
    if users == 0:
        _render_initial_admin_setup()
        return

    user = current_user()
    if user:
        _render_profile(user)
        render_admin_users()
        return

    admins = active_admin_count()

    left, right = st.columns([1.05, 1.0])

    with left:
        st.markdown(
            """
            <div class="ez-auth-hero">
              <div class="ez-auth-logo">EZScore</div>
              <div style="font-size:3rem">🎼 ♫ 🎧</div>
              <div class="ez-auth-tagline">Personnalisez votre lecture et vos partitions</div>
              <div class="ez-auth-sub">
                Retrouvez vos contenus, vos préférences et les fonctions réservées
                à votre compte. Sur tablette et smartphone, cette page reste
                entièrement tactile et sans hover obligatoire.
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with right:
        login_tab, register_tab = st.tabs(["Connexion", "Créer un compte"])
        with login_tab:
            _render_login_panel()
        with register_tab:
            _render_registration_panel()

        if admins == 0:
            st.error(
                "La base contient déjà des comptes mais aucun administrateur "
                "actif. Par sécurité, la récupération doit être faite côté "
                "serveur."
            )
