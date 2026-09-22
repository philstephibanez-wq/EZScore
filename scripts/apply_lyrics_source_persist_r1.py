from __future__ import annotations

import ast
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "ezscore/integration/choir_pipeline.py"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(
            f"{label}: motif attendu exactement 1 fois, trouvé {count}."
        )
    return text.replace(old, new, 1)


def backup(path: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    preferred = Path(r"H:\temp")
    base = preferred if preferred.exists() else Path.home() / "AppData" / "Local" / "Temp"
    out = base / f"EZScore_LYRICS_SOURCE_PERSIST_R1_backup_{stamp}"
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, out)
    return out


def patch(path: Path) -> None:
    text = path.read_text(encoding="utf-8")

    old_helper = """def _legacy_saved_lyrics(audio_hash: str) -> str:
    try:
        with sqlite3.connect(_DB_PATH) as conn:
            rows = conn.execute(
                "SELECT corrected_text, original_text, time_start FROM lyric_block_edits WHERE audio_hash = ? ORDER BY time_start",
                (str(audio_hash),),
            ).fetchall()
    except sqlite3.Error:
        return ""
    chunks = []
    for corrected, original, _ in rows:
        value = str(corrected or original or "").strip()
        if value and (not chunks or value != chunks[-1]):
            chunks.append(value)
    return "\\n\\n".join(chunks).strip()
"""

    new_helper = """def _text_from_result_payload(payload: Any) -> str:
    # Best-effort migration of historical persisted lyrics into one editable block.
    if not isinstance(payload, dict):
        return ""

    direct = str(
        payload.get("source_text")
        or payload.get("text")
        or ""
    ).strip()
    if direct:
        return direct

    segments = list(payload.get("segments", []) or [])
    segment_lines = []
    for segment in segments:
        if not isinstance(segment, dict):
            continue
        value = str(segment.get("text", "") or "").strip()
        if value:
            segment_lines.append(value)
    if segment_lines:
        return "\\n".join(segment_lines).strip()

    words = list(payload.get("words", []) or [])
    word_values = []
    for word in words:
        if not isinstance(word, dict):
            continue
        value = str(
            word.get("text")
            or word.get("word")
            or ""
        ).strip()
        if value:
            word_values.append(value)
    return " ".join(word_values).strip()


def _legacy_saved_lyrics(audio_hash: str) -> str:
    # Recover the last known editable lyrics from historical persistence.
    try:
        with sqlite3.connect(_DB_PATH) as conn:
            rows = conn.execute(
                "SELECT corrected_text, original_text, time_start "
                "FROM lyric_block_edits "
                "WHERE audio_hash = ? "
                "ORDER BY time_start",
                (str(audio_hash),),
            ).fetchall()

            chunks = []
            for corrected, original, _ in rows:
                value = str(corrected or original or "").strip()
                if value and (not chunks or value != chunks[-1]):
                    chunks.append(value)
            if chunks:
                return "\\n\\n".join(chunks).strip()

            row = conn.execute(
                "SELECT whisper_json "
                "FROM analyses "
                "WHERE audio_hash = ? "
                "ORDER BY updated_at DESC "
                "LIMIT 1",
                (str(audio_hash),),
            ).fetchone()
            if row and row[0]:
                try:
                    migrated = _text_from_result_payload(json.loads(row[0]))
                except Exception:
                    migrated = ""
                if migrated:
                    return migrated

            row = conn.execute(
                "SELECT whisper_json "
                "FROM analysis_versions "
                "WHERE audio_hash = ? "
                "ORDER BY version_no DESC "
                "LIMIT 1",
                (str(audio_hash),),
            ).fetchone()
            if row and row[0]:
                try:
                    migrated = _text_from_result_payload(json.loads(row[0]))
                except Exception:
                    migrated = ""
                if migrated:
                    return migrated
    except sqlite3.Error:
        return ""

    return ""


def _initial_user_lyrics(audio_hash: str) -> str:
    # Canonical editable source, with one-time migration from old storage.
    current = str(load_draft(audio_hash) or "").strip()
    if current:
        return current

    aligned = load_alignment(audio_hash) or {}
    current = str(aligned.get("source_text", "") or "").strip()
    if current:
        save_draft(audio_hash, current)
        return current

    migrated = _legacy_saved_lyrics(audio_hash)
    if migrated:
        save_draft(audio_hash, migrated)
        return migrated

    return ""
"""

    text = replace_once(
        text,
        old_helper,
        new_helper,
        "migration helper",
    )

    old_init = """    if text_key not in st.session_state:
        st.session_state[text_key] = (
            load_draft(audio_hash)
            or str(old_payload.get("source_text", "") or "")
        )
"""
    new_init = """    if text_key not in st.session_state:
        st.session_state[text_key] = _initial_user_lyrics(audio_hash)
"""
    text = replace_once(
        text,
        old_init,
        new_init,
        "initial lyrics source",
    )

    old_widget = """            current_text = st.text_area(
                "Texte exact du chant",
                key=text_key,
                height=300,
                placeholder=(
                    "Collez ici les paroles exactes. "
                    "Conservez les retours à la ligne : ils seront mémorisés."
                ),
            )
            save_draft(audio_hash, current_text)

            if not current_text.strip():
"""

    new_widget = """            def persist_current_text() -> None:
                save_draft(
                    audio_hash,
                    str(st.session_state.get(text_key, "") or ""),
                )

            current_text = st.text_area(
                "Texte exact du chant",
                key=text_key,
                height=300,
                placeholder=(
                    "Collez ici les paroles exactes. "
                    "Conservez les retours à la ligne : ils seront mémorisés."
                ),
                on_change=persist_current_text,
            )

            if not current_text.strip():
"""

    text = replace_once(
        text,
        old_widget,
        new_widget,
        "textarea persistence callback",
    )

    path.write_text(text, encoding="utf-8")


def main() -> int:
    if not TARGET.is_file():
        raise FileNotFoundError(TARGET)

    backup_path = backup(TARGET)
    print("Backup:", backup_path)

    with tempfile.TemporaryDirectory(prefix="ezscore_lyrics_source_persist_") as td:
        candidate = Path(td) / TARGET.name
        shutil.copy2(TARGET, candidate)
        patch(candidate)
        ast.parse(
            candidate.read_text(encoding="utf-8"),
            filename=str(candidate),
        )
        shutil.copy2(candidate, TARGET)

    print("PATCH OK")
    print(" - bloc utilisateur persisté à chaque modification")
    print(" - rechargement automatique à l'ouverture")
    print(" - migration automatique lyric_block_edits -> source canonique")
    print(" - migration fallback analyses.whisper_json")
    print(" - migration fallback analysis_versions.whisper_json")
    print(" - retours à la ligne conservés quand disponibles")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
