"""Streamlit authentication session and OIDC helpers for EZScore."""

from __future__ import annotations

import re
import streamlit as st

from ezscore.persistence import init_persistence
from .persistent import (
    SESSION_DAYS,
    create_persistent_session,
    ensure_persistent_session_schema,
    resolve_persistent_session,
    revoke_persistent_session,
)
from .roles import Role, can, normalize_role
from .storage import (
    authenticate_local,
    ensure_auth_schema,
    get_user_by_id,
    register_reader,
    upsert_external_identity,
    user_count,
)

_SESSION_USER_ID = "_ezscore_auth_user_id"
_OIDC_USER_ID = "_ezscore_oidc_user_id"
_PERSIST_COMPONENT_KEY = "_ezscore_persistent_session_component"
_PERSIST_TOKEN = "_ezscore_persistent_active_token"
_PERSIST_STORE = "_ezscore_persistent_store_token"
_PERSIST_CLEAR = "_ezscore_persistent_clear"

_SESSION_COMPONENT = st.components.v2.component(
    "ezscore_auth_persistent_session_v1",
    html='<span class="ezscore-auth-session-bridge" hidden></span>',
    css=".ezscore-auth-session-bridge{display:none!important}",
    js=r"""
export default function(component) {
  const {data, setStateValue} = component;
  const cookieName = "ezscore_local_session";
  const known = String(data.known_token || "");
  const store = String(data.store_token || "");
  const clear = Boolean(data.clear_token);

  function readCookie() {
    const prefix = cookieName + "=";
    for (const part of document.cookie.split(";")) {
      const item = part.trim();
      if (item.startsWith(prefix)) {
        return decodeURIComponent(item.slice(prefix.length));
      }
    }
    return "";
  }

  function writeCookie(value, maxAge) {
    let cookie =
      cookieName + "=" + encodeURIComponent(value) +
      "; Path=/; Max-Age=" + String(maxAge) +
      "; SameSite=Lax";
    if (window.location.protocol === "https:") cookie += "; Secure";
    document.cookie = cookie;
  }

  const current = readCookie();

  if (clear) {
    if (current) writeCookie("", 0);
    if (known) setStateValue("token", "");
    return;
  }

  if (store) {
    if (current !== store) writeCookie(store, Number(data.max_age || 2592000));
    if (known !== store) setStateValue("token", store);
    return;
  }

  if (current !== known) setStateValue("token", current);
}
""",
    isolate_styles=True,
)


def _component_token(value) -> str:
    if value is None:
        return ""
    try:
        token = getattr(value, "token", None)
        if token is not None:
            return str(token or "").strip()
    except Exception:
        pass
    try:
        return str(value.get("token", "") or "").strip()
    except Exception:
        return ""


def initialize_auth() -> None:
    # FIRST RUN CONTRACT
    #
    # A missing SQLite database is a supported state. Build all dependent
    # schemas in dependency order before touching a persistent browser token:
    #
    #   persistence tables -> app_users/app_identities -> app_sessions
    #
    # The functions are idempotent, so the exact same path is also used on
    # every normal startup and after database restoration.
    init_persistence()
    ensure_auth_schema()
    ensure_persistent_session_schema()

    # FIRST RUN WEB GATE
    #
    # A brand-new database must never open on the catalogue as an anonymous
    # visitor. Until the first administrator exists, Compte is the only
    # admissible landing page. This code runs before the main navigation radio
    # is instantiated, therefore the Streamlit widget receives the correct
    # state from its first render.
    #
    # The gate is evaluated on every rerun while app_users is empty. A user
    # cannot bypass it by clicking another navigation item. Once the initial
    # admin form creates the first account, user_count() becomes > 0 and the
    # normal navigation resumes on the next rerun.
    if user_count() == 0:
        st.session_state["main_menu"] = "Compte"
        st.session_state["_pending_main_menu"] = "Compte"
        st.session_state.pop(_SESSION_USER_ID, None)
        st.session_state.pop(_OIDC_USER_ID, None)

    existing = st.session_state.get(_PERSIST_COMPONENT_KEY)
    known_token = _component_token(existing)
    store_token = str(st.session_state.get(_PERSIST_STORE, "") or "")
    clear_token = bool(st.session_state.get(_PERSIST_CLEAR, False))

    def _on_token_change() -> None:
        # Required by Streamlit Components V2 for state names used in `default`.
        # The actual value is read from the component result just below.
        return None

    result = _SESSION_COMPONENT(
        data={
            "known_token": known_token,
            "store_token": store_token,
            "clear_token": clear_token,
            "max_age": int(SESSION_DAYS * 24 * 60 * 60),
        },
        default={"token": known_token},
        key=_PERSIST_COMPONENT_KEY,
        on_token_change=_on_token_change,
    )
    browser_token = _component_token(result)

    if store_token and browser_token == store_token:
        st.session_state.pop(_PERSIST_STORE, None)
    if clear_token and not browser_token:
        st.session_state.pop(_PERSIST_CLEAR, None)
    if browser_token:
        st.session_state[_PERSIST_TOKEN] = browser_token

    if (
        not _streamlit_oidc_logged_in()
        and st.session_state.get(_SESSION_USER_ID) is None
        and browser_token
    ):
        user_id = resolve_persistent_session(browser_token)
        if user_id is not None:
            st.session_state[_SESSION_USER_ID] = int(user_id)
        else:
            # Typical first-run case with an old browser cookie and a new DB:
            # clear the obsolete cookie instead of crashing on a missing user.
            st.session_state.pop(_PERSIST_TOKEN, None)
            st.session_state[_PERSIST_CLEAR] = True


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
        if st.session_state.get(_PERSIST_TOKEN):
            return "local · session persistante"
        return "local"
    return "anonymous"


def allowed(permission: str) -> bool:
    return can(current_role(), permission)


def require(permission: str) -> None:
    if not allowed(permission):
        raise PermissionError("Permission requise : " + str(permission))


def login(identifier: str, password: str, *, remember: bool = False) -> bool:
    user = authenticate_local(identifier, password)
    if not user:
        return False

    st.session_state[_SESSION_USER_ID] = int(user["user_id"])
    st.session_state.pop(_OIDC_USER_ID, None)

    if remember:
        token = create_persistent_session(int(user["user_id"]))
        st.session_state[_PERSIST_TOKEN] = token
        st.session_state[_PERSIST_STORE] = token
        st.session_state.pop(_PERSIST_CLEAR, None)
    else:
        old_token = str(st.session_state.pop(_PERSIST_TOKEN, "") or "")
        if old_token:
            revoke_persistent_session(old_token)
        st.session_state[_PERSIST_CLEAR] = True
    return True


def register_and_login(
    *,
    email: str,
    password: str,
    display_name: str = "",
    remember: bool = True,
) -> dict:
    user = register_reader(
        email=email,
        password=password,
        display_name=display_name,
    )
    st.session_state[_SESSION_USER_ID] = int(user["user_id"])
    st.session_state.pop(_OIDC_USER_ID, None)
    if remember:
        token = create_persistent_session(int(user["user_id"]))
        st.session_state[_PERSIST_TOKEN] = token
        st.session_state[_PERSIST_STORE] = token
    return user


def login_oidc(provider: str) -> None:
    provider_name = str(provider or "").strip()
    ready, reason = oidc_provider_status(provider_name)
    if not ready:
        raise ValueError(reason)
    st.login(provider_name)


def logout() -> None:
    token = str(st.session_state.pop(_PERSIST_TOKEN, "") or "")
    if token:
        revoke_persistent_session(token)
    st.session_state[_PERSIST_CLEAR] = True
    st.session_state.pop(_PERSIST_STORE, None)
    st.session_state.pop(_SESSION_USER_ID, None)
    st.session_state.pop(_OIDC_USER_ID, None)
    if _streamlit_oidc_logged_in():
        st.logout()
