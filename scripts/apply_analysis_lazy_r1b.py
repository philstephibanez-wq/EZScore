from __future__ import annotations

import shutil
import subprocess
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

TARGETS = {
    "EZScore.py": "f2227caa743e0b44ba345ac8d90fc7d8e2640e01",
    "ezscore/ui/stem_lab_analysis.py": "937e6ad6a9d082759564acda7251c8bdfe113963",
}

def git_index_blob(path_text: str) -> str:
    result = subprocess.run(
        ["git", "ls-files", "-s", "--", path_text],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    line = result.stdout.strip()
    if not line:
        return ""
    return line.split()[1]

def has_worktree_change(path_text: str) -> bool:
    result = subprocess.run(
        ["git", "diff", "--quiet", "--", path_text],
        cwd=ROOT,
    )
    return result.returncode != 0

def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: motif attendu exactement 1 fois, trouvé {count}.")
    return text.replace(old, new, 1)

def backup(paths: list[Path]) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    preferred = Path(r"H:\temp")
    base = preferred if preferred.exists() else Path.home() / "AppData" / "Local" / "Temp"
    out = base / f"EZScore_ANALYSIS_LAZY_R1b_backup_{stamp}"
    out.mkdir(parents=True, exist_ok=True)
    for path in paths:
        rel = path.relative_to(ROOT)
        dest = out / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)
    return out

def patch_stem_lab(path: Path) -> None:
    text = path.read_text(encoding="utf-8")

    old_tabs = """    tab_stem, tab_lyrics, tab_blocks, tab_midi = st.tabs(
        ["1 · STEM", "2 · Paroles", "3 · Blocs / structure", "4 · MIDI"]
    )
"""
    new_tabs = """    analysis_steps = [
        "1 · STEM",
        "2 · Paroles",
        "3 · Blocs / structure",
        "4 · MIDI",
    ]
    analysis_step_key = f"ezstem_analysis_step_{str(audio_hash)[:12]}"

    if analysis_step_key not in st.session_state:
        if not stems_cache_complete(audio_hash):
            st.session_state[analysis_step_key] = "1 · STEM"
        elif _load_speech(audio_hash) is None:
            st.session_state[analysis_step_key] = "2 · Paroles"
        else:
            st.session_state[analysis_step_key] = "1 · STEM"

    analysis_step = st.segmented_control(
        "Étape d'analyse",
        analysis_steps,
        key=analysis_step_key,
        width="stretch",
        label_visibility="collapsed",
    )
    analysis_step = str(
        analysis_step
        or st.session_state.get(analysis_step_key, analysis_steps[0])
    )
"""
    text = replace_once(text, old_tabs, new_tabs, "remplacement st.tabs principal")

    replacements = [
        ("    with tab_stem:\n", '    if analysis_step == "1 · STEM":\n', "branche STEM"),
        ("    with tab_lyrics:\n", '    elif analysis_step == "2 · Paroles":\n', "branche Paroles"),
        ("    with tab_blocks:\n", '    elif analysis_step == "3 · Blocs / structure":\n', "branche Blocs"),
        ("    with tab_midi:\n", '    elif analysis_step == "4 · MIDI":\n', "branche MIDI"),
    ]
    for old, new, label in replacements:
        text = replace_once(text, old, new, label)

    path.write_text(text, encoding="utf-8")

def patch_ezscore(path: Path) -> None:
    text = path.read_text(encoding="utf-8")

    old = """            if persisted_audio_path is None:
                audio_file_count = sum(
                    1
                    for p in AUDIO_DIR.iterdir()
                    if p.is_file()
                )

                st.warning(
                    "L'analyse du morceau est persistée, mais "
                    "aucun fichier audio correspondant à son "
                    "SHA-256 n'a été retrouvé dans "
                    f"{AUDIO_DIR}. "
                    f"{audio_file_count} fichier(s) audio présent(s)."
                )
            else:
"""
    new = """            if persisted_audio_path is None:
                audio_file_count = sum(
                    1
                    for p in AUDIO_DIR.iterdir()
                    if p.is_file()
                )

                _song_loading_notice.empty()
                st.warning(
                    "L'analyse du morceau est persistée, mais "
                    "aucun fichier audio correspondant à son "
                    "SHA-256 n'a été retrouvé dans "
                    f"{AUDIO_DIR}. "
                    f"{audio_file_count} fichier(s) audio présent(s)."
                )

                recover_col, back_col = st.columns(2)
                with recover_col:
                    if st.button(
                        "⬆️ Réimporter l'audio",
                        type="primary",
                        width="stretch",
                        key=f"missing_audio_import_{str(current_hash)[:12]}",
                    ):
                        st.session_state["_pending_main_menu"] = "Import"
                        st.rerun()

                with back_col:
                    if st.button(
                        "← Retour au répertoire",
                        width="stretch",
                        key=f"missing_audio_back_{str(current_hash)[:12]}",
                    ):
                        st.session_state["_pending_main_menu"] = "Répertoire"
                        st.rerun()
            else:
"""
    text = replace_once(text, old, new, "récupération audio manquant")
    path.write_text(text, encoding="utf-8")

def main() -> int:
    paths = [ROOT / name for name in TARGETS]

    mismatches = []
    for name, expected in TARGETS.items():
        path = ROOT / name
        if not path.is_file():
            mismatches.append((name, expected, "<missing>", True))
            continue
        actual = git_index_blob(name)
        dirty = has_worktree_change(name)
        if actual != expected or dirty:
            mismatches.append((name, expected, actual, dirty))

    if mismatches:
        print("ABORT: les fichiers cibles ne correspondent plus à la base vérifiée.")
        for name, expected, actual, dirty in mismatches:
            print(f"  {name}")
            print(f"    attendu (index): {expected}")
            print(f"    actuel  (index): {actual}")
            print(f"    modification worktree: {dirty}")
        print("Aucun fichier n'a été modifié.")
        return 2

    print("Backup:", backup(paths))
    patch_stem_lab(ROOT / "ezscore/ui/stem_lab_analysis.py")
    patch_ezscore(ROOT / "EZScore.py")

    print("PATCH OK")
    print(" - garde-fou Git: index blob + git diff (CRLF-safe)")
    print(" - Analyse: une seule étape exécutée par run")
    print(" - Lecteur STEM: monté uniquement dans l'étape STEM")
    print(" - Paroles/MMS_FA: ne remonte plus le player STEM")
    print(" - Audio manquant: Réimporter + Retour répertoire disponibles")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
