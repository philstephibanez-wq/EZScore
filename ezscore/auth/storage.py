"""Persistent EZScore accounts, profiles and external identities."""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import sqlite3
from datetime import datetime, timezone

from ezscore.persistence import DB_PATH
from .roles import Role, normalize_role

_PBKDF2_ITERATIONS = 310_000


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _email(value: str) -> str:
    return str(value or "").strip().lower()


def ensure_auth_schema() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS app_users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                display_name TEXT NOT NULL DEFAULT '',
                password_hash TEXT,
                role TEXT NOT NULL DEFAULT 'reader',
                active INTEGER NOT NULL DEFAULT 1,
                auth_provider TEXT NOT NULL DEFAULT 'local',
                provider_subject TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_login_at TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_app_users_provider_subject
            ON app_users(auth_provider, provider_subject)
            WHERE provider_subject IS NOT NULL
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS app_identities (
                identity_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                provider TEXT NOT NULL,
                subject TEXT NOT NULL,
                email TEXT NOT NULL DEFAULT '',
                display_name TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_login_at TEXT,
                UNIQUE(provider, subject),
                FOREIGN KEY(user_id) REFERENCES app_users(user_id)
                    ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_app_identities_user
            ON app_identities(user_id)
            """
        )
        conn.commit()


def _hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        str(password).encode("utf-8"),
        salt,
        _PBKDF2_ITERATIONS,
    )
    return "pbkdf2_sha256$" + str(_PBKDF2_ITERATIONS) + "$" + (
        base64.urlsafe_b64encode(salt).decode("ascii")
    ) + "$" + base64.urlsafe_b64encode(digest).decode("ascii")


def _verify_password(password: str, encoded: str | None) -> bool:
    if not encoded:
        return False
    try:
        algorithm, iterations_text, salt_text, digest_text = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        iterations = int(iterations_text)
        salt = base64.urlsafe_b64decode(salt_text.encode("ascii"))
        expected = base64.urlsafe_b64decode(digest_text.encode("ascii"))
        actual = hashlib.pbkdf2_hmac(
            "sha256",
            str(password).encode("utf-8"),
            salt,
            iterations,
        )
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False


def user_count() -> int:
    ensure_auth_schema()
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute("SELECT COUNT(*) FROM app_users").fetchone()
    return int(row[0] if row else 0)


def create_user(
    *,
    email: str,
    password: str,
    display_name: str = "",
    role: Role | str = Role.READER,
) -> dict:
    ensure_auth_schema()
    normalized_email = _email(email)
    if "@" not in normalized_email:
        raise ValueError("Adresse e-mail invalide.")
    if len(str(password)) < 8:
        raise ValueError("Le mot de passe doit contenir au moins 8 caractères.")

    normalized_role = normalize_role(role)
    if normalized_role == Role.ANONYMOUS:
        raise ValueError("anonymous n'est pas un compte persistant.")

    now = _now()
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.execute(
                """
                INSERT INTO app_users (
                    email, display_name, password_hash, role, active,
                    auth_provider, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, 1, 'local', ?, ?)
                """,
                (
                    normalized_email,
                    str(display_name or "").strip(),
                    _hash_password(password),
                    normalized_role.value,
                    now,
                    now,
                ),
            )
            conn.commit()
            user_id = int(cur.lastrowid)
    except sqlite3.IntegrityError as exc:
        raise ValueError("Un compte existe déjà avec cette adresse e-mail.") from exc

    return get_user_by_id(user_id)


def register_reader(
    *,
    email: str,
    password: str,
    display_name: str = "",
) -> dict:
    return create_user(
        email=email,
        password=password,
        display_name=display_name,
        role=Role.READER,
    )


def bootstrap_admin_from_env() -> bool:
    ensure_auth_schema()
    if user_count() != 0:
        return False

    email = _email(os.getenv("EZSCORE_ADMIN_EMAIL", ""))
    password = os.getenv("EZSCORE_ADMIN_PASSWORD", "")
    display_name = str(os.getenv("EZSCORE_ADMIN_NAME", "Administrateur")).strip()

    if not email or not password:
        return False

    create_user(
        email=email,
        password=password,
        display_name=display_name or "Administrateur",
        role=Role.ADMIN,
    )
    return True


def get_user_by_id(user_id: int) -> dict | None:
    ensure_auth_schema()
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            """
            SELECT user_id, email, display_name, role, active,
                   auth_provider, created_at, updated_at, last_login_at,
                   password_hash
            FROM app_users
            WHERE user_id = ?
            """,
            (int(user_id),),
        ).fetchone()

    if not row:
        return None

    keys = (
        "user_id", "email", "display_name", "role", "active",
        "auth_provider", "created_at", "updated_at", "last_login_at",
        "password_hash",
    )
    result = dict(zip(keys, row))
    result["active"] = bool(result["active"])
    result["has_local_password"] = bool(result.pop("password_hash", None))
    return result


def authenticate_local(email: str, password: str) -> dict | None:
    ensure_auth_schema()
    normalized_email = _email(email)

    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            """
            SELECT user_id, password_hash, active
            FROM app_users
            WHERE email = ?
            """,
            (normalized_email,),
        ).fetchone()

        if not row or not bool(row[2]) or not _verify_password(password, row[1]):
            return None

        now = _now()
        conn.execute(
            "UPDATE app_users SET last_login_at = ?, updated_at = ? WHERE user_id = ?",
            (now, now, int(row[0])),
        )
        conn.commit()

    return get_user_by_id(int(row[0]))


def upsert_external_identity(
    *,
    provider: str,
    subject: str,
    email: str,
    display_name: str = "",
) -> dict:
    """Link an OIDC identity to an EZScore account.

    Existing accounts are matched by e-mail. A new SSO account starts as reader.
    """
    ensure_auth_schema()
    provider_name = str(provider or "oidc").strip().lower() or "oidc"
    subject_value = str(subject or "").strip()
    normalized_email = _email(email)
    display = str(display_name or "").strip()

    if not subject_value:
        raise ValueError("Identité OIDC sans subject.")
    if "@" not in normalized_email:
        raise ValueError("Le fournisseur OIDC n'a pas fourni d'adresse e-mail.")

    now = _now()

    with sqlite3.connect(DB_PATH) as conn:
        identity = conn.execute(
            """
            SELECT user_id
            FROM app_identities
            WHERE provider = ? AND subject = ?
            """,
            (provider_name, subject_value),
        ).fetchone()

        if identity:
            user_id = int(identity[0])
            conn.execute(
                """
                UPDATE app_identities
                SET email = ?, display_name = ?, updated_at = ?, last_login_at = ?
                WHERE provider = ? AND subject = ?
                """,
                (
                    normalized_email,
                    display,
                    now,
                    now,
                    provider_name,
                    subject_value,
                ),
            )
        else:
            by_email = conn.execute(
                "SELECT user_id FROM app_users WHERE email = ?",
                (normalized_email,),
            ).fetchone()

            if by_email:
                user_id = int(by_email[0])
            else:
                cur = conn.execute(
                    """
                    INSERT INTO app_users (
                        email, display_name, password_hash, role, active,
                        auth_provider, provider_subject,
                        created_at, updated_at, last_login_at
                    )
                    VALUES (?, ?, NULL, 'reader', 1, ?, ?, ?, ?, ?)
                    """,
                    (
                        normalized_email,
                        display,
                        provider_name,
                        subject_value,
                        now,
                        now,
                        now,
                    ),
                )
                user_id = int(cur.lastrowid)

            conn.execute(
                """
                INSERT INTO app_identities (
                    user_id, provider, subject, email, display_name,
                    created_at, updated_at, last_login_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    provider_name,
                    subject_value,
                    normalized_email,
                    display,
                    now,
                    now,
                    now,
                ),
            )

        conn.execute(
            """
            UPDATE app_users
            SET last_login_at = ?, updated_at = ?,
                display_name = CASE
                    WHEN trim(display_name) = '' THEN ?
                    ELSE display_name
                END
            WHERE user_id = ?
            """,
            (now, now, display, user_id),
        )
        conn.commit()

    return get_user_by_id(user_id)


def list_identities(user_id: int) -> list[dict]:
    ensure_auth_schema()
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            """
            SELECT provider, subject, email, display_name, last_login_at
            FROM app_identities
            WHERE user_id = ?
            ORDER BY provider
            """,
            (int(user_id),),
        ).fetchall()

    return [
        {
            "provider": row[0],
            "subject": row[1],
            "email": row[2],
            "display_name": row[3],
            "last_login_at": row[4],
        }
        for row in rows
    ]


def update_profile(user_id: int, *, display_name: str) -> dict:
    display = str(display_name or "").strip()
    if len(display) > 120:
        raise ValueError("Le nom affiché est trop long.")

    ensure_auth_schema()
    with sqlite3.connect(DB_PATH) as conn:
        exists = conn.execute(
            "SELECT user_id FROM app_users WHERE user_id = ?",
            (int(user_id),),
        ).fetchone()
        if not exists:
            raise ValueError("Utilisateur introuvable.")

        conn.execute(
            """
            UPDATE app_users
            SET display_name = ?, updated_at = ?
            WHERE user_id = ?
            """,
            (display, _now(), int(user_id)),
        )
        conn.commit()

    return get_user_by_id(int(user_id))


def set_local_password(
    user_id: int,
    *,
    new_password: str,
    current_password: str | None = None,
) -> None:
    if len(str(new_password)) < 8:
        raise ValueError("Le mot de passe doit contenir au moins 8 caractères.")

    ensure_auth_schema()
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT password_hash FROM app_users WHERE user_id = ?",
            (int(user_id),),
        ).fetchone()
        if not row:
            raise ValueError("Utilisateur introuvable.")

        existing_hash = row[0]
        if existing_hash:
            if not current_password or not _verify_password(current_password, existing_hash):
                raise ValueError("Mot de passe actuel incorrect.")

        conn.execute(
            """
            UPDATE app_users
            SET password_hash = ?, updated_at = ?
            WHERE user_id = ?
            """,
            (_hash_password(new_password), _now(), int(user_id)),
        )
        conn.commit()


def list_users() -> list[dict]:
    ensure_auth_schema()
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            """
            SELECT user_id, email, display_name, role, active,
                   auth_provider, created_at, updated_at, last_login_at,
                   password_hash
            FROM app_users
            ORDER BY lower(email)
            """
        ).fetchall()

    keys = (
        "user_id", "email", "display_name", "role", "active",
        "auth_provider", "created_at", "updated_at", "last_login_at",
        "password_hash",
    )
    result = []
    for row in rows:
        item = dict(zip(keys, row))
        item["active"] = bool(item["active"])
        item["has_local_password"] = bool(item.pop("password_hash", None))
        result.append(item)
    return result


def update_user_access(user_id: int, *, role: Role | str, active: bool) -> None:
    normalized_role = normalize_role(role)
    if normalized_role == Role.ANONYMOUS:
        raise ValueError("anonymous n'est pas un rôle de compte.")

    ensure_auth_schema()
    with sqlite3.connect(DB_PATH) as conn:
        current = conn.execute(
            "SELECT role, active FROM app_users WHERE user_id = ?",
            (int(user_id),),
        ).fetchone()
        if not current:
            raise ValueError("Utilisateur introuvable.")

        removes_admin = (
            str(current[0]) == Role.ADMIN.value
            and bool(current[1])
            and (normalized_role != Role.ADMIN or not bool(active))
        )
        if removes_admin:
            remaining = conn.execute(
                """
                SELECT COUNT(*)
                FROM app_users
                WHERE role = 'admin' AND active = 1 AND user_id <> ?
                """,
                (int(user_id),),
            ).fetchone()
            if int(remaining[0] if remaining else 0) == 0:
                raise ValueError(
                    "Impossible de désactiver ou rétrograder le dernier administrateur."
                )

        conn.execute(
            """
            UPDATE app_users
            SET role = ?, active = ?, updated_at = ?
            WHERE user_id = ?
            """,
            (normalized_role.value, 1 if active else 0, _now(), int(user_id)),
        )
        conn.commit()


def reset_local_password(user_id: int, new_password: str) -> None:
    if len(str(new_password)) < 8:
        raise ValueError("Le mot de passe doit contenir au moins 8 caractères.")

    ensure_auth_schema()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            UPDATE app_users
            SET password_hash = ?, updated_at = ?
            WHERE user_id = ?
            """,
            (_hash_password(new_password), _now(), int(user_id)),
        )
        conn.commit()
