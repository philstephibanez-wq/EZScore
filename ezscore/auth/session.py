"""Streamlit authentication session and OIDC helpers for EZScore."""

from __future__ import annotations

import re
import streamlit as st

from .roles import Role, can, normalize_role
from .storage import (
    authenticate_local,
    bootstrap_admin_from_env,
    get_user_by_id,
    register_reader,
    upsert_external_identity,
)

_SESSION_USER_ID = "_ezscore_auth_user_id"
_OIDC_USER_ID = "_ezscore_oidc_user_id"


def initialize_auth() -> None:
    bootstrap_admin_from_env()


def _streamlit_oidc_logged_in() -> bool:
    try:
        return bool(getattr(st.user, "is_logged_in", False))
    except Exception:
        return False


def _oidc_claims() -> dict:
    if not _streamlit_oidc_logged_in():
        return {}
    try:
        if hasattr(st.user, "to_dict"):
            return dict(st.user.to_dict())
        return dict(st.user)
    except Exception:
        return {}


def _provider_from_claims(claims: dict) -> str:
    issuer = str(claims.get("iss", "") or "").lower()
    if "accounts.google.com" in issuer:
        return "google"
    if "microsoftonline.com" in issuer or "login.microsoftonline.com" in issuer:
        return "microsoft"
    if "auth0.com" in issuer:
        return "auth0"
    if "appleid.apple.com" in issuer:
        return "apple"
    return "oidc"


def _auth_section() -> dict:
    try:
        raw = st.secrets.get("auth", {})
        return dict(raw)
    except Exception:
        return {}


def oidc_configured_providers() -> tuple[str, ...]:
    auth = _auth_section()
    providers = []
    for key, value in auth.items():
        if key in {"redirect_uri", "cookie_secret", "expose_tokens"}:
            continue
        if hasattr(value, "keys") or isinstance(value, dict):
            providers.append(str(key))
    return tuple(providers)


def _looks_placeholder(value: str) -> bool:
    text = str(value or "").strip()
    upper = text.upper()
    if not text:
        return True
    bad_fragments = (
        "GOOGLE_CLIENT_ID",
        "GOOGLE_CLIENT_SECRET",
        "MICROSOFT_CLIENT_ID",
        "MICROSOFT_CLIENT_SECRET",
        "AUTH0_CLIENT_ID",
        "AUTH0_CLIENT_SECRET",
        "REMPLACER",
        "VOTRE_TENANT",
        "YOUR_",
        "EXAMPLE",
    )
    if any(fragment in upper for fragment in bad_fragments):
        return True
    if re.search(r"x{4,}", text, flags=re.IGNORECASE):
        return True
    if text.startswith("123456789012-"):
        return True
    return False


def oidc_provider_status(provider: str) -> tuple[bool, str]:
    provider_name = str(provider or "").strip()
    auth = _auth_section()

    if not auth:
        return False, "Aucune configuration [auth] dans secrets.toml."

    redirect_uri = str(auth.get("redirect_uri", "") or "").strip()
    cookie_secret = str(auth.get("cookie_secret", "") or "").strip()

    if not redirect_uri.endswith("/oauth2callback"):
        return False, "redirect_uri doit finir par /oauth2callback."
    if _looks_placeholder(cookie_secret) or len(cookie_secret) < 24:
        return False, "cookie_secret absent ou encore d'exemple."

    section = auth.get(provider_name)
    if not isinstance(section, dict) and not hasattr(section, "keys"):
        return False, "Fournisseur non configuré."

    section = dict(section)
    client_id = str(section.get("client_id", "") or "").strip()
    client_secret = str(section.get("client_secret", "") or "").strip()
    metadata = str(section.get("server_metadata_url", "") or "").strip()

    if _looks_placeholder(client_id):
        return False, "client_id absent ou encore d'exemple."
    if _looks_placeholder(client_secret):
        return False, "client_secret absent ou encore d'exemple."
    if not metadata.startswith("https://"):
        return False, "server_metadata_url invalide."

    if provider_name == "google" and not client_id.endswith(".apps.googleusercontent.com"):
        return False, "Le client_id Google n'a pas le format attendu."

    return True, "Configuré"


def current_user() -> dict | None:
    if _streamlit_oidc_logged_in():
        linked_user_id = st.session_state.get(_OIDC_USER_ID)
        if linked_user_id is not None:
            user = get_user_by_id(int(linked_user_id))
            if user and user.get("active"):
                return user
            st.session_state.pop(_OIDC_USER_ID, None)

        claims = _oidc_claims()
        subject = str(claims.get("sub", "") or "").strip()
        email = str(
            claims.get("email")
            or claims.get("preferred_username")
            or ""
        ).strip()
        email_verified = claims.get("email_verified")
        if email_verified is False or str(email_verified).lower() == "false":
            return None

        display_name = str(
            claims.get("name")
            or claims.get("given_name")
            or email
            or ""
        ).strip()
        picture_url = str(claims.get("picture") or "").strip()

        if subject and email:
            try:
                user = upsert_external_identity(
                    provider=_provider_from_claims(claims),
                    subject=subject,
                    email=email,
                    display_name=display_name,
                    picture_url=picture_url,
                )
            except Exception:
                return None

            if user and user.get("active"):
                st.session_state[_OIDC_USER_ID] = int(user["user_id"])
                return user

        return None

    user_id = st.session_state.get(_SESSION_USER_ID)
    if user_id is None:
        return None

    user = get_user_by_id(int(user_id))
    if not user or not user.get("active"):
        st.session_state.pop(_SESSION_USER_ID, None)
        return None
    return user


def current_role() -> Role:
    user = current_user()
    return normalize_role(user.get("role") if user else Role.ANONYMOUS)


def current_auth_method() -> str:
    if _streamlit_oidc_logged_in():
        return _provider_from_claims(_oidc_claims())
    if st.session_state.get(_SESSION_USER_ID) is not None:
        return "local"
    return "anonymous"


def allowed(permission: str) -> bool:
    return can(current_role(), permission)


def require(permission: str) -> None:
    if not allowed(permission):
        raise PermissionError("Permission requise : " + str(permission))


def login(identifier: str, password: str) -> bool:
    user = authenticate_local(identifier, password)
    if not user:
        return False
    st.session_state[_SESSION_USER_ID] = int(user["user_id"])
    st.session_state.pop(_OIDC_USER_ID, None)
    return True


def register_and_login(
    *,
    email: str,
    password: str,
    display_name: str = "",
) -> dict:
    user = register_reader(
        email=email,
        password=password,
        display_name=display_name,
    )
    st.session_state[_SESSION_USER_ID] = int(user["user_id"])
    st.session_state.pop(_OIDC_USER_ID, None)
    return user


def login_oidc(provider: str) -> None:
    provider_name = str(provider or "").strip()
    ready, reason = oidc_provider_status(provider_name)
    if not ready:
        raise ValueError(reason)
    st.login(provider_name)


def logout() -> None:
    st.session_state.pop(_SESSION_USER_ID, None)
    st.session_state.pop(_OIDC_USER_ID, None)
    if _streamlit_oidc_logged_in():
        st.logout()
