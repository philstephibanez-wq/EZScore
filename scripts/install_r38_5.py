#!/usr/bin/env python3
from pathlib import Path
import sys

repo = Path(sys.argv[1] if len(sys.argv) > 1 else '.').resolve()

def load(rel):
    p = repo / rel
    if not p.is_file():
        raise SystemExit(f'ABSENT: {p}')
    return p, p.read_text(encoding='utf-8')

def write_python_checked(path: Path, text: str):
    compile(text, str(path), 'exec')
    tmp = path.with_suffix(path.suffix + '.r38_5.tmp')
    tmp.write_text(text, encoding='utf-8', newline='\n')
    tmp.replace(path)

p, py = load('analysis/lyrics_timeline_analysis.py')

section_fn = r'''def section_label(line: str) -> str | None:
    s = line.strip()
    if not s:
        return None

    m = re.fullmatch(r'\[([^\[\]\r\n]{1,120})\]', s)
    if m:
        label = m.group(1).strip()
        return label or None

    m = re.fullmatch(r'([^\r\n:]{1,120}):', s)
    if m:
        label = m.group(1).strip()
        return label or None

    return None
'''

s0 = py.find('def section_label(line: str) -> str | None:')
s1 = py.find('_CHORD_TOKEN_RE=', s0)
if s0 < 0 or s1 < 0:
    raise SystemExit('section parser boundaries not found')
py = py[:s0] + section_fn.rstrip() + '\n\n' + py[s1:]

alignment = r'''def _token_similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    return difflib.SequenceMatcher(a=a, b=b, autojunk=False).ratio()


def _find_first_audible_phrase(provided: list[dict], recognized: list[dict]) -> tuple[int, int] | None:
    source = [row['norm'] for row in provided]
    heard = [row['norm'] for row in recognized]
    if not source or not heard:
        return None

    max_source_skip = min(3, max(0, len(source) - 1))

    for ri in range(len(heard)):
        rconf = float(recognized[ri].get('confidence', 0.0) or 0.0)
        if rconf < 0.05:
            continue
        for pi in range(max_source_skip + 1):
            available = min(7, len(source) - pi, len(heard) - ri)
            if available < 2:
                continue
            strong = 0
            consecutive = 0
            best_run = 0
            weighted = 0.0
            conf_sum = 0.0
            for off in range(available):
                sim = _token_similarity(source[pi + off], heard[ri + off])
                conf = float(recognized[ri + off].get('confidence', 0.0) or 0.0)
                conf_sum += conf
                if sim >= 0.80:
                    strong += 1
                    consecutive += 1
                    best_run = max(best_run, consecutive)
                    weighted += sim
                else:
                    consecutive = 0
                    weighted += sim * 0.20
            avg_conf = conf_sum / available
            avg_score = weighted / available
            if best_run >= 2 and strong >= min(3, available) and avg_score >= 0.62 and avg_conf >= 0.15:
                return pi, ri

    for ri in range(max(0, len(heard) - 1)):
        for pi in range(max_source_skip + 1):
            if pi + 1 >= len(source):
                continue
            if source[pi] == heard[ri] and source[pi + 1] == heard[ri + 1]:
                return pi, ri
    return None


def _seed_first_phrase(rows: list[dict], provided: list[dict], recognized: list[dict], source_start: int, heard_start: int) -> None:
    limit = min(8, len(provided) - source_start, len(recognized) - heard_start)
    seeded = 0
    for off in range(limit):
        pi = source_start + off
        ri = heard_start + off
        sim = _token_similarity(provided[pi]['norm'], recognized[ri]['norm'])
        if sim < 0.68:
            if seeded >= 2:
                break
            continue
        src = recognized[ri]
        rows[pi].update(start_ms=src['start_ms'], end_ms=src['end_ms'], confidence=src.get('confidence', 0.0), language=src.get('language'))
        seeded += 1


def interpolate_unmatched(rows: list[dict]) -> list[dict]:
    known = [i for i, row in enumerate(rows) if row.get('start_ms') is not None]
    if not known:
        return rows
    first_known = known[0]
    if 0 < first_known <= 3:
        anchor = int(rows[first_known]['start_ms'])
        step = 180
        base = max(0, anchor - first_known * step)
        for i in range(first_known):
            start = base + i * step
            rows[i].update(start_ms=start, end_ms=min(anchor, start + 145), confidence=0.10, language=None)
    known = [i for i, row in enumerate(rows) if row.get('start_ms') is not None]
    for i, row in enumerate(rows):
        if row.get('start_ms') is not None:
            continue
        left = max((k for k in known if k < i), default=None)
        right = min((k for k in known if k > i), default=None)
        if left is None:
            continue
        if right is not None:
            a = int(rows[left]['end_ms'])
            b = int(rows[right]['start_ms'])
            ratio = (i - left) / max(1, right - left)
            t = int(round(a + (b - a) * ratio))
            row.update(start_ms=t, end_ms=t + 120, confidence=0.25)
        else:
            t = int(rows[left]['end_ms']) + max(80, (i - left - 1) * 180)
            row.update(start_ms=t, end_ms=t + 150, confidence=0.18)
    return rows


def align_provided_text(provided: list[dict], recognized: list[dict]) -> list[dict]:
    rows = [dict(row, start_ms=None, end_ms=None, confidence=0.0, language=None) for row in provided]
    anchor = _find_first_audible_phrase(provided, recognized)
    if anchor is None:
        raise RuntimeError('No reliable first audible lyric phrase found')
    source_start, heard_start = anchor
    _seed_first_phrase(rows, provided, recognized, source_start, heard_start)
    a = [row['norm'] for row in provided[source_start:]]
    b = [row['norm'] for row in recognized[heard_start:]]
    matcher = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        ai = source_start + i1
        bj = heard_start + j1
        if tag == 'equal':
            for off in range(i2 - i1):
                pi = ai + off
                ri = bj + off
                src = recognized[ri]
                rows[pi].update(start_ms=src['start_ms'], end_ms=src['end_ms'], confidence=src.get('confidence', 0.0), language=src.get('language'))
            continue
        if tag != 'replace':
            continue
        n = min(i2 - i1, j2 - j1)
        for off in range(n):
            pi = ai + off
            ri = bj + off
            sim = _token_similarity(provided[pi]['norm'], recognized[ri]['norm'])
            conf = float(recognized[ri].get('confidence', 0.0) or 0.0)
            if sim < 0.82 or conf < 0.25:
                continue
            src = recognized[ri]
            rows[pi].update(start_ms=src['start_ms'], end_ms=src['end_ms'], confidence=max(0.15, conf * 0.75), language=src.get('language'))
    return interpolate_unmatched(rows)
'''

candidates = [
    py.find('def _token_similarity('),
    py.find('def _earliest_phrase_anchor('),
    py.find('def _first_acoustic_anchor('),
    py.find('def _find_first_audible_phrase('),
    py.find('def interpolate_unmatched(rows: list[dict]) -> list[dict]:'),
]
starts = [x for x in candidates if x >= 0]
if not starts:
    raise SystemExit('alignment region start not found')
a0 = min(starts)
a1 = py.find('\ndef main() -> None:', a0)
if a1 < 0:
    raise SystemExit('main() boundary not found')
py = py[:a0] + alignment.rstrip() + '\n\n' + py[a1+1:]
write_python_checked(p, py)

p, worker = load('worker_app/lyrics_worker_r37.py')
old_audio = '''    audio=paths.get("lead_vocals")
    if not audio or not Path(str(audio)).is_file():
        audio=paths.get("source")
    if not audio or not Path(str(audio)).is_file():
        raise RuntimeError("lyrics_audio_source_missing")
'''
new_audio = '''    if mode=="align":
        audio=paths.get("source")
        audio_kind="source"
    else:
        audio=paths.get("lead_vocals")
        audio_kind="lead_vocals"
        if not audio or not Path(str(audio)).is_file():
            audio=paths.get("source")
            audio_kind="source"
    if not audio or not Path(str(audio)).is_file():
        raise RuntimeError("lyrics_audio_source_missing")
    engine.log(f"Audio Lyrics ({mode}): {audio_kind} -> {audio}")
'''
if old_audio in worker:
    worker = worker.replace(old_audio, new_audio, 1)
write_python_checked(p, worker)

print('R38_5_INSTALL_OK')
