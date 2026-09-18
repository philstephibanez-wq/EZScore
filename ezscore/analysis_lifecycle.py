from __future__ import annotations

"""Lifecycle operations for full analysis reset and full song deletion.

This module is intentionally independent from the Analyse UI. It owns only:
- persisted analysis/editorial purge;
- technical cache purge;
- explicit preservation rules for a complete re-analysis.

No song-specific rule is allowed here.
"""

from dataclasses import dataclass
from pathlib import Path
import shutil
import sqlite3
from typing import Iterable


# Reanalysis keeps the catalogue identity and social placement of the song.
# Everything else carrying audio_hash is considered analysis/editorial state.
_REANALYSIS_PRESERVED_TABLES = frozenset({
    "songs",
    "song_editor_assignments",
    "user_playlist_items",
    "song_ratings",
})


@dataclass(frozen=True)
class PurgeResult:
    audio_hash: str
    deleted_rows: int
    deleted_tables: tuple[str, ...]
    deleted_cache_dirs: tuple[str, ...]


def _clean_hash(audio_hash: str) -> str:
    value = str(audio_hash or "").strip().lower()
    if not value:
        raise ValueError("audio_hash vide")
    return value


def analysis_cache_dirs(
    app_dir: str | Path,
    audio_hash: str,
) -> list[Path]:
    """Return known technical cache directories for one song.

    The current STEM/Whisper/structure/MIDI pipeline is rooted below
    data/analysis/stem_lab/<audio_hash>.
    """
    app = Path(app_dir)
    value = _clean_hash(audio_hash)

    candidates = [
        app / "data" / "analysis" / "stem_lab" / value,
    ]

    # Future-proof without broad recursive deletion: if a direct analysis
    # namespace later stores one directory exactly named after the hash, it is
    # safe to remove as part of this song lifecycle.
    analysis_root = app / "data" / "analysis"
    if analysis_root.is_dir():
        direct = analysis_root / value
        if direct not in candidates:
            candidates.append(direct)

    return candidates


def purge_analysis_cache(
    app_dir: str | Path,
    audio_hash: str,
) -> tuple[str, ...]:
    deleted: list[str] = []

    for path in analysis_cache_dirs(app_dir, audio_hash):
        if not path.exists():
            continue
        if not path.is_dir():
            raise RuntimeError(
                f"Cache technique inattendu (pas un dossier) : {path}"
            )
        shutil.rmtree(path)
        deleted.append(str(path))

    return tuple(deleted)


def _audio_hash_tables(conn: sqlite3.Connection) -> list[str]:
    result: list[str] = []

    rows = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """
    ).fetchall()

    for (table_name,) in rows:
        columns = {
            row[1]
            for row in conn.execute(
                f'PRAGMA table_info("{table_name}")'
            ).fetchall()
        }
        if "audio_hash" in columns:
            result.append(str(table_name))

    return result


def purge_analysis_database(
    db_path: str | Path,
    audio_hash: str,
    *,
    preserved_tables: Iterable[str] = _REANALYSIS_PRESERVED_TABLES,
) -> tuple[int, tuple[str, ...]]:
    """Remove all analysis/editorial rows while preserving song identity.

    Explicitly preserved:
    - songs: title/artist/catalogue identity;
    - song_editor_assignments: assigned editor;
    - user_playlist_items: playlist membership and setlist position;
    - song_ratings: collective/social rating.

    Every other table with an audio_hash column is purged transactionally.
    """
    value = _clean_hash(audio_hash)
    keep = {str(name) for name in preserved_tables}
    deleted_rows = 0
    deleted_tables: list[str] = []

    with sqlite3.connect(Path(db_path)) as conn:
        conn.execute("BEGIN")
        try:
            for table_name in _audio_hash_tables(conn):
                if table_name in keep:
                    continue

                before = conn.total_changes
                conn.execute(
                    f'DELETE FROM "{table_name}" WHERE audio_hash = ?',
                    (value,),
                )
                changed = conn.total_changes - before
                if changed:
                    deleted_rows += int(changed)
                    deleted_tables.append(table_name)

            conn.commit()
        except Exception:
            conn.rollback()
            raise

    return deleted_rows, tuple(deleted_tables)


def full_reanalysis_reset(
    *,
    app_dir: str | Path,
    db_path: str | Path,
    audio_hash: str,
) -> PurgeResult:
    """Reset the musical/editorial analysis as if freshly imported.

    Audio/catalogue identity, cover, editor assignment, playlist membership,
    setlist order and ratings stay in place. Technical caches, analysis
    snapshots, workflow state, preferences and editorial corrections are reset.
    """
    value = _clean_hash(audio_hash)

    # Cache first: if Windows locks a STEM/preview file, fail before touching DB.
    deleted_cache_dirs = purge_analysis_cache(app_dir, value)

    deleted_rows, deleted_tables = purge_analysis_database(
        db_path,
        value,
    )

    return PurgeResult(
        audio_hash=value,
        deleted_rows=deleted_rows,
        deleted_tables=deleted_tables,
        deleted_cache_dirs=deleted_cache_dirs,
    )
