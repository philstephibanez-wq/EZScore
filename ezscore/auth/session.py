"""Streamlit authentication session and server-side permission helpers."""

from __future__ import annotations

import streamlit as st

from .roles import Role, can, normalize_role
from .storage import authenticate_local, bootstrap_admin_from_env, get_user_by_id

_SESSION_USER_ID = "_ezscore_auth_user_id"


def initialize_auth() -> None:
    bootstrap_admin_from_env()


def current_user() -> dict | None:
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


def allowed(permission: str) -> bool:
    return can(current_role(), permission)


def require(permission: str) -> None:
    if not allowed(permission):
        raise PermissionError("Permission requise : " + str(permission))


def login(email: str, password: str) -> bool:
    user = authenticate_local(email, password)
    if not user:
        return False
    st.session_state[_SESSION_USER_ID] = int(user["user_id"])
    return True


def logout() -> None:
    st.session_state.pop(_SESSION_USER_ID, None)
