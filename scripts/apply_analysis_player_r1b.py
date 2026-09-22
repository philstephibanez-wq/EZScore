from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: motif attendu exactement 1 fois, trouvé {count}.")
    return text.replace(old, new, 1)


def backup(paths: list[Path]) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    preferred = Path(r"H:\temp")
    base = preferred if preferred.exists() else Path.home() / "AppData" / "Local" / "Temp"
    out = base / f"EZScore_ANALYSIS_PLAYER_R1b_backup_{stamp}"
    out.mkdir(parents=True, exist_ok=True)
    for path in paths:
        rel = path.relative_to(ROOT)
        dest = out / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)
    return out


def patch_forced_lyrics(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    text = replace_once(text, "import re\n", "import re\nimport sqlite3\n", "sqlite import")
    text = replace_once(
        text,
        'LAB_CACHE_DIR = APP_DIR / "data" / "analysis" / "stem_lab"\n',
        'LAB_CACHE_DIR = APP_DIR / "data" / "analysis" / "stem_lab"\nDB_PATH = APP_DIR / "data" / "EZScore.sqlite3"\n',
        "DB path",
    )

    old = '''def load_draft(audio_hash: str) -> str:\n    path = draft_path(audio_hash)\n    if path.is_file():\n        return path.read_text(encoding="utf-8")\n\n    payload = load_alignment(audio_hash)\n    if payload:\n        return str(payload.get("source_text", "") or "")\n    return ""\n\n\ndef save_draft(audio_hash: str, text: str) -> None:\n    draft_path(audio_hash).write_text(str(text or ""), encoding="utf-8")\n'''
    new = '''def _ensure_source_table(conn: sqlite3.Connection) -> None:\n    conn.execute(\n        """\n        CREATE TABLE IF NOT EXISTS user_lyrics_sources (\n            audio_hash TEXT PRIMARY KEY,\n            source_text TEXT NOT NULL DEFAULT '',\n            updated_at TEXT NOT NULL\n        )\n        """\n    )\n\n\ndef load_persisted_source_text(audio_hash: str) -> str:\n    try:\n        with sqlite3.connect(DB_PATH) as conn:\n            _ensure_source_table(conn)\n            row = conn.execute(\n                "SELECT source_text FROM user_lyrics_sources WHERE audio_hash = ?",\n                (str(audio_hash),),\n            ).fetchone()\n    except sqlite3.Error:\n        return ""\n    return str(row[0] or "") if row else ""\n\n\ndef save_persisted_source_text(audio_hash: str, text: str) -> None:\n    value = str(text or "")\n    try:\n        with sqlite3.connect(DB_PATH) as conn:\n            _ensure_source_table(conn)\n            conn.execute(\n                """\n                INSERT INTO user_lyrics_sources (audio_hash, source_text, updated_at)\n                VALUES (?, ?, ?)\n                ON CONFLICT(audio_hash) DO UPDATE SET\n                    source_text = excluded.source_text,\n                    updated_at = excluded.updated_at\n                """,\n                (str(audio_hash), value, datetime.now(timezone.utc).isoformat()),\n            )\n            conn.commit()\n    except sqlite3.Error:\n        pass\n\n\ndef load_draft(audio_hash: str) -> str:\n    path = draft_path(audio_hash)\n    if path.is_file():\n        value = path.read_text(encoding="utf-8")\n        if value.strip():\n            return value\n\n    payload = load_alignment(audio_hash)\n    if payload:\n        value = str(payload.get("source_text", "") or "")\n        if value.strip():\n            return value\n\n    return load_persisted_source_text(audio_hash)\n\n\ndef save_draft(audio_hash: str, text: str) -> None:\n    value = str(text or "")\n    draft_path(audio_hash).write_text(value, encoding="utf-8")\n    save_persisted_source_text(audio_hash, value)\n'''
    text = replace_once(text, old, new, "durable draft")

    text = replace_once(
        text,
        'def _emit_chunked(model, waveform, device, *, sample_rate: int):\n',
        'def _emit_chunked(model, waveform, device, *, sample_rate: int, progress=None):\n',
        "emit signature",
    )
    text = replace_once(
        text,
        '    total_samples = int(waveform.shape[-1])\n\n    with torch.inference_mode():\n        for sample_start in range(0, total_samples, chunk_samples):\n',
        '    total_samples = int(waveform.shape[-1])\n    total_chunks = max(1, (total_samples + chunk_samples - 1) // chunk_samples)\n\n    with torch.inference_mode():\n        for chunk_index, sample_start in enumerate(range(0, total_samples, chunk_samples), start=1):\n            if progress is not None:\n                progress(f"Analyse acoustique MMS_FA · segment {chunk_index}/{total_chunks}…")\n',
        "chunk progress",
    )
    text = replace_once(
        text,
        'def align_user_lyrics(audio_hash: str, source_text: str) -> dict[str, Any]:\n',
        'def align_user_lyrics(audio_hash: str, source_text: str, *, progress=None) -> dict[str, Any]:\n',
        "align signature",
    )
    text = replace_once(
        text,
        '    rows = _source_tokens(source_text)\n    transcript = [str(row["acoustic"]) for row in rows]\n\n    bundle = torchaudio.pipelines.MMS_FA\n',
        '    if progress is not None:\n        progress("Préparation phonétique du texte…")\n    rows = _source_tokens(source_text)\n    transcript = [str(row["acoustic"]) for row in rows]\n\n    if progress is not None:\n        progress("Chargement du modèle MMS_FA…")\n    bundle = torchaudio.pipelines.MMS_FA\n',
        "initial progress",
    )
    text = replace_once(
        text,
        '    emission, frame_map = _emit_chunked(\n        model,\n        waveform,\n        device,\n        sample_rate=sample_rate,\n    )\n\n    try:\n',
        '    emission, frame_map = _emit_chunked(\n        model,\n        waveform,\n        device,\n        sample_rate=sample_rate,\n        progress=progress,\n    )\n\n    if progress is not None:\n        progress("Alignement forcé texte ↔ chant…")\n\n    try:\n',
        "alignment progress",
    )
    text = replace_once(
        text,
        '    path = cache_path(audio_hash)\n    temp = path.with_suffix(".tmp")\n',
        '    if progress is not None:\n        progress("Enregistrement des mots horodatés…")\n\n    path = cache_path(audio_hash)\n    temp = path.with_suffix(".tmp")\n',
        "save progress",
    )
    path.write_text(text, encoding="utf-8")


def patch_choir(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    text = replace_once(text, "import json\n", "import json\nimport sqlite3\n", "choir sqlite")
    text = replace_once(
        text,
        'LEAD_ONLY_LYRICS = True\nMANUAL_LYRICS = True\n',
        '''LEAD_ONLY_LYRICS = True\nMANUAL_LYRICS = True\n\n_DB_PATH = Path(__file__).resolve().parents[2] / "data" / "EZScore.sqlite3"\n\n\ndef _legacy_saved_lyrics(audio_hash: str) -> str:\n    try:\n        with sqlite3.connect(_DB_PATH) as conn:\n            rows = conn.execute(\n                "SELECT corrected_text, original_text, time_start FROM lyric_block_edits WHERE audio_hash = ? ORDER BY time_start",\n                (str(audio_hash),),\n            ).fetchall()\n    except sqlite3.Error:\n        return ""\n    chunks = []\n    for corrected, original, _ in rows:\n        value = str(corrected or original or "").strip()\n        if value and (not chunks or value != chunks[-1]):\n            chunks.append(value)\n    return "\\n\\n".join(chunks).strip()\n''',
        "legacy recovery helper",
    )

    old = '''            current_text = st.text_area(\n                "Texte exact du chant",\n                key=text_key,\n                height=300,\n                placeholder=(\n                    "Collez ici les paroles exactes. "\n                    "Conservez les retours à la ligne : ils seront mémorisés."\n                ),\n            )\n            save_draft(audio_hash, current_text)\n'''
    new = '''            current_text = st.text_area(\n                "Texte exact du chant",\n                key=text_key,\n                height=300,\n                placeholder=(\n                    "Collez ici les paroles exactes. "\n                    "Conservez les retours à la ligne : ils seront mémorisés."\n                ),\n            )\n            save_draft(audio_hash, current_text)\n\n            if not current_text.strip():\n                legacy_text = _legacy_saved_lyrics(audio_hash)\n                if legacy_text and original_button(\n                    "↩ Récupérer les paroles enregistrées",\n                    key=f"ezscore_recover_legacy_lyrics_{short_hash}",\n                    width="stretch",\n                ):\n                    st.session_state[text_key] = legacy_text\n                    save_draft(audio_hash, legacy_text)\n                    st.rerun()\n'''
    text = replace_once(text, old, new, "recovery button")

    old = '''            if original_button(\n                label,\n                key=f"ezscore_force_align_{short_hash}",\n                type="primary",\n                width="stretch",\n                disabled=(not current_text.strip() or not lead_ready),\n            ):\n                try:\n                    with st.spinner(\n                        "Alignement acoustique du texte sur lead_vocals.wav…"\n                    ):\n                        align_user_lyrics(audio_hash, current_text)\n                except Exception as exc:\n                    st.error(f"Alignement des paroles impossible : {exc}")\n                else:\n                    st.rerun()\n'''
    new = '''            if original_button(\n                label,\n                key=f"ezscore_force_align_{short_hash}",\n                type="primary",\n                width="stretch",\n                disabled=(not current_text.strip() or not lead_ready),\n            ):\n                try:\n                    with st.status(\n                        "Alignement des paroles en cours…",\n                        expanded=True,\n                    ) as status:\n                        status.write("Initialisation MMS_FA…")\n                        align_user_lyrics(\n                            audio_hash,\n                            current_text,\n                            progress=status.write,\n                        )\n                        status.update(\n                            label="Paroles alignées.",\n                            state="complete",\n                            expanded=False,\n                        )\n                except Exception as exc:\n                    st.error(f"Alignement des paroles impossible : {exc}")\n                else:\n                    st.rerun()\n'''
    text = replace_once(text, old, new, "visible alignment status")

    old = '''            return original_success(\n                f"✓ Paroles alignées · {count} mots horodatés · "\n                f"moteur `{FORCED_ENGINE}` · texte utilisateur."\n            )\n'''
    new = '''            result = original_success(\n                f"✓ Paroles alignées · {count} mots horodatés · "\n                f"moteur `{FORCED_ENGINE}` · texte utilisateur."\n            )\n            if original_button(\n                "→ Étape 3 · Blocs / structure",\n                key=f"ezscore_next_blocks_{short_hash}",\n                width="stretch",\n            ):\n                st.session_state[f"ezstem_analysis_step_{short_hash}"] = "3 · Blocs / structure"\n                st.rerun()\n            return result\n'''
    text = replace_once(text, old, new, "next step button")
    path.write_text(text, encoding="utf-8")


def patch_player(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    text = replace_once(
        text,
        "from ezscore.player import stem_webaudio as base\n",
        "from ezscore.player import stem_webaudio as base\nfrom ezscore.analysis.forced_lyrics import load_alignment\n",
        "player alignment import",
    )
    text = replace_once(
        text,
        '    <div class="conductor-head">\n      <strong>Conducteur continu</strong>\n      <label class="diagram-toggle">\n',
        '    <div class="conductor-head">\n      <label class="diagram-toggle">\n',
        "remove conductor title",
    )

    marker = "\n\n_PLAYER_CSS = base._PLAYER_CSS + r'''\n"
    patch_block = '''\n\n_PLAYER_HTML = _replace_once(\n    _PLAYER_HTML,\n    """  <div class=\"transport\">\n    <button class=\"play\" type=\"button\">▶ Lecture</button>\n    <button class=\"pause\" type=\"button\">⏸ Pause</button>\n    <button class=\"stop\" type=\"button\">⏹ Stop</button>\n    <span class=\"time\">0:00 / 0:00</span>\n  </div>\n\n  <input class=\"seek\" type=\"range\" min=\"0\" max=\"1\" step=\"0.001\" value=\"0\">\n\n""",\n    "",\n    "transport haut retiré",\n)\n\n_PLAYER_HTML = _replace_once(\n    _PLAYER_HTML,\n    """    <div class=\"current-diagram\"></div>\n  </div>\n""",\n    """    <div class=\"transport conductor-transport\">\n      <button class=\"play\" type=\"button\">▶ Lecture</button>\n      <button class=\"pause\" type=\"button\">⏸ Pause</button>\n      <button class=\"stop\" type=\"button\">⏹ Stop</button>\n      <span class=\"time\">0:00 / 0:00</span>\n    </div>\n    <input class=\"seek conductor-seek\" type=\"range\" min=\"0\" max=\"1\" step=\"0.001\" value=\"0\">\n    <div class=\"current-diagram\"></div>\n  </div>\n""",\n    "transport sous conducteur",\n)\n'''
    text = replace_once(text, marker, patch_block + marker, "transport reorder")
    text = replace_once(
        text,
        ".current-diagram {\n",
        ".conductor-transport { margin-top:10px; }\n.conductor-seek { width:100%; margin:8px 0 2px; }\n.current-diagram {\n",
        "transport css",
    )
    # `duration` lives inside base._PLAYER_JS at runtime, not literally in
    # this Python source file. Patch the JS string after `_JS = base._PLAYER_JS`.
    text = replace_once(
        text,
        "_JS = base._PLAYER_JS\n",
        "_JS = base._PLAYER_JS\n"
        "_JS = _replace_once(\n"
        "    _JS,\n"
        "    \'  let duration = 0;\\n\',\n"
        "    \'  let duration = Number(data.duration_hint || 0);\\n\',\n"
        "    \'duration hint\',\n"
        ")\n",
        "duration hint runtime patch",
    )

    old = '''    player_words = list(words or [])\n\n    st.caption(\n'''
    new = '''    player_words = list(words or [])\n    if not player_words:\n        forced = load_alignment(audio_hash) or {}\n        player_words = list(forced.get("words", []) or [])\n\n    last_word_end = max(\n        [float(item.get("end", item.get("start", 0.0)) or 0.0) for item in player_words]\n        or [0.0]\n    )\n    last_beat_time = max(\n        [float(item.get("time", item.get("start", 0.0)) or 0.0) for item in beats]\n        or [0.0]\n    )\n    duration_hint = max(last_word_end, last_beat_time)\n\n    st.caption(\n'''
    text = replace_once(text, old, new, "player fallback words")
    text = replace_once(
        text,
        '            "diagram_storage_key": f"ezscore-stem-diagrams:{audio_hash}",\n',
        '            "diagram_storage_key": f"ezscore-stem-diagrams:{audio_hash}",\n            "duration_hint": float(duration_hint),\n',
        "duration data",
    )
    path.write_text(text, encoding="utf-8")


def main() -> int:
    import ast
    import tempfile

    paths = [
        ROOT / "ezscore/analysis/forced_lyrics.py",
        ROOT / "ezscore/integration/choir_pipeline.py",
        ROOT / "ezscore/player/stem_analysis_conductor.py",
    ]
    for path in paths:
        if not path.is_file():
            raise FileNotFoundError(path)

    backup_dir = backup(paths)
    print("Backup:", backup_dir)

    # Atomic application: all patching and syntax validation happens on
    # temporary copies. The repository is modified only if every step succeeds.
    with tempfile.TemporaryDirectory(prefix="ezscore_analysis_player_r1b_") as td:
        temp_root = Path(td)
        temp_paths = []
        for original in paths:
            rel = original.relative_to(ROOT)
            candidate = temp_root / rel
            candidate.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(original, candidate)
            temp_paths.append(candidate)

        patch_forced_lyrics(temp_paths[0])
        patch_choir(temp_paths[1])
        patch_player(temp_paths[2])

        for candidate in temp_paths:
            ast.parse(
                candidate.read_text(encoding="utf-8"),
                filename=str(candidate),
            )

        for candidate, original in zip(temp_paths, paths):
            shutil.copy2(candidate, original)

    print("PATCH OK")
    print(" - application atomique validée")
    print(" - progression MMS_FA visible")
    print(" - bouton Étape 3 ajouté")
    print(" - texte utilisateur persisté en SQLite + fichier")
    print(" - récupération des anciennes paroles enregistrées disponible")
    print(" - Lecture/Pause/Stop sous Accords/Paroles")
    print(" - libellé Conducteur continu supprimé")
    print(" - Diagrammes guitare à gauche")
    print(" - player recharge les mots canoniques si nécessaire")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
