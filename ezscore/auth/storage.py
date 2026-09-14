"""Persistent EZScore accounts, profiles and external identities."""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from ezscore.persistence import APP_DIR, DB_PATH
from .roles import Role, normalize_role

_PBKDF2_ITERATIONS = 310_000
AVATAR_DIR = APP_DIR / "data" / "avatars"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _email(value: str) -> str:
    return str(value or "").strip().lower()


def _display_name(value: str) -> str:
    return str(value or "").strip()


def _assert_unique_display_name(
    conn: sqlite3.Connection,
    display_name: str,
    *,
    exclude_user_id: int | None = None,
) -> None:
    display = _display_name(display_name)
    if not display:
        raise ValueError("Le nom affiché / login est obligatoire.")
    if len(display) > 120:
        raise ValueError("Le nom affiché / login est trop long.")

    if exclude_user_id is None:
        row = conn.execute(
            "SELECT user_id FROM app_users "
            "WHERE display_name = ? COLLATE NOCASE",
            (display,),
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT user_id FROM app_users "
            "WHERE display_name = ? COLLATE NOCASE AND user_id <> ?",
            (display, int(exclude_user_id)),
        ).fetchone()

    if row:
        raise ValueError("Ce nom affiché / login est déjà utilisé.")


def _unique_external_display_name(conn: sqlite3.Connection, value: str, email: str) -> str:
    base = _display_name(value) or str(email or "").split("@", 1)[0].strip() or "Utilisateur"
    candidate = base
    suffix = 2
    while conn.execute(
        "SELECT 1 FROM app_users WHERE display_name = ? COLLATE NOCASE",
        (candidate,),
    ).fetchone():
        candidate = f"{base}-{suffix}"
        suffix += 1
    return candidate


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
        user_columns = {
            row[1]
            for row in conn.execute("PRAGMA table_info(app_users)").fetchall()
        }
        for column, sql_type in {
            "avatar_path": "TEXT NOT NULL DEFAULT ''",
            "avatar_url": "TEXT NOT NULL DEFAULT ''",
            "avatar_source": "TEXT NOT NULL DEFAULT ''",
        }.items():
            if column not in user_columns:
                conn.execute(
                    f"ALTER TABLE app_users ADD COLUMN {column} {sql_type}"
                )

        # display_name is also the local login. Existing empty/duplicate names
        # are normalized once before the unique NOCASE index is created.
        rows = conn.execute(
            "SELECT user_id, email, display_name FROM app_users ORDER BY user_id"
        ).fetchall()
        seen = set()
        for user_id, email, display_name in rows:
            base = str(display_name or "").strip()
            if not base:
                base = str(email or "").split("@", 1)[0].strip() or f"user{user_id}"
            candidate = base
            suffix = 2
            while candidate.casefold() in seen:
                candidate = f"{base}-{suffix}"
                suffix += 1
            seen.add(candidate.casefold())
            if candidate != str(display_name or ""):
                conn.execute(
                    "UPDATE app_users SET display_name = ? WHERE user_id = ?",
                    (candidate, int(user_id)),
                )

        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_app_users_display_name_nocase
            ON app_users(display_name COLLATE NOCASE)
            WHERE trim(display_name) <> ''
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
        identity_columns = {
            row[1]
            for row in conn.execute("PRAGMA table_info(app_identities)").fetchall()
        }
        if "picture_url" not in identity_columns:
            conn.execute(
                "ALTER TABLE app_identities ADD COLUMN "
                "picture_url TEXT NOT NULL DEFAULT ''"
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

    display = _display_name(display_name)
    normalized_role = normalize_role(role)
    if normalized_role == Role.ANONYMOUS:
        raise ValueError("anonymous n'est pas un compte persistant.")

    now = _now()
    try:
        with sqlite3.connect(DB_PATH) as conn:
            _assert_unique_display_name(conn, display)
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
                    display,
                    _hash_password(password),
                    normalized_role.value,
                    now,
                    now,
                ),
            )
            conn.commit()
            user_id = int(cur.lastrowid)
    except sqlite3.IntegrityError as exc:
        raise ValueError(
            "Un compte existe déjà avec cet e-mail ou ce nom affiché / login."
        ) from exc

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
    """Create or recover the explicitly configured administrator.

    If EZSCORE_ADMIN_EMAIL matches an existing account, that account is
    promoted to active admin instead of creating a duplicate. This is useful
    after restoring a database whose role assignments were lost.
    """
    ensure_auth_schema()

    email = _email(os.getenv("EZSCORE_ADMIN_EMAIL", ""))
    password = os.getenv("EZSCORE_ADMIN_PASSWORD", "")
    display_name = str(os.getenv("EZSCORE_ADMIN_NAME", "Administrateur")).strip()

    if not email or not password:
        return False

    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT user_id, password_hash FROM app_users WHERE email = ?",
            (email,),
        ).fetchone()

        if row:
            user_id = int(row[0])
            password_hash = row[1] or _hash_password(password)
            conn.execute(
                """
                UPDATE app_users
                SET role = 'admin',
                    active = 1,
                    password_hash = ?,
                    display_name = CASE
                        WHEN trim(display_name) = '' THEN ?
                        ELSE display_name
                    END,
                    updated_at = ?
                WHERE user_id = ?
                """,
                (password_hash, display_name or "Administrateur", _now(), user_id),
            )
            conn.commit()
            return True

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
                   password_hash, avatar_path, avatar_url, avatar_source
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
        "password_hash", "avatar_path", "avatar_url", "avatar_source",
    )
    result = dict(zip(keys, row))
    result["active"] = bool(result["active"])
    result["has_local_password"] = bool(result.pop("password_hash", None))
    return result


def authenticate_local(identifier: str, password: str) -> dict | None:
    ensure_auth_schema()
    raw_identifier = str(identifier or "").strip()
    normalized_email = _email(raw_identifier)

    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            """
            SELECT user_id, password_hash, active
            FROM app_users
            WHERE email = ?
               OR display_name = ? COLLATE NOCASE
            LIMIT 1
            """,
            (normalized_email, raw_identifier),
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
    picture_url: str = "",
) -> dict:
    """Link an OIDC identity to an EZScore account.

    Existing accounts are matched by e-mail. A new SSO account starts as reader.
    """
    ensure_auth_schema()
    provider_name = str(provider or "oidc").strip().lower() or "oidc"
    subject_value = str(subject or "").strip()
    normalized_email = _email(email)
    display = str(display_name or "").strip()
    picture = str(picture_url or "").strip()

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
                SET email = ?, display_name = ?, picture_url = ?,
                    updated_at = ?, last_login_at = ?
                WHERE provider = ? AND subject = ?
                """,
                (
                    normalized_email,
                    display,
                    picture,
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
                account_display = _unique_external_display_name(
                    conn, display, normalized_email
                )
                cur = conn.execute(
                    """
                    INSERT INTO app_users (
                        email, display_name, password_hash, role, active,
                        auth_provider, provider_subject,
                        created_at, updated_at, last_login_at,
                        avatar_url, avatar_source
                    )
                    VALUES (?, ?, NULL, 'reader', 1, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        normalized_email,
                        account_display,
                        provider_name,
                        subject_value,
                        now,
                        now,
                        now,
                        picture,
                        provider_name if picture else "",
                    ),
                )
                user_id = int(cur.lastrowid)

            conn.execute(
                """
                INSERT INTO app_identities (
                    user_id, provider, subject, email, display_name,
                    picture_url, created_at, updated_at, last_login_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    provider_name,
                    subject_value,
                    normalized_email,
                    display,
                    picture,
                    now,
                    now,
                    now,
                ),
            )

        conn.execute(
            """
            UPDATE app_users
            SET last_login_at = ?, updated_at = ?,
                avatar_url = CASE
                    WHEN trim(avatar_path) = '' AND ? <> '' THEN ?
                    ELSE avatar_url
                END,
                avatar_source = CASE
                    WHEN trim(avatar_path) = '' AND ? <> '' THEN ?
                    ELSE avatar_source
                END
            WHERE user_id = ?
            """,
            (
                now, now,
                picture, picture,
                picture, provider_name,
                user_id,
            ),
        )
        conn.commit()

    return get_user_by_id(user_id)


def list_identities(user_id: int) -> list[dict]:
    ensure_auth_schema()
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            """
            SELECT provider, subject, email, display_name, picture_url, last_login_at
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
            "picture_url": row[4],
            "last_login_at": row[5],
        }
        for row in rows
    ]


def update_profile(user_id: int, *, display_name: str) -> dict:
    display = _display_name(display_name)

    ensure_auth_schema()
    with sqlite3.connect(DB_PATH) as conn:
        exists = conn.execute(
            "SELECT user_id FROM app_users WHERE user_id = ?",
            (int(user_id),),
        ).fetchone()
        if not exists:
            raise ValueError("Utilisateur introuvable.")

        _assert_unique_display_name(
            conn,
            display,
            exclude_user_id=int(user_id),
        )
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


def save_user_avatar(user_id: int, uploaded_file) -> dict:
    ensure_auth_schema()
    if uploaded_file is None:
        raise ValueError("Aucune image sélectionnée.")

    suffix = Path(str(getattr(uploaded_file, "name", "") or "")).suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
        raise ValueError("Format avatar non supporté.")

    AVATAR_DIR.mkdir(parents=True, exist_ok=True)
    for old in AVATAR_DIR.glob(f"user_{int(user_id)}.*"):
        try:
            old.unlink()
        except OSError:
            pass

    target = AVATAR_DIR / f"user_{int(user_id)}{suffix}"
    target.write_bytes(uploaded_file.getvalue())
    relative = str(target.relative_to(APP_DIR))

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            UPDATE app_users
            SET avatar_path = ?, avatar_source = 'local', updated_at = ?
            WHERE user_id = ?
            """,
            (relative, _now(), int(user_id)),
        )
        conn.commit()

    return get_user_by_id(int(user_id))


def restore_provider_avatar(user_id: int) -> dict:
    ensure_auth_schema()
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            """
            SELECT provider, picture_url
            FROM app_identities
            WHERE user_id = ? AND trim(picture_url) <> ''
            ORDER BY CASE WHEN provider = 'google' THEN 0 ELSE 1 END,
                     identity_id
            LIMIT 1
            """,
            (int(user_id),),
        ).fetchone()

        if not row:
            raise ValueError("Aucune photo de fournisseur disponible.")

        for old in AVATAR_DIR.glob(f"user_{int(user_id)}.*"):
            try:
                old.unlink()
            except OSError:
                pass

        conn.execute(
            """
            UPDATE app_users
            SET avatar_path = '', avatar_url = ?, avatar_source = ?, updated_at = ?
            WHERE user_id = ?
            """,
            (str(row[1] or ""), str(row[0] or ""), _now(), int(user_id)),
        )
        conn.commit()

    return get_user_by_id(int(user_id))


def avatar_value(user: dict | None):
    user = user or {}
    raw_path = str(user.get("avatar_path", "") or "").strip()
    if raw_path:
        candidate = Path(raw_path)
        if not candidate.is_absolute():
            candidate = APP_DIR / candidate
        if candidate.is_file():
            return str(candidate)

    url = str(user.get("avatar_url", "") or "").strip()
    return url or None


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
        has_assignments = conn.execute(
            """
            SELECT 1 FROM sqlite_master
            WHERE type = 'table' AND name = 'song_editor_assignments'
            """
        ).fetchone() is not None

        if has_assignments:
            rows = conn.execute(
                """
                SELECT u.user_id, u.email, u.display_name, u.role, u.active,
                       u.auth_provider, u.created_at, u.updated_at,
                       u.last_login_at, u.password_hash,
                       u.avatar_path, u.avatar_url, u.avatar_source,
                       COUNT(a.audio_hash) AS assigned_songs
                FROM app_users u
                LEFT JOIN song_editor_assignments a
                       ON a.user_id = u.user_id
                GROUP BY u.user_id
                ORDER BY lower(u.display_name), lower(u.email)
                """
            ).fetchall()
        else:
            rows = [
                tuple(row) + (0,)
                for row in conn.execute(
                    """
                    SELECT user_id, email, display_name, role, active,
                           auth_provider, created_at, updated_at, last_login_at,
                           password_hash, avatar_path, avatar_url, avatar_source
                    FROM app_users
                    ORDER BY lower(display_name), lower(email)
                    """
                ).fetchall()
            ]

    keys = (
        "user_id", "email", "display_name", "role", "active",
        "auth_provider", "created_at", "updated_at", "last_login_at",
        "password_hash", "avatar_path", "avatar_url", "avatar_source",
        "assigned_songs",
    )
    result = []
    for row in rows:
        item = dict(zip(keys, row))
        item["active"] = bool(item["active"])
        item["has_local_password"] = bool(item.pop("password_hash", None))
        item["assigned_songs"] = int(item.get("assigned_songs") or 0)
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


def delete_user(user_id: int) -> None:
    """Delete a user and linked identities, while protecting the last admin."""
    ensure_auth_schema()
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT role, active FROM app_users WHERE user_id = ?",
            (int(user_id),),
        ).fetchone()
        if not row:
            raise ValueError("Utilisateur introuvable.")

        if str(row[0]) == Role.ADMIN.value and bool(row[1]):
            remaining = conn.execute(
                """
                SELECT COUNT(*)
                FROM app_users
                WHERE role = 'admin' AND active = 1 AND user_id <> ?
                """,
                (int(user_id),),
            ).fetchone()
            if int(remaining[0] if remaining else 0) == 0:
                raise ValueError("Impossible de supprimer le dernier administrateur actif.")

        conn.execute(
            "DELETE FROM app_identities WHERE user_id = ?",
            (int(user_id),),
        )
        conn.execute(
            "DELETE FROM app_users WHERE user_id = ?",
            (int(user_id),),
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
