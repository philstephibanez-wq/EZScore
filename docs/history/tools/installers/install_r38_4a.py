#!/usr/bin/env python3
from pathlib import Path
import re
import sys

repo = Path(sys.argv[1] if len(sys.argv) > 1 else '.').resolve()

def load(rel):
    p = repo / rel
    if not p.is_file():
        raise SystemExit(f'ABSENT: {p}')
    return p, p.read_text(encoding='utf-8')

def write_python_checked(path: Path, text: str):
    compile(text, str(path), 'exec')
    tmp = path.with_suffix(path.suffix + '.r38_4a.tmp')
    tmp.write_text(text, encoding='utf-8', newline='\n')
    tmp.replace(path)

# --- Analyzer -------------------------------------------------------------
p, py = load('analysis/lyrics_timeline_analysis.py')

section_fn = r'''def section_label(line: str) -> str | None:
    s = line.strip()
    if not s:
        return None

    # Sections are declarative markers: no whitelist and no implicit section.
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
pat = re.compile(r"def section_label\(line: str\) -> str \| None:\n.*?(?=\n_CHORD_TOKEN_RE=)", re.S)
if not pat.search(py):
    raise SystemExit('section_label function not found')
py = pat.sub(section_fn.rstrip() + '\n', py, count=1)

alignment = r'''def _token_similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    return difflib.SequenceMatcher(a=a, b=b, autojunk=False).ratio()


def _earliest_phrase_anchor(provided: list[dict], recognized: list[dict]) -> tuple[int, int] | None:
    # Establish the first sung phrase chronologically on the real audio clock.
    # A lone word such as "Je" is never enough evidence.
    source = [row['norm'] for row in provided]
    heard = [row['norm'] for row in recognized]
    if not source or not heard:
        return None

    max_source_prefix_skip = min(3, max(0, len(source) - 1))

    for ri in range(len(heard)):
        for pi in range(max_source_prefix_skip + 1):
            length = min(6, len(source) - pi, len(heard) - ri)
            if length < 2:
                continue

            strong = 0
            run = 0
            best_run = 0
            score = 0.0
            conf_sum = 0.0

            for off in range(length):
                sim = _token_similarity(source[pi + off], heard[ri + off])
                conf = float(recognized[ri + off].get('confidence', 0.0) or 0.0)
                conf_sum += conf
                if sim >= 0.82:
                    strong += 1
                    run += 1
                    best_run = max(best_run, run)
                    score += sim
                else:
                    run = 0
                    score += sim * 0.25

            avg_conf = conf_sum / length
            avg_score = score / length
            if best_run >= 2 and strong >= min(3, length) and avg_score >= 0.66 and avg_conf >= 0.20:
                return pi, ri

    # Conservative fallback: earliest exact two-word phrase.
    for ri in range(max(0, len(heard) - 1)):
        for pi in range(max_source_prefix_skip + 1):
            if pi + 1 >= len(source):
                continue
            if source[pi] == heard[ri] and source[pi + 1] == heard[ri + 1]:
                c1 = float(recognized[ri].get('confidence', 0.0) or 0.0)
                c2 = float(recognized[ri + 1].get('confidence', 0.0) or 0.0)
                if (c1 + c2) / 2 >= 0.15:
                    return pi, ri
    return None


def interpolate_unmatched(rows: list[dict]) -> list[dict]:
    known = [i for i, row in enumerate(rows) if row.get('start_ms') is not None]
    if not known:
        return rows

    first_known = known[0]
    # Recover only a tiny missing prefix immediately before the first real phrase.
    # Never smear words backwards through a long instrumental intro.
    if 0 < first_known <= 3:
        anchor = int(rows[first_known]['start_ms'])
        step = 190
        base = max(0, anchor - first_known * step)
        for i in range(first_known):
            start = base + i * step
            rows[i].update(start_ms=start, end_ms=min(anchor, start + 150), confidence=0.12, language=None)

    known = [i for i, row in enumerate(rows) if row.get('start_ms') is not None]
    for i, row in enumerate(rows):
        if row.get('start_ms') is not None:
            continue
        left = max((k for k in known if k < i), default=None)
        right = min((k for k in known if k > i), default=None)
        if left is None:
            continue
        if right is not None:
            left_end = int(rows[left]['end_ms'])
            right_start = int(rows[right]['start_ms'])
            ratio = (i - left) / max(1, right - left)
            t = int(round(left_end + (right_start - left_end) * ratio))
            row.update(start_ms=t, end_ms=t + 120, confidence=0.30)
        else:
            t = int(rows[left]['end_ms']) + max(80, (i - left - 1) * 180)
            row.update(start_ms=t, end_ms=t + 160, confidence=0.20)
    return rows


def align_provided_text(provided: list[dict], recognized: list[dict]) -> list[dict]:
    rows = [dict(row, start_ms=None, end_ms=None, confidence=0.0, language=None) for row in provided]
    anchor = _earliest_phrase_anchor(provided, recognized)
    if anchor is None:
        raise RuntimeError('No reliable early lyric/audio phrase anchor found')

    source_start, heard_start = anchor

    # Seed the first real phrase directly with Whisper timestamps.
    seed_len = min(6, len(provided) - source_start, len(recognized) - heard_start)
    seeded = 0
    for off in range(seed_len):
        pi = source_start + off
        ri = heard_start + off
        sim = _token_similarity(provided[pi]['norm'], recognized[ri]['norm'])
        if sim < 0.72:
            if seeded >= 2:
                break
            continue
        src = recognized[ri]
        rows[pi].update(start_ms=src['start_ms'], end_ms=src['end_ms'], confidence=src.get('confidence', 0.0), language=src.get('language'))
        seeded += 1

    # Monotonic continuation from this early anchor. Later repeated choruses can
    # no longer replace the initial alignment position.
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
            if sim < 0.82 or conf < 0.30:
                continue
            src = recognized[ri]
            rows[pi].update(start_ms=src['start_ms'], end_ms=src['end_ms'], confidence=max(0.20, conf * 0.75), language=src.get('language'))

    return interpolate_unmatched(rows)
'''

# Works both on f0b baseline and on the failed R38.4 local patch.
start_candidates = [
    py.find('def _token_similarity('),
    py.find('def _earliest_phrase_anchor('),
    py.find('def _first_acoustic_anchor('),
    py.find('def interpolate_unmatched(rows: list[dict]) -> list[dict]:'),
]
starts = [x for x in start_candidates if x >= 0]
if not starts:
    raise SystemExit('lyrics alignment region start not found')
start = min(starts)
main = py.find('\ndef main() -> None:', start)
if main < 0:
    raise SystemExit('lyrics main() boundary not found')
py = py[:start] + alignment.rstrip() + '\n\n' + py[main + 1:]
write_python_checked(p, py)

# --- Worker diagnostics ---------------------------------------------------
p, worker = load('worker_app/lyrics_worker_r37.py')

# Preserve/restore source audio for align.
if 'if mode=="align":\n        audio=paths.get("source")' not in worker:
    old = '''    audio=paths.get("lead_vocals")
    if not audio or not Path(str(audio)).is_file():
        audio=paths.get("source")
    if not audio or not Path(str(audio)).is_file():
        raise RuntimeError("lyrics_audio_source_missing")
'''
    new = '''    if mode=="align":
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
    if old not in worker:
        raise SystemExit('worker audio selection block not found')
    worker = worker.replace(old, new, 1)

if 'lyrics_output_tail=[]' not in worker:
    worker = worker.replace('    last_progress=-1\n', '    lyrics_output_tail=[]\n    last_progress=-1\n', 1)
    worker = worker.replace(
        '                if line:\n                    engine.log("[LYRICS] "+line)\n',
        '                if line:\n                    lyrics_output_tail.append(line)\n                    lyrics_output_tail=lyrics_output_tail[-12:]\n                    engine.log("[LYRICS] "+line)\n',
        1,
    )
    worker = worker.replace(
        '        rc=proc.wait()\n',
        '''        rc=proc.wait()\n\n        while True:\n            try:\n                line=outq.get_nowait()\n            except queue.Empty:\n                break\n            if line:\n                lyrics_output_tail.append(line)\n                lyrics_output_tail=lyrics_output_tail[-12:]\n                engine.log("[LYRICS] "+line)\n''',
        1,
    )
    worker = worker.replace(
        '        error=f"lyrics_python_exit_{rc}"\n',
        '        tail=" | ".join(lyrics_output_tail[-6:]).strip()\n        error=(f"lyrics_python_exit_{rc}: {tail}" if tail else f"lyrics_python_exit_{rc}")[:400]\n',
        1,
    )

write_python_checked(p, worker)
print('R38_4A_INSTALL_OK')
