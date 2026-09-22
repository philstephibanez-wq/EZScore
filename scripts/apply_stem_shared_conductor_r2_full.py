from __future__ import annotations

import ast
import hashlib
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_HEAD = "8e6fb686445132189df0afcd860f4803ef221cc6"

STEM_SOURCE = ROOT / "files" / "ezscore" / "player" / "stem_analysis_conductor.py"
STEM_TARGET = ROOT / "ezscore" / "player" / "stem_analysis_conductor.py"
APP_TARGET = ROOT / "EZScore.py"


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def insert_once_before(source: str, needle: str, insertion: str, label: str) -> str:
    count = source.count(needle)
    if count != 1:
        raise RuntimeError(
            f"{label}: attendu 1 ancrage, trouvé {count}. Aucun fichier modifié."
        )
    return source.replace(needle, insertion + needle, 1)


head = subprocess.check_output(
    ["git", "rev-parse", "HEAD"],
    cwd=ROOT,
    text=True,
).strip()

if head != EXPECTED_HEAD:
    raise RuntimeError(
        "HEAD Git inattendu.\n"
        f"Attendu : {EXPECTED_HEAD}\n"
        f"Trouvé  : {head}\n"
        "Aucun fichier modifié."
    )

if not STEM_SOURCE.is_file():
    raise RuntimeError(f"Fichier complet manquant : {STEM_SOURCE}")

stem_candidate = STEM_SOURCE.read_text(encoding="utf-8")
ast.parse(stem_candidate, filename=str(STEM_TARGET))

required_stem_markers = (
    '"ezscore_stem_shared_conductor_r2_full"',
    '"lyrics-editor.css"',
    '"lyrics-layout.js"',
    'class="ez-row-label">Structure</div>',
    'class="ez-row-label">Accords</div>',
    'class="ez-row-label">Chant</div>',
    "accord_forme_capo",
    "load_structure_blocks",
    "ezLayoutLaneNodes({",
    "ezVisualXForTime(",
)
for marker in required_stem_markers:
    if marker not in stem_candidate:
        raise RuntimeError(
            f"Fichier STEM complet invalide, marqueur absent : {marker!r}"
        )

# ------------------------------------------------------------------
# EZScore.py: ensure the complete requested sidebar behavior.
# Works from clean master OR from already-applied R1/R1c state.
# ------------------------------------------------------------------
app = APP_TARGET.read_text(encoding="utf-8")

signature_widget = (
    '        signature_options = [\n'
    '            "Auto",\n'
    '            "2/4",\n'
    '            "3/4",\n'
    '            "4/4",\n'
    '            "5/4",\n'
    '            "6/8",\n'
    '            "7/8",\n'
    '            "9/8",\n'
    '            "12/8",\n'
    '        ]\n'
    '        current_signature_mode = str(\n'
    '            st.session_state.get("setting_signature_mode", "Auto") or "Auto"\n'
    '        )\n'
    '        if current_signature_mode not in signature_options:\n'
    '            signature_options.append(current_signature_mode)\n\n'
    '        signature_mode = st.selectbox(\n'
    '            "⏱ Time signature",\n'
    '            signature_options,\n'
    '            key="setting_signature_mode",\n'
    '            help=(\n'
    '                "Change uniquement la représentation métrique du conducteur "\n'
    '                "et de la grille. Aucun beat, accord ou mot n’est déplacé."\n'
    '            ),\n'
    '        )\n\n'
)

if '"⏱ Time signature"' not in app:
    app = insert_once_before(
        app,
        "        capo_user = st.selectbox(\n",
        signature_widget,
        "insertion Time signature",
    )

old_pref = (
    '    if _stored_capo != int(capo_user):\n'
    '        save_song_preferences(\n'
    '            audio_hash=audio_hash,\n'
    '            capo=capo_user,\n'
    '            settings=_stored_settings,\n'
    '        )\n'
)

new_pref = (
    '    _effective_pref_settings = dict(_stored_settings)\n'
    '    _effective_pref_settings["signature_mode"] = str(signature_mode)\n\n'
    '    if (\n'
    '        _stored_capo != int(capo_user)\n'
    '        or str(_stored_settings.get("signature_mode", "Auto"))\n'
    '        != str(signature_mode)\n'
    '    ):\n'
    '        save_song_preferences(\n'
    '            audio_hash=audio_hash,\n'
    '            capo=capo_user,\n'
    '            settings=_effective_pref_settings,\n'
    '        )\n'
    '        _stored_settings = _effective_pref_settings\n'
)

if '_effective_pref_settings["signature_mode"]' not in app:
    count = app.count(old_pref)
    if count != 1:
        raise RuntimeError(
            "Persistance capo/signature : bloc master introuvable ou ambigu. "
            f"Occurrences={count}. Aucun fichier modifié."
        )
    app = app.replace(old_pref, new_pref, 1)

# Hide the extra editorial status panel in Analyse only.
if 'if song_view != "Analyse":' not in app:
    start_marker = "    st.sidebar.markdown(\n        SCORE.render(\n"
    end_marker = '\n\n    if song_mode == "Édition":'
    start = app.find(start_marker)
    if start < 0:
        raise RuntimeError(
            "Panneau SCORE du left panel introuvable. Aucun fichier modifié."
        )
    end = app.find(end_marker, start)
    if end < 0:
        raise RuntimeError(
            "Fin du panneau SCORE introuvable. Aucun fichier modifié."
        )
    block = app[start:end]
    indented = "\n".join(
        ("    " + line if line.strip() else line)
        for line in block.splitlines()
    )
    app = app[:start] + '    if song_view != "Analyse":\n' + indented + app[end:]

# Validate COMPLETE final Python files before write.
ast.parse(app, filename=str(APP_TARGET))
ast.parse(stem_candidate, filename=str(STEM_TARGET))

with tempfile.TemporaryDirectory(prefix="ezscore_r2_full_") as td:
    td = Path(td)
    tmp_stem = td / "stem_analysis_conductor.py"
    tmp_app = td / "EZScore.py"

    tmp_stem.write_text(stem_candidate, encoding="utf-8")
    tmp_app.write_text(app, encoding="utf-8")

    ast.parse(tmp_stem.read_text(encoding="utf-8"), filename=str(tmp_stem))
    ast.parse(tmp_app.read_text(encoding="utf-8"), filename=str(tmp_app))

    backup_root = (
        Path("H:/temp")
        if Path("H:/temp").exists()
        else ROOT / ".ezscore_patch_backup"
    )
    backup_root.mkdir(parents=True, exist_ok=True)

    stem_backup = backup_root / "stem_analysis_conductor.before_R2_FULL.py"
    app_backup = backup_root / "EZScore.before_R2_FULL.py"

    shutil.copy2(STEM_TARGET, stem_backup)
    shutil.copy2(APP_TARGET, app_backup)

    shutil.copy2(tmp_stem, STEM_TARGET)
    shutil.copy2(tmp_app, APP_TARGET)

# Verify exact copied business file bytes immediately.
installed_stem = STEM_TARGET.read_text(encoding="utf-8")
if sha256_text(installed_stem) != sha256_text(stem_candidate):
    raise RuntimeError(
        "ERREUR CRITIQUE : le fichier STEM installé n'est pas identique "
        "au fichier livré."
    )

print("EZScore_STEM_SHARED_CONDUCTOR_R2_FULL appliqué.")
print("Git HEAD :", head)
print("Fichiers métier prêts :")
print(" - ezscore/player/stem_analysis_conductor.py (remplacement complet)")
print(" - EZScore.py (Time signature + Capodastre + panneau Analyse)")
print("SHA256 STEM installé :", sha256_text(installed_stem))
print("Backups :")
print(" -", stem_backup)
print(" -", app_backup)
