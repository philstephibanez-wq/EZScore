#!/usr/bin/env python3
from pathlib import Path
import re
import sys

repo = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()

def read(rel):
    p = repo / rel
    if not p.is_file():
        raise SystemExit(f"ABSENT: {p}")
    return p, p.read_text(encoding="utf-8")

def write_checked_python(path, text):
    compile(text, str(path), "exec")
    tmp = path.with_suffix(path.suffix + ".r38_6.tmp")
    tmp.write_text(text, encoding="utf-8", newline="\n")
    tmp.replace(path)

p, src = read("analysis/lyrics_timeline_analysis.py")

new_align = '''def _r386_similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    return difflib.SequenceMatcher(a=a, b=b, autojunk=False).ratio()


def _r386_first_phrase(provided: list[dict], recognized: list[dict]) -> tuple[int, int, int] | None:
    """Earliest chronological local phrase compatible with source start."""
    if not provided or not recognized:
        return None
    max_source_skip = min(3, max(0, len(provided) - 1))
    for ri in range(len(recognized)):
        for pi in range(max_source_skip + 1):
            max_len = min(6, len(provided) - pi, len(recognized) - ri)
            if max_len < 2:
                continue
            consecutive = 0
            best_run = 0
            strong = 0
            for off in range(max_len):
                sim = _r386_similarity(provided[pi + off]['norm'], recognized[ri + off]['norm'])
                if sim >= 0.80:
                    strong += 1
                    consecutive += 1
                    best_run = max(best_run, consecutive)
                else:
                    consecutive = 0
            if best_run >= 2 and strong >= min(3, max_len):
                seed = 0
                for off in range(max_len):
                    if _r386_similarity(provided[pi + off]['norm'], recognized[ri + off]['norm']) >= 0.72:
                        seed += 1
                    else:
                        break
                if seed >= 2:
                    return pi, ri, seed
    return None


def _r386_forward_candidate(provided: list[dict], recognized: list[dict], pi: int, cursor: int, lookahead: int = 18) -> int | None:
    """Find one source word only in a bounded FORWARD acoustic window."""
    if cursor >= len(recognized):
        return None
    end = min(len(recognized), cursor + lookahead)
    best = None
    best_score = 0.0
    for ri in range(cursor, end):
        sim = _r386_similarity(provided[pi]['norm'], recognized[ri]['norm'])
        if sim < 0.78:
            continue
        score = sim
        if pi + 1 < len(provided) and ri + 1 < len(recognized):
            score += 0.55 * _r386_similarity(provided[pi + 1]['norm'], recognized[ri + 1]['norm'])
        conf = float(recognized[ri].get('confidence', 0.0) or 0.0)
        score += min(0.15, max(0.0, conf) * 0.15)
        if score > best_score + 0.04:
            best_score = score
            best = ri
    return best


def _r386_interpolate_small_gaps(rows: list[dict]) -> list[dict]:
    known = [i for i, row in enumerate(rows) if row.get('start_ms') is not None]
    if not known:
        raise RuntimeError('No reliable acoustic anchor found in provided lyrics')
    for left_pos in range(len(known) - 1):
        left = known[left_pos]
        right = known[left_pos + 1]
        missing = right - left - 1
        if missing <= 0 or missing > 4:
            continue
        a = int(rows[left]['end_ms'])
        b = int(rows[right]['start_ms'])
        if b <= a or b - a > 8000:
            continue
        for n in range(1, missing + 1):
            i = left + n
            ratio = n / (missing + 1)
            t = int(round(a + (b - a) * ratio))
            rows[i].update(start_ms=t, end_ms=min(b, t + 140), confidence=0.18, language=None)
    return rows


def align_provided_text(provided: list[dict], recognized: list[dict]) -> list[dict]:
    rows = [dict(row, start_ms=None, end_ms=None, confidence=0.0, language=None) for row in provided]
    anchor = _r386_first_phrase(provided, recognized)
    if anchor is None:
        raise RuntimeError('No reliable first audible lyric phrase found')
    source_start, heard_start, seed_len = anchor

    # CRITICAL: the first acoustic phrase is written once and NEVER overwritten.
    for off in range(seed_len):
        pi = source_start + off
        ri = heard_start + off
        src = recognized[ri]
        rows[pi].update(start_ms=src['start_ms'], end_ms=src['end_ms'], confidence=src.get('confidence', 0.0), language=src.get('language'))

    cursor = heard_start + seed_len
    # There is no global matching pass after this point.
    for pi in range(source_start + seed_len, len(provided)):
        ri = _r386_forward_candidate(provided, recognized, pi, cursor)
        if ri is None:
            continue
        src = recognized[ri]
        rows[pi].update(start_ms=src['start_ms'], end_ms=src['end_ms'], confidence=src.get('confidence', 0.0), language=src.get('language'))
        cursor = ri + 1

    return _r386_interpolate_small_gaps(rows)
'''

start = src.find("def align_provided_text(")
if start < 0:
    raise SystemExit("align_provided_text() not found")
main = src.find("\ndef main() -> None:", start)
if main < 0:
    raise SystemExit("main() boundary not found")
helper_candidates = []
for needle in ("\ndef _r386_similarity(", "\ndef _find_first_audible_phrase(", "\ndef _earliest_phrase_anchor(", "\ndef _token_similarity("):
    x = src.rfind(needle, 0, start)
    if x >= 0 and start - x < 12000:
        helper_candidates.append(x + 1)
replace_start = min(helper_candidates) if helper_candidates else start
src = src[:replace_start] + new_align.rstrip() + "\n\n" + src[main + 1:]
write_checked_python(p, src)

p, twig = read("templates/song/lyricslab.html.twig")
if 'data-song-id="{{ song.id }}"' not in twig:
    marker = "data-lyricslab"
    pos = twig.find(marker)
    if pos < 0:
        raise SystemExit("data-lyricslab marker not found")
    end = pos + len(marker)
    twig = twig[:end] + '\n         data-song-id="{{ song.id }}"' + twig[end:]

supp_script = '<script src="/assets/js/lyricslab-r38-6-fix.js?v=20260928r38_6"></script>'
if supp_script not in twig:
    m = re.search(r'(<script[^>]+lyricslab-r37\.js[^>]*></script>)', twig)
    if not m:
        raise SystemExit("LyricsLab JS script marker not found")
    twig = twig[:m.end()] + "\n" + supp_script + twig[m.end():]
p.write_text(twig, encoding="utf-8", newline="\n")
print("R38_6_INSTALL_OK")
