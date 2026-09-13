"""Authentication and account-management UI."""

from __future__ import annotations

import streamlit as st

from .roles import Role
from .session import allowed, current_user, login, logout
from .storage import (
    create_user,
    list_users,
    reset_local_password,
    update_user_access,
    user_count,
)


def render_account_bar() -> None:
    user = current_user()
    with st.container(border=True):
        c1, c2 = st.columns([3.0, 1.2])
        with c1:
            if user:
                name = str(user.get("display_name") or user.get("email") or "Compte")
                st.markdown("**👤 " + name + "** · " + str(user.get("role", "reader")))
            else:
                st.markdown("**👤 Visiteur** · accès public")
        with c2:
            if user:
                if st.button("Déconnexion", key="auth_logout", width="stretch"):
                    logout()
                    st.rerun()
            else:
                with st.popover("Connexion", width="stretch"):
                    with st.form("auth_login_form", clear_on_submit=False):
                        email = st.text_input(
                            "E-mail",
                            key="auth_login_email",
                        )
                        password = st.text_input(
                            "Mot de passe",
                            type="password",
                            key="auth_login_password",
                        )
                        submitted = st.form_submit_button(
                            "Se connecter",
                            type="primary",
                            width="stretch",
                        )
                    if submitted:
                        if login(email, password):
                            st.rerun()
                        st.error("Identifiants invalides.")

        if user_count() == 0:
            st.warning(
                "Aucun administrateur n'est configuré. Définissez "
                "EZSCORE_ADMIN_EMAIL et EZSCORE_ADMIN_PASSWORD dans "
                "l'environnement du serveur puis redémarrez EZScore."
            )


def render_admin_users() -> None:
    if not allowed("admin.users"):
        return

    with st.expander("👥 Utilisateurs et droits", expanded=False):
        st.caption(
            "Les droits sont contrôlés côté serveur. Le masquage de l'interface "
            "n'est qu'une conséquence de ces permissions."
        )

        with st.form("admin_create_user", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                email = st.text_input("E-mail du nouvel utilisateur")
                display_name = st.text_input("Nom affiché")
            with c2:
                role = st.selectbox(
                    "Rôle",
                    [Role.READER.value, Role.EDITOR.value, Role.ADMIN.value],
                )
                password = st.text_input("Mot de passe initial", type="password")
            create = st.form_submit_button("Créer le compte", type="primary")

        if create:
            try:
                create_user(
                    email=email,
                    password=password,
                    display_name=display_name,
                    role=role,
                )
                st.success("Compte créé.")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))

        role_values = [Role.READER.value, Role.EDITOR.value, Role.ADMIN.value]
        for user in list_users():
            with st.container(border=True):
                st.markdown(
                    "**" + str(user["display_name"] or user["email"]) + "**  \n"
                    + str(user["email"]) + " · " + str(user["auth_provider"])
                )
                c1, c2, c3 = st.columns([1.1, 0.8, 1.4])
                with c1:
                    new_role = st.selectbox(
                        "Rôle",
                        role_values,
                        index=role_values.index(user["role"])
                        if user["role"] in role_values
                        else 0,
                        key="admin_role_" + str(user["user_id"]),
                    )
                with c2:
                    active = st.toggle(
                        "Actif",
                        value=bool(user["active"]),
                        key="admin_active_" + str(user["user_id"]),
                    )
                with c3:
                    new_password = st.text_input(
                        "Nouveau mot de passe",
                        type="password",
                        key="admin_password_" + str(user["user_id"]),
                    )

                a1, a2 = st.columns(2)
                with a1:
                    if st.button(
                        "Enregistrer les droits",
                        key="admin_save_access_" + str(user["user_id"]),
                        width="stretch",
                    ):
                        try:
                            update_user_access(
                                int(user["user_id"]),
                                role=new_role,
                                active=active,
                            )
                            st.success("Droits enregistrés.")
                            st.rerun()
                        except Exception as exc:
                            st.error(str(exc))
                with a2:
                    if st.button(
                        "Changer le mot de passe",
                        key="admin_reset_password_" + str(user["user_id"]),
                        width="stretch",
                        disabled=not bool(new_password),
                    ):
                        try:
                            reset_local_password(int(user["user_id"]), new_password)
                            st.success("Mot de passe modifié.")
                        except Exception as exc:
                            st.error(str(exc))
