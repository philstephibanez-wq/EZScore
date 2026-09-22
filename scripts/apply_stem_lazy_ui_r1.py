from __future__ import annotations
import ast
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "ezscore/ui/stem_lab_analysis.py"


def backup(path: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    preferred = Path(r"H:\temp")
    base = preferred if preferred.exists() else Path.home() / "AppData" / "Local" / "Temp"
    out = base / f"EZScore_STEM_LAZY_UI_R1_backup_{stamp}"
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

    anchor = (
        '    analysis_step = str(\n'
        '        analysis_step\n'
        '        or st.session_state.get(analysis_step_key, analysis_steps[0])\n'
        '    )\n'
        '\n'
        '    stems = cached_stem_paths(audio_hash)\n'
    )
    replacement = (
        '    analysis_step = str(\n'
        '        analysis_step\n'
        '        or st.session_state.get(analysis_step_key, analysis_steps[0])\n'
        '    )\n'
        '\n'
        '    short_hash = str(audio_hash)[:12]\n'
        '    stem_player_open_key = f"ezstem_player_open_{short_hash}"\n'
        '    stem_downloads_open_key = f"ezstem_downloads_open_{short_hash}"\n'
        '\n'
        '    if analysis_step != "1 · STEM":\n'
        '        st.session_state[stem_player_open_key] = False\n'
        '        st.session_state[stem_downloads_open_key] = False\n'
        '\n'
        '    stems = cached_stem_paths(audio_hash)\n'
    )
    text = replace_once(text, anchor, replacement, "lifecycle")

    old_download = (
        '            vocal_parts = vocal_stem_paths(audio_hash)\n'
        '            all_stems = {**stems, **vocal_parts}\n'
        '            _download_stems(all_stems)\n'
        '\n'
        '            regen_all_col, regen_vocal_col = st.columns(2)\n'
    )
    new_download = (
        '            vocal_parts = vocal_stem_paths(audio_hash)\n'
        '            all_stems = {**stems, **vocal_parts}\n'
        '\n'
        '            downloads_open = bool(\n'
        '                st.session_state.get(stem_downloads_open_key, False)\n'
        '            )\n'
        '            if not downloads_open:\n'
        '                if st.button(\n'
        '                    "⬇ Préparer les téléchargements STEM",\n'
        '                    key=f"ezstem_open_downloads_{short_hash}",\n'
        '                    width="stretch",\n'
        '                    help=(\n'
        '                        "Charge les WAV uniquement à la demande. "\n'
        '                        "Évite de gros payloads pendant la navigation."\n'
        '                    ),\n'
        '                ):\n'
        '                    st.session_state[stem_downloads_open_key] = True\n'
        '                    st.rerun()\n'
        '            else:\n'
        '                if st.button(\n'
        '                    "✕ Fermer les téléchargements STEM",\n'
        '                    key=f"ezstem_close_downloads_{short_hash}",\n'
        '                    width="stretch",\n'
        '                ):\n'
        '                    st.session_state[stem_downloads_open_key] = False\n'
        '                    st.rerun()\n'
        '                _download_stems(all_stems)\n'
        '\n'
        '            regen_all_col, regen_vocal_col = st.columns(2)\n'
    )
    text = replace_once(text, old_download, new_download, "downloads lazy")

    old_player = (
        '            if not _stem_ffmpeg_available():\n'
        '                st.error("FFmpeg est requis pour le lecteur STEM.")\n'
        '            else:\n'
        '                st.markdown("### Lecteur STEM")\n'
        '                st.caption(\n'
        '                    "Original + Chant + Chœurs + Batterie + Basse + Other. "\n'
        '                    + ("Paroles synchronisées actives." if words\n'
        '                       else "Les paroles synchronisées apparaîtront après l\'étape 2.")\n'
        '                )\n'
        '                _render_stem_player(\n'
        '                    source, all_stems,\n'
        '                    preview_dir=_work_dir(audio_hash) / "browser_preview",\n'
        '                    key=f"ezstem_player_{str(audio_hash)[:12]}_{len(words)}",\n'
        '                    words=words,\n'
        '                )\n'
    )
    new_player = (
        '            if not _stem_ffmpeg_available():\n'
        '                st.error("FFmpeg est requis pour le lecteur STEM.")\n'
        '            else:\n'
        '                st.markdown("### Lecteur STEM")\n'
        '                st.caption(\n'
        '                    "Original + Chant + Chœurs + Batterie + Basse + Other. "\n'
        '                    + ("Paroles synchronisées actives." if words\n'
        '                       else "Les paroles synchronisées apparaîtront après l\'étape 2.")\n'
        '                )\n'
        '\n'
        '                player_open = bool(\n'
        '                    st.session_state.get(stem_player_open_key, False)\n'
        '                )\n'
        '                if not player_open:\n'
        '                    st.info(\n'
        '                        "Le lecteur audio est déchargé pendant la navigation. "\n'
        '                        "Ouvrez-le uniquement pour écouter."\n'
        '                    )\n'
        '                    if st.button(\n'
        '                        "▶ Ouvrir le lecteur STEM",\n'
        '                        type="primary",\n'
        '                        width="stretch",\n'
        '                        key=f"ezstem_open_player_{short_hash}",\n'
        '                        help=(\n'
        '                            "Monte le mixer à la demande. "\n'
        '                            "Bouton adapté clavier/télécommande Android."\n'
        '                        ),\n'
        '                    ):\n'
        '                        st.session_state[stem_player_open_key] = True\n'
        '                        st.rerun()\n'
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
        '                        source, all_stems,\n'
        '                        preview_dir=_work_dir(audio_hash) / "browser_preview",\n'
        '                        key=f"ezstem_player_{short_hash}_{len(words)}",\n'
        '                        words=words,\n'
        '                    )\n'
    )
    text = replace_once(text, old_player, new_player, "player lazy")

    path.write_text(text, encoding="utf-8")


def main() -> int:
    if not TARGET.is_file():
        raise FileNotFoundError(TARGET)

    print("Backup:", backup(TARGET))
    with tempfile.TemporaryDirectory(prefix="ezscore_stem_lazy_ui_") as td:
        candidate = Path(td) / TARGET.name
        shutil.copy2(TARGET, candidate)
        patch(candidate)
        ast.parse(candidate.read_text(encoding="utf-8"), filename=str(candidate))
        shutil.copy2(candidate, TARGET)

    print("PATCH OK")
    print(" - retour STEM sans montage automatique du lecteur")
    print(" - téléchargements WAV chargés uniquement à la demande")
    print(" - lecteur STEM ouvert uniquement par bouton explicite")
    print(" - lecteur/téléchargements déchargés en quittant STEM")
    print(" - boutons pleine largeur adaptés clavier/télécommande Android")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
