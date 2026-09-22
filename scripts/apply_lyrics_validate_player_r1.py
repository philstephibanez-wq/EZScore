from __future__ import annotations

import ast
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORCED = ROOT / "ezscore/analysis/forced_lyrics.py"
CHOIR = ROOT / "ezscore/integration/choir_pipeline.py"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: motif attendu exactement 1 fois, trouvé {count}.")
    return text.replace(old, new, 1)


def backup(paths: list[Path]) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    preferred = Path(r"H:\temp")
    base = preferred if preferred.exists() else Path.home() / "AppData" / "Local" / "Temp"
    out = base / f"EZScore_LYRICS_VALIDATE_PLAYER_R1_backup_{stamp}"
    out.mkdir(parents=True, exist_ok=True)
    for path in paths:
        rel = path.relative_to(ROOT)
        dest = out / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)
    return out


def patch_forced(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    old = '''    for name in (\n        "structure_analysis.json",\n        "karaoke_conductor.json",\n        "choir_analysis.json",\n        "choir_words_from_vocals.json",\n        "whisper_backing_small.json",\n    ):\n'''
    new = '''    for name in (\n        "karaoke_conductor.json",\n        "choir_analysis.json",\n        "choir_words_from_vocals.json",\n        "whisper_backing_small.json",\n    ):\n'''
    text = replace_once(text, old, new, "preserve structure_analysis timeline")
    path.write_text(text, encoding="utf-8")


def patch_choir(path: Path) -> None:
    text = path.read_text(encoding="utf-8")

    if "def _initial_user_lyrics(" not in text:
        old_helper = '''def _legacy_saved_lyrics(audio_hash: str) -> str:\n    try:\n        with sqlite3.connect(_DB_PATH) as conn:\n            rows = conn.execute(\n                "SELECT corrected_text, original_text, time_start FROM lyric_block_edits WHERE audio_hash = ? ORDER BY time_start",\n                (str(audio_hash),),\n            ).fetchall()\n    except sqlite3.Error:\n        return ""\n    chunks = []\n    for corrected, original, _ in rows:\n        value = str(corrected or original or "").strip()\n        if value and (not chunks or value != chunks[-1]):\n            chunks.append(value)\n    return "\\n\\n".join(chunks).strip()\n'''
        new_helper = '''def _text_from_result_payload(payload: Any) -> str:\n    if not isinstance(payload, dict):\n        return ""\n    direct = str(payload.get("source_text") or payload.get("text") or "").strip()\n    if direct:\n        return direct\n    segments = list(payload.get("segments", []) or [])\n    lines = [\n        str(item.get("text", "") or "").strip()\n        for item in segments\n        if isinstance(item, dict) and str(item.get("text", "") or "").strip()\n    ]\n    if lines:\n        return "\\n".join(lines).strip()\n    words = list(payload.get("words", []) or [])\n    values = [\n        str(item.get("text") or item.get("word") or "").strip()\n        for item in words\n        if isinstance(item, dict) and str(item.get("text") or item.get("word") or "").strip()\n    ]\n    return " ".join(values).strip()\n\n\ndef _legacy_saved_lyrics(audio_hash: str) -> str:\n    try:\n        with sqlite3.connect(_DB_PATH) as conn:\n            rows = conn.execute(\n                "SELECT corrected_text, original_text, time_start "\n                "FROM lyric_block_edits WHERE audio_hash = ? ORDER BY time_start",\n                (str(audio_hash),),\n            ).fetchall()\n            chunks = []\n            for corrected, original, _ in rows:\n                value = str(corrected or original or "").strip()\n                if value and (not chunks or value != chunks[-1]):\n                    chunks.append(value)\n            if chunks:\n                return "\\n\\n".join(chunks).strip()\n            row = conn.execute(\n                "SELECT whisper_json FROM analyses WHERE audio_hash = ? ORDER BY updated_at DESC LIMIT 1",\n                (str(audio_hash),),\n            ).fetchone()\n            if row and row[0]:\n                try:\n                    value = _text_from_result_payload(json.loads(row[0]))\n                except Exception:\n                    value = ""\n                if value:\n                    return value\n            row = conn.execute(\n                "SELECT whisper_json FROM analysis_versions WHERE audio_hash = ? ORDER BY version_no DESC LIMIT 1",\n                (str(audio_hash),),\n            ).fetchone()\n            if row and row[0]:\n                try:\n                    value = _text_from_result_payload(json.loads(row[0]))\n                except Exception:\n                    value = ""\n                if value:\n                    return value\n    except sqlite3.Error:\n        return ""\n    return ""\n\n\ndef _initial_user_lyrics(audio_hash: str) -> str:\n    current = str(load_draft(audio_hash) or "").strip()\n    if current:\n        return current\n    aligned = load_alignment(audio_hash) or {}\n    current = str(aligned.get("source_text", "") or "").strip()\n    if current:\n        save_draft(audio_hash, current)\n        return current\n    migrated = _legacy_saved_lyrics(audio_hash)\n    if migrated:\n        save_draft(audio_hash, migrated)\n        return migrated\n    return ""\n'''
        text = replace_once(text, old_helper, new_helper, "durable source migration helper")

    old_init = '''    if text_key not in st.session_state:\n        st.session_state[text_key] = (\n            load_draft(audio_hash)\n            or str(old_payload.get("source_text", "") or "")\n        )\n'''
    if old_init in text:
        text = replace_once(text, old_init, '''    if text_key not in st.session_state:\n        st.session_state[text_key] = _initial_user_lyrics(audio_hash)\n''', "durable textarea init")

    # Remove automatic persistence variants.
    text = text.replace('''            )\n            save_draft(audio_hash, current_text)\n\n            if not current_text.strip():\n''', '''            )\n\n            if not current_text.strip():\n''', 1)
    if "            def persist_current_text() -> None:\n" in text:
        start = text.index("            def persist_current_text() -> None:\n")
        end = text.index("            current_text = st.text_area(", start)
        text = text[:start] + text[end:]
        text = text.replace('''                ),\n                on_change=persist_current_text,\n            )\n''', '''                ),\n            )\n''', 1)

    marker = '''            if not current_text.strip():\n                legacy_text = _legacy_saved_lyrics(audio_hash)\n'''
    validation = '''            persisted_text = str(load_draft(audio_hash) or "")\n            source_changed = current_text != persisted_text\n\n            validate_col, _ = st.columns([1, 2])\n            with validate_col:\n                if original_button(\n                    "💾 Valider les paroles",\n                    key=f"ezscore_validate_lyrics_{short_hash}",\n                    type="primary",\n                    width="stretch",\n                    disabled=(not current_text.strip() or not source_changed),\n                ):\n                    save_draft(audio_hash, current_text)\n                    st.success("✓ Bloc de paroles enregistré.")\n                    st.rerun()\n\n            if source_changed and current_text.strip():\n                st.info(\n                    "Modifications non validées. "\n                    "Validez le bloc avant de relancer l'alignement."\n                )\n\n            if not current_text.strip():\n                legacy_text = _legacy_saved_lyrics(audio_hash)\n'''
    text = replace_once(text, marker, validation, "explicit validate button")

    old_disabled = '                disabled=(not current_text.strip() or not lead_ready),\n'
    new_disabled = '                disabled=(not current_text.strip() or not lead_ready or source_changed),\n'
    text = replace_once(text, old_disabled, new_disabled, "align requires validated source")

    old_condition = '''            if (\n                speech is not None\n                and stem_lab.stems_cache_complete(audio_hash)\n                and not has_timeline\n            ):\n'''
    new_condition = '''            if (\n                stem_lab.stems_cache_complete(audio_hash)\n                and not has_timeline\n            ):\n'''
    text = replace_once(text, old_condition, new_condition, "timeline independent from speech")

    path.write_text(text, encoding="utf-8")


def main() -> int:
    paths = [FORCED, CHOIR]
    for path in paths:
        if not path.is_file():
            raise FileNotFoundError(path)

    print("Backup:", backup(paths))

    with tempfile.TemporaryDirectory(prefix="ezscore_lyrics_validate_player_") as td:
        td = Path(td)
        temp_forced = td / "forced_lyrics.py"
        temp_choir = td / "choir_pipeline.py"
        shutil.copy2(FORCED, temp_forced)
        shutil.copy2(CHOIR, temp_choir)
        patch_forced(temp_forced)
        patch_choir(temp_choir)
        ast.parse(temp_forced.read_text(encoding="utf-8"), filename=str(temp_forced))
        ast.parse(temp_choir.read_text(encoding="utf-8"), filename=str(temp_choir))
        shutil.copy2(temp_forced, FORCED)
        shutil.copy2(temp_choir, CHOIR)

    print("PATCH OK")
    print(" - bouton explicite Valider les paroles")
    print(" - alignement interdit tant que le bloc modifié n'est pas validé")
    print(" - bloc durable rechargé/migré automatiquement")
    print(" - structure_analysis.json n'est plus supprimé par MMS_FA")
    print(" - beats/accords reconstruits même si les paroles ne sont pas encore alignées")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
