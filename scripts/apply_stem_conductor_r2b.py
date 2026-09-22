from __future__ import annotations

import ast
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "ezscore/player/stem_analysis_conductor.py"


def backup(path: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    preferred = Path(r"H:\temp")
    base = preferred if preferred.exists() else Path.home() / "AppData" / "Local" / "Temp"
    out = base / f"EZScore_STEM_CONDUCTOR_R2b_backup_{stamp}"
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, out)
    return out


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: attendu 1 motif, trouvé {count}.")
    return text.replace(old, new, 1)


def patch(path: Path) -> None:
    text = path.read_text(encoding="utf-8")

    # stem_webaudio._PLAYER_JS already declares:
    #     let activeWordIndex = -1;
    # R2 incorrectly added a second declaration inside conductor_js.
    text = replace_once(
        text,
        "  let activeWordIndex=-2;\n  let pixelsPerSecond=96;\n",
        "  let pixelsPerSecond=96;\n",
        "suppression double déclaration activeWordIndex",
    )

    path.write_text(text, encoding="utf-8")


def main() -> int:
    if not TARGET.is_file():
        raise FileNotFoundError(TARGET)

    print("Backup:", backup(TARGET))

    with tempfile.TemporaryDirectory(prefix="ezscore_stem_conductor_r2b_") as td:
        candidate = Path(td) / TARGET.name
        shutil.copy2(TARGET, candidate)
        patch(candidate)

        ast.parse(
            candidate.read_text(encoding="utf-8"),
            filename=str(candidate),
        )

        shutil.copy2(candidate, TARGET)

    print("PATCH OK")
    print(" - double déclaration activeWordIndex supprimée")
    print(" - déclaration historique du moteur WebAudio conservée")
    print(" - conducteur R2 et payload beats/mots conservés")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
