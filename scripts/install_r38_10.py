#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re
import shutil
import sys

ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
BACKUP = ROOT / "var" / "backup" / ("r38-10-" + datetime.now().strftime("%Y%m%d-%H%M%S"))

def read(rel: str) -> str:
    p = ROOT / rel
    if not p.is_file():
        raise RuntimeError(f"Missing required file: {rel}")
    return p.read_text(encoding="utf-8")

def backup(p: Path) -> None:
    if not p.exists():
        return
    dst = BACKUP / p.relative_to(ROOT)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(p, dst)

def save(rel: str, text: str) -> None:
    p = ROOT / rel
    old = p.read_text(encoding="utf-8") if p.exists() else None
    if old == text:
        print(f"[OK] {rel}: already applied")
        return
    if p.exists():
        backup(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8", newline="\n")
    print(f"[OK] {rel}")

def replace_function(text: str, name: str, replacement: str) -> tuple[str, bool]:
    m = re.search(rf"(?m)^def {re.escape(name)}\s*\(", text)
    if not m:
        return text, False
    nxt = re.search(r"(?m)^def [A-Za-z_]\w*\s*\(", text[m.end():])
    end = m.end() + nxt.start() if nxt else len(text)
    return text[:m.start()] + replacement.rstrip() + "\n\n" + text[end:], True

HELPERS = '\ndef _r3810_similarity(a: str, b: str) -> float:\n    if not a or not b:\n        return 0.0\n    if a == b:\n        return 1.0\n    return difflib.SequenceMatcher(a=a, b=b, autojunk=False).ratio()\n\n\ndef _r3810_match_score(source_norm: str, recognized_norm: str, confidence: float, source_pos: float, recognized_pos: float) -> float:\n    sim = _r3810_similarity(source_norm, recognized_norm)\n    if sim >= 0.999:\n        lexical = 6.0\n    elif sim >= 0.90:\n        lexical = 5.0\n    elif sim >= 0.78:\n        lexical = 3.2\n    elif sim >= 0.64:\n        lexical = 1.2\n    else:\n        lexical = -3.0\n    positional_penalty = abs(source_pos - recognized_pos) * 2.0\n    confidence_bonus = max(0.0, min(1.0, float(confidence or 0.0))) * 0.55\n    return lexical + confidence_bonus - positional_penalty\n\n\ndef _r3810_sequential_mapping(provided: list[dict], recognized: list[dict], acoustic_t0: int) -> tuple[dict[int, tuple[int, int]], list[dict]]:\n    rec = [\n        row for row in recognized\n        if int(row.get("end_ms", row.get("start_ms", 0)) or 0) >= acoustic_t0 - 250\n    ]\n    if not rec:\n        raise RuntimeError("No recognized vocal words at or after acoustic T0")\n\n    src = provided[1:]\n    n = len(src)\n    m = len(rec)\n    if n == 0:\n        return {}, rec\n\n    neg = -10**15\n    dp = [[neg] * (m + 1) for _ in range(n + 1)]\n    back: list[list[tuple[int, int, str] | None]] = [[None] * (m + 1) for _ in range(n + 1)]\n    dp[0][0] = 0.0\n    SOURCE_GAP = -1.35\n    RECOGNIZED_GAP = -1.05\n\n    for i in range(n + 1):\n        for j in range(m + 1):\n            current = dp[i][j]\n            if current <= neg / 2:\n                continue\n\n            if i < n:\n                cand = current + SOURCE_GAP\n                if cand > dp[i + 1][j]:\n                    dp[i + 1][j] = cand\n                    back[i + 1][j] = (i, j, "skip_source")\n\n            if j < m:\n                cand = current + RECOGNIZED_GAP\n                if cand > dp[i][j + 1]:\n                    dp[i][j + 1] = cand\n                    back[i][j + 1] = (i, j, "skip_recognized")\n\n            if i < n and j < m:\n                source_pos = (i + 1) / max(1, n)\n                recognized_pos = (j + 1) / max(1, m)\n                score = _r3810_match_score(\n                    src[i].get("norm") or "",\n                    rec[j].get("norm") or "",\n                    float(rec[j].get("confidence", 0.0) or 0.0),\n                    source_pos,\n                    recognized_pos,\n                )\n                cand = current + score\n                if cand > dp[i + 1][j + 1]:\n                    dp[i + 1][j + 1] = cand\n                    back[i + 1][j + 1] = (i, j, "match11")\n\n            if i + 1 < n and j < m:\n                joined_source = (src[i].get("norm") or "") + (src[i + 1].get("norm") or "")\n                sim = _r3810_similarity(joined_source, rec[j].get("norm") or "")\n                if sim >= 0.72:\n                    source_pos = (i + 1.5) / max(1, n)\n                    recognized_pos = (j + 1) / max(1, m)\n                    score = 4.8 * sim + min(0.5, float(rec[j].get("confidence", 0.0) or 0.0) * 0.5)\n                    score -= abs(source_pos - recognized_pos) * 2.0\n                    cand = current + score\n                    if cand > dp[i + 2][j + 1]:\n                        dp[i + 2][j + 1] = cand\n                        back[i + 2][j + 1] = (i, j, "match21")\n\n            if i < n and j + 1 < m:\n                joined_rec = (rec[j].get("norm") or "") + (rec[j + 1].get("norm") or "")\n                sim = _r3810_similarity(src[i].get("norm") or "", joined_rec)\n                if sim >= 0.72:\n                    source_pos = (i + 1) / max(1, n)\n                    recognized_pos = (j + 1.5) / max(1, m)\n                    conf = (\n                        float(rec[j].get("confidence", 0.0) or 0.0)\n                        + float(rec[j + 1].get("confidence", 0.0) or 0.0)\n                    ) / 2.0\n                    score = 4.8 * sim + min(0.5, conf * 0.5)\n                    score -= abs(source_pos - recognized_pos) * 2.0\n                    cand = current + score\n                    if cand > dp[i + 1][j + 2]:\n                        dp[i + 1][j + 2] = cand\n                        back[i + 1][j + 2] = (i, j, "match12")\n\n    i, j = n, m\n    operations: list[tuple[int, int, int, int, str]] = []\n    while i > 0 or j > 0:\n        step = back[i][j]\n        if step is None:\n            raise RuntimeError(f"Sequential alignment traceback failed at source={i}, recognized={j}")\n        pi, pj, op = step\n        operations.append((pi, pj, i, j, op))\n        i, j = pi, pj\n    operations.reverse()\n\n    mapping: dict[int, tuple[int, int]] = {}\n    for pi, pj, ni, nj, op in operations:\n        if op == "match11":\n            mapping[pi + 1] = (pj, pj)\n        elif op == "match21":\n            mapping[pi + 1] = (pj, pj)\n            mapping[pi + 2] = (pj, pj)\n        elif op == "match12":\n            mapping[pi + 1] = (pj, pj + 1)\n\n    return mapping, rec\n\n\ndef _r3810_curve_sample(left_time: int, right_time: int, recognized_times: list[int], position: int, count: int) -> int:\n    if count <= 0:\n        return left_time\n    controls: list[tuple[float, float]] = [(0.0, float(left_time))]\n    q = len(recognized_times)\n    for idx, value in enumerate(recognized_times):\n        controls.append(((idx + 1) / (q + 1), float(value)))\n    controls.append((1.0, float(right_time)))\n    x = position / (count + 1)\n    for idx in range(1, len(controls)):\n        x1, y1 = controls[idx]\n        x0, y0 = controls[idx - 1]\n        if x <= x1:\n            if x1 <= x0:\n                return int(round(y1))\n            p = (x - x0) / (x1 - x0)\n            return int(round(y0 + (y1 - y0) * p))\n    return int(round(right_time))\n\n\ndef _r3810_apply_mapping(provided: list[dict], mapping: dict[int, tuple[int, int]], rec: list[dict], acoustic_t0: int) -> list[dict]:\n    rows = [\n        dict(row, start_ms=None, end_ms=None, confidence=0.0, language=None)\n        for row in provided\n    ]\n    rows[0].update(\n        start_ms=acoustic_t0,\n        end_ms=acoustic_t0 + 160,\n        confidence=1.0,\n        language=None,\n        alignment="acoustic_trigger",\n    )\n\n    grouped: dict[int, list[int]] = {}\n    for source_index, (r0, r1) in mapping.items():\n        grouped.setdefault(r0, []).append(source_index)\n        start = max(acoustic_t0, int(rec[r0]["start_ms"]))\n        end = max(start + 60, int(rec[r1].get("end_ms", start + 120)))\n        conf = min(\n            float(rec[k].get("confidence", 0.0) or 0.0)\n            for k in range(r0, r1 + 1)\n        )\n        rows[source_index].update(\n            start_ms=start,\n            end_ms=end,\n            confidence=conf,\n            language=rec[r0].get("language"),\n            recognized_index=r0,\n            alignment="lexical_anchor",\n        )\n\n    for r0, source_indexes in grouped.items():\n        same = sorted(i for i in source_indexes if mapping[i] == (r0, r0))\n        if len(same) < 2:\n            continue\n        start = max(acoustic_t0, int(rec[r0]["start_ms"]))\n        end = max(start + 80, int(rec[r0].get("end_ms", start + 160)))\n        span = max(80, end - start)\n        weights = [max(1, len(provided[i].get("norm") or "")) for i in same]\n        total = sum(weights)\n        cursor = start\n        consumed = 0\n        for pos, source_index in enumerate(same):\n            consumed += weights[pos]\n            next_time = end if pos == len(same) - 1 else start + int(round(span * consumed / total))\n            rows[source_index]["start_ms"] = cursor\n            rows[source_index]["end_ms"] = max(cursor + 40, next_time)\n            cursor = next_time\n\n    real_anchors = [0] + sorted(mapping)\n    for anchor_pos, left_source in enumerate(real_anchors):\n        right_source = real_anchors[anchor_pos + 1] if anchor_pos + 1 < len(real_anchors) else len(rows)\n        gap_sources = [\n            i for i in range(left_source + 1, right_source)\n            if rows[i].get("start_ms") is None\n        ]\n        if not gap_sources:\n            continue\n\n        if left_source == 0:\n            left_rec_end = -1\n            left_time = acoustic_t0\n        else:\n            left_rec_end = mapping[left_source][1]\n            left_time = int(rows[left_source].get("end_ms") or rows[left_source]["start_ms"])\n\n        if right_source < len(rows):\n            right_rec_start = mapping[right_source][0]\n            right_time = int(rows[right_source]["start_ms"])\n        else:\n            right_rec_start = len(rec)\n            right_time = max(\n                left_time + 120,\n                int(rec[-1].get("end_ms", rec[-1]["start_ms"] + 120)),\n            )\n\n        candidate_rec = [\n            k for k in range(left_rec_end + 1, right_rec_start)\n            if int(rec[k].get("start_ms", 0)) >= acoustic_t0\n        ]\n        recognized_times = [int(rec[k]["start_ms"]) for k in candidate_rec]\n\n        for pos, source_index in enumerate(gap_sources, start=1):\n            t = _r3810_curve_sample(\n                left_time,\n                right_time,\n                recognized_times,\n                pos,\n                len(gap_sources),\n            )\n            rows[source_index].update(\n                start_ms=max(acoustic_t0, t),\n                end_ms=max(acoustic_t0, t) + 120,\n                confidence=0.22,\n                language=None,\n                alignment="acoustic_resample",\n            )\n\n    rows[0]["start_ms"] = acoustic_t0\n    previous = acoustic_t0\n    for idx, row in enumerate(rows):\n        if row.get("start_ms") is None:\n            row["start_ms"] = previous\n            row["end_ms"] = previous + 120\n            row["alignment"] = "monotonic_fallback"\n        start = max(acoustic_t0, int(row["start_ms"]))\n        if idx > 0:\n            start = max(previous + 1, start)\n        row["start_ms"] = start\n        row["end_ms"] = max(start + 40, int(row.get("end_ms") or start + 120))\n        previous = start\n\n    for idx in range(len(rows) - 1):\n        next_start = int(rows[idx + 1]["start_ms"])\n        rows[idx]["end_ms"] = max(\n            int(rows[idx]["start_ms"]) + 40,\n            min(int(rows[idx]["end_ms"]), next_start),\n        )\n\n    return rows\n'
ALIGN = '\ndef align_provided_text(provided: list[dict], recognized: list[dict], first_vocal_onset_ms: int | None = None) -> list[dict]:\n    """\n    One absolute t0→tn sequence.\n\n    - source word 0 is immutable at the acoustic onset;\n    - source and Whisper words are globally aligned in monotonic order;\n    - no sections participate in timing;\n    - unmatched words inherit the variable acoustic cadence from Whisper onsets;\n    - no fixed ms/word spacing and no global timeline offset.\n    """\n    if not provided:\n        return []\n    if not recognized:\n        raise RuntimeError("Whisper returned no timed words")\n\n    acoustic_t0 = (\n        max(0, int(first_vocal_onset_ms))\n        if first_vocal_onset_ms is not None\n        else max(0, int(recognized[0]["start_ms"]))\n    )\n\n    mapping, rec = _r3810_sequential_mapping(provided, recognized, acoustic_t0)\n    rows = _r3810_apply_mapping(provided, mapping, rec, acoustic_t0)\n\n    lexical = sum(1 for row in rows if row.get("alignment") == "lexical_anchor")\n    resampled = sum(1 for row in rows if row.get("alignment") == "acoustic_resample")\n    print(\n        f"[LYRICS] Sequential timeline: trigger={acoustic_t0} ms; "\n        f"source={len(provided)}; recognized={len(rec)}; "\n        f"lexical={lexical}; acoustic_resample={resampled}",\n        flush=True,\n    )\n    return rows\n'

def patch_analyzer() -> None:
    rel = "analysis/lyrics_timeline_analysis.py"
    text = read(rel)

    for name in (
        "_r389_legacy_interpolate",
        "_r389_legacy_align",
        "_r3810_similarity",
        "_r3810_match_score",
        "_r3810_sequential_mapping",
        "_r3810_curve_sample",
        "_r3810_apply_mapping",
    ):
        text, _ = replace_function(text, name, "")

    text, ok = replace_function(text, "align_provided_text", ALIGN)
    if not ok:
        raise RuntimeError("align_provided_text() not found; no unsafe edit applied.")

    pos = text.find("def align_provided_text(")
    if pos < 0:
        raise RuntimeError("New align_provided_text() missing.")
    text = text[:pos] + HELPERS.rstrip() + "\n\n" + text[pos:]

    if "rows = align_provided_text(provided, words, vocal_onset_ms)" not in text:
        calls = list(re.finditer(
            r"(?m)^(\s*)rows\s*=\s*align_provided_text\(provided,\s*words(?:,\s*[A-Za-z_]\w*)?\)\s*$",
            text,
        ))
        if not calls:
            raise RuntimeError("Analyzer align call not found.")
        c = calls[-1]
        indent = c.group(1)
        text = text[:c.start()] + indent + "rows = align_provided_text(provided, words, vocal_onset_ms)" + text[c.end():]

    text = re.sub(
        r'(?m)^\s*if rows:\s*\n\s*print\(f"\[LYRICS\] Global lyric offset:[^\n]*\n',
        "",
        text,
        count=1,
    )

    text = text.replace(
        "'version': 'r38.9-legacy-plus-acoustic-offset'",
        "'version': 'r38.10-sequential-variable-timeline'",
    )

    old = """        'language': row.get('language'),\n    } for row in anchored_rows]"""
    new = """        'language': row.get('language'),\n        'alignment': row.get('alignment'),\n        'recognized_index': row.get('recognized_index'),\n    } for row in anchored_rows]"""
    if old in text:
        text = text.replace(old, new, 1)

    save(rel, text)

def patch_lyrics_display() -> None:
    rel = "public/assets/js/lyricslab-r37.js"
    text = read(rel)

    old = "const left=visRaw(xBeat(i)),next=i+1<beats.length?visRaw(xBeat(i+1)):left+spacing"
    new = "const left=xBeat(i),next=i+1<beats.length?xBeat(i+1):left+spacing"
    if old not in text and new not in text:
        raise RuntimeError("LyricsLab chord geometry anchor not found.")
    text = text.replace(old, new, 1)

    old_render = "track.style.transform=`translate3d(${x-visMetric(lastTime)}px,0,0)`;"
    new_render = (
        "track.style.transform='none';"
        "chordLane.style.transform=`translate3d(${x-rawMetric(lastTime)}px,0,0)`;"
        "wordLane.style.transform=`translate3d(${x-visMetric(lastTime)}px,0,0)`;"
    )
    if old_render not in text and new_render not in text:
        raise RuntimeError("LyricsLab shared transform anchor not found.")
    text = text.replace(old_render, new_render, 1)

    old_width = "track.style.width=Math.max(2600,visMetric(end)+spacing*8)+'px';"
    new_width = "track.style.width=Math.max(2600,rawMetric(end)+spacing*8,visMetric(end)+spacing*8)+'px';"
    if old_width not in text and new_width not in text:
        raise RuntimeError("LyricsLab track width anchor not found.")
    text = text.replace(old_width, new_width, 1)

    marker = "const stage=host.querySelector('[data-stage]'),zone=host.querySelector('[data-reading-zone]'),diagram=host.querySelector('[data-diagram]'),track=host.querySelector('[data-track]'),chordLane=host.querySelector('[data-chords-lane]'),wordLane=host.querySelector('[data-words-lane]');"
    addition = marker + "\nchordLane.style.willChange='transform';wordLane.style.willChange='transform';"
    if marker in text and "chordLane.style.willChange='transform'" not in text:
        text = text.replace(marker, addition, 1)

    save(rel, text)

def patch_cache_bust() -> None:
    rel = "templates/song/lyricslab.html.twig"
    text = read(rel)
    text = re.sub(
        r"lyricslab-r37\.js\?v=[^\"']+",
        "lyricslab-r37.js?v=20260928r38_10",
        text,
        count=1,
    )
    save(rel, text)

def main() -> None:
    patch_analyzer()
    patch_lyrics_display()
    patch_cache_bust()
    print(f"[OK] Backup: {BACKUP}")
    print("R38_10_INSTALL_OK")

if __name__ == "__main__":
    main()
