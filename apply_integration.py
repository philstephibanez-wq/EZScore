from __future__ import annotations

from pathlib import Path
import shutil
import sys

ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
EZ = ROOT / "EZScore.py"
PACKAGE_AUDIO = ROOT / "ezscore" / "audio"
DELIVERY = Path(__file__).resolve().parent


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(
            f"{label}: motif attendu exactement 1 fois, trouvé {count}. "
            "Aucun patch partiel n'a été écrit."
        )
    return text.replace(old, new, 1)


if not EZ.exists():
    raise SystemExit(f"EZScore.py introuvable : {EZ}")

original = EZ.read_text(encoding="utf-8")
updated = original

anchor = "from ezscore.midi import MIDI_INSTRUMENTS\n"
insert = '''from ezscore.midi import MIDI_INSTRUMENTS
from ezscore.audio import (
    bs_roformer_disponible,
    separer_audio_harmonique,
    nettoyer_separation,
)
'''
updated = replace_once(updated, anchor, insert, "imports audio")

old_sidebar = '''    if demucs_disponible():
        st.sidebar.success("🎚️ Demucs : disponible")
    else:
        st.sidebar.warning("🎚️ Demucs : non installé")
'''
new_sidebar = '''    if bs_roformer_disponible():
        st.sidebar.success("🎚️ BS-RoFormer : disponible")
        if demucs_disponible():
            st.sidebar.caption("Demucs disponible en secours")
    elif demucs_disponible():
        st.sidebar.warning("🎚️ BS-RoFormer absent · Demucs utilisé en secours")
    else:
        st.sidebar.error("🎚️ Aucun séparateur audio disponible")
'''
updated = replace_once(updated, old_sidebar, new_sidebar, "sidebar séparateur")

start_marker = "\ndef separer_accompagnement_demucs(audio_bytes, extension):\n"
end_marker = "\n\n@st.cache_data(show_spinner=False)\ndef analyser_musique_cache(\n"
start = updated.find(start_marker)
end = updated.find(end_marker, start + 1)
if start < 0 or end < 0:
    raise RuntimeError(
        "Bloc separer_accompagnement_demucs introuvable. "
        "Aucun patch partiel n'a été écrit."
    )

replacement = '''
def separer_accompagnement(audio_bytes, extension):
    # Séparation harmonique modulaire : BS-RoFormer, puis Demucs en secours.
    return separer_audio_harmonique(
        audio_bytes=audio_bytes,
        extension=extension,
        device=DEVICE,
    )
'''
updated = updated[:start] + "\n" + replacement.rstrip() + updated[end:]

old_begin = '''    workdir = None
    _music_started = time.perf_counter()

    try:
        _demucs_started = time.perf_counter()
        workdir, original_path, accompaniment_path = (
            separer_accompagnement_demucs(
                audio_bytes,
                extension
            )
        )
        _demucs_seconds = time.perf_counter() - _demucs_started
        _rhythm_started = time.perf_counter()
'''
new_begin = '''    separation_result = None
    _separator_name = "unknown"
    _music_started = time.perf_counter()

    try:
        _separation_started = time.perf_counter()
        separation_result = separer_accompagnement(
            audio_bytes,
            extension,
        )
        original_path = separation_result.analysis_source_path
        accompaniment_path = separation_result.harmonic_path
        _separator_name = separation_result.engine
        _separation_seconds = time.perf_counter() - _separation_started
        _rhythm_started = time.perf_counter()
'''
updated = replace_once(updated, old_begin, new_begin, "début analyse")

old_perf = '''                "demucs_seconds": float(_demucs_seconds),
'''
new_perf = '''                "separator": str(_separator_name),
                "separation_seconds": float(_separation_seconds),
                "demucs_seconds": (
                    float(_separation_seconds)
                    if _separator_name == "demucs"
                    else 0.0
                ),
                "bs_roformer_seconds": (
                    float(_separation_seconds)
                    if _separator_name == "bs_roformer"
                    else 0.0
                ),
'''
updated = replace_once(updated, old_perf, new_perf, "performance séparation")

old_cleanup = '''    finally:
        if workdir:
            shutil.rmtree(
                workdir,
                ignore_errors=True
            )
'''
new_cleanup = '''    finally:
        if separation_result is not None:
            nettoyer_separation(separation_result)
'''
updated = replace_once(updated, old_cleanup, new_cleanup, "nettoyage séparation")

old_metric = '''                with perf_cols[0]:
                    st.metric(
                        "Demucs",
                        f"{_perf.get('demucs_seconds', 0.0):.1f} s",
                    )
'''
new_metric = '''                with perf_cols[0]:
                    _separator_perf = str(
                        _perf.get("separator", "demucs") or "demucs"
                    )
                    st.metric(
                        (
                            "BS-RoFormer"
                            if _separator_perf == "bs_roformer"
                            else "Demucs"
                        ),
                        f"{_perf.get('separation_seconds', _perf.get('demucs_seconds', 0.0)):.1f} s",
                    )
'''
updated = replace_once(updated, old_metric, new_metric, "métrique séparateur")

# Tous les motifs ont été validés : on écrit seulement maintenant.
PACKAGE_AUDIO.mkdir(parents=True, exist_ok=True)
shutil.copy2(DELIVERY / "ezscore" / "audio" / "__init__.py", PACKAGE_AUDIO / "__init__.py")
shutil.copy2(DELIVERY / "ezscore" / "audio" / "separation.py", PACKAGE_AUDIO / "separation.py")

backup = ROOT / "EZScore.py.before_bs_roformer"
if not backup.exists():
    backup.write_text(original, encoding="utf-8")

EZ.write_text(updated, encoding="utf-8")

print("Patch EZScore BS-RoFormer appliqué.")
print(f"Racine : {ROOT}")
print(f"Backup : {backup}")
print("Aucun commit/push Git n'a été effectué.")
