"""Read-only authentication persistence diagnostics for EZScore."""

from __future__ import annotations

import hashlib
import sqlite3
from typing import Any

import streamlit as st

from ezscore.persistence import DB_PATH
from . import session as auth_session
from .persistent import resolve_persistent_session


def _component_token(value: Any) -> str:
    try:
        return str(auth_session._component_token(value) or "").strip()
    except Exception:
        return ""


def _safe_user_id_from_token(token: str) -> int | None:
    if not token:
        return None
    try:
        return resolve_persistent_session(token)
    except Exception:
        return None


def _active_db_sessions() -> list[tuple]:
    try:
        with sqlite3.connect(DB_PATH) as conn:
            return conn.execute(
                """
                SELECT session_id, user_id, created_at, expires_at, revoked_at
                FROM app_sessions
                WHERE revoked_at IS NULL
                ORDER BY session_id DESC
                LIMIT 10
                """
            ).fetchall()
    except Exception:
        return []


def _oidc_state() -> tuple[bool, str]:
    try:
        logged = bool(auth_session._streamlit_oidc_logged_in())
    except Exception:
        logged = False

    provider = ""
    if logged:
        try:
            provider = str(
                auth_session._provider_from_claims(auth_session._oidc_claims())
                or ""
            )
        except Exception:
            provider = ""
    return logged, provider



def _request_cookie_names() -> list[str]:
    """Return request cookie names only; never return cookie values."""
    try:
        cookies = st.context.cookies
        return sorted(str(name) for name in cookies.keys())
    except Exception:
        return []


def _native_streamlit_cookie_state() -> dict:
    names = _request_cookie_names()
    exact = set(names)
    return {
        "cookie_names": names,
        "streamlit_user": "_streamlit_user" in exact,
        "streamlit_user_tokens": "_streamlit_user_tokens" in exact,
        "streamlit_related": [
            name for name in names
            if "streamlit" in name.lower()
            or "user" in name.lower()
            or "token" in name.lower()
        ],
    }


def _auth_config_snapshot() -> dict:
    """Read safe OIDC configuration metadata without exposing secrets."""
    try:
        auth = dict(st.secrets.get("auth", {}) or {})
    except Exception:
        auth = {}

    redirect_uri = str(auth.get("redirect_uri", "") or "").strip()
    cookie_secret = str(auth.get("cookie_secret", "") or "")

    fingerprint = "-"
    if cookie_secret:
        fingerprint = hashlib.sha256(
            cookie_secret.encode("utf-8")
        ).hexdigest()[:12]

    return {
        "redirect_uri": redirect_uri or "-",
        "cookie_secret_present": bool(cookie_secret),
        "cookie_secret_fingerprint": fingerprint,
    }


def auth_diagnostic_snapshot() -> dict:
    native = _native_streamlit_cookie_state()
    auth_config = _auth_config_snapshot()
    request_token = auth_session._request_persistent_token()
    component_value = st.session_state.get(
        auth_session._PERSIST_COMPONENT_KEY
    )
    component_token = _component_token(component_value)

    active_token = str(
        st.session_state.get(auth_session._PERSIST_TOKEN, "") or ""
    ).strip()
    store_token = str(
        st.session_state.get(auth_session._PERSIST_STORE, "") or ""
    ).strip()
    clear_pending = bool(
        st.session_state.get(auth_session._PERSIST_CLEAR, False)
    )

    local_user_id = st.session_state.get(auth_session._SESSION_USER_ID)
    oidc_user_id = st.session_state.get(auth_session._OIDC_USER_ID)

    oidc_logged, oidc_provider = _oidc_state()

    request_user_id = _safe_user_id_from_token(request_token)
    component_user_id = _safe_user_id_from_token(component_token)
    active_user_id = _safe_user_id_from_token(active_token)
    store_user_id = _safe_user_id_from_token(store_token)

    sessions = _active_db_sessions()

    if component_token:
        browser_bridge = "TOKEN REÇU"
    else:
        browser_bridge = "AUCUN TOKEN REÇU"

    if component_token and component_user_id is not None:
        restore = f"VALIDE → user_id={component_user_id}"
    elif component_token:
        restore = "TOKEN REÇU MAIS INVALIDE EN BDD"
    else:
        restore = "IMPOSSIBLE : aucun token navigateur remonté"

    return {
        "native_cookie_names": native["cookie_names"],
        "native_streamlit_user": native["streamlit_user"],
        "native_streamlit_user_tokens": native["streamlit_user_tokens"],
        "native_streamlit_related": native["streamlit_related"],
        "redirect_uri": auth_config["redirect_uri"],
        "cookie_secret_present": auth_config["cookie_secret_present"],
        "cookie_secret_fingerprint": auth_config["cookie_secret_fingerprint"],
        "oidc_logged": oidc_logged,
        "oidc_provider": oidc_provider or "-",
        "request_has_token": bool(request_token),
        "request_user_id": request_user_id,
        "component_has_token": bool(component_token),
        "component_user_id": component_user_id,
        "active_has_token": bool(active_token),
        "active_user_id": active_user_id,
        "store_has_token": bool(store_token),
        "store_user_id": store_user_id,
        "clear_pending": clear_pending,
        "local_user_id": local_user_id,
        "oidc_user_id": oidc_user_id,
        "browser_bridge": browser_bridge,
        "restore": restore,
        "active_db_sessions": sessions,
    }


def render_auth_diagnostics() -> None:
    """Render a read-only diagnostic block on the Account page."""
    snap = auth_diagnostic_snapshot()

    with st.expander("Diagnostic session / persistance", expanded=True):
        st.caption(
            "Lecture seule. Aucun token brut, mot de passe ou secret OAuth "
            "n'est affiché."
        )

        st.markdown("#### OIDC natif Streamlit")
        native_cols = st.columns(3)
        with native_cols[0]:
            st.metric(
                "_streamlit_user",
                "PRESENT" if snap["native_streamlit_user"] else "ABSENT",
            )
        with native_cols[1]:
            st.metric(
                "_streamlit_user_tokens",
                "PRESENT"
                if snap["native_streamlit_user_tokens"]
                else "ABSENT",
            )
        with native_cols[2]:
            st.metric(
                "st.user",
                "connecté" if snap["oidc_logged"] else "non connecté",
            )

        st.code(
            "\n".join(
                [
                    "redirect_uri              : "
                    + str(snap["redirect_uri"]),
                    "cookie_secret présent     : "
                    + ("OUI" if snap["cookie_secret_present"] else "NON"),
                    "cookie_secret empreinte   : "
                    + str(snap["cookie_secret_fingerprint"]),
                    "_streamlit_user           : "
                    + ("PRESENT" if snap["native_streamlit_user"] else "ABSENT"),
                    "_streamlit_user_tokens    : "
                    + (
                        "PRESENT"
                        if snap["native_streamlit_user_tokens"]
                        else "ABSENT"
                    ),
                    "cookies Streamlit liés    : "
                    + (
                        ", ".join(snap["native_streamlit_related"])
                        if snap["native_streamlit_related"]
                        else "AUCUN"
                    ),
                ]
            ),
            language="text",
        )

        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric(
                "OIDC Streamlit",
                "connecté" if snap["oidc_logged"] else "non connecté",
            )
            st.caption("Provider : " + str(snap["oidc_provider"]))
        with c2:
            st.metric(
                "Bridge navigateur",
                snap["browser_bridge"],
            )
        with c3:
            st.metric(
                "Restauration DB",
                "valide"
                if snap["component_user_id"] is not None
                else "non restaurée",
            )

        st.code(
            "\n".join(
                [
                    "OIDC Streamlit       : "
                    + ("OUI" if snap["oidc_logged"] else "NON"),
                    "OIDC provider        : "
                    + str(snap["oidc_provider"]),
                    "OIDC user_id state   : "
                    + str(snap["oidc_user_id"]),
                    "Local user_id state  : "
                    + str(snap["local_user_id"]),
                    "",
                    "Cookie requête       : "
                    + ("PRESENT" if snap["request_has_token"] else "ABSENT"),
                    "Cookie requête -> DB : "
                    + str(snap["request_user_id"]),
                    "Composant navigateur : "
                    + ("TOKEN PRESENT" if snap["component_has_token"] else "ABSENT"),
                    "Token composant -> DB: "
                    + str(snap["component_user_id"]),
                    "Token actif Python   : "
                    + ("PRESENT" if snap["active_has_token"] else "ABSENT"),
                    "Token actif -> DB    : "
                    + str(snap["active_user_id"]),
                    "Token à écrire       : "
                    + ("PRESENT" if snap["store_has_token"] else "ABSENT"),
                    "Token à écrire -> DB : "
                    + str(snap["store_user_id"]),
                    "Effacement en attente: "
                    + ("OUI" if snap["clear_pending"] else "NON"),
                    "",
                    "Diagnostic restauration : " + str(snap["restore"]),
                ]
            ),
            language="text",
        )

        sessions = snap["active_db_sessions"]
        st.write("Sessions serveur actives :", len(sessions))
        if sessions:
            rows = [
                {
                    "session_id": row[0],
                    "user_id": row[1],
                    "created_at": row[2],
                    "expires_at": row[3],
                }
                for row in sessions
            ]
            st.dataframe(rows, width="stretch", hide_index=True)
        else:
            st.warning("Aucune session active trouvée dans app_sessions.")

        if st.button(
            "Actualiser le diagnostic",
            key="auth_diag_refresh",
            width="stretch",
        ):
            st.rerun()
