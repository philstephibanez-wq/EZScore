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
        raise RuntimeError(f"{label}: attendu 1 motif, trouvé {count}.")
    return text.replace(old, new, 1)


def backup(paths: list[Path]) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    preferred = Path(r"H:\temp")
    base = preferred if preferred.exists() else Path.home() / "AppData" / "Local" / "Temp"
    out = base / f"EZScore_LYRICS_DB_SOURCE_R1_backup_{stamp}"
    out.mkdir(parents=True, exist_ok=True)
    for path in paths:
        rel = path.relative_to(ROOT)
        dest = out / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)
    return out


def patch_forced(path: Path) -> None:
    text = path.read_text(encoding="utf-8")

    old = """def load_draft(audio_hash: str) -> str:
    path = draft_path(audio_hash)
    if path.is_file():
        value = path.read_text(encoding="utf-8")
        if value.strip():
            return value

    payload = load_alignment(audio_hash)
    if payload:
        value = str(payload.get("source_text", "") or "")
        if value.strip():
            return value

    return load_persisted_source_text(audio_hash)


def save_draft(audio_hash: str, text: str) -> None:
    value = str(text or "")
    draft_path(audio_hash).write_text(value, encoding="utf-8")
    save_persisted_source_text(audio_hash, value)
"""
    new = """def load_draft(audio_hash: str) -> str:
    # SQLite is the business source of truth.
    persisted = load_persisted_source_text(audio_hash)
    if persisted.strip():
        return persisted

    # One-time migration fallback from old technical artifacts.
    path = draft_path(audio_hash)
    if path.is_file():
        value = path.read_text(encoding="utf-8")
        if value.strip():
            save_persisted_source_text(audio_hash, value)
            return value

    payload = load_alignment(audio_hash)
    if payload:
        value = str(payload.get("source_text", "") or "")
        if value.strip():
            save_persisted_source_text(audio_hash, value)
            return value

    return ""


def save_draft(audio_hash: str, text: str) -> None:
    value = str(text or "")

    # Business source of truth.
    save_persisted_source_text(audio_hash, value)

    # Technical mirror only.
    try:
        draft_path(audio_hash).write_text(value, encoding="utf-8")
    except OSError:
        pass
"""
    text = replace_once(text, old, new, "load/save BDD prioritaire")
    path.write_text(text, encoding="utf-8")


def patch_choir(path: Path) -> None:
    text = path.read_text(encoding="utf-8")

    text = replace_once(
        text,
        """    load_alignment,
    load_draft,
    save_draft,
)
""",
        """    load_alignment,
    load_draft,
    load_persisted_source_text,
    save_draft,
)
""",
        "import BDD",
    )

    text = replace_once(
        text,
        """    if text_key not in st.session_state:
        st.session_state[text_key] = _initial_user_lyrics(audio_hash)
""",
        """    persisted_source = str(load_persisted_source_text(audio_hash) or "")

    if text_key not in st.session_state:
        st.session_state[text_key] = (
            persisted_source or _initial_user_lyrics(audio_hash)
        )
    elif (
        not str(st.session_state.get(text_key, "") or "").strip()
        and persisted_source.strip()
    ):
        # Never let an empty stale widget mask durable DB content.
        st.session_state[text_key] = persisted_source
""",
        "hydratation session depuis BDD",
    )

    text = replace_once(
        text,
        """            persisted_text = str(load_draft(audio_hash) or "")
            source_changed = current_text != persisted_text
""",
        """            persisted_text = str(
                load_persisted_source_text(audio_hash) or ""
            )
            source_changed = current_text != persisted_text
""",
        "comparaison BDD",
    )

    text = replace_once(
        text,
        """                ):
                    save_draft(audio_hash, current_text)
                    st.success("✓ Bloc de paroles enregistré.")
                    st.rerun()
""",
        """                ):
                    save_draft(audio_hash, current_text)
                    saved_text = str(
                        load_persisted_source_text(audio_hash) or ""
                    )
                    if saved_text != current_text:
                        st.error("Échec de persistance BDD du bloc de paroles.")
                    else:
                        st.session_state[text_key] = saved_text
                        st.success("✓ Bloc de paroles enregistré en BDD.")
                        st.rerun()
""",
        "validation relecture BDD",
    )

    path.write_text(text, encoding="utf-8")


def main() -> int:
    paths = [FORCED, CHOIR]
    for path in paths:
        if not path.is_file():
            raise FileNotFoundError(path)

    print("Backup:", backup(paths))

    with tempfile.TemporaryDirectory(prefix="ezscore_lyrics_db_source_") as td:
        td = Path(td)
        ftmp = td / "forced_lyrics.py"
        ctmp = td / "choir_pipeline.py"
        shutil.copy2(FORCED, ftmp)
        shutil.copy2(CHOIR, ctmp)

        patch_forced(ftmp)
        patch_choir(ctmp)

        ast.parse(ftmp.read_text(encoding="utf-8"), filename=str(ftmp))
        ast.parse(ctmp.read_text(encoding="utf-8"), filename=str(ctmp))

        shutil.copy2(ftmp, FORCED)
        shutil.copy2(ctmp, CHOIR)

    print("PATCH OK")
    print(" - SQLite = source de vérité du bloc de paroles")
    print(" - lyrics_input.txt = miroir technique seulement")
    print(" - textarea hydraté depuis SQLite")
    print(" - session_state vide ne masque plus la BDD")
    print(" - validation relit la BDD avant confirmation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
