#!/usr/bin/env python
from __future__ import annotations

import argparse
import py_compile
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path


def replace_top_level_def(source: str, name: str, replacement: str) -> str:
    pattern = re.compile(rf"(?m)^def {re.escape(name)}\s*\(")
    match = pattern.search(source)
    if not match:
        raise RuntimeError(f"Fonction introuvable: {name}")
    next_def = re.search(r"(?m)^def [A-Za-z_]\w*\s*\(", source[match.end():])
    end = len(source) if next_def is None else match.end() + next_def.start()
    return source[:match.start()] + replacement.rstrip() + "\n\n" + source[end:]


NEW_RESOLVE = r"""
def resolve_lyric_block_edit(
    edits,
    time_start,
    time_end,
    tolerance=0.02,
    block_id=None,
):
    # R34: block_id stable first; timestamps are legacy fallback only.
    edits = edits or {}
    t0 = float(time_start)
    t1 = float(time_end)

    if block_id is not None:
        try:
            stable_key = f"block:{int(block_id)}"
        except (TypeError, ValueError):
            stable_key = ""
        if stable_key and stable_key in edits:
            return edits[stable_key]

    exact = edits.get(_lyric_block_key(t0, t1))
    if exact:
        return exact

    best = None
    best_delta = None
    tol = float(tolerance)

    for key, item in edits.items():
        if str(key).startswith("block:"):
            continue
        e0 = float(item.get("time_start", 0.0) or 0.0)
        e1 = float(item.get("time_end", e0) or e0)
        d0 = abs(e0 - t0)
        d1 = abs(e1 - t1)
        if d0 <= tol and d1 <= tol:
            delta = d0 + d1
            if best_delta is None or delta < best_delta:
                best = item
                best_delta = delta

    if best:
        return best

    best = None
    best_score = None
    for key, item in edits.items():
        if str(key).startswith("block:"):
            continue
        e0 = float(item.get("time_start", 0.0) or 0.0)
        e1 = float(item.get("time_end", e0) or e0)
        if e1 <= e0 or t1 <= t0:
            continue
        overlap = max(0.0, min(e1, t1) - max(e0, t0))
        if overlap <= 0.0:
            continue
        old_len = e1 - e0
        new_len = t1 - t0
        cover = overlap / min(old_len, new_len)
        old_mid = (e0 + e1) / 2.0
        new_mid = (t0 + t1) / 2.0
        center_delta = abs(old_mid - new_mid)
        max_len = max(old_len, new_len)
        if cover < 0.70 or center_delta > 0.35 * max_len:
            continue
        score = (cover, -center_delta)
        if best_score is None or score > best_score:
            best = item
            best_score = score

    return best or {}
"""


NEW_SNAPSHOT = r"""
def save_lyric_block_edits_snapshot(audio_hash, items):
    # Save ALL validated blocks with a stable block:<id> key.
    # Empty text is an explicit instrumental state.
    now = _utc_now_iso()
    normalized = []

    for item in items or []:
        block_id = item.get("block_id")
        if block_id is not None:
            try:
                block_key = f"block:{int(block_id)}"
            except (TypeError, ValueError):
                block_key = str(item.get("block_key", "") or "").strip()
        else:
            block_key = str(item.get("block_key", "") or "").strip()

        if not block_key:
            continue

        t0 = float(item.get("time_start", 0.0) or 0.0)
        t1 = float(item.get("time_end", t0) or t0)

        normalized.append({
            "block_key": block_key,
            "original_text": str(item.get("original_text", "") or "").strip(),
            "edited_text": str(item.get("edited_text", "") or "").strip(),
            "time_start": t0,
            "time_end": t1,
        })

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "DELETE FROM lyric_block_edits WHERE audio_hash = ?",
            (str(audio_hash),),
        )

        for item in normalized:
            conn.execute(
                (
                    "INSERT INTO lyric_block_edits ("
                    "audio_hash, block_key, original_text, corrected_text, "
                    "time_start, time_end, updated_at"
                    ") VALUES (?, ?, ?, ?, ?, ?, ?)"
                ),
                (
                    str(audio_hash),
                    item["block_key"],
                    item["original_text"],
                    item["edited_text"],
                    item["time_start"],
                    item["time_end"],
                    now,
                ),
            )
        conn.commit()
"""


NEW_EFFECTIVE = r"""
def effective_lyrics_words_for_sections(
    resultat,
    audio_hash,
    sections,
):
    edits = load_lyric_block_edits(audio_hash)
    effective = []

    if not sections:
        return [
            {
                "text": str(word.get("text", "") or "").strip(),
                "start": float(word.get("start", 0.0) or 0.0),
                "end": float(
                    word.get("end", word.get("start", 0.0)) or 0.0
                ),
            }
            for word in extraire_mots(resultat)
            if str(word.get("text", "") or "").strip()
        ]

    for section in sections:
        t0 = float(section.get("time_start", 0.0) or 0.0)
        t1 = float(section.get("time_end", t0) or t0)
        if t1 <= t0:
            continue

        source_words = _source_words_for_interval(resultat, t0, t1)
        edit = resolve_lyric_block_edit(
            edits,
            t0,
            t1,
            block_id=section.get("block_id"),
        )
        has_edit = bool(edit)
        corrected = str(
            edit.get("corrected_text", "") if has_edit else ""
        ).strip()

        if has_edit:
            if corrected:
                block_words = _redistribute_corrected_block_text(
                    corrected,
                    source_words,
                )
            else:
                block_words = []
        else:
            block_words = [
                {**word, "manual_line_end": False}
                for word in source_words
            ]

        effective.extend(block_words)

    effective.sort(
        key=lambda word: (
            float(word.get("start", 0.0) or 0.0),
            float(word.get("end", 0.0) or 0.0),
        )
    )
    return effective
"""


def patch_persistence(path: Path) -> None:
    source = path.read_text(encoding="utf-8")
    if "CREATE TABLE IF NOT EXISTS lyric_block_edits" not in source:
        raise RuntimeError("Version persistence.py non reconnue")
    source = replace_top_level_def(source, "resolve_lyric_block_edit", NEW_RESOLVE)
    source = replace_top_level_def(
        source, "save_lyric_block_edits_snapshot", NEW_SNAPSHOT
    )
    source = replace_top_level_def(
        source, "effective_lyrics_words_for_sections", NEW_EFFECTIVE
    )
    path.write_text(source, encoding="utf-8")


def patch_ezscore(path: Path) -> None:
    source = path.read_text(encoding="utf-8")

    old_live = """                    if (
                        _canonical_structure_rows(live_draft)
                        != _canonical_structure_rows(draft_blocks)
                    ):
                        # Modification de cellule : conserver la même clé de tableau
                        # afin de ne pas perdre les cases cochées ni le focus.
                        st.session_state[
                            _structure_draft_key(audio_hash)
                        ] = [dict(b) for b in live_draft]
                        st.rerun()
"""
    new_live = """                    if (
                        _canonical_structure_rows(live_draft)
                        != _canonical_structure_rows(draft_blocks)
                    ):
                        st.session_state[
                            _structure_draft_key(audio_hash)
                        ] = [dict(b) for b in live_draft]
                        draft_blocks = [dict(b) for b in live_draft]
"""
    if old_live not in source:
        raise RuntimeError("Bloc live_draft non reconnu")
    source = source.replace(old_live, new_live, 1)

    old_preview = """                    _preview_key = _lyric_block_key(
                        _preview_t0,
                        _preview_t1,
                    )

                    _preview_source_words = _source_words_for_interval(
                        resultat,
                        _preview_t0,
                        _preview_t1,
                    )
                    _preview_original = " ".join(
                        str(word.get("text", "") or "").strip()
                        for word in _preview_source_words
                        if str(word.get("text", "") or "").strip()
                    ).strip()

                    _preview_edit = resolve_lyric_block_edit(
                        _preview_lyric_edits,
                        _preview_t0,
                        _preview_t1,
                    )
"""
    new_preview = """                    _preview_block_id = int(
                        _preview_block.get("block_id", _preview_index + 1)
                        or (_preview_index + 1)
                    )
                    _preview_key = f"block:{_preview_block_id}"

                    _preview_source_words = _source_words_for_interval(
                        resultat,
                        _preview_t0,
                        _preview_t1,
                    )
                    _preview_original = " ".join(
                        str(word.get("text", "") or "").strip()
                        for word in _preview_source_words
                        if str(word.get("text", "") or "").strip()
                    ).strip()

                    _preview_edit = resolve_lyric_block_edit(
                        _preview_lyric_edits,
                        _preview_t0,
                        _preview_t1,
                        block_id=_preview_block_id,
                    )
"""
    if old_preview not in source:
        raise RuntimeError("Bloc preview paroles non reconnu")
    source = source.replace(old_preview, new_preview, 1)

    duplicate = """                    _preview_block_id = int(
                        _preview_block.get("block_id", _preview_index + 1)
                        or (_preview_index + 1)
                    )
                    _preview_widget_key = (
"""
    if duplicate not in source:
        raise RuntimeError("Second calcul block_id non reconnu")
    source = source.replace(duplicate, """                    _preview_widget_key = (
""", 1)

    source = source.replace(
        """                                resolve_lyric_block_edit(
                                    _preview_lyric_edits,
                                    item["time_start"],
                                    item["time_end"],
                                ).get("corrected_text", "")
""",
        """                                resolve_lyric_block_edit(
                                    _preview_lyric_edits,
                                    item["time_start"],
                                    item["time_end"],
                                    block_id=item.get("block_id"),
                                ).get("corrected_text", "")
""",
    )

    source = source.replace(
        """                            if resolve_lyric_block_edit(
                                _preview_lyric_edits,
                                item["time_start"],
                                item["time_end"],
                            )
""",
        """                            if resolve_lyric_block_edit(
                                _preview_lyric_edits,
                                item["time_start"],
                                item["time_end"],
                                block_id=item.get("block_id"),
                            )
""",
    )

    if "            def render_one_block(title, t0, t1):\n" not in source:
        raise RuntimeError("render_one_block non reconnu")
    source = source.replace(
        "            def render_one_block(title, t0, t1):\n",
        "            def render_one_block(title, t0, t1, block_id=None):\n",
        1,
    )

    old_render = """                edit = resolve_lyric_block_edit(
                    edits_by_block,
                    t0,
                    t1,
                )
"""
    new_render = """                edit = resolve_lyric_block_edit(
                    edits_by_block,
                    t0,
                    t1,
                    block_id=block_id,
                )
"""
    if old_render not in source:
        raise RuntimeError("Résolution parolier non reconnue")
    source = source.replace(old_render, new_render, 1)

    old_call = (
        "                    has_lyrics = "
        "render_one_block(title, t0, t1) or has_lyrics\n"
    )
    new_call = """                    has_lyrics = render_one_block(
                        title,
                        t0,
                        t1,
                        block_id=section.get("block_id"),
                    ) or has_lyrics
"""
    if old_call not in source:
        raise RuntimeError("Appel render_one_block non reconnu")
    source = source.replace(old_call, new_call, 1)

    old_print = """                    edit_print = resolve_lyric_block_edit(
                        edits_by_block,
                        t0_print,
                        t1_print,
                    )
"""
    new_print = """                    edit_print = resolve_lyric_block_edit(
                        edits_by_block,
                        t0_print,
                        t1_print,
                        block_id=section.get("block_id"),
                    )
"""
    if old_print not in source:
        raise RuntimeError("Résolution impression non reconnue")
    source = source.replace(old_print, new_print, 1)

    anchor = """            # Une seule transaction utilisateur : structure + paroles.
"""
    panel = """            with st.expander("🔤 Phonèmes / beats", expanded=False):
                _block_phonemes = build_phoneme_timeline(
                    resultat=resultat,
                    beats=beats,
                    beats_per_measure=beats_par_mesure_effectif,
                )
                if _block_phonemes:
                    st.dataframe(
                        pd.DataFrame(
                            beat_phoneme_groups(_block_phonemes)
                        ),
                        width="stretch",
                        hide_index=True,
                        height=320,
                    )
                    with st.expander(
                        "Détail phonème par phonème",
                        expanded=False,
                    ):
                        st.dataframe(
                            pd.DataFrame(
                                phoneme_diagnostic_rows(
                                    _block_phonemes
                                )
                            ),
                            width="stretch",
                            hide_index=True,
                            height=360,
                        )
                else:
                    st.caption("Aucune timeline phonétique disponible.")

"""
    if anchor not in source:
        raise RuntimeError("Ancre panneau phonèmes non reconnue")
    if 'with st.expander("🔤 Phonèmes / beats"' not in source:
        source = source.replace(anchor, panel + anchor, 1)

    path.write_text(source, encoding="utf-8")


def compile_targets(root: Path) -> None:
    for rel in [
        "EZScore.py",
        "EZScoreTemplate.py",
        "ezscore/persistence.py",
        "ezscore/phonetics/__init__.py",
        "ezscore/phonetics/timeline.py",
        "ezscore/ui/song_fsm.py",
    ]:
        p = root / rel
        if p.exists():
            py_compile.compile(str(p), doraise=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    ez = root / "EZScore.py"
    persistence = root / "ezscore" / "persistence.py"

    if not ez.exists() or not persistence.exists():
        print("ERREUR: racine EZScore invalide.", file=sys.stderr)
        return 2

    if "R34: block_id stable first" in persistence.read_text(encoding="utf-8"):
        print("R34 semble déjà appliquée.", file=sys.stderr)
        return 3

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = root / f"_backup_R34_{stamp}"
    (backup / "ezscore").mkdir(parents=True, exist_ok=True)
    shutil.copy2(ez, backup / "EZScore.py")
    shutil.copy2(persistence, backup / "ezscore" / "persistence.py")

    try:
        patch_persistence(persistence)
        patch_ezscore(ez)
        compile_targets(root)
    except Exception as exc:
        shutil.copy2(backup / "EZScore.py", ez)
        shutil.copy2(backup / "ezscore" / "persistence.py", persistence)
        print(f"ECHEC R34: {exc}", file=sys.stderr)
        print(f"Rollback automatique depuis {backup}", file=sys.stderr)
        return 1

    print("R34 appliquée.")
    print(f"Backup: {backup}")
    print("Compilation ciblée: OK")
    print("Schéma SQLite: INCHANGÉ")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
