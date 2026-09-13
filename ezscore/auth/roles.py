"""Role and permission model for EZScore."""

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
        "song.read_public",
        "song.read_private",
        "song.import",
        "song.analyse",
        "song.edit",
        "song.validate",
        "song.publish",
        "song.delete",
    },
    Role.READER: {
        "song.read_public",
        "song.read_private",
    },
    Role.ANONYMOUS: {
        "song.read_public",
    },
}

SSO_PROVIDERS = ("google", "facebook", "apple", "microsoft")


def normalize_role(role: Role | str | None) -> Role:
    try:
        return Role(str(role))
    except (ValueError, TypeError):
        return Role.ANONYMOUS


def can(role: Role | str | None, permission: str) -> bool:
    normalized = normalize_role(role)
    rights = PERMISSIONS[normalized]
    return "*" in rights or str(permission) in rights
