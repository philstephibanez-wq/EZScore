"""SQLite persistence, editorial workflow and edit storage for EZScore."""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from difflib import SequenceMatcher
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import streamlit as st

from .notation import accord_forme_capo, formatter_mesure_signature
from .transcription import extraire_mots, _normaliser_pattern_mesure

__all__ = [
    'PERSISTENCE_SCHEMA_VERSION',
    'ANALYSIS_ENGINE_VERSION',
    'APP_DIR',
    'DATA_DIR',
    'AUDIO_DIR',
    'COVER_DIR',
    'DB_PATH',
    '_utc_now_iso',
    '_json_safe',
    'init_persistence',
    'audio_sha256',
    '_lyric_block_key',
    'load_lyric_block_edits',
    'resolve_lyric_block_edit',
    'save_lyric_block_edit',
    'save_lyric_block_edits_snapshot',
    'reset_lyric_block_edits',
    '_source_words_for_interval',
    '_redistribute_corrected_block_text',
    'effective_lyrics_words_for_sections',
    '_lyric_line_key',
    'load_lyric_line_edits',
    'save_lyric_line_edit',
    'reset_lyric_line_edits',
    '_words_from_corrected_text',
    'get_app_state',
    'set_app_state',
    'load_song_preferences',
    'save_song_preferences',
    'current_song_settings_payload',
    'prepare_song_preferences_for_open',
    'migrate_archived_audio_catalog',
    'persist_audio_source',
    'find_persisted_audio',
    'list_song_catalog',
    'catalog_primary_text',
    'catalog_secondary_text',
    'catalog_letter_for_song',
    'filter_catalog',
    'catalog_display_name',
    'ensure_song',
    'update_song_metadata',
    'get_song_editor_assignment',
    'assign_song_editor',
    '_cover_extension',
    'save_song_cover',
    'delete_song_cover',
    'song_cover_path',
    'load_block_edits',
    'save_block_edit',
    'libelle_bloc_affiche',
    'appliquer_editions_blocs',
    '_alpha_label_from_index',
    'validated_partition_modifications',
    'load_structure_blocks',
    '_save_structure_blocks',
    '_normaliser_partition_blocs',
    'ensure_structure_blocks',
    '_next_manual_cluster',
    'update_structure_block_sequential',
    '_structure_draft_key',
    '_structure_editor_revision_key',
    '_structure_action_message_key',
    '_canonical_structure_rows',
    '_structure_draft_is_dirty',
    '_structure_draft_from_persisted',
    '_get_structure_draft',
    '_set_structure_draft',
    '_normalize_structure_draft',
    '_apply_structure_table_live_edit',
    '_next_structure_draft_id',
    '_insert_structure_draft_after',
    '_append_structure_draft',
    '_delete_structure_draft_row',
    '_delete_structure_draft_rows',
    '_persist_structure_draft',
    'save_structure_blocks_from_table',
    'reset_structure_blocks_from_analysis',
    'add_structure_separator',
    'split_structure_block',
    'merge_structure_block_with_next',
    'materialiser_structure_blocks',
    'accord_reel_depuis_forme_capo',
    'parser_notation_mesure',
    'load_measure_edits',
    'save_measure_edit',
    'delete_measure_edit',
    'appliquer_editions_mesures_aux_beats',
    'notation_affichee_depuis_reelle',
    'notation_reelle_depuis_affichage',
    '_placer_texte_monospaced',
    '_placer_accords_monospaced',
    '_decaler_paroles_sous_accords',
    'construire_lignes_paroles_intervalle',
    'construire_lignes_paroles_completes_intervalle',
    'make_analysis_parameters',
    'make_analysis_key',
    'load_latest_analysis_parameters',
    'hydrate_settings_from_parameters',
    'next_analysis_version_no',
    '_song_version_snapshot_payload',
    '_editorial_date_fr',
    '_normalize_version_label',
    '_normalize_edition_label',
    '_next_version_label',
    'get_song_workflow',
    'list_song_editorial_versions',
    'latest_song_editorial_version',
    'get_song_editorial_version',
    'save_song_working_state',
    'save_working_note',
    'update_song_editorial_note',
    'publish_song_editorial_version',
    'resume_song_modifications',
    'editorial_status_label',
    'save_analysis_version',
    'list_analysis_versions',
    'load_analysis_version',
    'delete_analysis_version',
    '_audio_paths_for_hash',
    'delete_song_completely',
    'clear_deleted_song_session_state',
    'render_delete_song_controls',
    '_restore_song_version_snapshot',
    'prepare_analysis_version_for_open',
    'load_beat_edits',
    'save_beat_edit',
    'clear_beat_edits_for_measure',
    'appliquer_editions_beats',
    'reconstruire_mesures_depuis_beats',
    'render_beat_editor',
    'load_latest_persisted_analysis',
    'load_persisted_analysis',
    'save_persisted_analysis'
]

# ============================================================
# PERSISTANCE EZScore — SQLITE
# ============================================================

PERSISTENCE_SCHEMA_VERSION = 1
ANALYSIS_ENGINE_VERSION = "V29_R14_BALANCED_MIDI_EDITORIAL"

APP_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = APP_DIR / "data"
AUDIO_DIR = DATA_DIR / "audio"
COVER_DIR = DATA_DIR / "covers"
DB_PATH = DATA_DIR / "EZScore.sqlite3"


def _utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


def _json_safe(value):
    """Convertit récursivement les types numpy en JSON standard."""
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Path):
        return str(value)
    return value


def init_persistence():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    COVER_DIR.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS songs (
                audio_hash TEXT PRIMARY KEY,
                original_filename TEXT NOT NULL,
                title TEXT NOT NULL DEFAULT '',
                artist TEXT NOT NULL DEFAULT '',
                editor TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        song_columns = {
            row[1]
            for row in conn.execute(
                "PRAGMA table_info(songs)"
            ).fetchall()
        }

        if "editor" not in song_columns:
            conn.execute(
                "ALTER TABLE songs ADD COLUMN editor TEXT NOT NULL DEFAULT ''"
            )

        if "strumming_primary" not in song_columns:
            conn.execute(
                "ALTER TABLE songs ADD COLUMN strumming_primary "
                "TEXT NOT NULL DEFAULT ''"
            )

        if "strumming_secondary" not in song_columns:
            conn.execute(
                "ALTER TABLE songs ADD COLUMN strumming_secondary "
                "TEXT NOT NULL DEFAULT ''"
            )

        if "cover_path" not in song_columns:
            conn.execute(
                "ALTER TABLE songs ADD COLUMN cover_path "
                "TEXT NOT NULL DEFAULT ''"
            )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS song_editor_assignments (
                audio_hash TEXT PRIMARY KEY,
                user_id INTEGER,
                display_name TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL,
                FOREIGN KEY (audio_hash) REFERENCES songs(audio_hash)
                    ON DELETE CASCADE
            )
            """
        )

        conn.execute("""
            CREATE TABLE IF NOT EXISTS analyses (
                audio_hash TEXT NOT NULL,
                analysis_key TEXT NOT NULL,
                engine_version TEXT NOT NULL,
                parameters_json TEXT NOT NULL,
                music_json TEXT NOT NULL,
                whisper_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (audio_hash, analysis_key),
                FOREIGN KEY (audio_hash) REFERENCES songs(audio_hash)
                    ON DELETE CASCADE
            )
        """)

        # Prépare la future édition de noms de blocs sans l'activer
        # dans l'interface V25.
        conn.execute("""
            CREATE TABLE IF NOT EXISTS block_edits (
                audio_hash TEXT NOT NULL,
                block_cluster TEXT NOT NULL,
                custom_label TEXT NOT NULL DEFAULT '',
                measure_start INTEGER,
                measure_end INTEGER,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (audio_hash, block_cluster),
                FOREIGN KEY (audio_hash) REFERENCES songs(audio_hash)
                    ON DELETE CASCADE
            )
        """)

        columns = {
            row[1]
            for row in conn.execute(
                "PRAGMA table_info(block_edits)"
            ).fetchall()
        }

        if "measure_start" not in columns:
            conn.execute(
                "ALTER TABLE block_edits ADD COLUMN measure_start INTEGER"
            )

        if "measure_end" not in columns:
            conn.execute(
                "ALTER TABLE block_edits ADD COLUMN measure_end INTEGER"
            )


        conn.execute("""
            CREATE TABLE IF NOT EXISTS analysis_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                audio_hash TEXT NOT NULL,
                analysis_key TEXT NOT NULL,
                version_no INTEGER NOT NULL,
                parameters_json TEXT NOT NULL,
                music_json TEXT NOT NULL,
                whisper_json TEXT NOT NULL,
                title TEXT NOT NULL DEFAULT '',
                artist TEXT NOT NULL DEFAULT '',
                editor TEXT NOT NULL DEFAULT '',
                capo INTEGER NOT NULL DEFAULT 0,
                structure_json TEXT NOT NULL DEFAULT '[]',
                measure_edits_json TEXT NOT NULL DEFAULT '{}',
                lyric_edits_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                UNIQUE(audio_hash, version_no),
                FOREIGN KEY (audio_hash) REFERENCES songs(audio_hash)
                    ON DELETE CASCADE
            )
        """)

        version_columns = {
            row[1]
            for row in conn.execute(
                "PRAGMA table_info(analysis_versions)"
            ).fetchall()
        }

        _version_migrations = {
            "title": "TEXT NOT NULL DEFAULT ''",
            "artist": "TEXT NOT NULL DEFAULT ''",
            "editor": "TEXT NOT NULL DEFAULT ''",
            "capo": "INTEGER NOT NULL DEFAULT 0",
            "structure_json": "TEXT NOT NULL DEFAULT '[]'",
            "measure_edits_json": "TEXT NOT NULL DEFAULT '{}'",
            "lyric_edits_json": "TEXT NOT NULL DEFAULT '{}'",
            "strumming_primary": "TEXT NOT NULL DEFAULT ''",
            "strumming_secondary": "TEXT NOT NULL DEFAULT ''",
        }

        for _column, _sql_type in _version_migrations.items():
            if _column not in version_columns:
                conn.execute(
                    f"ALTER TABLE analysis_versions "
                    f"ADD COLUMN {_column} {_sql_type}"
                )

        conn.execute("""
            CREATE TABLE IF NOT EXISTS song_editorial_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                audio_hash TEXT NOT NULL,
                version_no INTEGER NOT NULL,
                release_no INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'validated',
                source_analysis_version_no INTEGER,
                note TEXT NOT NULL DEFAULT '',
                validated_at TEXT NOT NULL,
                published_at TEXT,
                updated_at TEXT NOT NULL,
                UNIQUE(audio_hash, version_no),
                FOREIGN KEY (audio_hash) REFERENCES songs(audio_hash)
                    ON DELETE CASCADE
            )
        """)

        editorial_columns = {
            row[1]
            for row in conn.execute(
                "PRAGMA table_info(song_editorial_versions)"
            ).fetchall()
        }

        if "version_label" not in editorial_columns:
            conn.execute(
                "ALTER TABLE song_editorial_versions "
                "ADD COLUMN version_label TEXT NOT NULL DEFAULT ''"
            )
            conn.execute(
                "UPDATE song_editorial_versions "
                "SET version_label = CAST(version_no AS TEXT) "
                "WHERE TRIM(version_label) = ''"
            )

        if "edition_label" not in editorial_columns:
            conn.execute(
                "ALTER TABLE song_editorial_versions "
                "ADD COLUMN edition_label TEXT NOT NULL DEFAULT 'Standard'"
            )

        conn.execute("""
            CREATE TABLE IF NOT EXISTS song_workflow (
                audio_hash TEXT PRIMARY KEY,
                state TEXT NOT NULL DEFAULT 'working',
                current_version_no INTEGER,
                working_note TEXT NOT NULL DEFAULT '',
                target_version_label TEXT NOT NULL DEFAULT '1.0',
                target_edition_label TEXT NOT NULL DEFAULT 'Standard',
                updated_at TEXT NOT NULL,
                FOREIGN KEY (audio_hash) REFERENCES songs(audio_hash)
                    ON DELETE CASCADE
            )
        """)

        workflow_columns = {
            row[1]
            for row in conn.execute(
                "PRAGMA table_info(song_workflow)"
            ).fetchall()
        }

        if "target_version_label" not in workflow_columns:
            conn.execute(
                "ALTER TABLE song_workflow "
                "ADD COLUMN target_version_label TEXT NOT NULL DEFAULT '1.0'"
            )

        if "target_edition_label" not in workflow_columns:
            conn.execute(
                "ALTER TABLE song_workflow "
                "ADD COLUMN target_edition_label TEXT NOT NULL DEFAULT 'Standard'"
            )

        # Migration R15 -> R16 :
        # une ancienne version seulement « validée » redevient un travail
        # courant. Son numéro visible sert de version cible, sans publication.
        conn.execute(
            """
            UPDATE song_workflow
            SET target_version_label = COALESCE(
                (
                    SELECT version_label
                    FROM song_editorial_versions
                    WHERE song_editorial_versions.audio_hash =
                          song_workflow.audio_hash
                      AND song_editorial_versions.version_no =
                          song_workflow.current_version_no
                ),
                target_version_label
            )
            WHERE current_version_no IS NOT NULL
              AND (
                  TRIM(target_version_label) = ''
                  OR target_version_label = '1.0'
              )
            """
        )
        conn.execute(
            """
            UPDATE song_workflow
            SET state = 'working'
            WHERE state = 'validated'
            """
        )

        conn.execute("""
            CREATE TABLE IF NOT EXISTS beat_edits (
                audio_hash TEXT NOT NULL,
                beat_index INTEGER NOT NULL,
                chord_override TEXT,
                time_offset_ms REAL NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (audio_hash, beat_index),
                FOREIGN KEY (audio_hash) REFERENCES songs(audio_hash)
                    ON DELETE CASCADE
            )
        """)


        conn.execute("""
            CREATE TABLE IF NOT EXISTS app_state (
                state_key TEXT PRIMARY KEY,
                state_value TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS song_preferences (
                audio_hash TEXT PRIMARY KEY,
                capo INTEGER NOT NULL DEFAULT 0,
                settings_json TEXT NOT NULL DEFAULT '{}',
                updated_at TEXT NOT NULL,
                FOREIGN KEY (audio_hash) REFERENCES songs(audio_hash)
                    ON DELETE CASCADE
            )
        """)


        conn.execute("""
            CREATE TABLE IF NOT EXISTS structure_blocks (
                audio_hash TEXT NOT NULL,
                block_id INTEGER NOT NULL,
                order_index INTEGER NOT NULL,
                cluster TEXT NOT NULL,
                custom_label TEXT NOT NULL DEFAULT '',
                measure_start INTEGER NOT NULL,
                measure_end INTEGER NOT NULL,
                detected_measure_start INTEGER,
                detected_measure_end INTEGER,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (audio_hash, block_id),
                FOREIGN KEY (audio_hash) REFERENCES songs(audio_hash)
                    ON DELETE CASCADE
            )
        """)


        conn.execute("""
            CREATE TABLE IF NOT EXISTS measure_edits (
                audio_hash TEXT NOT NULL,
                measure_no INTEGER NOT NULL,
                notation_real TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (audio_hash, measure_no),
                FOREIGN KEY (audio_hash) REFERENCES songs(audio_hash)
                    ON DELETE CASCADE
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS lyric_block_edits (
                audio_hash TEXT NOT NULL,
                block_key TEXT NOT NULL,
                original_text TEXT NOT NULL DEFAULT '',
                corrected_text TEXT NOT NULL DEFAULT '',
                time_start REAL NOT NULL,
                time_end REAL NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (audio_hash, block_key),
                FOREIGN KEY (audio_hash) REFERENCES songs(audio_hash)
                    ON DELETE CASCADE
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS lyric_line_edits (
                audio_hash TEXT NOT NULL,
                line_key TEXT NOT NULL,
                original_text TEXT NOT NULL DEFAULT '',
                corrected_text TEXT NOT NULL DEFAULT '',
                time_start REAL NOT NULL,
                time_end REAL NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (audio_hash, line_key),
                FOREIGN KEY (audio_hash) REFERENCES songs(audio_hash)
                    ON DELETE CASCADE
            )
        """)

        conn.commit()


def audio_sha256(audio_bytes):
    return hashlib.sha256(audio_bytes).hexdigest()




def _lyric_block_key(time_start, time_end):
    payload = f"{float(time_start):.3f}|{float(time_end):.3f}"
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def _lyric_text_without_layout(value):
    """Normalize only whitespace, preserving words/punctuation for comparison."""
    return " ".join(str(value or "").split())


def _recover_lyric_linebreaks_from_versions(conn, audio_hash, edits):
    """Recover manual line breaks lost by older regressions.

    Recovery is deliberately conservative: a historical text is accepted only
    when its content is identical after whitespace normalization. Therefore this
    can restore layout (newlines) without resurrecting old wording changes.
    """
    try:
        rows = conn.execute(
            """
            SELECT lyric_edits_json
            FROM analysis_versions
            WHERE audio_hash = ?
              AND trim(lyric_edits_json) NOT IN ('', '{}')
            ORDER BY version_no DESC
            """,
            (str(audio_hash),),
        ).fetchall()
    except sqlite3.OperationalError:
        return edits

    if not rows:
        return edits

    changed = []

    def _matching_current(hist):
        h0 = float(hist.get("time_start", 0.0) or 0.0)
        h1 = float(hist.get("time_end", h0) or h0)
        exact_key = _lyric_block_key(h0, h1)
        if exact_key in edits:
            return exact_key, edits[exact_key]
        best = None
        best_delta = None
        for key, item in edits.items():
            e0 = float(item.get("time_start", 0.0) or 0.0)
            e1 = float(item.get("time_end", e0) or e0)
            d0 = abs(e0 - h0)
            d1 = abs(e1 - h1)
            if d0 <= 0.02 and d1 <= 0.02:
                delta = d0 + d1
                if best_delta is None or delta < best_delta:
                    best = (key, item)
                    best_delta = delta
        return best

    for row in rows:
        try:
            historic = json.loads(row[0] or "{}")
        except Exception:
            continue
        if not isinstance(historic, dict):
            continue

        for hist in historic.values():
            if not isinstance(hist, dict):
                continue
            historic_text = str(hist.get("corrected_text", "") or "")
            if "\n" not in historic_text and "\r" not in historic_text:
                continue

            match = _matching_current(hist)
            if match is None:
                # If there is no current override, recover only when the old
                # formatted text contains exactly the same words as the old
                # source/original text. This restores layout only.
                original = str(hist.get("original_text", "") or "")
                if (
                    _lyric_text_without_layout(historic_text)
                    != _lyric_text_without_layout(original)
                ):
                    continue
                h0 = float(hist.get("time_start", 0.0) or 0.0)
                h1 = float(hist.get("time_end", h0) or h0)
                key = _lyric_block_key(h0, h1)
                item = {
                    "original_text": original,
                    "corrected_text": historic_text,
                    "time_start": h0,
                    "time_end": h1,
                }
                edits[key] = item
                changed.append((key, item))
                continue

            key, current = match
            current_text = str(current.get("corrected_text", "") or "")
            if "\n" in current_text or "\r" in current_text:
                continue
            if (
                _lyric_text_without_layout(current_text)
                != _lyric_text_without_layout(historic_text)
            ):
                continue
            current["corrected_text"] = historic_text
            changed.append((key, current))

    if changed:
        now = _utc_now_iso()
        for key, item in changed:
            conn.execute(
                """
                INSERT INTO lyric_block_edits (
                    audio_hash, block_key, original_text, corrected_text,
                    time_start, time_end, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(audio_hash, block_key)
                DO UPDATE SET
                    original_text = excluded.original_text,
                    corrected_text = excluded.corrected_text,
                    time_start = excluded.time_start,
                    time_end = excluded.time_end,
                    updated_at = excluded.updated_at
                """,
                (
                    str(audio_hash),
                    str(key),
                    str(item.get("original_text", "") or ""),
                    str(item.get("corrected_text", "") or ""),
                    float(item.get("time_start", 0.0) or 0.0),
                    float(item.get("time_end", 0.0) or 0.0),
                    now,
                ),
            )
        conn.commit()

    return edits


def load_lyric_block_edits(audio_hash):
    if not audio_hash:
        return {}
    try:
        with sqlite3.connect(DB_PATH) as conn:
            rows = conn.execute(
                """
                SELECT block_key, original_text, corrected_text,
                       time_start, time_end
                FROM lyric_block_edits
                WHERE audio_hash = ?
                """,
                (str(audio_hash),),
            ).fetchall()

            edits = {
                r[0]: {
                    "original_text": r[1] or "",
                    "corrected_text": r[2] or "",
                    "time_start": float(r[3]),
                    "time_end": float(r[4]),
                }
                for r in rows
            }
            return _recover_lyric_linebreaks_from_versions(
                conn,
                audio_hash,
                edits,
            )
    except sqlite3.OperationalError:
        return {}


def resolve_lyric_block_edit(edits, time_start, time_end, tolerance=0.02):
    """Resolve the current block edit, including the legacy ±1 ms boundary.

    Exact key lookup remains authoritative. A narrow boundary fallback recovers
    corrections saved before the block end convention changed to +0.001 s,
    preserving text and manual line breaks.
    """
    edits = edits or {}
    t0 = float(time_start)
    t1 = float(time_end)
    exact = edits.get(_lyric_block_key(t0, t1))
    if exact:
        return exact

    best = None
    best_delta = None
    tol = float(tolerance)

    for item in edits.values():
        e0 = float(item.get("time_start", 0.0) or 0.0)
        e1 = float(item.get("time_end", e0) or e0)
        d0 = abs(e0 - t0)
        d1 = abs(e1 - t1)
        if d0 <= tol and d1 <= tol:
            delta = d0 + d1
            if best_delta is None or delta < best_delta:
                best = item
                best_delta = delta

    return best or {}


def save_lyric_block_edit(
    audio_hash, block_key, original_text, corrected_text,
    time_start, time_end,
):
    """Persist the canonical correction for one structural block.

    Older corrections overlapping the same current block are removed first.
    This prevents an obsolete boundary or old editor from winning in another
    view of the same song.
    """
    original = str(original_text or "").strip()
    corrected = str(corrected_text or "").strip()
    t0 = float(time_start)
    t1 = float(time_end)

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            DELETE FROM lyric_block_edits
            WHERE audio_hash = ?
              AND block_key <> ?
              AND NOT (time_end <= ? OR time_start >= ?)
            """,
            (str(audio_hash), str(block_key), t0, t1),
        )

        if not corrected or corrected == original:
            conn.execute(
                "DELETE FROM lyric_block_edits "
                "WHERE audio_hash = ? AND block_key = ?",
                (str(audio_hash), str(block_key)),
            )
        else:
            conn.execute(
                """
                INSERT INTO lyric_block_edits (
                    audio_hash, block_key, original_text, corrected_text,
                    time_start, time_end, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(audio_hash, block_key)
                DO UPDATE SET
                    original_text = excluded.original_text,
                    corrected_text = excluded.corrected_text,
                    time_start = excluded.time_start,
                    time_end = excluded.time_end,
                    updated_at = excluded.updated_at
                """,
                (
                    str(audio_hash), str(block_key), original, corrected,
                    t0, t1, _utc_now_iso(),
                ),
            )
        conn.commit()

def save_lyric_block_edits_snapshot(audio_hash, items):
    """Persist the complete current lyric state for all structural blocks.

    This is intentionally atomic. It allows a verse to be cut from one block
    and pasted into another, including making a block explicitly empty.
    Stale edits from an older block layout are removed in the same transaction.
    """
    now = _utc_now_iso()
    normalized = []

    for item in items or []:
        block_key = str(item.get("block_key", "") or "").strip()
        if not block_key:
            continue

        original = str(item.get("original_text", "") or "").strip()
        edited = str(item.get("edited_text", "") or "").strip()
        t0 = float(item.get("time_start", 0.0) or 0.0)
        t1 = float(item.get("time_end", t0) or t0)

        normalized.append({
            "block_key": block_key,
            "original_text": original,
            "edited_text": edited,
            "time_start": t0,
            "time_end": t1,
        })

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "DELETE FROM lyric_block_edits WHERE audio_hash = ?",
            (str(audio_hash),),
        )

        for item in normalized:
            # Identical text needs no override. An empty edited block DOES:
            # it explicitly means that its lyrics were moved elsewhere.
            if item["edited_text"] == item["original_text"]:
                continue

            conn.execute(
                """
                INSERT INTO lyric_block_edits (
                    audio_hash, block_key, original_text, corrected_text,
                    time_start, time_end, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(audio_hash),
                    item["block_key"],
                    item["original_text"],
                    item["edited_text"],
                    item["time_start"],
                    item["time_end"],
                    now,
                ),
            )

        conn.commit()


def reset_lyric_block_edits(audio_hash):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "DELETE FROM lyric_block_edits WHERE audio_hash = ?",
            (str(audio_hash),),
        )
        # Nettoie aussi les anciennes corrections ligne-à-ligne V38c.
        conn.execute(
            "DELETE FROM lyric_line_edits WHERE audio_hash = ?",
            (str(audio_hash),),
        )
        conn.commit()


def _source_words_for_interval(resultat, t0, t1):
    words = []
    for word in extraire_mots(resultat):
        w0 = float(word["start"])
        w1 = float(word["end"])
        midpoint = (w0 + w1) / 2.0
        if float(t0) <= midpoint < float(t1):
            txt = str(word["text"]).strip()
            if txt:
                words.append({
                    "text": txt,
                    "start": w0,
                    "end": w1,
                })
    return words


def _redistribute_corrected_block_text(corrected_text, source_words):
    """
    Reprojette le texte corrigé sur la timeline Whisper sans décaler les mots
    qui n'ont pas changé.

    Principe :
    - les mots identiques gardent exactement leurs timestamps d'origine ;
    - un remplacement 1 pour 1 garde aussi la fenêtre temporelle du mot source ;
    - seules les insertions/remplacements de longueur différente sont
      interpolés localement dans la fenêtre voisine ;
    - les retours à la ligne manuels restent portés par manual_line_end.

    Cela évite le comportement précédent qui redistribuait TOUS les mots sur
    toute la durée du bloc dès qu'un seul mot était ajouté/supprimé.
    """
    if not source_words:
        return []

    lines = [
        line.strip()
        for line in str(corrected_text or "").splitlines()
        if line.strip()
    ]
    if not lines:
        return []

    tokens = []
    line_ends = set()
    for line in lines:
        parts = re.findall(r"\S+", line)
        tokens.extend(parts)
        if parts:
            line_ends.add(len(tokens) - 1)

    if not tokens:
        return []

    src_tokens = [
        str(word.get("text", "") or "").strip()
        for word in source_words
    ]

    def _match_token(value):
        value = str(value or "").casefold().strip()
        value = re.sub(r"^[^\wÀ-ÿ]+|[^\wÀ-ÿ]+$", "", value)
        return value

    src_norm = [_match_token(value) for value in src_tokens]
    dst_norm = [_match_token(value) for value in tokens]

    matcher = SequenceMatcher(a=src_norm, b=dst_norm, autojunk=False)
    mapped = [None] * len(tokens)

    block_start = float(source_words[0]["start"])
    block_end = float(source_words[-1]["end"])
    block_end = max(block_end, block_start + 0.02)

    def _place_segment(dst_start, dst_end, src_start, src_end):
        count = max(0, dst_end - dst_start)
        if count <= 0:
            return

        if src_start < src_end:
            left = float(source_words[src_start]["start"])
            right = float(source_words[src_end - 1]["end"])
        else:
            prev_end = (
                float(source_words[src_start - 1]["end"])
                if src_start > 0
                else block_start
            )
            next_start = (
                float(source_words[src_start]["start"])
                if src_start < len(source_words)
                else block_end
            )
            left = prev_end
            right = next_start

        if right <= left:
            right = min(block_end, left + max(0.04, 0.12 * count))
        if right <= left:
            left = max(block_start, right - max(0.04, 0.12 * count))

        width = max(right - left, 0.02)
        step = width / max(count, 1)

        for local_index, dst_index in enumerate(range(dst_start, dst_end)):
            seg_start = left + local_index * step
            seg_end = left + (local_index + 1) * step
            mapped[dst_index] = {
                "text": tokens[dst_index],
                "start": float(max(block_start, seg_start)),
                "end": float(min(block_end, max(seg_end, seg_start + 0.02))),
                "manual_line_end": dst_index in line_ends,
            }

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for src_index, dst_index in zip(range(i1, i2), range(j1, j2)):
                word = source_words[src_index]
                mapped[dst_index] = {
                    "text": tokens[dst_index],
                    "start": float(word["start"]),
                    "end": float(word["end"]),
                    "manual_line_end": dst_index in line_ends,
                }
            continue

        if tag == "replace" and (i2 - i1) == (j2 - j1):
            for src_index, dst_index in zip(range(i1, i2), range(j1, j2)):
                word = source_words[src_index]
                mapped[dst_index] = {
                    "text": tokens[dst_index],
                    "start": float(word["start"]),
                    "end": float(word["end"]),
                    "manual_line_end": dst_index in line_ends,
                }
            continue

        if tag in ("replace", "insert"):
            _place_segment(j1, j2, i1, i2)

    # Sécurité : tous les tokens doivent avoir une position, même sur un
    # opcode atypique. On ne touche pas aux timestamps déjà ancrés.
    for index, item in enumerate(mapped):
        if item is None:
            _place_segment(index, index + 1, 0, len(source_words))

    result = [item for item in mapped if item is not None]
    result.sort(
        key=lambda item: (
            float(item.get("start", 0.0)),
            float(item.get("end", 0.0)),
        )
    )
    return result


def effective_lyrics_words_for_sections(
    resultat,
    audio_hash,
    sections,
):
    """Canonical lyric timeline for players and synchronized views.

    The persisted structural blocks define the intervals. Only a correction
    whose key matches the current block boundaries is applied; obsolete edits
    from older block layouts are ignored.
    """
    edits = load_lyric_block_edits(audio_hash)
    effective = []

    if not sections:
        return [
            {
                "text": str(word.get("text", "") or "").strip(),
                "start": float(word.get("start", 0.0) or 0.0),
                "end": float(
                    word.get("end", word.get("start", 0.0)) or 0.0
                ),
            }
            for word in extraire_mots(resultat)
            if str(word.get("text", "") or "").strip()
        ]

    for section in sections:
        t0 = float(section.get("time_start", 0.0) or 0.0)
        t1 = float(section.get("time_end", t0) or t0)
        if t1 <= t0:
            continue

        source_words = _source_words_for_interval(resultat, t0, t1)
        block_key = _lyric_block_key(t0, t1)
        edit = resolve_lyric_block_edit(edits, t0, t1)
        has_edit = bool(edit)
        corrected = str(
            edit.get("corrected_text", "") if has_edit else ""
        ).strip()

        if has_edit:
            if corrected:
                block_words = _redistribute_corrected_block_text(
                    corrected,
                    source_words,
                )
            else:
                # Explicitly empty block: the editor moved/removed its lyrics.
                block_words = []
        else:
            block_words = [
                {**word, "manual_line_end": False}
                for word in source_words
            ]

        effective.extend(block_words)

    effective.sort(
        key=lambda word: (
            float(word.get("start", 0.0) or 0.0),
            float(word.get("end", 0.0) or 0.0),
        )
    )
    return effective


def _lyric_line_key(time_start, time_end, original_text):
    payload = (
        f"{float(time_start):.3f}|"
        f"{float(time_end):.3f}|"
        f"{str(original_text).strip()}"
    )
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def load_lyric_line_edits(audio_hash):
    if not audio_hash:
        return {}

    try:
        with sqlite3.connect(DB_PATH) as conn:
            rows = conn.execute(
                """
                SELECT
                    line_key,
                    original_text,
                    corrected_text,
                    time_start,
                    time_end
                FROM lyric_line_edits
                WHERE audio_hash = ?
                """,
                (str(audio_hash),),
            ).fetchall()
    except sqlite3.OperationalError:
        return {}

    return {
        row[0]: {
            "original_text": row[1] or "",
            "corrected_text": row[2] or "",
            "time_start": float(row[3]),
            "time_end": float(row[4]),
        }
        for row in rows
    }


def save_lyric_line_edit(
    audio_hash,
    line_key,
    original_text,
    corrected_text,
    time_start,
    time_end,
):
    """
    Corrige uniquement le texte de la ligne.
    Aucun accord, beat, timestamp audio ou résultat d'analyse n'est modifié.
    """
    corrected = str(corrected_text or "").strip()

    with sqlite3.connect(DB_PATH) as conn:
        if not corrected or corrected == str(original_text or "").strip():
            conn.execute(
                """
                DELETE FROM lyric_line_edits
                WHERE audio_hash = ? AND line_key = ?
                """,
                (str(audio_hash), str(line_key)),
            )
        else:
            conn.execute(
                """
                INSERT INTO lyric_line_edits (
                    audio_hash,
                    line_key,
                    original_text,
                    corrected_text,
                    time_start,
                    time_end,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(audio_hash, line_key)
                DO UPDATE SET
                    original_text = excluded.original_text,
                    corrected_text = excluded.corrected_text,
                    time_start = excluded.time_start,
                    time_end = excluded.time_end,
                    updated_at = excluded.updated_at
                """,
                (
                    str(audio_hash),
                    str(line_key),
                    str(original_text or "").strip(),
                    corrected,
                    float(time_start),
                    float(time_end),
                    _utc_now_iso(),
                ),
            )
        conn.commit()


def reset_lyric_line_edits(audio_hash):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "DELETE FROM lyric_line_edits WHERE audio_hash = ?",
            (str(audio_hash),),
        )
        conn.commit()


def _words_from_corrected_text(corrected_text, source_words):
    """
    Redistribue une phrase corrigée DANS LA MÊME FENÊTRE TEMPORELLE.

    Les accords ne bougent jamais.

    Whisper ne donnant ici que des timestamps par mot, on interpole les
    nouveaux mots sur les centres temporels des mots originaux. Cela permet
    de remplacer, par exemple :

        "nous deux mangerons calaux sur l'œil"

    par :

        "Nous ne mangions qu'un jour sur deux"

    sans déplacer la timeline harmonique.
    """
    tokens = re.findall(r"\\S+", str(corrected_text or "").strip())
    if not tokens:
        return []

    if not source_words:
        return []

    source_centers = np.asarray(
        [
            (float(w["start"]) + float(w["end"])) / 2.0
            for w in source_words
        ],
        dtype=float,
    )

    line_start = float(source_words[0]["start"])
    line_end = float(source_words[-1]["end"])
    line_duration = max(line_end - line_start, 1e-6)

    if len(tokens) == 1:
        centers = np.asarray(
            [(line_start + line_end) / 2.0],
            dtype=float,
        )
    elif len(source_centers) == 1:
        centers = np.linspace(
            line_start,
            line_end,
            num=len(tokens),
        )
    else:
        src_axis = np.linspace(0.0, 1.0, num=len(source_centers))
        dst_axis = np.linspace(0.0, 1.0, num=len(tokens))
        centers = np.interp(
            dst_axis,
            src_axis,
            source_centers,
        )

    # Durée locale de chaque nouveau mot : assez courte pour ne pas
    # faire chevaucher artificiellement les ancrages, mais non nulle.
    nominal = min(
        0.45,
        max(0.08, line_duration / max(len(tokens) * 2.2, 1.0)),
    )

    result = []
    previous_end = line_start

    for i, (token, center) in enumerate(zip(tokens, centers)):
        start = max(
            line_start,
            float(center) - nominal / 2.0,
            previous_end,
        )

        if i + 1 < len(centers):
            next_center = float(centers[i + 1])
            end = min(
                line_end,
                float(center) + nominal / 2.0,
                max(start + 0.02, (float(center) + next_center) / 2.0),
            )
        else:
            end = min(
                line_end,
                max(start + 0.02, float(center) + nominal / 2.0),
            )

        result.append({
            "text": token,
            "start": float(start),
            "end": float(max(end, start + 0.02)),
        })
        previous_end = float(max(end, start + 0.02))

    return result


def get_app_state(state_key, default=""):
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            """
            SELECT state_value
            FROM app_state
            WHERE state_key = ?
            """,
            (state_key,),
        ).fetchone()

    if row is None:
        return default

    return row[0]


def set_app_state(state_key, state_value):
    now = _utc_now_iso()

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO app_state (
                state_key, state_value, updated_at
            )
            VALUES (?, ?, ?)
            ON CONFLICT(state_key)
            DO UPDATE SET
                state_value = excluded.state_value,
                updated_at = excluded.updated_at
            """,
            (
                str(state_key),
                str(state_value or ""),
                now,
            ),
        )
        conn.commit()


def load_song_preferences(audio_hash):
    """
    Préférences UI persistantes propres à une chanson.

    Elles sont distinctes de l'analyse :
      - capo : affichage uniquement ;
      - settings : dernière configuration validée/affichée pour le morceau.

    Compatibilité descendante : si la table n'existe pas encore ou si aucun
    enregistrement n'existe, retourne None.
    """
    if not audio_hash:
        return None

    try:
        with sqlite3.connect(DB_PATH) as conn:
            row = conn.execute(
                """
                SELECT capo, settings_json
                FROM song_preferences
                WHERE audio_hash = ?
                """,
                (str(audio_hash),),
            ).fetchone()
    except sqlite3.OperationalError:
        return None

    if row is None:
        return None

    try:
        settings = json.loads(row[1] or "{}")
    except Exception:
        settings = {}

    return {
        "capo": max(0, min(12, int(row[0] or 0))),
        "settings": settings if isinstance(settings, dict) else {},
    }


def save_song_preferences(audio_hash, capo, settings):
    """
    Sauvegarde sans déclencher aucune analyse.
    """
    if not audio_hash:
        return

    capo_value = max(0, min(12, int(capo or 0)))
    settings_json = json.dumps(
        _json_safe(settings or {}),
        ensure_ascii=False,
        sort_keys=True,
    )

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO song_preferences (
                audio_hash, capo, settings_json, updated_at
            )
            VALUES (?, ?, ?, ?)
            ON CONFLICT(audio_hash)
            DO UPDATE SET
                capo = excluded.capo,
                settings_json = excluded.settings_json,
                updated_at = excluded.updated_at
            """,
            (
                str(audio_hash),
                capo_value,
                settings_json,
                _utc_now_iso(),
            ),
        )
        conn.commit()


def current_song_settings_payload(whisper_device="cpu"):
    """
    Snapshot des réglages avancés depuis Session State.

    Aucun accès à une globale du module principal : toutes les valeurs
    appartiennent au contexte Streamlit ou sont passées explicitement.
    """
    return {
        "signature_mode": st.session_state.get("setting_signature_mode", "Auto"),
        "analyse_sr": int(st.session_state.get("setting_analyse_sr", 22050)),
        "hop_length": int(st.session_state.get("setting_hop_length", 2048)),
        "silence_rms_ratio": float(st.session_state.get("setting_silence_rms", 0.22)),
        "silence_chroma_ratio": float(st.session_state.get("setting_silence_chroma", 0.18)),
        "poids_fondamentale": float(st.session_state.get("setting_poids_fondamentale", 0.22)),
        "fermata_enabled": bool(st.session_state.get("setting_fermata_enabled", True)),
        "fermata_gap_ratio": float(st.session_state.get("setting_fermata_gap", 1.85)),
        "sections_enabled": bool(st.session_state.get("setting_sections_enabled", True)),
        "section_block_measures": int(st.session_state.get("setting_section_block_measures", 4)),
        "section_similarity": float(st.session_state.get("setting_section_similarity", 0.66)),
        "whisper_model": "small",
        "whisper_device": str(whisper_device or "cpu"),
    }


def prepare_song_preferences_for_open(audio_hash):
    """
    Prépare le prochain rerun AVANT la création des widgets.

    Priorité :
      1. préférences propres au morceau ;
      2. paramètres de la dernière analyse comme fallback historique.
    """
    preferences = load_song_preferences(audio_hash)
    latest_params = load_latest_analysis_parameters(audio_hash)

    if latest_params:
        st.session_state[
            "_pending_analysis_settings"
        ] = latest_params

    if preferences:
        st.session_state[
            "_pending_song_preferences"
        ] = preferences


def migrate_archived_audio_catalog():
    """
    Répare les cas où un audio existe déjà dans data/audio mais ne possède
    pas encore d'entrée songs.

    R10 :
    - les nouveaux fichiers conservent leur nom original ;
    - les anciens fichiers nommés par SHA-256 restent compatibles ;
    - l'identité technique reste toujours le SHA-256 du contenu réel.
    """
    with sqlite3.connect(DB_PATH) as conn:
        known_hashes = {
            str(row[0]).lower()
            for row in conn.execute(
                "SELECT audio_hash FROM songs"
            ).fetchall()
        }

    for path in AUDIO_DIR.iterdir():
        if not path.is_file():
            continue

        try:
            raw = path.read_bytes()
        except OSError:
            continue

        actual_hash = hashlib.sha256(raw).hexdigest().lower()

        if actual_hash in known_hashes:
            continue

        ensure_song(
            actual_hash,
            path.name,
        )
        known_hashes.add(actual_hash)


def persist_audio_source(audio_hash, original_filename, audio_bytes):
    """
    Archive une COPIE CONFORME de l'audio importé.

    - mêmes octets ;
    - même nom de fichier ;
    - SHA-256 utilisé uniquement comme identité interne.

    Un fichier homonyme de contenu différent n'est jamais écrasé.
    """
    audio_hash = str(audio_hash or "").strip().lower()
    safe_name = Path(str(original_filename or "")).name.strip()

    if not safe_name:
        raise RuntimeError("Nom de fichier audio invalide.")

    incoming_hash = hashlib.sha256(audio_bytes).hexdigest().lower()

    if incoming_hash != audio_hash:
        raise RuntimeError(
            "Le contenu audio ne correspond pas au SHA-256 attendu."
        )

    target = AUDIO_DIR / safe_name

    if target.exists():
        try:
            existing_hash = hashlib.sha256(
                target.read_bytes()
            ).hexdigest().lower()
        except OSError as exc:
            raise RuntimeError(
                f"Impossible de vérifier le fichier audio existant : {exc}"
            ) from exc

        if existing_hash != incoming_hash:
            raise RuntimeError(
                f'Un fichier nommé « {safe_name} » existe déjà dans data/audio '
                "avec un contenu différent."
            )

        return target

    target.write_bytes(audio_bytes)

    # Contrôle après écriture : la copie doit être strictement conforme.
    try:
        written_hash = hashlib.sha256(
            target.read_bytes()
        ).hexdigest().lower()
    except OSError as exc:
        raise RuntimeError(
            f"Impossible de vérifier la copie audio : {exc}"
        ) from exc

    if written_hash != incoming_hash:
        try:
            target.unlink()
        except OSError:
            pass
        raise RuntimeError(
            "La copie audio archivée n'est pas conforme au fichier importé."
        )

    return target


def find_persisted_audio(audio_hash):
    """
    Résout l'audio archivé par son SHA-256 réel.

    Priorité :
    1. nom original enregistré dans songs ;
    2. scan de data/audio avec vérification SHA-256.

    Le scan maintient la compatibilité avec les anciens fichiers nommés
    <sha256>.<ext>.
    """
    audio_hash = str(audio_hash or "").strip().lower()

    if not audio_hash:
        return None

    original_filename = ""

    try:
        with sqlite3.connect(DB_PATH) as conn:
            row = conn.execute(
                """
                SELECT original_filename
                FROM songs
                WHERE audio_hash = ?
                """,
                (audio_hash,),
            ).fetchone()
        if row:
            original_filename = Path(
                str(row[0] or "")
            ).name.strip()
    except sqlite3.Error:
        original_filename = ""

    if original_filename:
        candidate = AUDIO_DIR / original_filename
        if candidate.exists() and candidate.is_file():
            try:
                digest = hashlib.sha256(
                    candidate.read_bytes()
                ).hexdigest().lower()
            except OSError:
                digest = ""

            if digest == audio_hash:
                return candidate

    for candidate in AUDIO_DIR.iterdir():
        if not candidate.is_file():
            continue

        try:
            digest = hashlib.sha256(
                candidate.read_bytes()
            ).hexdigest().lower()
        except OSError:
            continue

        if digest == audio_hash:
            return candidate

    return None


def list_song_catalog(sort_by="title"):
    """
    Catalogue alphabétique au choix :
    - title  : titre puis auteur
    - artist : auteur/interprète puis titre
    """
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            """
            SELECT audio_hash, original_filename, title, artist, editor,
                   strumming_primary, strumming_secondary, cover_path,
                   created_at, updated_at
            FROM songs
            """
        ).fetchall()

    items = [
        {
            "audio_hash": row[0],
            "original_filename": row[1],
            "title": row[2],
            "artist": row[3],
            "editor": row[4] or "",
            "strumming_primary": row[5] or "",
            "strumming_secondary": row[6] or "",
            "cover_path": row[7] or "",
            "created_at": row[8],
            "updated_at": row[9],
        }
        for row in rows
    ]

    def norm(value):
        return str(value or "").strip().casefold()

    if sort_by == "artist":
        items.sort(
            key=lambda s: (
                norm(s.get("artist")) or "\uffff",
                norm(s.get("title"))
                or norm(Path(s.get("original_filename", "")).stem),
            )
        )
    else:
        items.sort(
            key=lambda s: (
                norm(s.get("title"))
                or norm(Path(s.get("original_filename", "")).stem),
                norm(s.get("artist")),
            )
        )

    return items



def catalog_primary_text(song, sort_by="title"):
    title = str(song.get("title", "") or "").strip()
    artist = str(song.get("artist", "") or "").strip()
    filename = str(song.get("original_filename", "") or "").strip()

    title = title or Path(filename).stem or "Sans titre"

    if sort_by == "artist":
        return artist or "Auteur inconnu"

    return title


def catalog_secondary_text(song, sort_by="title"):
    title = str(song.get("title", "") or "").strip()
    artist = str(song.get("artist", "") or "").strip()
    filename = str(song.get("original_filename", "") or "").strip()

    title = title or Path(filename).stem or "Sans titre"

    if sort_by == "artist":
        return title

    return artist or "Auteur inconnu"


def catalog_letter_for_song(song, sort_by="title"):
    raw = catalog_primary_text(song, sort_by=sort_by).strip()

    if not raw:
        return "#"

    first = raw[0].upper()
    return first if "A" <= first <= "Z" else "#"


def filter_catalog(catalog, sort_by, letter="Tous", query=""):
    query_norm = str(query or "").strip().casefold()

    result = []

    for song in catalog:
        if letter not in ("Tous", ""):
            if catalog_letter_for_song(song, sort_by=sort_by) != letter:
                continue

        if query_norm:
            haystack = " ".join([
                str(song.get("title", "") or ""),
                str(song.get("artist", "") or ""),
                str(song.get("original_filename", "") or ""),
            ]).casefold()

            if query_norm not in haystack:
                continue

        result.append(song)

    return result


def catalog_display_name(song, sort_by="title"):
    title = str(song.get("title", "") or "").strip()
    artist = str(song.get("artist", "") or "").strip()
    filename = str(song.get("original_filename", "") or "").strip()

    title = title or Path(filename).stem or "Sans titre"

    if sort_by == "artist":
        return f"{artist or 'Auteur inconnu'} — {title}"

    if artist:
        return f"{title} — {artist}"

    return title


def ensure_song(audio_hash, original_filename):
    now = _utc_now_iso()
    default_title = Path(original_filename).stem

    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            """
            SELECT audio_hash, original_filename, title, artist, editor,
                   strumming_primary, strumming_secondary, cover_path,
                   created_at, updated_at
            FROM songs
            WHERE audio_hash = ?
            """,
            (audio_hash,),
        ).fetchone()

        if row is None:
            conn.execute(
                """
                INSERT INTO songs (
                    audio_hash, original_filename, title, artist, editor,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, '', '', ?, ?)
                """,
                (
                    audio_hash,
                    original_filename,
                    default_title,
                    now,
                    now,
                ),
            )
            conn.commit()

            return {
                "audio_hash": audio_hash,
                "original_filename": original_filename,
                "title": default_title,
                "artist": "",
                "editor": "",
                "strumming_primary": "",
                "strumming_secondary": "",
                "cover_path": "",
                "created_at": now,
                "updated_at": now,
            }

        # Le nom physique peut changer alors que l'audio est identique.
        if row[1] != original_filename:
            conn.execute(
                """
                UPDATE songs
                SET original_filename = ?, updated_at = ?
                WHERE audio_hash = ?
                """,
                (original_filename, now, audio_hash),
            )
            conn.commit()

        return {
            "audio_hash": row[0],
            "original_filename": original_filename,
            "title": row[2],
            "artist": row[3],
            "editor": row[4] or "",
            "strumming_primary": row[5] or "",
            "strumming_secondary": row[6] or "",
            "cover_path": row[7] or "",
            "created_at": row[8],
            "updated_at": now if row[1] != original_filename else row[9],
        }


def update_song_metadata(audio_hash, title, artist, editor, strumming_primary, strumming_secondary):
    now = _utc_now_iso()

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            UPDATE songs
            SET title = ?, artist = ?, editor = ?,
                strumming_primary = ?, strumming_secondary = ?,
                updated_at = ?
            WHERE audio_hash = ?
            """,
            (
                str(title or "").strip(),
                str(artist or "").strip(),
                str(editor or "").strip(),
                str(strumming_primary or "").strip(),
                str(strumming_secondary or "").strip(),
                now,
                audio_hash,
            ),
        )
        conn.commit()



def get_song_editor_assignment(audio_hash):
    with sqlite3.connect(DB_PATH) as conn:
        try:
            row = conn.execute(
                """
                SELECT user_id, display_name, updated_at
                FROM song_editor_assignments
                WHERE audio_hash = ?
                """,
                (str(audio_hash),),
            ).fetchone()
        except sqlite3.OperationalError:
            return None

    if not row:
        return None
    return {
        "user_id": int(row[0]) if row[0] is not None else None,
        "display_name": row[1] or "",
        "updated_at": row[2],
    }


def assign_song_editor(audio_hash, user_id, display_name):
    """Assign a song to a real EZScore user while keeping a readable snapshot."""
    now = _utc_now_iso()
    name = str(display_name or "").strip()
    uid = int(user_id) if user_id is not None else None

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO song_editor_assignments (
                audio_hash, user_id, display_name, updated_at
            )
            VALUES (?, ?, ?, ?)
            ON CONFLICT(audio_hash)
            DO UPDATE SET
                user_id = excluded.user_id,
                display_name = excluded.display_name,
                updated_at = excluded.updated_at
            """,
            (str(audio_hash), uid, name, now),
        )
        conn.execute(
            """
            UPDATE songs
            SET editor = ?, updated_at = ?
            WHERE audio_hash = ?
            """,
            (name, now, str(audio_hash)),
        )
        conn.commit()

    return get_song_editor_assignment(audio_hash)


def _cover_extension(filename):
    suffix = Path(str(filename or "")).suffix.lower()
    return suffix if suffix in (".jpg", ".jpeg", ".png", ".webp") else ".jpg"


def save_song_cover(audio_hash, uploaded_file):
    if uploaded_file is None:
        return None

    COVER_DIR.mkdir(parents=True, exist_ok=True)
    ext = _cover_extension(getattr(uploaded_file, "name", "cover.jpg"))

    for old in COVER_DIR.glob(f"{audio_hash}.*"):
        try:
            old.unlink()
        except OSError:
            pass

    target = COVER_DIR / f"{audio_hash}{ext}"
    target.write_bytes(uploaded_file.getvalue())
    now = _utc_now_iso()

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            UPDATE songs
            SET cover_path = ?, updated_at = ?
            WHERE audio_hash = ?
            """,
            (str(target.relative_to(APP_DIR)), now, audio_hash),
        )
        conn.commit()

    return target


def delete_song_cover(audio_hash):
    for old in COVER_DIR.glob(f"{audio_hash}.*"):
        try:
            old.unlink()
        except OSError:
            pass

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            UPDATE songs
            SET cover_path = '', updated_at = ?
            WHERE audio_hash = ?
            """,
            (_utc_now_iso(), audio_hash),
        )
        conn.commit()


def song_cover_path(song):
    raw = str((song or {}).get("cover_path", "") or "").strip()
    if raw:
        candidate = Path(raw)
        if not candidate.is_absolute():
            candidate = APP_DIR / candidate
        if candidate.is_file():
            return candidate

    audio_hash = str((song or {}).get("audio_hash", "") or "").strip()
    if audio_hash:
        for candidate in COVER_DIR.glob(f"{audio_hash}.*"):
            if candidate.is_file():
                return candidate

    return None


def load_block_edits(audio_hash):
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            """
            SELECT block_cluster, custom_label, measure_start, measure_end
            FROM block_edits
            WHERE audio_hash = ?
            """,
            (audio_hash,),
        ).fetchall()

    return {
        row[0]: {
            "custom_label": row[1] or "",
            "measure_start": row[2],
            "measure_end": row[3],
        }
        for row in rows
    }


def save_block_edit(
    audio_hash,
    block_cluster,
    custom_label,
    measure_start,
    measure_end,
):
    now = _utc_now_iso()

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO block_edits (
                audio_hash,
                block_cluster,
                custom_label,
                measure_start,
                measure_end,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(audio_hash, block_cluster)
            DO UPDATE SET
                custom_label = excluded.custom_label,
                measure_start = excluded.measure_start,
                measure_end = excluded.measure_end,
                updated_at = excluded.updated_at
            """,
            (
                audio_hash,
                str(block_cluster),
                str(custom_label or "").strip(),
                int(measure_start),
                int(measure_end),
                now,
            ),
        )
        conn.commit()


def libelle_bloc_affiche(section):
    """
    Affichage utilisateur :
    - nom personnalisé s'il existe ;
    - sinon fallback neutre "Bloc X".

    L'identifiant technique A/B/C reste interne.
    """
    custom = str(
        section.get("custom_label", "") or ""
    ).strip()

    if custom:
        return custom

    return f'Bloc {section["cluster"]}'


def appliquer_editions_blocs(
    sections_structurelles,
    block_edits,
    total_measures,
):
    result = []

    for section in sections_structurelles:
        copie = dict(section)
        cluster = str(section["cluster"])
        edit = block_edits.get(cluster, {})

        detected_start = int(section["measure_start"])
        detected_end = int(section["measure_end"])

        start = edit.get("measure_start")
        end = edit.get("measure_end")

        start = detected_start if start is None else int(start)
        end = detected_end if end is None else int(end)

        start = max(1, min(int(total_measures), start))
        end = max(1, min(int(total_measures), end))

        if start > end:
            start, end = end, start

        copie["detected_measure_start"] = detected_start
        copie["detected_measure_end"] = detected_end
        copie["measure_start"] = start
        copie["measure_end"] = end
        copie["custom_label"] = str(
            edit.get("custom_label", "") or ""
        ).strip()

        result.append(copie)

    return result



def _alpha_label_from_index(index):
    index = int(index)
    letters = ""
    while True:
        letters = chr(ord("A") + (index % 26)) + letters
        index = index // 26 - 1
        if index < 0:
            break
    return letters


def validated_partition_modifications(audio_hash):
    """
    Retourne uniquement les modifications déjà persistées/validées.

    Sont considérées comme modifications de partition :
    - corrections de grille (measure_edits)
    - corrections de paroles (lyric_block_edits)
    - structure manuelle : nom personnalisé, frontière déplacée
      ou bloc sans référence de détection (ex. séparation ajoutée)

    Ce statut ne représente PAS les changements encore présents
    seulement dans les widgets d'édition.
    """
    grid_edits = load_measure_edits(audio_hash)
    lyric_edits = load_lyric_block_edits(audio_hash)

    try:
        blocks = load_structure_blocks(audio_hash)
    except Exception:
        blocks = []

    edited_blocks = []
    for block in blocks:
        custom_label = str(
            block.get("custom_label", "") or ""
        ).strip()

        current_start = int(block.get("measure_start", 0) or 0)
        current_end = int(block.get("measure_end", 0) or 0)

        detected_start = block.get("detected_measure_start")
        detected_end = block.get("detected_measure_end")

        boundary_changed = False

        if detected_start is None or detected_end is None:
            # Cas typique d'un bloc ajouté manuellement.
            boundary_changed = True
        else:
            boundary_changed = (
                current_start != int(detected_start)
                or current_end != int(detected_end)
            )

        if custom_label or boundary_changed:
            edited_blocks.append(block)

    return {
        "grid": len(grid_edits),
        "lyrics": len(lyric_edits),
        "blocks": len(edited_blocks),
        "has_any": bool(
            grid_edits
            or lyric_edits
            or edited_blocks
        ),
    }


def load_structure_blocks(audio_hash):
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            """
            SELECT
                block_id,
                order_index,
                cluster,
                custom_label,
                measure_start,
                measure_end,
                detected_measure_start,
                detected_measure_end
            FROM structure_blocks
            WHERE audio_hash = ?
            ORDER BY order_index ASC, block_id ASC
            """,
            (audio_hash,),
        ).fetchall()

    return [
        {
            "block_id": int(row[0]),
            "order_index": int(row[1]),
            "cluster": str(row[2]),
            "custom_label": str(row[3] or ""),
            "measure_start": int(row[4]),
            "measure_end": int(row[5]),
            "detected_measure_start": (
                None if row[6] is None else int(row[6])
            ),
            "detected_measure_end": (
                None if row[7] is None else int(row[7])
            ),
        }
        for row in rows
    ]


def _save_structure_blocks(audio_hash, blocks):
    """
    Sauvegarde atomiquement toute la partition manuelle.
    """
    now = _utc_now_iso()

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "DELETE FROM structure_blocks WHERE audio_hash = ?",
            (audio_hash,),
        )

        for order_index, block in enumerate(blocks):
            conn.execute(
                """
                INSERT INTO structure_blocks (
                    audio_hash,
                    block_id,
                    order_index,
                    cluster,
                    custom_label,
                    measure_start,
                    measure_end,
                    detected_measure_start,
                    detected_measure_end,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    audio_hash,
                    int(block["block_id"]),
                    int(order_index),
                    str(block["cluster"]),
                    str(block.get("custom_label", "") or "").strip(),
                    int(block["measure_start"]),
                    int(block["measure_end"]),
                    block.get("detected_measure_start"),
                    block.get("detected_measure_end"),
                    now,
                ),
            )

        conn.commit()


def _normaliser_partition_blocs(blocks, total_measures):
    """
    Garantit une partition continue du morceau :
    - première mesure = 1
    - aucun trou
    - aucun chevauchement
    - dernière mesure = total_measures
    - au moins une mesure par bloc
    """
    if not blocks:
        return []

    total_measures = max(1, int(total_measures))
    blocks = [dict(b) for b in blocks]
    blocks.sort(key=lambda b: int(b.get("order_index", b["block_id"])))

    # Si trop de blocs pour le nombre de mesures, on tronque proprement.
    blocks = blocks[:total_measures]

    boundaries = []
    for i, block in enumerate(blocks[:-1]):
        desired_end = int(block.get("measure_end", i + 1))
        min_end = i + 1
        remaining = len(blocks) - i - 1
        max_end = total_measures - remaining
        desired_end = max(min_end, min(max_end, desired_end))
        boundaries.append(desired_end)

    previous_end = 0
    for i, block in enumerate(blocks):
        start = previous_end + 1
        if i < len(boundaries):
            end = boundaries[i]
        else:
            end = total_measures

        block["order_index"] = i
        block["measure_start"] = start
        block["measure_end"] = end
        previous_end = end

    return blocks


def ensure_structure_blocks(
    audio_hash,
    detected_sections,
    total_measures,
):
    """
    Crée une partition persistante lors de la première ouverture seulement.

    Les anciens noms stockés par cluster dans block_edits sont récupérés,
    mais les anciennes bornes indépendantes sont ignorées : elles pouvaient
    créer chevauchements et trous.
    """
    existing = load_structure_blocks(audio_hash)
    if existing:
        normalized = _normaliser_partition_blocs(
            existing,
            total_measures,
        )
        if normalized != existing:
            _save_structure_blocks(audio_hash, normalized)
        return normalized

    total_measures = max(1, int(total_measures))
    legacy_labels = load_block_edits(audio_hash)

    detected = sorted(
        [dict(s) for s in detected_sections],
        key=lambda s: (
            int(s["measure_start"]),
            int(s["measure_end"]),
        ),
    )

    blocks = []

    if not detected:
        blocks = [{
            "block_id": 1,
            "order_index": 0,
            "cluster": "A",
            "custom_label": "",
            "measure_start": 1,
            "measure_end": total_measures,
            "detected_measure_start": 1,
            "detected_measure_end": total_measures,
        }]
    else:
        # Les débuts détectés définissent les frontières initiales.
        starts = []
        source_for_start = {}

        for section in detected:
            start = max(1, min(total_measures, int(section["measure_start"])))
            if start not in source_for_start:
                starts.append(start)
                source_for_start[start] = section

        if 1 not in source_for_start:
            starts.insert(0, 1)
            source_for_start[1] = detected[0]

        starts = sorted(set(starts))

        for i, start in enumerate(starts):
            end = (
                starts[i + 1] - 1
                if i + 1 < len(starts)
                else total_measures
            )

            if end < start:
                continue

            section = source_for_start[start]
            cluster = str(section.get("cluster", _alpha_label_from_index(i)))
            legacy = legacy_labels.get(cluster, {})

            blocks.append({
                "block_id": i + 1,
                "order_index": i,
                "cluster": cluster,
                "custom_label": str(
                    legacy.get("custom_label", "") or ""
                ).strip(),
                "measure_start": start,
                "measure_end": end,
                "detected_measure_start": int(section.get(
                    "measure_start",
                    start,
                )),
                "detected_measure_end": int(section.get(
                    "measure_end",
                    end,
                )),
            })

    blocks = _normaliser_partition_blocs(
        blocks,
        total_measures,
    )
    _save_structure_blocks(audio_hash, blocks)
    return blocks


def _next_manual_cluster(blocks):
    used = {str(b.get("cluster", "")) for b in blocks}
    index = 0
    while True:
        candidate = _alpha_label_from_index(index)
        if candidate not in used:
            return candidate
        index += 1


def update_structure_block_sequential(
    audio_hash,
    block_id,
    custom_label,
    measure_start,
    measure_end,
    total_measures,
):
    """
    Édition d'un bloc avec recalage automatique des voisins.

    - changer la fin d'un bloc fixe automatiquement le début du suivant ;
    - changer le début fixe automatiquement la fin du précédent.
    """
    blocks = load_structure_blocks(audio_hash)
    if not blocks:
        return False, "Aucun bloc persistant."

    idx = next(
        (i for i, b in enumerate(blocks) if int(b["block_id"]) == int(block_id)),
        None,
    )
    if idx is None:
        return False, "Bloc introuvable."

    total_measures = int(total_measures)
    start = int(measure_start)
    end = int(measure_end)

    if idx == 0:
        start = 1
    if idx == len(blocks) - 1:
        end = total_measures

    # Préserver au moins une mesure pour les voisins.
    if idx > 0:
        min_start = int(blocks[idx - 1]["measure_start"]) + 1
        start = max(min_start, start)
    else:
        start = 1

    if idx < len(blocks) - 1:
        max_end = int(blocks[idx + 1]["measure_end"]) - 1
        end = min(max_end, end)
    else:
        end = total_measures

    if start > end:
        return False, "Bornes incompatibles : le bloc doit contenir au moins une mesure."

    blocks[idx]["custom_label"] = str(custom_label or "").strip()
    blocks[idx]["measure_start"] = start
    blocks[idx]["measure_end"] = end

    if idx > 0:
        blocks[idx - 1]["measure_end"] = start - 1

    if idx < len(blocks) - 1:
        blocks[idx + 1]["measure_start"] = end + 1

    blocks = _normaliser_partition_blocs(
        blocks,
        total_measures,
    )
    _save_structure_blocks(audio_hash, blocks)

    return True, "Bloc enregistré et voisins recalés."




def _structure_draft_key(audio_hash):
    return f"structure_draft_{str(audio_hash)[:16]}"


def _structure_editor_revision_key(audio_hash):
    return f"structure_editor_revision_{str(audio_hash)[:16]}"


def _structure_action_message_key(audio_hash):
    return f"structure_action_message_{str(audio_hash)[:16]}"


def _canonical_structure_rows(blocks):
    """Forme stable pour comparer brouillon et état persisté."""
    return [
        (
            str(b.get("custom_label", "") or "").strip(),
            int(b.get("measure_start", 0) or 0),
            int(b.get("measure_end", 0) or 0),
        )
        for b in blocks
    ]


def _structure_draft_is_dirty(audio_hash):
    draft = st.session_state.get(_structure_draft_key(audio_hash))
    if not draft:
        return False
    persisted = load_structure_blocks(audio_hash)
    return _canonical_structure_rows(draft) != _canonical_structure_rows(persisted)


def _structure_draft_from_persisted(audio_hash):
    blocks = [dict(b) for b in load_structure_blocks(audio_hash)]
    st.session_state[_structure_draft_key(audio_hash)] = blocks
    st.session_state.setdefault(_structure_editor_revision_key(audio_hash), 0)
    return blocks


def _get_structure_draft(audio_hash):
    draft = st.session_state.get(_structure_draft_key(audio_hash))
    if draft is None:
        return _structure_draft_from_persisted(audio_hash)
    return [dict(b) for b in draft]


def _set_structure_draft(audio_hash, blocks, message=None):
    st.session_state[_structure_draft_key(audio_hash)] = [dict(b) for b in blocks]
    rev_key = _structure_editor_revision_key(audio_hash)
    st.session_state[rev_key] = int(st.session_state.get(rev_key, 0)) + 1
    if message:
        st.session_state[_structure_action_message_key(audio_hash)] = str(message)


def _normalize_structure_draft(blocks, total_measures):
    """
    Normalise le brouillon uniquement en mémoire :
    - Début = Fin précédente + 1
    - dernier Fin = total
    - aucun trou / chevauchement
    - au moins 1 mesure par bloc
    """
    if not blocks:
        return []

    total_measures = max(1, int(total_measures))
    blocks = [dict(b) for b in blocks]
    blocks = blocks[:total_measures]

    previous_end = 0
    for i, block in enumerate(blocks):
        start = previous_end + 1
        remaining = len(blocks) - i - 1

        block["order_index"] = i
        block["measure_start"] = start

        if i == len(blocks) - 1:
            end = total_measures
        else:
            requested = int(block.get("measure_end", start) or start)
            min_end = start
            max_end = total_measures - remaining
            end = max(min_end, min(max_end, requested))

        block["measure_end"] = end
        previous_end = end

    return blocks


def _apply_structure_table_live_edit(blocks, edited_rows, total_measures):
    """
    Applique immédiatement Nom/Fin du tableau puis recalcule Début/Nb mesures.

    Si une frontière change, les blocs suivants sont décalés en conservant
    leurs durées antérieures autant que possible.
    """
    blocks = [dict(b) for b in blocks]
    if len(edited_rows) != len(blocks):
        return _normalize_structure_draft(blocks, total_measures)

    durations = [
        max(1, int(b["measure_end"]) - int(b["measure_start"]) + 1)
        for b in blocks
    ]

    changed_index = None
    requested_end = None

    for i, row in enumerate(edited_rows):
        blocks[i]["custom_label"] = str(row.get("Nom", "") or "").strip() or "Nouveau bloc"

        if i < len(blocks) - 1:
            try:
                candidate = int(row.get("Fin"))
            except Exception:
                candidate = int(blocks[i]["measure_end"])

            if candidate != int(blocks[i]["measure_end"]) and changed_index is None:
                changed_index = i
                requested_end = candidate

    if changed_index is None:
        return _normalize_structure_draft(blocks, total_measures)

    # Refaire toute la chaîne, puis préserver au mieux les durées après le pivot.
    previous_end = 0
    for i, block in enumerate(blocks):
        start = previous_end + 1
        block["measure_start"] = start
        block["order_index"] = i

        if i == len(blocks) - 1:
            end = int(total_measures)
        elif i == changed_index:
            remaining = len(blocks) - i - 1
            max_end = int(total_measures) - remaining
            end = max(start, min(max_end, int(requested_end)))
        elif i > changed_index:
            remaining = len(blocks) - i - 1
            max_end = int(total_measures) - remaining
            end = min(start + durations[i] - 1, max_end)
            end = max(start, end)
        else:
            end = int(block["measure_end"])
            remaining = len(blocks) - i - 1
            end = max(start, min(int(total_measures) - remaining, end))

        block["measure_end"] = end
        previous_end = end

    return _normalize_structure_draft(blocks, total_measures)


def _next_structure_draft_id(blocks):
    positive = [int(b.get("block_id", 0) or 0) for b in blocks]
    return (max(positive) if positive else 0) + 1


def _insert_structure_draft_after(blocks, row_index, total_measures):
    """
    Insère un bloc après la ligne choisie.
    Le nouveau bloc prend par défaut la dernière mesure du bloc courant.
    """
    blocks = _normalize_structure_draft(blocks, total_measures)
    if not blocks:
        return blocks, "Aucun bloc disponible."

    row_index = max(0, min(len(blocks) - 1, int(row_index)))
    target = blocks[row_index]

    if int(target["measure_end"]) <= int(target["measure_start"]):
        return blocks, "Ce bloc ne contient qu'une mesure : impossible de le scinder ici."

    old_end = int(target["measure_end"])
    target["measure_end"] = old_end - 1

    new_block = {
        "block_id": _next_structure_draft_id(blocks),
        "order_index": row_index + 1,
        "cluster": _next_manual_cluster(blocks),
        "custom_label": "Nouveau bloc",
        "measure_start": old_end,
        "measure_end": old_end,
        "detected_measure_start": None,
        "detected_measure_end": None,
    }
    blocks.insert(row_index + 1, new_block)
    blocks = _normalize_structure_draft(blocks, total_measures)
    return blocks, "Bloc inséré. Ajustez sa frontière si nécessaire."


def _append_structure_draft(blocks, total_measures):
    """Ajoute un bloc final en prenant 1 mesure au dernier bloc."""
    if not blocks:
        return blocks, "Aucun bloc disponible."
    return _insert_structure_draft_after(
        blocks,
        len(blocks) - 1,
        total_measures,
    )


def _delete_structure_draft_row(blocks, row_index, total_measures):
    """
    Supprime un bloc sans trou :
    - premier bloc : sa plage est absorbée par le suivant ;
    - sinon : sa plage est absorbée par le précédent.
    """
    blocks = _normalize_structure_draft(blocks, total_measures)

    if len(blocks) <= 1:
        return blocks, "Le dernier bloc restant ne peut pas être supprimé."

    row_index = max(0, min(len(blocks) - 1, int(row_index)))
    victim = blocks[row_index]

    if row_index == 0:
        blocks[1]["measure_start"] = int(victim["measure_start"])
    else:
        blocks[row_index - 1]["measure_end"] = int(victim["measure_end"])

    del blocks[row_index]
    blocks = _normalize_structure_draft(blocks, total_measures)
    return blocks, "Bloc supprimé ; la séquence a été refermée automatiquement."



def _delete_structure_draft_rows(blocks, row_indices, total_measures):
    """
    Supprime plusieurs blocs en une seule opération.

    Les cases restent cochables librement dans le tableau ; aucune suppression
    n'est appliquée avant clic sur "Supprimer la sélection".
    """
    blocks = _normalize_structure_draft(blocks, total_measures)

    selected = sorted({
        int(i)
        for i in row_indices
        if 0 <= int(i) < len(blocks)
    })

    if not selected:
        return blocks, "Aucun bloc sélectionné."

    if len(selected) >= len(blocks):
        return blocks, "Il faut conserver au moins un bloc."

    survivors = [
        dict(block)
        for i, block in enumerate(blocks)
        if i not in set(selected)
    ]

    survivors = _normalize_structure_draft(
        survivors,
        total_measures,
    )

    return (
        survivors,
        f"{len(selected)} bloc(s) supprimé(s) ; "
        "la séquence a été refermée automatiquement.",
    )


def _persist_structure_draft(audio_hash, draft, total_measures):
    """
    Persiste exactement le brouillon visible.
    Une nouvelle version est créée par l'appelant.
    """
    blocks = _normalize_structure_draft(draft, total_measures)

    if not blocks:
        return False, "Le morceau doit conserver au moins un bloc."

    _save_structure_blocks(audio_hash, blocks)
    st.session_state[_structure_draft_key(audio_hash)] = [dict(b) for b in blocks]
    return True, "Découpage validé."



def save_structure_blocks_from_table(
    audio_hash,
    blocks,
    edited_rows,
    total_measures,
):
    """
    Sauvegarde un découpage strictement séquentiel.

    Principe musicien :
      - on modifie le NOM et éventuellement la FIN d'un bloc ;
      - le bloc suivant commence automatiquement à FIN + 1 ;
      - si une frontière est déplacée, tous les blocs suivants sont
        décalés en conservant leur durée d'origine autant que possible ;
      - le dernier bloc absorbe le reliquat jusqu'à la dernière mesure.

    Exemple :
      Refrain 1 finit à 33
      -> Couplet 2 commence automatiquement à 34
      -> les blocs suivants sont décalés.
    """
    if not blocks:
        return False, "Aucun bloc à enregistrer."

    total_measures = int(total_measures)
    new_blocks = [dict(b) for b in blocks]

    if len(edited_rows) != len(new_blocks):
        return False, "Le nombre de lignes du tableau ne correspond plus aux blocs."

    # Durée actuelle de chaque bloc avant édition.
    durations = [
        max(
            1,
            int(block["measure_end"]) - int(block["measure_start"]) + 1,
        )
        for block in new_blocks
    ]

    # La première frontière modifiée devient le pivot.
    # Les blocs suivants sont ensuite décalés en gardant leur durée.
    changed_index = None
    requested_end = None

    for i, row in enumerate(edited_rows[:-1]):
        try:
            candidate_end = int(row.get("Fin"))
        except Exception:
            return False, f"Ligne {i + 1} : fin invalide."

        old_end = int(new_blocks[i]["measure_end"])

        if candidate_end != old_end and changed_index is None:
            changed_index = i
            requested_end = candidate_end

    # Mettre à jour les noms dans tous les cas.
    for i, row in enumerate(edited_rows):
        label = str(row.get("Nom", "") or "").strip()
        new_blocks[i]["custom_label"] = label or "Nouveau bloc"

    # Si aucune frontière n'a changé, on normalise simplement les débuts.
    if changed_index is None:
        previous_end = 0
        for i, block in enumerate(new_blocks):
            block["measure_start"] = previous_end + 1

            if i == len(new_blocks) - 1:
                block["measure_end"] = total_measures
            else:
                # Conserver la fin actuellement affichée si elle reste valide.
                end_value = int(block["measure_end"])
                min_end = int(block["measure_start"])
                remaining = len(new_blocks) - i - 1
                max_end = total_measures - remaining
                block["measure_end"] = max(
                    min_end,
                    min(max_end, end_value),
                )

            block["order_index"] = i
            previous_end = int(block["measure_end"])

        _save_structure_blocks(audio_hash, new_blocks)
        return True, "Découpage enregistré."

    # Valider la nouvelle fin du bloc pivot.
    pivot_start = int(new_blocks[changed_index]["measure_start"])
    remaining_blocks = len(new_blocks) - changed_index - 1
    max_pivot_end = total_measures - remaining_blocks

    if requested_end < pivot_start or requested_end > max_pivot_end:
        return (
            False,
            (
                f"Fin {requested_end} impossible pour "
                f"{new_blocks[changed_index].get('custom_label') or 'ce bloc'}. "
                f"Valeur attendue entre {pivot_start} et {max_pivot_end}."
            ),
        )

    # Tout ce qui précède reste inchangé, sauf normalisation des débuts.
    previous_end = 0

    for i in range(changed_index):
        block = new_blocks[i]
        block["measure_start"] = previous_end + 1
        block["order_index"] = i
        previous_end = int(block["measure_end"])

    # Bloc pivot.
    pivot = new_blocks[changed_index]
    pivot["measure_start"] = previous_end + 1
    pivot["measure_end"] = int(requested_end)
    pivot["order_index"] = changed_index
    previous_end = int(requested_end)

    # Décaler les suivants en conservant leur durée.
    for i in range(changed_index + 1, len(new_blocks)):
        block = new_blocks[i]
        block["measure_start"] = previous_end + 1
        block["order_index"] = i

        if i == len(new_blocks) - 1:
            block["measure_end"] = total_measures
        else:
            proposed_end = (
                int(block["measure_start"])
                + int(durations[i])
                - 1
            )

            remaining_after = len(new_blocks) - i - 1
            max_end = total_measures - remaining_after

            block["measure_end"] = min(
                proposed_end,
                max_end,
            )

        previous_end = int(block["measure_end"])

    # Dernière sécurité : partition continue jusqu'à la fin.
    if new_blocks:
        new_blocks[0]["measure_start"] = 1
        for i in range(1, len(new_blocks)):
            new_blocks[i]["measure_start"] = (
                int(new_blocks[i - 1]["measure_end"]) + 1
            )
        new_blocks[-1]["measure_end"] = total_measures

    _save_structure_blocks(audio_hash, new_blocks)

    next_txt = ""
    if changed_index + 1 < len(new_blocks):
        nxt = new_blocks[changed_index + 1]
        next_txt = (
            f" Le bloc suivant commence maintenant à "
            f"{nxt['measure_start']}."
        )

    return True, "Découpage décalé automatiquement." + next_txt


def reset_structure_blocks_from_analysis(audio_hash):
    """
    Supprime seulement la structure manuelle.
    Au prochain rerun, ensure_structure_blocks() la reconstruit
    depuis l'analyse persistée.
    """
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            DELETE FROM structure_blocks
            WHERE audio_hash = ?
            """,
            (audio_hash,),
        )
        conn.commit()


def add_structure_separator(
    audio_hash,
    split_after_measure,
    total_measures,
):
    """
    Ajoute une frontière après une mesure en scindant le bloc
    qui contient cette mesure.
    """
    blocks = load_structure_blocks(audio_hash)

    if not blocks:
        return False, "Aucun bloc disponible."

    split_after = int(split_after_measure)

    if split_after < 1 or split_after >= int(total_measures):
        return False, "La séparation doit être située avant la dernière mesure."

    # Si cette frontière existe déjà, ne rien faire.
    for block in blocks[:-1]:
        if int(block["measure_end"]) == split_after:
            return False, "Une séparation existe déjà à cet endroit."

    target = next(
        (
            block
            for block in blocks
            if int(block["measure_start"]) <= split_after < int(block["measure_end"])
        ),
        None,
    )

    if target is None:
        return False, "Impossible de trouver le bloc à scinder."

    ok, message = split_structure_block(
        audio_hash=audio_hash,
        block_id=int(target["block_id"]),
        split_after_measure=split_after,
        total_measures=total_measures,
    )

    if not ok:
        return ok, message

    # Le nouveau bloc créé par la scission reçoit un nom neutre lisible.
    blocks_after = load_structure_blocks(audio_hash)
    new_block = next(
        (
            b
            for b in blocks_after
            if int(b["measure_start"]) == split_after + 1
        ),
        None,
    )

    if new_block is not None and not str(
        new_block.get("custom_label", "") or ""
    ).strip():
        new_block["custom_label"] = "Nouveau bloc"
        _save_structure_blocks(audio_hash, blocks_after)

    return True, f"Séparation ajoutée après la mesure {split_after}."


def split_structure_block(
    audio_hash,
    block_id,
    split_after_measure,
    total_measures,
):
    """
    Scinde un bloc après la mesure choisie.
    """
    blocks = load_structure_blocks(audio_hash)
    idx = next(
        (i for i, b in enumerate(blocks) if int(b["block_id"]) == int(block_id)),
        None,
    )
    if idx is None:
        return False, "Bloc introuvable."

    block = blocks[idx]
    split_after = int(split_after_measure)

    if not (
        int(block["measure_start"])
        <= split_after
        < int(block["measure_end"])
    ):
        return False, "La scission doit être située à l'intérieur du bloc."

    new_id = max(int(b["block_id"]) for b in blocks) + 1
    new_cluster = _next_manual_cluster(blocks)

    new_block = {
        "block_id": new_id,
        "order_index": idx + 1,
        "cluster": new_cluster,
        "custom_label": "",
        "measure_start": split_after + 1,
        "measure_end": int(block["measure_end"]),
        "detected_measure_start": int(block["detected_measure_start"])
            if block.get("detected_measure_start") is not None else None,
        "detected_measure_end": int(block["detected_measure_end"])
            if block.get("detected_measure_end") is not None else None,
    }

    blocks[idx]["measure_end"] = split_after
    blocks.insert(idx + 1, new_block)

    blocks = _normaliser_partition_blocs(blocks, total_measures)
    _save_structure_blocks(audio_hash, blocks)

    return True, f"Bloc scindé après la mesure {split_after}."


def merge_structure_block_with_next(
    audio_hash,
    block_id,
    total_measures,
):
    blocks = load_structure_blocks(audio_hash)
    idx = next(
        (i for i, b in enumerate(blocks) if int(b["block_id"]) == int(block_id)),
        None,
    )

    if idx is None:
        return False, "Bloc introuvable."

    if idx >= len(blocks) - 1:
        return False, "Le dernier bloc ne peut pas être fusionné avec un suivant."

    blocks[idx]["measure_end"] = int(
        blocks[idx + 1]["measure_end"]
    )
    del blocks[idx + 1]

    blocks = _normaliser_partition_blocs(blocks, total_measures)
    _save_structure_blocks(audio_hash, blocks)

    return True, "Fusion effectuée."


def materialiser_structure_blocks(
    blocks,
    mesures,
    detected_sections,
):
    """
    Convertit la partition persistante dans le format attendu par
    grille, parolier et diagnostic.
    """
    result = []

    def overlap(a0, a1, b0, b1):
        return max(0, min(a1, b1) - max(a0, b0) + 1)

    for block in blocks:
        start = int(block["measure_start"])
        end = int(block["measure_end"])

        groupe = [
            m for m in mesures
            if start <= int(m["numero"]) <= end
        ]

        if not groupe:
            continue

        best = None
        best_overlap = -1

        for detected in detected_sections:
            ov = overlap(
                start,
                end,
                int(detected["measure_start"]),
                int(detected["measure_end"]),
            )
            if ov > best_overlap:
                best_overlap = ov
                best = detected

        best = best or {}

        result.append({
            "block_id": int(block["block_id"]),
            "order_index": int(block["order_index"]),
            "cluster": str(block["cluster"]),
            "custom_label": str(block.get("custom_label", "") or ""),
            "measure_start": start,
            "measure_end": end,
            "detected_measure_start": block.get("detected_measure_start"),
            "detected_measure_end": block.get("detected_measure_end"),
            "time_start": float(groupe[0]["debut"]),
            # +1 ms : même convention que l'éditeur de blocs. Cela évite
            # qu'un mot situé exactement sur une frontière passe dans le
            # bloc voisin selon la vue utilisée.
            "time_end": float(groupe[-1]["fin"]) + 0.001,
            "measure_patterns": [
                _normaliser_pattern_mesure(m.get("notation", ""))
                for m in groupe
            ],
            "confidence": float(best.get("confidence", 0.0)),
            "cluster_repeats": int(best.get("cluster_repeats", 1)),
            "lyric_repeat": float(best.get("lyric_repeat", 0.0)),
            "harmonic_repeat": float(best.get("harmonic_repeat", 0.0)),
            "type": libelle_bloc_affiche({
                "cluster": str(block["cluster"]),
                "custom_label": str(block.get("custom_label", "") or ""),
            }),
        })

    return result



_CHORD_TOKEN_RE = re.compile(
    r"""
    (?P<chord>
        [A-G]
        (?:\#|b)?
        (?:
            maj7
            |m7b5
            |dim7
            |dim
            |m7
            |7
            |m
        )?
    )
    |
    (?P<hold>-)
    |
    (?P<silence>\.)
    """,
    re.VERBOSE,
)


def accord_reel_depuis_forme_capo(accord_forme, capo):
    """
    Inverse de accord_forme_capo :
      forme jouée Am, capo 3 -> accord réel Cm
    """
    if not accord_forme or accord_forme in (".", "-", "?", "^"):
        return accord_forme

    capo = int(capo or 0)
    if capo == 0:
        return accord_forme

    root = accord_forme[0]
    suffix_start = 1

    if len(accord_forme) >= 2 and accord_forme[1] in ("#", "b"):
        root += accord_forme[1]
        suffix_start = 2

    if root not in _NOTE_TO_PC:
        return accord_forme

    pc_forme = _NOTE_TO_PC[root]
    pc_reel = (pc_forme + capo) % 12

    return _NOTES_SHARP[pc_reel] + accord_forme[suffix_start:]


def parser_notation_mesure(notation, expected_positions):
    """
    Parse la notation EZScore d'UNE mesure.

    Exemples :
      Am---           -> 4 positions
      Am-Em-          -> 4 positions
      D.C-            -> 4 positions
      Am-- | Em--     -> 6 positions

    '-' signifie : tenir l'accord de la position précédente.
    '.' signifie : silence harmonique.
    '^' final est le point d'orgue.
    """
    raw = str(notation or "").strip()
    fermata = raw.endswith("^")

    if fermata:
        raw = raw[:-1].rstrip()

    # Les barres des signatures composées sont purement visuelles.
    compact = raw.replace("|", "").replace(" ", "")

    if not compact:
        return False, [], fermata, "Mesure vide."

    tokens = []
    cursor = 0

    for match in _CHORD_TOKEN_RE.finditer(compact):
        if match.start() != cursor:
            bad = compact[cursor:match.start()]
            return (
                False,
                [],
                fermata,
                f"Syntaxe inconnue : {bad!r}.",
            )

        cursor = match.end()

        if match.group("chord"):
            tokens.append(match.group("chord"))
        elif match.group("silence"):
            tokens.append(".")
        else:
            # tenue
            if not tokens or tokens[-1] == ".":
                return (
                    False,
                    [],
                    fermata,
                    "'-' ne peut pas suivre un silence ou commencer une mesure.",
                )
            tokens.append(tokens[-1])

    if cursor != len(compact):
        return (
            False,
            [],
            fermata,
            f"Syntaxe inconnue : {compact[cursor:]!r}.",
        )

    if len(tokens) != int(expected_positions):
        return (
            False,
            tokens,
            fermata,
            (
                f"{len(tokens)} position(s) lue(s), "
                f"{int(expected_positions)} attendue(s)."
            ),
        )

    return True, tokens, fermata, ""


def load_measure_edits(audio_hash):
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            """
            SELECT measure_no, notation_real
            FROM measure_edits
            WHERE audio_hash = ?
            ORDER BY measure_no
            """,
            (audio_hash,),
        ).fetchall()

    return {
        int(row[0]): str(row[1])
        for row in rows
    }


def save_measure_edit(
    audio_hash,
    measure_no,
    notation_real,
):
    now = _utc_now_iso()

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO measure_edits (
                audio_hash,
                measure_no,
                notation_real,
                updated_at
            )
            VALUES (?, ?, ?, ?)
            ON CONFLICT(audio_hash, measure_no)
            DO UPDATE SET
                notation_real = excluded.notation_real,
                updated_at = excluded.updated_at
            """,
            (
                audio_hash,
                int(measure_no),
                str(notation_real),
                now,
            ),
        )
        conn.commit()


def delete_measure_edit(audio_hash, measure_no):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            DELETE FROM measure_edits
            WHERE audio_hash = ? AND measure_no = ?
            """,
            (audio_hash, int(measure_no)),
        )
        conn.commit()


def appliquer_editions_mesures_aux_beats(
    audio_hash,
    beats,
    beats_par_mesure,
    signature,
):
    """
    Les corrections de grille sont appliquées aux beats internes,
    puis le reste de EZScore reconstruit ses mesures normalement.
    """
    edits = load_measure_edits(audio_hash)

    if not edits:
        return beats

    resultat = [dict(b) for b in beats]
    positions = int(beats_par_mesure)

    for measure_no, notation_real in edits.items():
        ok, symbols, _fermata, _error = parser_notation_mesure(
            notation_real,
            positions,
        )

        if not ok:
            continue

        start = (int(measure_no) - 1) * positions

        for offset, accord in enumerate(symbols):
            idx = start + offset
            if idx >= len(resultat):
                break
            resultat[idx]["accord"] = accord

    return resultat


def notation_affichee_depuis_reelle(
    notation_real,
    signature,
    capo,
    expected_positions,
):
    ok, symbols, fermata, _error = parser_notation_mesure(
        notation_real,
        expected_positions,
    )
    if not ok:
        return notation_real

    affiches = [
        accord_forme_capo(a, capo)
        for a in symbols
    ]

    return formatter_mesure_signature(
        affiches,
        signature,
        fermata=fermata,
    )


def notation_reelle_depuis_affichage(
    notation_affichee,
    signature,
    capo,
    expected_positions,
):
    ok, symbols, fermata, error = parser_notation_mesure(
        notation_affichee,
        expected_positions,
    )

    if not ok:
        return False, "", error

    reels = [
        accord_reel_depuis_forme_capo(a, capo)
        for a in symbols
    ]

    notation_real = formatter_mesure_signature(
        reels,
        signature,
        fermata=fermata,
    )

    return True, notation_real, ""


def _placer_texte_monospaced(
    items,
    origin_time,
    end_time,
    target_width,
    min_gap=1,
):
    """
    Place une suite d'éléments horodatés sur une ligne monospace.

    Les positions temporelles donnent la position idéale. En cas de
    collision textuelle, on décale uniquement le texte vers la droite.
    """
    if not items:
        return "", []

    origin_time = float(origin_time)
    end_time = max(float(end_time), origin_time + 1e-6)
    target_width = max(int(target_width), 1)

    placements = []
    previous_end = -1

    for item in items:
        txt = str(item["text"])
        t = float(item["time"])

        ratio = np.clip(
            (t - origin_time) / (end_time - origin_time),
            0.0,
            1.0,
        )
        ideal = int(round(ratio * max(target_width - 1, 0)))

        pos = max(ideal, previous_end + int(min_gap))
        placements.append((pos, txt, t))
        previous_end = pos + len(txt) - 1

    width = max(
        target_width,
        max(pos + len(txt) for pos, txt, _ in placements),
    )
    chars = [" "] * width

    for pos, txt, _ in placements:
        if pos + len(txt) > len(chars):
            chars.extend(
                [" "] * (pos + len(txt) - len(chars))
            )
        for j, ch in enumerate(txt):
            chars[pos + j] = ch

    return "".join(chars).rstrip(), placements


def _placer_accords_monospaced(
    events,
    origin_time,
    end_time,
    target_width,
    min_gap=2,
):
    """
    Place les notations de mesure sur la timeline.

    Contrairement aux paroles, les accords restent à leur position
    temporelle de référence ; seuls les accords qui se chevaucheraient
    sont repoussés juste assez pour rester lisibles.
    """
    if not events:
        return "", []

    origin_time = float(origin_time)
    end_time = max(float(end_time), origin_time + 1e-6)
    target_width = max(int(target_width), 1)

    placements = []
    previous_end = -1

    for event in events:
        txt = str(event["text"])
        t = float(event["time"])

        ratio = np.clip(
            (t - origin_time) / (end_time - origin_time),
            0.0,
            1.0,
        )
        ideal = int(round(ratio * max(target_width - 1, 0)))
        pos = max(ideal, previous_end + int(min_gap))

        placements.append((pos, txt, t))
        previous_end = pos + len(txt) - 1

    width = max(
        target_width,
        max(pos + len(txt) for pos, txt, _ in placements),
    )
    chars = [" "] * width

    for pos, txt, _ in placements:
        if pos + len(txt) > len(chars):
            chars.extend(
                [" "] * (pos + len(txt) - len(chars))
            )
        for j, ch in enumerate(txt):
            chars[pos + j] = ch

    return "".join(chars).rstrip(), placements


def _decaler_paroles_sous_accords(
    words,
    chord_placements,
    origin_time,
    end_time,
    target_width,
):
    """
    V38c — accords fixes, texte lisible.

    Les accords ne bougent jamais.

    Pour les paroles :
      - jamais de suppression d'espaces naturels ;
      - jamais de découpage artificiel d'un mot ;
      - on ajoute des espaces ENTRE les mots pour amener le mot
        correspondant sous l'accord.

    Si un accord tombe au milieu d'un mot et qu'on ne possède pas de
    timestamps syllabiques, le mot entier est ancré au plus près sans
    introduire de "_" dans son orthographe.
    """
    if not words:
        return ""

    anchors_by_word = {i: [] for i in range(len(words))}

    for chord_pos, _notation, chord_time in chord_placements:
        target_index = None

        for i, word in enumerate(words):
            w0 = float(word["start"])
            w1 = float(word["end"])

            if w0 <= chord_time <= w1:
                target_index = i
                break

            if chord_time < w0:
                target_index = i
                break

        if target_index is not None:
            anchors_by_word[target_index].append(
                int(chord_pos)
            )

    output = []
    cursor = 0

    for i, word in enumerate(words):
        txt = str(word["text"]).strip()
        if not txt:
            continue

        # Toujours au moins un espace naturel entre deux mots.
        if output:
            output.append(" ")
            cursor += 1

        desired_start = cursor
        anchors = anchors_by_word.get(i, [])

        if anchors:
            # Le mot peut être repoussé vers la droite, jamais vers la gauche.
            desired_start = max(
                desired_start,
                min(anchors),
            )

        if desired_start > cursor:
            output.append(" " * (desired_start - cursor))
            cursor = desired_start

        output.append(txt)
        cursor += len(txt)

    return "".join(output).rstrip()

def construire_lignes_paroles_intervalle(
    mesures,
    resultat,
    t0,
    t1,
    max_chars=74,
    corrected_block_text=None,
):
    """
    V38d : correction par bloc.
    Les accords restent fixes. Le texte corrigé est redistribué sur
    la timeline Whisper d'origine. Les retours à la ligne manuels sont
    respectés.
    """
    source_words = _source_words_for_interval(resultat, t0, t1)
    if not source_words:
        return []

    manual_mode = bool(str(corrected_block_text or "").strip())
    if manual_mode:
        mots = _redistribute_corrected_block_text(
            corrected_block_text, source_words
        )
    else:
        mots = [{**w, "manual_line_end": False} for w in source_words]

    groupes, courant, longueur = [], [], 0

    for i, word in enumerate(mots):
        txt = str(word["text"]).strip()
        if not txt:
            continue

        ajout = len(txt) + (1 if courant else 0)
        if not manual_mode and courant and longueur + ajout > int(max_chars):
            groupes.append(courant)
            courant, longueur = [], 0

        courant.append(word)
        longueur += ajout

        if manual_mode and word.get("manual_line_end"):
            groupes.append(courant)
            courant, longueur = [], 0
            continue

        if not manual_mode:
            punctuation = txt.endswith((".", "!", "?", ";", ":"))
            pause = 0.0
            if i + 1 < len(mots):
                pause = float(mots[i + 1]["start"]) - float(word["end"])
            if ((punctuation and longueur >= 24)
                    or (pause >= 0.75 and longueur >= 20)):
                groupes.append(courant)
                courant, longueur = [], 0

    if courant:
        groupes.append(courant)

    lignes = []

    for groupe in groupes:
        lt0 = float(groupe[0]["start"])
        lt1 = float(groupe[-1]["end"])

        mesures_ligne = [
            m for m in mesures
            if (
                float(m["fin"]) > lt0
                and float(m["debut"]) < lt1 + 1e-6
                and float(m["fin"]) > float(t0)
                and float(m["debut"]) < float(t1)
            )
        ]

        if mesures_ligne:
            origin_time = max(float(t0), float(mesures_ligne[0]["debut"]))
            line_end = min(
                float(t1),
                max(lt1, float(mesures_ligne[-1]["fin"])),
            )
        else:
            origin_time, line_end = lt0, lt1

        duration = max(line_end - origin_time, 1e-6)
        compact = " ".join(str(w["text"]) for w in groupe)
        notation_chars = sum(
            len(str(m.get("notation", ""))) + 2 for m in mesures_ligne
        )

        target_width = max(
            len(compact) + 6,
            notation_chars,
            int(round(duration * 7.0)),
            32,
        )
        target_width = min(target_width, 118)

        chord_events = [
            {
                "time": max(origin_time, float(m["debut"])),
                "text": str(m["notation"]),
            }
            for m in mesures_ligne
        ]

        accords, placements = _placer_accords_monospaced(
            events=chord_events,
            origin_time=origin_time,
            end_time=line_end,
            target_width=target_width,
            min_gap=2,
        )

        paroles = _decaler_paroles_sous_accords(
            words=groupe,
            chord_placements=placements,
            origin_time=origin_time,
            end_time=line_end,
            target_width=target_width,
        )

        lignes.append({
            "accords": accords,
            "paroles": paroles,
            "debut": lt0,
            "fin": lt1,
            "manual_verse": bool(manual_mode),
            # Métadonnée seulement : permet d'identifier les mesures déjà
            # rendues sans modifier le rendu vocal historique.
            "mesure_numeros": [
                int(m.get("numero", 0) or 0)
                for m in mesures_ligne
                if int(m.get("numero", 0) or 0) > 0
            ],
            "instrumental": False,
        })

    if manual_mode and len(lignes) > 1:
        # Le parolier doit matérialiser les retours à la ligne saisis dans
        # Blocs > Édition. Les lignes vocales restent inchangées ; on insère
        # uniquement un séparateur visuel entre deux vers manuels.
        separated = []
        for index, line in enumerate(lignes):
            separated.append(line)
            if index < len(lignes) - 1:
                separated.append({
                    "accords": "",
                    "paroles": " ",
                    "debut": float(line.get("fin", 0.0)),
                    "fin": float(line.get("fin", 0.0)),
                    "mesure_numeros": [],
                    "instrumental": False,
                    "manual_verse_separator": True,
                })
        lignes = separated

    return lignes




def construire_lignes_paroles_completes_intervalle(
    mesures,
    resultat,
    t0,
    t1,
    max_chars=74,
    corrected_block_text=None,
):
    """
    R10 — complète le rendu historique sans le remplacer.

    Les lignes vocales sont produites exactement par
    construire_lignes_paroles_intervalle().

    On ajoute ensuite uniquement les mesures de l'intervalle qui n'ont été
    représentées par AUCUNE ligne vocale. Cela rend visibles :
    - l'introduction instrumentale ;
    - les passages instrumentaux entre deux zones chantées ;
    - la fin instrumentale.

    Une chanson dont toutes les mesures sont déjà représentées ne reçoit
    aucune ligne supplémentaire.
    """
    vocal_lines = construire_lignes_paroles_intervalle(
        mesures=mesures,
        resultat=resultat,
        t0=t0,
        t1=t1,
        max_chars=max_chars,
        corrected_block_text=corrected_block_text,
    )

    represented = set()
    for line in vocal_lines:
        represented.update(
            int(n)
            for n in line.get("mesure_numeros", [])
            if int(n) > 0
        )

    interval_measures = [
        m
        for m in mesures
        if (
            float(m["fin"]) > float(t0)
            and float(m["debut"]) < float(t1)
        )
    ]

    missing = [
        m
        for m in interval_measures
        if int(m.get("numero", 0) or 0) not in represented
    ]

    instrumental_lines = []
    group = []

    def flush_group():
        nonlocal group
        if not group:
            return

        # Rendu compact, lisible, sans modifier la notation de mesure.
        accords = "   ".join(
            str(m.get("notation", "") or "")
            for m in group
        ).strip()

        instrumental_lines.append({
            "accords": accords,
            "paroles": "[instrumental]",
            "debut": max(float(t0), float(group[0]["debut"])),
            "fin": min(float(t1), float(group[-1]["fin"])),
            "mesure_numeros": [
                int(m.get("numero", 0) or 0)
                for m in group
            ],
            "instrumental": True,
        })

        group = []

    previous_no = None

    for measure in missing:
        measure_no = int(measure.get("numero", 0) or 0)

        if (
            group
            and (
                previous_no is None
                or measure_no != previous_no + 1
                or len(group) >= 4
            )
        ):
            flush_group()

        group.append(measure)
        previous_no = measure_no

    flush_group()

    completed = [dict(line) for line in vocal_lines] + instrumental_lines

    completed.sort(
        key=lambda line: (
            float(line.get("debut", 0.0)),
            0 if line.get("instrumental") else 1,
        )
    )

    return completed




def make_analysis_parameters(
    signature_mode,
    analyse_sr,
    hop_length,
    silence_rms_ratio,
    silence_chroma_ratio,
    poids_fondamentale,
    fermata_enabled,
    fermata_gap_ratio,
    whisper_device="cpu",
):
    return {
        "schema_version": PERSISTENCE_SCHEMA_VERSION,
        "engine_version": ANALYSIS_ENGINE_VERSION,
        "signature_mode": signature_mode,
        "analyse_sr": int(analyse_sr),
        "hop_length": int(hop_length),
        "silence_rms_ratio": float(silence_rms_ratio),
        "silence_chroma_ratio": float(silence_chroma_ratio),
        "poids_fondamentale": float(poids_fondamentale),
        "fermata_enabled": bool(fermata_enabled),
        "fermata_gap_ratio": float(fermata_gap_ratio),
        "whisper_model": "small",
        "whisper_device": str(whisper_device or "cpu"),
    }


def make_analysis_key(parameters):
    canonical = json.dumps(
        _json_safe(parameters),
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()



def load_latest_analysis_parameters(audio_hash):
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            """
            SELECT parameters_json
            FROM analyses
            WHERE audio_hash = ?
            ORDER BY updated_at DESC
            LIMIT 1
            """,
            (audio_hash,),
        ).fetchone()

    if row is None:
        return None

    try:
        return json.loads(row[0])
    except Exception:
        return None


def hydrate_settings_from_parameters(parameters):
    """
    Prépare les valeurs des widgets pour le prochain rerun.
    """
    if not parameters:
        return

    mapping = {
        "setting_signature_mode": parameters.get("signature_mode", "Auto"),
        "setting_analyse_sr": int(parameters.get("analyse_sr", 22050)),
        "setting_hop_length": int(parameters.get("hop_length", 2048)),
        "setting_silence_rms": float(parameters.get("silence_rms_ratio", 0.22)),
        "setting_silence_chroma": float(parameters.get("silence_chroma_ratio", 0.18)),
        "setting_poids_fondamentale": float(parameters.get("poids_fondamentale", 0.22)),
        "setting_fermata_enabled": bool(parameters.get("fermata_enabled", True)),
        "setting_fermata_gap": float(parameters.get("fermata_gap_ratio", 1.85)),
    }

    for key, value in mapping.items():
        st.session_state[key] = value


def next_analysis_version_no(audio_hash):
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            """
            SELECT COALESCE(MAX(version_no), 0)
            FROM analysis_versions
            WHERE audio_hash = ?
            """,
            (audio_hash,),
        ).fetchone()

    return int(row[0] or 0) + 1


def _song_version_snapshot_payload(audio_hash):
    with sqlite3.connect(DB_PATH) as conn:
        song_row = conn.execute(
            """
            SELECT title, artist, editor,
                   strumming_primary, strumming_secondary
            FROM songs
            WHERE audio_hash = ?
            """,
            (audio_hash,),
        ).fetchone()

        pref_row = conn.execute(
            """
            SELECT capo
            FROM song_preferences
            WHERE audio_hash = ?
            """,
            (audio_hash,),
        ).fetchone()

    title = song_row[0] if song_row else ""
    artist = song_row[1] if song_row else ""
    editor = song_row[2] if song_row else ""
    strumming_primary = song_row[3] if song_row else ""
    strumming_secondary = song_row[4] if song_row else ""
    capo = int(pref_row[0] or 0) if pref_row else 0

    structure = load_structure_blocks(audio_hash)
    measure_edits = load_measure_edits(audio_hash)
    lyric_edits = load_lyric_block_edits(audio_hash)

    return {
        "title": str(title or ""),
        "artist": str(artist or ""),
        "editor": str(editor or ""),
        "strumming_primary": str(strumming_primary or ""),
        "strumming_secondary": str(strumming_secondary or ""),
        "capo": int(capo),
        "structure": structure,
        "measure_edits": measure_edits,
        "lyric_edits": lyric_edits,
    }



def _editorial_date_fr(value, with_time=False):
    raw = str(value or "").strip()
    if not raw:
        return ""
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return dt.strftime("%d/%m/%Y %H:%M" if with_time else "%d/%m/%Y")
    except Exception:
        return raw[:16] if with_time else raw[:10]


def _normalize_version_label(value, fallback="1.0"):
    label = str(value or "").strip()
    if label.lower().startswith("v"):
        label = label[1:].strip()
    return label or str(fallback)


def _normalize_edition_label(value):
    label = str(value or "").strip()
    return label or "Standard"


def _next_version_label(value):
    label = _normalize_version_label(value, "1.0")
    match = re.fullmatch(r"(\d+)\.(\d+)", label)
    if match:
        return f"{int(match.group(1))}.{int(match.group(2)) + 1}"

    match = re.fullmatch(r"(\d+)", label)
    if match:
        return f"{int(match.group(1)) + 1}.0"

    return label


def get_song_workflow(audio_hash):
    now = _utc_now_iso()

    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            """
            SELECT state, current_version_no, working_note,
                   target_version_label, target_edition_label, updated_at
            FROM song_workflow
            WHERE audio_hash = ?
            """,
            (audio_hash,),
        ).fetchone()

        if row is None:
            conn.execute(
                """
                INSERT INTO song_workflow (
                    audio_hash, state, current_version_no,
                    working_note, target_version_label,
                    target_edition_label, updated_at
                )
                VALUES (?, 'working', NULL, '', '1.0', 'Standard', ?)
                """,
                (audio_hash, now),
            )
            conn.commit()
            return {
                "state": "working",
                "current_version_no": None,
                "working_note": "",
                "target_version_label": "1.0",
                "target_edition_label": "Standard",
                "updated_at": now,
            }

    return {
        "state": str(row[0] or "working"),
        "current_version_no": int(row[1]) if row[1] is not None else None,
        "working_note": str(row[2] or ""),
        "target_version_label": _normalize_version_label(row[3], "1.0"),
        "target_edition_label": _normalize_edition_label(row[4]),
        "updated_at": str(row[5] or ""),
    }


def list_song_editorial_versions(audio_hash):
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            """
            SELECT version_no, release_no, status,
                   source_analysis_version_no, note,
                   validated_at, published_at, updated_at,
                   version_label, edition_label
            FROM song_editorial_versions
            WHERE audio_hash = ?
            ORDER BY version_no DESC
            """,
            (audio_hash,),
        ).fetchall()

    return [
        {
            "version_no": int(row[0]),
            "release_no": int(row[1] or 0),
            "status": str(row[2] or "published"),
            "source_analysis_version_no": (
                int(row[3]) if row[3] is not None else None
            ),
            "note": str(row[4] or ""),
            "validated_at": str(row[5] or ""),
            "published_at": str(row[6] or "") if row[6] else "",
            "updated_at": str(row[7] or ""),
            "version_label": _normalize_version_label(row[8], str(row[0])),
            "edition_label": _normalize_edition_label(row[9]),
        }
        for row in rows
    ]


def latest_song_editorial_version(audio_hash):
    versions = list_song_editorial_versions(audio_hash)
    return versions[0] if versions else None


def get_song_editorial_version(audio_hash, version_no):
    if version_no is None:
        return None

    for item in list_song_editorial_versions(audio_hash):
        if int(item["version_no"]) == int(version_no):
            return item

    return None


def save_song_working_state(
    audio_hash,
    note,
    target_version_label,
    target_edition_label,
):
    now = _utc_now_iso()
    version_label = _normalize_version_label(target_version_label, "1.0")
    edition_label = _normalize_edition_label(target_edition_label)

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            UPDATE song_workflow
            SET state = 'working',
                working_note = ?,
                target_version_label = ?,
                target_edition_label = ?,
                updated_at = ?
            WHERE audio_hash = ?
            """,
            (
                str(note or ""),
                version_label,
                edition_label,
                now,
                audio_hash,
            ),
        )
        conn.execute(
            "UPDATE songs SET updated_at = ? WHERE audio_hash = ?",
            (now, audio_hash),
        )
        conn.commit()

    return version_label, edition_label


def save_working_note(audio_hash, note):
    workflow = get_song_workflow(audio_hash)
    return save_song_working_state(
        audio_hash,
        note,
        workflow.get("target_version_label", "1.0"),
        workflow.get("target_edition_label", "Standard"),
    )


def update_song_editorial_note(audio_hash, version_no, note):
    now = _utc_now_iso()

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            UPDATE song_editorial_versions
            SET note = ?, updated_at = ?
            WHERE audio_hash = ? AND version_no = ?
            """,
            (str(note or ""), now, audio_hash, int(version_no)),
        )
        conn.execute(
            "UPDATE songs SET updated_at = ? WHERE audio_hash = ?",
            (now, audio_hash),
        )
        conn.commit()


def publish_song_editorial_version(
    audio_hash,
    source_analysis_version_no,
    note,
    version_label,
    edition_label,
):
    versions = list_song_editorial_versions(audio_hash)
    internal_version_no = max(
        [v["version_no"] for v in versions] + [0]
    ) + 1

    version_label = _normalize_version_label(version_label, "1.0")
    edition_label = _normalize_edition_label(edition_label)

    same_publication = [
        v for v in versions
        if v.get("status") == "published"
        and _normalize_version_label(v.get("version_label")) == version_label
        and _normalize_edition_label(v.get("edition_label")) == edition_label
    ]

    release_no = max(
        [int(v.get("release_no", 0) or 0) for v in same_publication] + [0]
    ) + 1

    now = _utc_now_iso()

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO song_editorial_versions (
                audio_hash, version_no, release_no, status,
                source_analysis_version_no, note,
                validated_at, published_at, updated_at,
                version_label, edition_label
            )
            VALUES (?, ?, ?, 'published', ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                audio_hash,
                internal_version_no,
                release_no,
                int(source_analysis_version_no),
                str(note or ""),
                now,
                now,
                now,
                version_label,
                edition_label,
            ),
        )

        conn.execute(
            """
            INSERT INTO song_workflow (
                audio_hash, state, current_version_no,
                working_note, target_version_label,
                target_edition_label, updated_at
            )
            VALUES (?, 'published', ?, ?, ?, ?, ?)
            ON CONFLICT(audio_hash)
            DO UPDATE SET
                state = excluded.state,
                current_version_no = excluded.current_version_no,
                working_note = excluded.working_note,
                target_version_label = excluded.target_version_label,
                target_edition_label = excluded.target_edition_label,
                updated_at = excluded.updated_at
            """,
            (
                audio_hash,
                internal_version_no,
                str(note or ""),
                version_label,
                edition_label,
                now,
            ),
        )

        conn.execute(
            "UPDATE songs SET updated_at = ? WHERE audio_hash = ?",
            (now, audio_hash),
        )
        conn.commit()

    return {
        "version_no": internal_version_no,
        "version_label": version_label,
        "edition_label": edition_label,
        "release_no": release_no,
    }


def resume_song_modifications(
    audio_hash,
    keep_version=False,
    edition_label=None,
):
    workflow = get_song_workflow(audio_hash)
    current = get_song_editorial_version(
        audio_hash,
        workflow.get("current_version_no"),
    )

    current_version_label = (
        current.get("version_label", "")
        if current is not None
        else workflow.get("target_version_label", "1.0")
    )

    target_version_label = (
        _normalize_version_label(current_version_label)
        if keep_version
        else _next_version_label(current_version_label)
    )

    target_edition_label = _normalize_edition_label(
        edition_label
        if edition_label is not None
        else (
            current.get("edition_label", "Standard")
            if current is not None
            else workflow.get("target_edition_label", "Standard")
        )
    )

    note = (
        current.get("note", "")
        if current is not None
        else workflow.get("working_note", "")
    )
    now = _utc_now_iso()

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            UPDATE song_workflow
            SET state = 'working',
                working_note = ?,
                target_version_label = ?,
                target_edition_label = ?,
                updated_at = ?
            WHERE audio_hash = ?
            """,
            (
                str(note or ""),
                target_version_label,
                target_edition_label,
                now,
                audio_hash,
            ),
        )
        conn.execute(
            "UPDATE songs SET updated_at = ? WHERE audio_hash = ?",
            (now, audio_hash),
        )
        conn.commit()

    return target_version_label, target_edition_label


def editorial_status_label(workflow, version=None):
    state = str((workflow or {}).get("state", "working"))

    if state == "published" and version is not None:
        return (
            f"V{version['version_label']} · {version['edition_label']} · "
            f"R{version['release_no']} · Publiée · "
            f"{_editorial_date_fr(version.get('published_at'))}"
        )

    version_label = _normalize_version_label(
        (workflow or {}).get("target_version_label", "1.0")
    )
    edition_label = _normalize_edition_label(
        (workflow or {}).get("target_edition_label", "Standard")
    )

    return (
        f"Modification en cours · cible V{version_label} · {edition_label}"
    )



def save_analysis_version(
    audio_hash,
    analysis_key,
    parameters,
    musique,
    resultat,
):
    """
    V39d : une version n'est plus seulement une analyse.
    C'est un snapshot complet de la partition courante.
    """
    version_no = next_analysis_version_no(audio_hash)
    now = _utc_now_iso()
    snapshot = _song_version_snapshot_payload(audio_hash)

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO analysis_versions (
                audio_hash,
                analysis_key,
                version_no,
                parameters_json,
                music_json,
                whisper_json,
                title,
                artist,
                editor,
                capo,
                strumming_primary,
                strumming_secondary,
                structure_json,
                measure_edits_json,
                lyric_edits_json,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                audio_hash,
                analysis_key,
                version_no,
                json.dumps(
                    _json_safe(parameters),
                    ensure_ascii=False,
                    sort_keys=True,
                ),
                json.dumps(_json_safe(musique), ensure_ascii=False),
                json.dumps(_json_safe(resultat), ensure_ascii=False),
                snapshot["title"],
                snapshot["artist"],
                snapshot["editor"],
                int(snapshot["capo"]),
                snapshot["strumming_primary"],
                snapshot["strumming_secondary"],
                json.dumps(
                    _json_safe(snapshot["structure"]),
                    ensure_ascii=False,
                ),
                json.dumps(
                    _json_safe(snapshot["measure_edits"]),
                    ensure_ascii=False,
                    sort_keys=True,
                ),
                json.dumps(
                    _json_safe(snapshot["lyric_edits"]),
                    ensure_ascii=False,
                    sort_keys=True,
                ),
                now,
            ),
        )
        conn.commit()

    return version_no


def list_analysis_versions(audio_hash):
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            """
            SELECT
                version_no,
                analysis_key,
                parameters_json,
                created_at,
                title,
                artist,
                editor,
                capo,
                strumming_primary,
                strumming_secondary
            FROM analysis_versions
            WHERE audio_hash = ?
            ORDER BY version_no DESC
            """,
            (audio_hash,),
        ).fetchall()

    result = []

    for row in rows:
        try:
            params = json.loads(row[2])
        except Exception:
            params = {}

        result.append({
            "version_no": int(row[0]),
            "analysis_key": row[1],
            "parameters": params,
            "created_at": row[3],
            "title": str(row[4] or ""),
            "artist": str(row[5] or ""),
            "editor": str(row[6] or ""),
            "capo": int(row[7] or 0),
            "strumming_primary": str(row[8] or ""),
            "strumming_secondary": str(row[9] or ""),
        })

    return result


def load_analysis_version(audio_hash, version_no):
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            """
            SELECT
                version_no,
                analysis_key,
                parameters_json,
                music_json,
                whisper_json,
                created_at,
                title,
                artist,
                editor,
                capo,
                strumming_primary,
                strumming_secondary,
                structure_json,
                measure_edits_json,
                lyric_edits_json
            FROM analysis_versions
            WHERE audio_hash = ? AND version_no = ?
            """,
            (audio_hash, int(version_no)),
        ).fetchone()

    if row is None:
        return None

    try:
        return {
            "version_no": int(row[0]),
            "analysis_key": row[1],
            "parameters": json.loads(row[2]),
            "musique": json.loads(row[3]),
            "resultat": json.loads(row[4]),
            "created_at": row[5],
            "title": str(row[6] or ""),
            "artist": str(row[7] or ""),
            "editor": str(row[8] or ""),
            "capo": int(row[9] or 0),
            "strumming_primary": str(row[10] or ""),
            "strumming_secondary": str(row[11] or ""),
            "structure": json.loads(row[12] or "[]"),
            "measure_edits": json.loads(row[13] or "{}"),
            "lyric_edits": json.loads(row[14] or "{}"),
        }
    except Exception:
        return None


def delete_analysis_version(audio_hash, version_no):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            DELETE FROM analysis_versions
            WHERE audio_hash = ? AND version_no = ?
            """,
            (audio_hash, int(version_no)),
        )
        conn.commit()


def _audio_paths_for_hash(audio_hash):
    """
    Retourne tous les fichiers de data/audio dont le contenu correspond
    réellement au SHA-256 du morceau.
    """
    audio_hash = str(audio_hash or "").strip().lower()
    if not audio_hash:
        return []

    matches = []

    preferred = find_persisted_audio(audio_hash)
    if preferred is not None:
        matches.append(preferred)

    for candidate in AUDIO_DIR.iterdir():
        if not candidate.is_file():
            continue
        if candidate in matches:
            continue

        try:
            digest = hashlib.sha256(
                candidate.read_bytes()
            ).hexdigest().lower()
        except OSError:
            continue

        if digest == audio_hash:
            matches.append(candidate)

    return matches


def delete_song_completely(audio_hash):
    """
    Supprime une chanson entière.

    La suppression est par audio_hash :
    - audio archivé ;
    - toutes les tables SQLite possédant une colonne audio_hash ;
    - songs supprimé en dernier ;
    - last_song_hash nettoyé si nécessaire.

    Aucun autre morceau n'est touché.
    """
    audio_hash = str(audio_hash or "").strip().lower()
    if not audio_hash:
        return {
            "deleted": False,
            "audio_files_deleted": 0,
        }

    # Évite qu'un audio orphelin soit recréé au prochain démarrage par
    # migrate_archived_audio_catalog().
    audio_paths = _audio_paths_for_hash(audio_hash)
    cover_paths = list(
        COVER_DIR.glob(f"{audio_hash}.*")
    )

    for path in audio_paths:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        except OSError as exc:
            raise RuntimeError(
                f"Impossible de supprimer l'audio « {path.name} » : {exc}"
            ) from exc

    for path in cover_paths:
        try:
            path.unlink()
        except OSError:
            pass

    now = _utc_now_iso()

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("BEGIN")
        try:
            tables = [
                row[0]
                for row in conn.execute(
                    """
                    SELECT name
                    FROM sqlite_master
                    WHERE type = 'table'
                      AND name NOT LIKE 'sqlite_%'
                    """
                ).fetchall()
            ]

            # Dépendances d'abord ; songs en dernier.
            for table_name in tables:
                if table_name == "songs":
                    continue

                columns = {
                    row[1]
                    for row in conn.execute(
                        f'PRAGMA table_info("{table_name}")'
                    ).fetchall()
                }

                if "audio_hash" in columns:
                    conn.execute(
                        f'DELETE FROM "{table_name}" WHERE audio_hash = ?',
                        (audio_hash,),
                    )

            conn.execute(
                "DELETE FROM songs WHERE audio_hash = ?",
                (audio_hash,),
            )

            last_song = conn.execute(
                """
                SELECT state_value
                FROM app_state
                WHERE state_key = 'last_song_hash'
                """
            ).fetchone()

            if (
                last_song
                and str(last_song[0] or "").strip().lower() == audio_hash
            ):
                conn.execute(
                    """
                    INSERT INTO app_state (
                        state_key, state_value, updated_at
                    )
                    VALUES ('last_song_hash', '', ?)
                    ON CONFLICT(state_key)
                    DO UPDATE SET
                        state_value = excluded.state_value,
                        updated_at = excluded.updated_at
                    """,
                    (now,),
                )

            conn.commit()
        except Exception:
            conn.rollback()
            raise

    return {
        "deleted": True,
        "audio_files_deleted": len(audio_paths),
    }


def clear_deleted_song_session_state(audio_hash):
    audio_hash = str(audio_hash or "").strip()
    short_hash = audio_hash[:12]

    if st.session_state.get("active_song_hash") == audio_hash:
        st.session_state["active_song_hash"] = ""

    st.session_state.pop("active_analysis_version_no", None)

    for key in list(st.session_state.keys()):
        key_text = str(key)
        if (
            (audio_hash and audio_hash in key_text)
            or (short_hash and short_hash in key_text)
        ):
            st.session_state.pop(key, None)


def render_delete_song_controls(
    audio_hash,
    display_name,
    key_suffix,
):
    st.markdown("---")
    st.markdown("**Chanson complète**")
    st.warning(
        f"Supprimer définitivement « {display_name} » ?"
    )
    st.caption(
        "Supprime l'audio archivé, les analyses, versions, blocs, "
        "corrections, préférences et données éditoriales."
    )

    confirmed = st.checkbox(
        "Je confirme la suppression définitive",
        key=f"confirm_full_delete_{key_suffix}",
    )

    if st.button(
        "🗑 Supprimer définitivement la chanson",
        disabled=not confirmed,
        key=f"full_delete_{key_suffix}",
    ):
        delete_song_completely(audio_hash)
        clear_deleted_song_session_state(audio_hash)
        st.session_state["_pending_main_menu"] = "Répertoire"
        st.rerun()


def _restore_song_version_snapshot(audio_hash, version):
    """
    Restaure le snapshot de partition sélectionné comme copie de travail.
    Les versions restent immuables dans analysis_versions.
    """
    if not version:
        return

    now = _utc_now_iso()

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            UPDATE songs
            SET title = ?, artist = ?, editor = ?,
                strumming_primary = ?, strumming_secondary = ?,
                updated_at = ?
            WHERE audio_hash = ?
            """,
            (
                str(version.get("title", "") or ""),
                str(version.get("artist", "") or ""),
                str(version.get("editor", "") or ""),
                str(version.get("strumming_primary", "") or ""),
                str(version.get("strumming_secondary", "") or ""),
                now,
                audio_hash,
            ),
        )

        # Capo : ne touche jamais l'analyse.
        pref = conn.execute(
            """
            SELECT settings_json
            FROM song_preferences
            WHERE audio_hash = ?
            """,
            (audio_hash,),
        ).fetchone()

        settings_json = (
            pref[0]
            if pref and pref[0]
            else json.dumps(
                _json_safe(version.get("parameters", {}) or {}),
                ensure_ascii=False,
                sort_keys=True,
            )
        )

        conn.execute(
            """
            INSERT INTO song_preferences (
                audio_hash, capo, settings_json, updated_at
            )
            VALUES (?, ?, ?, ?)
            ON CONFLICT(audio_hash)
            DO UPDATE SET
                capo = excluded.capo,
                settings_json = excluded.settings_json,
                updated_at = excluded.updated_at
            """,
            (
                audio_hash,
                int(version.get("capo", 0) or 0),
                settings_json,
                now,
            ),
        )

        conn.execute(
            "DELETE FROM structure_blocks WHERE audio_hash = ?",
            (audio_hash,),
        )
        for order_index, block in enumerate(version.get("structure", []) or []):
            conn.execute(
                """
                INSERT INTO structure_blocks (
                    audio_hash,
                    block_id,
                    order_index,
                    cluster,
                    custom_label,
                    measure_start,
                    measure_end,
                    detected_measure_start,
                    detected_measure_end,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    audio_hash,
                    int(block["block_id"]),
                    int(order_index),
                    str(block.get("cluster", "")),
                    str(block.get("custom_label", "") or ""),
                    int(block["measure_start"]),
                    int(block["measure_end"]),
                    block.get("detected_measure_start"),
                    block.get("detected_measure_end"),
                    now,
                ),
            )

        conn.execute(
            "DELETE FROM measure_edits WHERE audio_hash = ?",
            (audio_hash,),
        )
        for measure_no, notation in (
            version.get("measure_edits", {}) or {}
        ).items():
            conn.execute(
                """
                INSERT INTO measure_edits (
                    audio_hash, measure_no, notation_real, updated_at
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    audio_hash,
                    int(measure_no),
                    str(notation),
                    now,
                ),
            )

        conn.execute(
            "DELETE FROM lyric_block_edits WHERE audio_hash = ?",
            (audio_hash,),
        )
        for block_key, edit in (
            version.get("lyric_edits", {}) or {}
        ).items():
            conn.execute(
                """
                INSERT INTO lyric_block_edits (
                    audio_hash,
                    block_key,
                    original_text,
                    corrected_text,
                    time_start,
                    time_end,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    audio_hash,
                    str(block_key),
                    str(edit.get("original_text", "") or ""),
                    str(edit.get("corrected_text", "") or ""),
                    float(edit.get("time_start", 0.0) or 0.0),
                    float(edit.get("time_end", 0.0) or 0.0),
                    now,
                ),
            )

        conn.commit()


def prepare_analysis_version_for_open(audio_hash, version_no):
    version = load_analysis_version(audio_hash, version_no)

    if version is None:
        return False

    _restore_song_version_snapshot(audio_hash, version)

    st.session_state["active_analysis_version_no"] = int(version_no)
    st.session_state["_pending_analysis_settings"] = dict(
        version.get("parameters", {}) or {}
    )
    st.session_state["_pending_song_preferences"] = {
        "capo": int(version.get("capo", 0) or 0),
        "settings": dict(version.get("parameters", {}) or {}),
    }

    return True



def load_beat_edits(audio_hash):
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            """
            SELECT beat_index, chord_override, time_offset_ms
            FROM beat_edits
            WHERE audio_hash = ?
            """,
            (audio_hash,),
        ).fetchall()

    return {
        int(row[0]): {
            "chord_override": row[1],
            "time_offset_ms": float(row[2] or 0.0),
        }
        for row in rows
    }


def save_beat_edit(
    audio_hash,
    beat_index,
    chord_override,
    time_offset_ms,
):
    now = _utc_now_iso()

    chord = str(chord_override or "").strip()
    chord_value = chord if chord else None

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO beat_edits (
                audio_hash, beat_index, chord_override,
                time_offset_ms, updated_at
            )
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(audio_hash, beat_index)
            DO UPDATE SET
                chord_override = excluded.chord_override,
                time_offset_ms = excluded.time_offset_ms,
                updated_at = excluded.updated_at
            """,
            (
                audio_hash,
                int(beat_index),
                chord_value,
                float(time_offset_ms),
                now,
            ),
        )
        conn.commit()


def clear_beat_edits_for_measure(
    audio_hash,
    beat_indices,
):
    if not beat_indices:
        return

    placeholders = ",".join("?" for _ in beat_indices)
    params = [audio_hash] + [int(i) for i in beat_indices]

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            f"""
            DELETE FROM beat_edits
            WHERE audio_hash = ?
              AND beat_index IN ({placeholders})
            """,
            params,
        )
        conn.commit()


def appliquer_editions_beats(beats_detectes, beat_edits):
    """
    Produit les beats effectifs utilisés partout dans l'UI.
    Les accords et temps détectés bruts restent intacts dans l'analyse.
    """
    beats = []

    for beat in beats_detectes:
        copie = dict(beat)
        idx = int(copie["index"])
        edit = beat_edits.get(idx, {})

        detected_t = float(copie["temps"])
        offset_ms = float(edit.get("time_offset_ms", 0.0))
        accord_override = edit.get("chord_override")

        copie["detected_temps"] = detected_t
        copie["edit_offset_ms"] = offset_ms
        copie["temps"] = detected_t + offset_ms / 1000.0

        if accord_override not in (None, ""):
            copie["accord"] = str(accord_override).strip()

        beats.append(copie)

    beats.sort(key=lambda b: int(b["index"]))

    # Garder un ordre temporel strict.
    for i in range(1, len(beats)):
        if beats[i]["temps"] <= beats[i - 1]["temps"] + 0.005:
            beats[i]["temps"] = beats[i - 1]["temps"] + 0.005

    for i in range(len(beats)):
        if i + 1 < len(beats):
            beats[i]["fin"] = beats[i + 1]["temps"]
            beats[i]["intervalle"] = beats[i + 1]["temps"] - beats[i]["temps"]
        else:
            interval = float(beats[i].get("intervalle", 0.5))
            beats[i]["fin"] = beats[i]["temps"] + max(interval, 0.05)

    return beats


def reconstruire_mesures_depuis_beats(
    beats,
    original_mesures,
    signature,
    beats_par_mesure,
):
    mesures = []

    for start in range(0, len(beats), int(beats_par_mesure)):
        groupe = beats[start:start + int(beats_par_mesure)]
        if not groupe:
            continue

        symboles = [b["accord"] for b in groupe]
        while len(symboles) < int(beats_par_mesure):
            symboles.append(".")

        numero = len(mesures) + 1
        original = (
            original_mesures[numero - 1]
            if numero - 1 < len(original_mesures)
            else {}
        )
        fermata = bool(original.get("fermata", False))

        mesures.append({
            "numero": numero,
            "debut": float(groupe[0]["temps"]),
            "fin": float(groupe[-1]["fin"]),
            "accords": symboles,
            "notation": formatter_mesure_signature(
                symboles,
                signature,
                fermata=fermata,
            ),
            "fermata": fermata,
        })

    return mesures


def render_beat_editor(
    context_key,
    audio_hash,
    beats,
    mesures,
    beats_par_mesure,
):
    """
    Éditeur partagé grille/parolier.
    Toute correction est persistée dans beat_edits et se répercute partout.
    """
    if not mesures:
        return

    with st.expander("✏️ Corriger accords / battements", expanded=False):
        st.caption(
            "Les corrections sont communes à la grille et au parolier. "
            "Accord et placement temporel sont persistés sans réanalyse."
        )

        measure_numbers = [int(m["numero"]) for m in mesures]
        selected_measure = st.selectbox(
            "Mesure à corriger",
            measure_numbers,
            key=f"beat_editor_measure_{context_key}_{audio_hash[:10]}",
        )

        start = (int(selected_measure) - 1) * int(beats_par_mesure)
        groupe = beats[start:start + int(beats_par_mesure)]

        with st.form(
            f"beat_editor_form_{context_key}_{audio_hash[:10]}_{selected_measure}",
            clear_on_submit=False,
        ):
            values = []

            for local_pos, beat in enumerate(groupe, start=1):
                c1, c2, c3 = st.columns([0.7, 1.4, 1.0])

                with c1:
                    st.markdown(f"**Beat {local_pos}**")

                with c2:
                    chord_value = st.text_input(
                        "Accord",
                        value=str(beat.get("accord", "")),
                        key=(
                            f"beat_chord_{context_key}_{audio_hash[:10]}_"
                            f"{beat['index']}"
                        ),
                    )

                with c3:
                    offset_value = st.number_input(
                        "Décalage (ms)",
                        min_value=-800.0,
                        max_value=800.0,
                        value=float(beat.get("edit_offset_ms", 0.0)),
                        step=10.0,
                        key=(
                            f"beat_offset_{context_key}_{audio_hash[:10]}_"
                            f"{beat['index']}"
                        ),
                    )

                values.append(
                    (
                        int(beat["index"]),
                        chord_value,
                        float(offset_value),
                    )
                )

            save_changes = st.form_submit_button(
                "💾 Enregistrer les corrections",
                type="primary",
            )

        if save_changes:
            for beat_index, chord_value, offset_value in values:
                save_beat_edit(
                    audio_hash,
                    beat_index,
                    chord_value,
                    offset_value,
                )

            st.success(
                "Corrections enregistrées. Grille et parolier seront synchronisés."
            )
            st.rerun()

        if st.button(
            "Réinitialiser cette mesure",
            key=f"reset_measure_{context_key}_{audio_hash[:10]}_{selected_measure}",
        ):
            clear_beat_edits_for_measure(
                audio_hash,
                [int(b["index"]) for b in groupe],
            )
            st.rerun()



def load_latest_persisted_analysis(audio_hash):
    """
    Charge la dernière analyse persistée d'un morceau, indépendamment
    de la clé correspondant aux widgets actuellement affichés.

    Utilisé à l'ouverture depuis le Répertoire afin qu'une chanson
    déjà analysée ne soit JAMAIS recalculée implicitement.
    """
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            """
            SELECT
                analysis_key,
                parameters_json,
                music_json,
                whisper_json,
                updated_at
            FROM analyses
            WHERE audio_hash = ?
            ORDER BY updated_at DESC
            LIMIT 1
            """,
            (audio_hash,),
        ).fetchone()

    if row is None:
        return None

    try:
        parameters = json.loads(row[1])
        musique = json.loads(row[2])
        resultat = json.loads(row[3])
    except Exception:
        return None

    return {
        "analysis_key": row[0],
        "parameters": parameters,
        "musique": musique,
        "resultat": resultat,
        "updated_at": row[4],
    }


def load_persisted_analysis(audio_hash, analysis_key):
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            """
            SELECT music_json, whisper_json
            FROM analyses
            WHERE audio_hash = ? AND analysis_key = ?
            """,
            (audio_hash, analysis_key),
        ).fetchone()

    if row is None:
        return None

    return {
        "musique": json.loads(row[0]),
        "resultat": json.loads(row[1]),
    }


def save_persisted_analysis(
    audio_hash,
    analysis_key,
    parameters,
    musique,
    resultat,
):
    now = _utc_now_iso()

    parameters_json = json.dumps(
        _json_safe(parameters),
        ensure_ascii=False,
        sort_keys=True,
    )
    music_json = json.dumps(
        _json_safe(musique),
        ensure_ascii=False,
    )
    whisper_json = json.dumps(
        _json_safe(resultat),
        ensure_ascii=False,
    )

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO analyses (
                audio_hash,
                analysis_key,
                engine_version,
                parameters_json,
                music_json,
                whisper_json,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(audio_hash, analysis_key)
            DO UPDATE SET
                engine_version = excluded.engine_version,
                parameters_json = excluded.parameters_json,
                music_json = excluded.music_json,
                whisper_json = excluded.whisper_json,
                updated_at = excluded.updated_at
            """,
            (
                audio_hash,
                analysis_key,
                ANALYSIS_ENGINE_VERSION,
                parameters_json,
                music_json,
                whisper_json,
                now,
                now,
            ),
        )
        conn.commit()


init_persistence()
