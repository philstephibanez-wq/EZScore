"""EZScore authentication package."""

from .roles import Role, can
from .session import (
    allowed,
    current_role,
    current_user,
    initialize_auth,
    login,
    logout,
    require,
)
from .ui import render_account_bar, render_admin_users

__all__ = [
    "Role",
    "can",
    "allowed",
    "current_role",
    "current_user",
    "initialize_auth",
    "login",
    "logout",
    "require",
    "render_account_bar",
    "render_admin_users",
]
