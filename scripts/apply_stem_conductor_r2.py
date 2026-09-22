from __future__ import annotations
import ast
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAYER = ROOT / "ezscore/player/stem_analysis_conductor.py"
UI = ROOT / "ezscore/ui/stem_lab_analysis.py"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: attendu 1 motif, trouvé {count}.")
    return text.replace(old, new, 1)


def backup(paths: list[Path]) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    preferred = Path(r"H:\temp")
    base = preferred if preferred.exists() else Path.home() / "AppData" / "Local" / "Temp"
    out = base / f"EZScore_STEM_CONDUCTOR_R2_backup_{stamp}"
    out.mkdir(parents=True, exist_ok=True)
    for path in paths:
        rel = path.relative_to(ROOT)
        dest = out / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)
    return out


def patch_player(path: Path) -> None:
    text = path.read_text(encoding="utf-8")

    text = replace_once(
        text,
        "  let pixelsPerSecond=96;\n",
        "  let activeWordIndex=-2;\n  let pixelsPerSecond=96;\n",
        "activeWordIndex manquant",
    )

    text = replace_once(
        text,
        "  renderConductor(0);\n\n",
        (
            "  requestAnimationFrame(() => {\n"
            "    layoutConductor();\n"
            "    renderConductor(0);\n"
            "  });\n\n"
        ),
        "premier rendu différé",
    )

    old_caption = (
        '    st.caption(\n'
        '        "Conducteur STEM : 1 ligne Accords + 1 ligne Paroles · "\n'
        '        "notation Am--- · \'_\' = prolongation vocale · "\n'
        '        "défilement continu sans retour à la ligne."\n'
        '    )\n'
    )
    new_caption = (
        '    st.caption(\n'
        '        "Conducteur STEM : 1 ligne Accords + 1 ligne Paroles · "\n'
        '        "notation Am--- · \'_\' = prolongation vocale · "\n'
        '        "défilement continu sans retour à la ligne. "\n'
        '        f"Payload : {len(beats)} beats · {len(player_words)} mots."\n'
        '    )\n'
    )
    text = replace_once(text, old_caption, new_caption, "compteurs payload")

    path.write_text(text, encoding="utf-8")


def patch_ui(path: Path) -> None:
    text = path.read_text(encoding="utf-8")

    old = (
        '                else:\n'
        '                    if st.button(\n'
        '                        "✕ Fermer le lecteur STEM",\n'
        '                        width="stretch",\n'
        '                        key=f"ezstem_close_player_{short_hash}",\n'
        '                    ):\n'
        '                        st.session_state[stem_player_open_key] = False\n'
        '                        st.rerun()\n'
        '\n'
        '                    _render_stem_player(\n'
    )
    new = (
        '                else:\n'
        '                    _render_stem_player(\n'
    )
    text = replace_once(text, old, new, "suppression bouton fermer")

    path.write_text(text, encoding="utf-8")


def main() -> int:
    paths = [PLAYER, UI]
    for path in paths:
        if not path.is_file():
            raise FileNotFoundError(path)

    print("Backup:", backup(paths))

    with tempfile.TemporaryDirectory(prefix="ezscore_stem_conductor_r2_") as td:
        td = Path(td)
        ptmp = td / PLAYER.name
        uitmp = td / UI.name
        shutil.copy2(PLAYER, ptmp)
        shutil.copy2(UI, uitmp)

        patch_player(ptmp)
        patch_ui(uitmp)

        ast.parse(ptmp.read_text(encoding="utf-8"), filename=str(ptmp))
        ast.parse(uitmp.read_text(encoding="utf-8"), filename=str(uitmp))

        shutil.copy2(ptmp, PLAYER)
        shutil.copy2(uitmp, UI)

    print("PATCH OK")
    print(" - bug JS activeWordIndex corrigé")
    print(" - premier rendu conducteur différé après layout")
    print(" - compteurs beats/mots visibles")
    print(" - bouton Fermer le lecteur STEM supprimé")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
