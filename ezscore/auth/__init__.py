"""EZScore authentication package."""

from .roles import Role, can
from .session import (
    allowed,
    current_auth_method,
    current_role,
    current_user,
    initialize_auth,
    login,
    login_oidc,
    logout,
    oidc_configured_providers,
    oidc_provider_status,
    register_and_login,
    require,
)
from .ui import (
    render_account_header,
    render_account_page as _render_account_page,
    render_admin_users,
)
from .diagnostics import render_auth_diagnostics


def render_account_page() -> None:
    """Account page plus temporary read-only persistence diagnostics."""
    render_auth_diagnostics()
    _render_account_page()


__all__ = [
    "Role",
    "can",
    "allowed",
    "current_auth_method",
    "current_role",
    "current_user",
    "initialize_auth",
    "login",
    "login_oidc",
    "logout",
    "oidc_configured_providers",
    "oidc_provider_status",
    "register_and_login",
    "require",
    "render_account_header",
    "render_account_page",
    "render_admin_users",
]
