"""Authentication and authorization foundation for EZScore."""

from __future__ import annotations

from enum import StrEnum


class Role(StrEnum):
    ADMIN = "admin"
    EDITOR = "editor"
    READER = "reader"
    ANONYMOUS = "anonymous"


PERMISSIONS = {
    Role.ADMIN: {"*"},
    Role.EDITOR: {
        "song.read",
        "song.import",
        "song.analyse",
        "song.edit",
        "song.validate",
        "song.publish",
    },
    Role.READER: {"song.read"},
    Role.ANONYMOUS: {"song.read_public"},
}

SSO_PROVIDERS = ("google", "facebook", "apple", "microsoft")


def can(role: Role | str, permission: str) -> bool:
    """Return whether a role owns a permission."""
    try:
        normalized = Role(role)
    except ValueError:
        normalized = Role.ANONYMOUS
    rights = PERMISSIONS[normalized]
    return "*" in rights or permission in rights
