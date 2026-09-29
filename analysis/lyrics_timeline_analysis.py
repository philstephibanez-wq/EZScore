#!/usr/bin/env python3
from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import time
import unicodedata
from pathlib import Path

SAMPLE_RATE = 16000
CHUNK_SECONDS = 26.0
OVERLAP_SECONDS = 2.0

def write_json(path: str | Path, payload: dict) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(payload, ensure_ascii=False)

    import tempfile
    fd, tmp_name = tempfile.mkstemp(
        prefix=p.name + '.',
        suffix='.tmp',
        dir=str(p.parent),
        text=True,
    )
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='') as handle:
            handle.write(data)
            handle.flush()
            try:
                os.fsync(handle.fileno())
            except OSError:
                pass

        last_error = None
        for attempt in range(20):
            try:
                os.replace(tmp, p)
                return
            except PermissionError as exc:
                last_error = exc
                time.sleep(0.025 * (attempt + 1))

        try:
            p.write_text(data, encoding='utf-8')
            return
        except Exception:
            if last_error is not None:
                raise last_error
            raise
    finally:
        tmp.unlink(missing_ok=True)

def progress(path: str | None, percent: int, stage: str, message: str, **extra) -> None:
    if not path:
        return
    payload = {
        'percent': max(0, min(100, int(percent))),
        'stage': stage,
        'message': message,
        'updated_at': time.time(),
    }
    payload.update(extra)
    write_json(path, payload)

def normalise_token(value: str) -> str:
    value = unicodedata.normalize('NFKD', value.lower())
    value = ''.join(c for c in value if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9'’-]+", '', value)

def normalise_section_type(label: str) -> str:
    value=unicodedata.normalize('NFKD',label.lower())
    value=''.join(c for c in value if not unicodedata.combining(c))
    value=re.sub(r'\s+\d+\s*$','',value).strip()
    aliases={'intro':'intro','introduction':'intro','couplet':'verse','verse':'verse','refrain':'chorus','chorus':'chorus','pont':'bridge','bridge':'bridge','pre-refrain':'prechorus','pre chorus':'prechorus','prechorus':'prechorus','instrumental':'instrumental','solo':'solo','final':'final','outro':'outro','coda':'coda'}
    return aliases.get(value,'section')

def section_label(line: str) -> str | None:
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

_CHORD_TOKEN_RE=re.compile(r'^(?:[A-G](?:#|b|♭)?(?:maj|min|m|dim|aug|sus|add|M)?(?:\d{0,2})?(?:\([^)]*\))?(?:/[A-G](?:#|b|♭)?)?|[._|-]|\([xX0-9]{4,8}\))$')

def is_chord_line(line: str) -> bool:
    tokens=re.findall(r'\S+',line.strip())
    if not tokens:
        return False
    ok=0
    musical=0
    for token in tokens:
        c=token.strip().strip('|')
        if not c:
            ok+=1
            continue
        if _CHORD_TOKEN_RE.fullmatch(c):
            ok+=1
            if re.match(r'^[A-G]',c):
                musical+=1
    return musical>0 and ok/max(1,len(tokens))>=0.72

def source_tokens(text: str) -> list[dict]:
    rows=[]
    current_section=None
    current_section_type=None
    for line in text.replace('\r\n','\n').replace('\r','\n').split('\n'):
        label=section_label(line)
        if label is not None:
            current_section=label
            current_section_type=normalise_section_type(label)
            continue
        if is_chord_line(line):
            continue
        raw_words=re.findall(r'\S+',line)
        words=[]
        leading_punctuation=''
        for token in raw_words:
            token_norm=normalise_token(token)
            if token_norm:
                if leading_punctuation:
                    token=leading_punctuation+token
                    leading_punctuation=''
                words.append(token)
            elif words:
                # Editorial punctuation stays attached to the preceding word.
                words[-1]+=token
            else:
                leading_punctuation+=token
        if leading_punctuation and words:
            words[-1]+=leading_punctuation
        for i,word in enumerate(words):
            rows.append({
                'text':word,
                'norm':normalise_token(word),
                'line_break_after':i==len(words)-1,
                'section_label':current_section,
                'section_type':current_section_type,
            })
    if rows:
        rows[-1]['line_break_after']=False
    return rows

def choose_model_path() -> str:
    explicit = os.environ.get('EZSCORE_WHISPER_MODEL')
    if explicit and Path(explicit).is_file():
        return explicit

    # Accuracy first. Turbo is intentionally not preferred for LyricsLab extraction.
    candidates = [
        r'H:\EZScoreModels\whisper\large-v3.pt',
        r'H:\EZScoreModels\whisper\large-v3-turbo.pt',
        r'H:\EZScoreModels\whisper\medium.pt',
        r'H:\EZScoreModels\whisper\small.pt',
    ]
    for candidate in candidates:
        if Path(candidate).is_file():
            return candidate
    raise RuntimeError(
        'No Whisper model found. Install large-v3 at '
        r'H:\EZScoreModels\whisper\large-v3.pt or set EZSCORE_WHISPER_MODEL.'
    )

def dedupe_words(words: list[dict]) -> list[dict]:
    words.sort(key=lambda row: (row['start_ms'], row['end_ms']))
    out: list[dict] = []
    for row in words:
        if out:
            prev = out[-1]
            same = row['norm'] and row['norm'] == prev['norm']
            close = abs(row['start_ms'] - prev['start_ms']) <= 900
            overlap = row['start_ms'] <= prev['end_ms'] + 250
            if same and close and overlap:
                if row.get('confidence', 0) > prev.get('confidence', 0):
                    out[-1] = row
                continue
        out.append(row)
    return out

def transcribe_multilingual(model, audio_path: str, progress_file: str | None) -> tuple[list[dict], list[dict]]:
    import whisper

    audio = whisper.load_audio(audio_path)
    total_samples = len(audio)
    if total_samples == 0:
        raise RuntimeError('Audio is empty')

    chunk_samples = int(CHUNK_SECONDS * SAMPLE_RATE)
    overlap_samples = int(OVERLAP_SECONDS * SAMPLE_RATE)
    step = max(1, chunk_samples - overlap_samples)

    words: list[dict] = []
    segments: list[dict] = []
    starts = list(range(0, total_samples, step))
    count = len(starts)

    for index, start_sample in enumerate(starts):
        end_sample = min(total_samples, start_sample + chunk_samples)
        chunk = audio[start_sample:end_sample]
        if len(chunk) < SAMPLE_RATE // 2:
            continue

        pct = 20 + int(55 * (index / max(1, count)))
        progress(
            progress_file,
            pct,
            'transcribe',
            f'Transcription multilingue {index + 1}/{count}',
        )

        # language=None => language detection is repeated for every chunk.
        # This materially improves songs containing language switches.
        result = model.transcribe(
            chunk,
            language=None,
            task='transcribe',
            fp16=True,
            word_timestamps=True,
            condition_on_previous_text=False,
            verbose=False,
            temperature=0.0,
        )
        language = str(result.get('language') or 'und')
        offset_s = start_sample / SAMPLE_RATE
        keep_after_s = offset_s if index == 0 else offset_s + OVERLAP_SECONDS * 0.55

        for segment in result.get('segments', []) or []:
            seg_start = offset_s + float(segment.get('start', 0))
            seg_end = offset_s + float(segment.get('end', segment.get('start', 0)))
            midpoint = (seg_start + seg_end) / 2
            if index > 0 and midpoint < keep_after_s:
                continue
            text = str(segment.get('text', '')).strip()
            if text:
                segments.append({
                    'text': text,
                    'start_ms': int(round(seg_start * 1000)),
                    'end_ms': int(round(seg_end * 1000)),
                    'language': language,
                })

            for word in segment.get('words', []) or []:
                text = str(word.get('word', '')).strip()
                if not text:
                    continue
                word_start_s = offset_s + float(word.get('start', segment.get('start', 0)))
                word_end_s = offset_s + float(word.get('end', word.get('start', segment.get('end', 0))))
                if index > 0 and word_end_s < keep_after_s:
                    continue
                words.append({
                    'text': text,
                    'norm': normalise_token(text),
                    'start_ms': int(round(word_start_s * 1000)),
                    'end_ms': int(round(word_end_s * 1000)),
                    'confidence': float(word.get('probability', 0.0) or 0.0),
                    'language': language,
                })

    words = dedupe_words(words)
    segments.sort(key=lambda row: row['start_ms'])
    return words, segments

def extracted_text(segments: list[dict]) -> str:
    # Keep phrase boundaries from Whisper segments. The user remains free to edit.
    rows = []
    previous_language = None
    for segment in segments:
        text = segment['text'].strip()
        if not text:
            continue
        language = segment.get('language') or 'und'
        # Do not add language tags into the lyrics text. We only preserve natural lines.
        if rows and language != previous_language and previous_language is not None:
            rows.append('')
        rows.append(text)
        previous_language = language
    return '\n'.join(rows).strip()

def _r386_similarity(a: str, b: str) -> float:
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


def detect_first_vocal_onset(audio_path: str | None) -> tuple[int | None, dict]:
    if not audio_path or not Path(audio_path).is_file():
        return None, {"method": "unavailable", "found": False}
    import numpy as np
    import whisper
    audio = whisper.load_audio(audio_path)
    if audio is None or len(audio) < SAMPLE_RATE // 4:
        return None, {"method": "empty", "found": False}
    frame = max(1, int(SAMPLE_RATE * 0.030))
    hop = max(1, int(SAMPLE_RATE * 0.010))
    if len(audio) < frame:
        return None, {"method": "too_short", "found": False}
    sq = np.asarray(audio, dtype=np.float32) ** 2
    kernel = np.ones(frame, dtype=np.float32) / float(frame)
    rms = np.sqrt(np.convolve(sq, kernel, mode="valid")[::hop] + 1e-12)
    db = 20.0 * np.log10(rms + 1e-9)
    p20 = float(np.percentile(db, 20))
    p90 = float(np.percentile(db, 90))
    spread = max(6.0, p90 - p20)
    threshold = min(p90 - 5.0, p20 + max(10.0, spread * 0.38))
    active = db >= threshold
    win = max(1, int(round(0.180 / (hop / SAMPLE_RATE))))
    need = max(1, int(round(0.120 / (hop / SAMPLE_RATE))))
    counts = np.convolve(active.astype(np.int16), np.ones(win, dtype=np.int16), mode="same")
    candidates = np.flatnonzero(counts >= need)
    if candidates.size == 0:
        return None, {"method":"rms_sustained","found":False,"threshold_db":round(threshold,2)}
    idx = int(candidates[0])
    shoulder = threshold - 6.0
    while idx > 0 and db[idx - 1] >= shoulder:
        idx -= 1
    onset_ms = max(0, int(round((idx * hop) * 1000.0 / SAMPLE_RATE)))
    return onset_ms, {"method":"rms_sustained","found":True,"threshold_db":round(threshold,2)}

def _r388_similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    return difflib.SequenceMatcher(a=a,b=b,autojunk=False).ratio()

def _r388_fill_unmatched(rows: list[dict]) -> list[dict]:
    known=[i for i,r in enumerate(rows) if r.get("start_ms") is not None]
    if not known:
        raise RuntimeError("No acoustic anchor available")
    for i,row in enumerate(rows):
        if row.get("start_ms") is not None:
            continue
        left=max((k for k in known if k<i),default=None)
        right=min((k for k in known if k>i),default=None)
        if left is None:
            continue
        if right is not None:
            a=int(rows[left]["end_ms"]); b=int(rows[right]["start_ms"])
            ratio=(i-left)/max(1,right-left)
            t=int(round(a+(b-a)*ratio))
            t=max(a,min(b,t))
            row.update(start_ms=t,end_ms=max(t+40,min(b,t+140)),confidence=0.30)
        else:
            t=int(rows[left]["end_ms"])+max(80,(i-left-1)*180)
            row.update(start_ms=t,end_ms=t+160,confidence=0.20)
    return rows









def _r3810_similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    return difflib.SequenceMatcher(a=a, b=b, autojunk=False).ratio()


def _r3810_match_score(source_norm: str, recognized_norm: str, confidence: float, source_pos: float, recognized_pos: float) -> float:
    sim = _r3810_similarity(source_norm, recognized_norm)
    if sim >= 0.999:
        lexical = 6.0
    elif sim >= 0.90:
        lexical = 5.0
    elif sim >= 0.78:
        lexical = 3.2
    elif sim >= 0.64:
        lexical = 1.2
    else:
        lexical = -3.0
    positional_penalty = abs(source_pos - recognized_pos) * 2.0
    confidence_bonus = max(0.0, min(1.0, float(confidence or 0.0))) * 0.55
    return lexical + confidence_bonus - positional_penalty


def _r3810_sequential_mapping(provided: list[dict], recognized: list[dict], acoustic_t0: int) -> tuple[dict[int, tuple[int, int]], list[dict]]:
    rec = [
        row for row in recognized
        if int(row.get("end_ms", row.get("start_ms", 0)) or 0) >= acoustic_t0 - 250
    ]
    if not rec:
        raise RuntimeError("No recognized vocal words at or after acoustic T0")

    src = provided[1:]
    n = len(src)
    m = len(rec)
    if n == 0:
        return {}, rec

    neg = -10**15
    dp = [[neg] * (m + 1) for _ in range(n + 1)]
    back: list[list[tuple[int, int, str] | None]] = [[None] * (m + 1) for _ in range(n + 1)]
    dp[0][0] = 0.0
    SOURCE_GAP = -1.35
    RECOGNIZED_GAP = -1.05

    for i in range(n + 1):
        for j in range(m + 1):
            current = dp[i][j]
            if current <= neg / 2:
                continue

            if i < n:
                cand = current + SOURCE_GAP
                if cand > dp[i + 1][j]:
                    dp[i + 1][j] = cand
                    back[i + 1][j] = (i, j, "skip_source")

            if j < m:
                cand = current + RECOGNIZED_GAP
                if cand > dp[i][j + 1]:
                    dp[i][j + 1] = cand
                    back[i][j + 1] = (i, j, "skip_recognized")

            if i < n and j < m:
                source_pos = (i + 1) / max(1, n)
                recognized_pos = (j + 1) / max(1, m)
                score = _r3810_match_score(
                    src[i].get("norm") or "",
                    rec[j].get("norm") or "",
                    float(rec[j].get("confidence", 0.0) or 0.0),
                    source_pos,
                    recognized_pos,
                )
                cand = current + score
                if cand > dp[i + 1][j + 1]:
                    dp[i + 1][j + 1] = cand
                    back[i + 1][j + 1] = (i, j, "match11")

            if i + 1 < n and j < m:
                joined_source = (src[i].get("norm") or "") + (src[i + 1].get("norm") or "")
                sim = _r3810_similarity(joined_source, rec[j].get("norm") or "")
                if sim >= 0.72:
                    source_pos = (i + 1.5) / max(1, n)
                    recognized_pos = (j + 1) / max(1, m)
                    score = 4.8 * sim + min(0.5, float(rec[j].get("confidence", 0.0) or 0.0) * 0.5)
                    score -= abs(source_pos - recognized_pos) * 2.0
                    cand = current + score
                    if cand > dp[i + 2][j + 1]:
                        dp[i + 2][j + 1] = cand
                        back[i + 2][j + 1] = (i, j, "match21")

            if i < n and j + 1 < m:
                joined_rec = (rec[j].get("norm") or "") + (rec[j + 1].get("norm") or "")
                sim = _r3810_similarity(src[i].get("norm") or "", joined_rec)
                if sim >= 0.72:
                    source_pos = (i + 1) / max(1, n)
                    recognized_pos = (j + 1.5) / max(1, m)
                    conf = (
                        float(rec[j].get("confidence", 0.0) or 0.0)
                        + float(rec[j + 1].get("confidence", 0.0) or 0.0)
                    ) / 2.0
                    score = 4.8 * sim + min(0.5, conf * 0.5)
                    score -= abs(source_pos - recognized_pos) * 2.0
                    cand = current + score
                    if cand > dp[i + 1][j + 2]:
                        dp[i + 1][j + 2] = cand
                        back[i + 1][j + 2] = (i, j, "match12")

    i, j = n, m
    operations: list[tuple[int, int, int, int, str]] = []
    while i > 0 or j > 0:
        step = back[i][j]
        if step is None:
            raise RuntimeError(f"Sequential alignment traceback failed at source={i}, recognized={j}")
        pi, pj, op = step
        operations.append((pi, pj, i, j, op))
        i, j = pi, pj
    operations.reverse()

    mapping: dict[int, tuple[int, int]] = {}
    for pi, pj, ni, nj, op in operations:
        if op == "match11":
            mapping[pi + 1] = (pj, pj)
        elif op == "match21":
            mapping[pi + 1] = (pj, pj)
            mapping[pi + 2] = (pj, pj)
        elif op == "match12":
            mapping[pi + 1] = (pj, pj + 1)

    return mapping, rec


# R38.13 syllabic vocal timeline.
# Orthographic French syllables + local Whisper cadence. This is not yet phoneme recognition.
_R3813_VOWELS = set("aeiouyàâäéèêëîïôöùûüÿœæ")

def _r3813_letters(text: str) -> str:
    return "".join(ch for ch in str(text or "").lower() if ch.isalpha() or ch in "'’")

def _r3813_syllabify_french(text: str) -> list[str]:
    raw = _r3813_letters(text)
    if not raw:
        return []
    raw = raw.replace("'", "").replace("’", "")
    nuclei: list[tuple[int, int]] = []
    i = 0
    while i < len(raw):
        if raw[i] not in _R3813_VOWELS:
            i += 1
            continue
        j = i + 1
        while j < len(raw) and raw[j] in _R3813_VOWELS:
            j += 1
        nuclei.append((i, j))
        i = j
    if not nuclei:
        return [raw]
    if len(nuclei) > 1:
        a, b = nuclei[-1]
        if raw[a:b] == "e" and b == len(raw):
            nuclei.pop()
    if len(nuclei) <= 1:
        return [raw]
    boundaries = [0]
    common = {"ch", "ph", "th", "gn", "tr", "dr", "cr", "gr", "fr", "vr", "pl", "bl", "cl", "gl", "fl"}
    for idx in range(len(nuclei) - 1):
        _a, left_end = nuclei[idx]
        right_start, _b = nuclei[idx + 1]
        consonants = raw[left_end:right_start]
        if len(consonants) <= 1:
            cut = right_start
        else:
            keep = 2 if consonants[-2:] in common else 1
            cut = max(left_end, right_start - keep)
        boundaries.append(cut)
    boundaries.append(len(raw))
    result = [raw[boundaries[k]:boundaries[k + 1]] for k in range(len(boundaries) - 1)]
    return [s for s in result if s] or [raw]

def _r3813_syllable_count(text: str) -> int:
    return max(1, len(_r3813_syllabify_french(text)))

def _r3813_attach_syllables(rows: list[dict], acoustic_t0: int) -> list[dict]:
    previous_start = acoustic_t0 - 1
    for word_index, row in enumerate(rows):
        syllables = _r3813_syllabify_french(row.get("text") or "")
        if not syllables:
            row["syllables"] = []
            continue
        word_start = max(acoustic_t0, int(row.get("start_ms") or acoustic_t0))
        word_end = max(word_start + max(60, 45 * len(syllables)), int(row.get("end_ms") or word_start + 120))
        duration = max(len(syllables), word_end - word_start)
        weights = [max(1, len(s)) for s in syllables]
        total = sum(weights)
        cursor = word_start
        consumed = 0
        items = []
        for syllable_index, (syl, weight) in enumerate(zip(syllables, weights)):
            consumed += weight
            end = word_end if syllable_index == len(syllables) - 1 else word_start + int(round(duration * consumed / total))
            start = max(cursor, acoustic_t0 if word_index == 0 and syllable_index == 0 else previous_start + 1)
            end = max(start + 1, end)
            nucleus = start + (end - start) // 2
            items.append({
                "text": syl,
                "syllable_index": syllable_index,
                "start_ms": start,
                "nucleus_ms": min(end, max(start, nucleus)),
                "end_ms": end,
                "confidence": round(float(row.get("confidence", 0.0) or 0.0), 4),
                "alignment": row.get("alignment"),
                "nucleus_method": "interval_center",
            })
            previous_start = start
            cursor = end
        row["syllables"] = items
        row["start_ms"] = items[0]["start_ms"]
        row["end_ms"] = items[-1]["end_ms"]
    return rows

def _r3810_curve_sample(left_time: int, right_time: int, recognized_times: list[int], position: int, count: int) -> int:
    if count <= 0:
        return left_time
    controls: list[tuple[float, float]] = [(0.0, float(left_time))]
    q = len(recognized_times)
    for idx, value in enumerate(recognized_times):
        controls.append(((idx + 1) / (q + 1), float(value)))
    controls.append((1.0, float(right_time)))
    x = position / (count + 1)
    for idx in range(1, len(controls)):
        x1, y1 = controls[idx]
        x0, y0 = controls[idx - 1]
        if x <= x1:
            if x1 <= x0:
                return int(round(y1))
            p = (x - x0) / (x1 - x0)
            return int(round(y0 + (y1 - y0) * p))
    return int(round(right_time))


def _r3810_apply_mapping(provided: list[dict], mapping: dict[int, tuple[int, int]], rec: list[dict], acoustic_t0: int) -> list[dict]:
    rows = [
        dict(row, start_ms=None, end_ms=None, confidence=0.0, language=None)
        for row in provided
    ]
    rows[0].update(
        start_ms=acoustic_t0,
        end_ms=acoustic_t0 + 160,
        confidence=1.0,
        language=None,
        alignment="acoustic_trigger",
    )

    grouped: dict[int, list[int]] = {}
    for source_index, (r0, r1) in mapping.items():
        grouped.setdefault(r0, []).append(source_index)
        start = max(acoustic_t0, int(rec[r0]["start_ms"]))
        end = max(start + 60, int(rec[r1].get("end_ms", start + 120)))
        conf = min(
            float(rec[k].get("confidence", 0.0) or 0.0)
            for k in range(r0, r1 + 1)
        )
        rows[source_index].update(
            start_ms=start,
            end_ms=end,
            confidence=conf,
            language=rec[r0].get("language"),
            recognized_index=r0,
            alignment="lexical_anchor",
        )

    for r0, source_indexes in grouped.items():
        same = sorted(i for i in source_indexes if mapping[i] == (r0, r0))
        if len(same) < 2:
            continue
        start = max(acoustic_t0, int(rec[r0]["start_ms"]))
        end = max(start + 80, int(rec[r0].get("end_ms", start + 160)))
        span = max(80, end - start)
        weights = [max(1, len(provided[i].get("norm") or "")) for i in same]
        total = sum(weights)
        cursor = start
        consumed = 0
        for pos, source_index in enumerate(same):
            consumed += weights[pos]
            next_time = end if pos == len(same) - 1 else start + int(round(span * consumed / total))
            rows[source_index]["start_ms"] = cursor
            rows[source_index]["end_ms"] = max(cursor + 40, next_time)
            cursor = next_time

    real_anchors = [0] + sorted(mapping)
    for anchor_pos, left_source in enumerate(real_anchors):
        right_source = real_anchors[anchor_pos + 1] if anchor_pos + 1 < len(real_anchors) else len(rows)
        gap_sources = [
            i for i in range(left_source + 1, right_source)
            if rows[i].get("start_ms") is None
        ]
        if not gap_sources:
            continue

        if left_source == 0:
            left_rec_end = -1
            left_time = acoustic_t0
        else:
            left_rec_end = mapping[left_source][1]
            left_time = int(rows[left_source].get("end_ms") or rows[left_source]["start_ms"])

        if right_source < len(rows):
            right_rec_start = mapping[right_source][0]
            right_time = int(rows[right_source]["start_ms"])
        else:
            right_rec_start = len(rec)
            right_time = max(
                left_time + 120,
                int(rec[-1].get("end_ms", rec[-1]["start_ms"] + 120)),
            )

        candidate_rec = [
            k for k in range(left_rec_end + 1, right_rec_start)
            if int(rec[k].get("start_ms", 0)) >= acoustic_t0
        ]
        recognized_times = [int(rec[k]["start_ms"]) for k in candidate_rec]

        total_syllables = sum(
            _r3813_syllable_count(provided[i].get("text") or "")
            for i in gap_sources
        )
        syllable_offset = 0
        for source_index in gap_sources:
            syllable_count = _r3813_syllable_count(provided[source_index].get("text") or "")
            start_position = syllable_offset + 1
            end_position = min(max(1, total_syllables), syllable_offset + syllable_count + 1)
            t = _r3810_curve_sample(
                left_time,
                right_time,
                recognized_times,
                start_position,
                max(1, total_syllables),
            )
            t2 = _r3810_curve_sample(
                left_time,
                right_time,
                recognized_times,
                end_position,
                max(1, total_syllables),
            )
            rows[source_index].update(
                start_ms=max(acoustic_t0, t),
                end_ms=max(max(acoustic_t0, t) + 60, t2),
                confidence=0.22,
                language=None,
                alignment="syllabic_acoustic_resample",
            )
            syllable_offset += syllable_count

    rows[0]["start_ms"] = acoustic_t0
    previous = acoustic_t0
    for idx, row in enumerate(rows):
        if row.get("start_ms") is None:
            row["start_ms"] = previous
            row["end_ms"] = previous + 120
            row["alignment"] = "monotonic_fallback"
        start = max(acoustic_t0, int(row["start_ms"]))
        if idx > 0:
            start = max(previous + 1, start)
        row["start_ms"] = start
        row["end_ms"] = max(start + 40, int(row.get("end_ms") or start + 120))
        previous = start

    for idx in range(len(rows) - 1):
        next_start = int(rows[idx + 1]["start_ms"])
        rows[idx]["end_ms"] = max(
            int(rows[idx]["start_ms"]) + 40,
            min(int(rows[idx]["end_ms"]), next_start),
        )

    return rows

def align_provided_text(provided: list[dict], recognized: list[dict], first_vocal_onset_ms: int | None = None) -> list[dict]:
    """
    One absolute t0→tn sequence.

    - source word 0 is immutable at the acoustic onset;
    - source and Whisper words are globally aligned in monotonic order;
    - no sections participate in timing;
    - unmatched words inherit the variable acoustic cadence from Whisper onsets;
    - no fixed ms/word spacing and no global timeline offset.
    """
    if not provided:
        return []
    if not recognized:
        raise RuntimeError("Whisper returned no timed words")

    acoustic_t0 = (
        max(0, int(first_vocal_onset_ms))
        if first_vocal_onset_ms is not None
        else max(0, int(recognized[0]["start_ms"]))
    )

    mapping, rec = _r3810_sequential_mapping(provided, recognized, acoustic_t0)
    rows = _r3810_apply_mapping(provided, mapping, rec, acoustic_t0)

    rows = _r3813_attach_syllables(rows, acoustic_t0)
    lexical = sum(1 for row in rows if row.get("alignment") == "lexical_anchor")
    resampled = sum(1 for row in rows if row.get("alignment") in {"acoustic_resample", "syllabic_acoustic_resample"})
    print(
        f"[LYRICS] Sequential timeline: trigger={acoustic_t0} ms; "
        f"source={len(provided)}; recognized={len(rec)}; "
        f"lexical={lexical}; acoustic_resample={resampled}",
        flush=True,
    )
    return rows

# R38.17A acoustic syllabic alignment correction
# Vocal timeline only. Harmonic beat/chord timestamps are not modified.

def _r3817a_median(values, fallback):
    xs = sorted(float(v) for v in values if v is not None)
    return xs[len(xs)//2] if xs else float(fallback)


def _r3817a_cadence_ms(recognized):
    starts = [int(r.get("start_ms", 0) or 0) for r in recognized]
    diffs = [b-a for a,b in zip(starts, starts[1:]) if 90 <= b-a <= 1800]
    return max(220.0, min(950.0, _r3817a_median(diffs, 480.0)))


def _r3810_sequential_mapping(provided, recognized, acoustic_t0):
    # IMPORTANT R38.17A:
    # all source words participate. The old code used provided[1:] and therefore
    # forced source word 0 to the RMS trigger even when that trigger was not speech.
    rec = [
        row for row in recognized
        if int(row.get("end_ms", row.get("start_ms", 0)) or 0) >= acoustic_t0 - 350
    ]
    if not rec:
        raise RuntimeError("No recognized vocal words at or after acoustic lower bound")

    src = provided
    n, m = len(src), len(rec)
    if n == 0:
        return {}, rec

    neg = -10**15
    dp = [[neg] * (m + 1) for _ in range(n + 1)]
    back = [[None] * (m + 1) for _ in range(n + 1)]
    dp[0][0] = 0.0
    SOURCE_GAP = -1.35
    RECOGNIZED_GAP = -1.05

    for i in range(n + 1):
        for j in range(m + 1):
            cur = dp[i][j]
            if cur <= neg / 2:
                continue

            if i < n and cur + SOURCE_GAP > dp[i+1][j]:
                dp[i+1][j] = cur + SOURCE_GAP
                back[i+1][j] = (i, j, "skip_source")

            if j < m and cur + RECOGNIZED_GAP > dp[i][j+1]:
                dp[i][j+1] = cur + RECOGNIZED_GAP
                back[i][j+1] = (i, j, "skip_recognized")

            if i < n and j < m:
                score = _r3810_match_score(
                    src[i].get("norm") or "",
                    rec[j].get("norm") or "",
                    float(rec[j].get("confidence", 0.0) or 0.0),
                    (i + 0.5) / max(1, n),
                    (j + 0.5) / max(1, m),
                )
                cand = cur + score
                if cand > dp[i+1][j+1]:
                    dp[i+1][j+1] = cand
                    back[i+1][j+1] = (i, j, "match11")

            if i + 1 < n and j < m:
                joined = (src[i].get("norm") or "") + (src[i+1].get("norm") or "")
                sim = _r3810_similarity(joined, rec[j].get("norm") or "")
                if sim >= 0.72:
                    cand = cur + 4.8 * sim + min(
                        0.5, float(rec[j].get("confidence", 0.0) or 0.0) * 0.5
                    )
                    if cand > dp[i+2][j+1]:
                        dp[i+2][j+1] = cand
                        back[i+2][j+1] = (i, j, "match21")

            if i < n and j + 1 < m:
                joined = (rec[j].get("norm") or "") + (rec[j+1].get("norm") or "")
                sim = _r3810_similarity(src[i].get("norm") or "", joined)
                if sim >= 0.72:
                    conf = (
                        float(rec[j].get("confidence", 0.0) or 0.0)
                        + float(rec[j+1].get("confidence", 0.0) or 0.0)
                    ) / 2.0
                    cand = cur + 4.8 * sim + min(0.5, conf * 0.5)
                    if cand > dp[i+1][j+2]:
                        dp[i+1][j+2] = cand
                        back[i+1][j+2] = (i, j, "match12")

    i, j = n, m
    ops = []
    while i > 0 or j > 0:
        step = back[i][j]
        if step is None:
            raise RuntimeError(f"R38.17A traceback failed at source={i}, recognized={j}")
        pi, pj, op = step
        ops.append((pi, pj, i, j, op))
        i, j = pi, pj
    ops.reverse()

    mapping = {}
    for pi, pj, ni, nj, op in ops:
        if op == "match11":
            mapping[pi] = (pj, pj)
        elif op == "match21":
            mapping[pi] = (pj, pj)
            mapping[pi+1] = (pj, pj)
        elif op == "match12":
            mapping[pi] = (pj, pj+1)

    return mapping, rec


def _r3817a_effective_t0(provided, mapping, rec, raw_t0):
    # RMS is a lower search bound, not automatically the timestamp of word 0.
    if not mapping:
        return raw_t0, {
            "raw_t0_ms": raw_t0,
            "effective_t0_ms": raw_t0,
            "method": "rms_lower_bound_no_anchor",
        }

    first_source = min(mapping)
    first_rec = mapping[first_source][0]
    first_anchor = max(raw_t0, int(rec[first_rec]["start_ms"]))
    cadence = _r3817a_cadence_ms(rec)

    if first_source == 0:
        effective = first_anchor
        method = "first_word_lexical_anchor"
    else:
        expected = cadence * first_source
        observed = max(0, first_anchor - raw_t0)
        if observed > expected * 1.85 + 900:
            effective = max(raw_t0, int(round(first_anchor - expected * 1.35)))
            method = "lexical_anchor_calibrated_lower_bound"
        else:
            effective = raw_t0
            method = "rms_lower_bound_consistent"

    return effective, {
        "raw_t0_ms": raw_t0,
        "effective_t0_ms": effective,
        "first_lexical_source_index": first_source,
        "first_lexical_recognized_index": first_rec,
        "first_lexical_anchor_ms": first_anchor,
        "median_word_cadence_ms": round(cadence, 2),
        "method": method,
    }


def _r3810_apply_mapping(provided, mapping, rec, acoustic_t0):
    rows = [
        dict(row, start_ms=None, end_ms=None, confidence=0.0, language=None)
        for row in provided
    ]

    for source_index, (r0, r1) in mapping.items():
        start = max(acoustic_t0, int(rec[r0]["start_ms"]))
        end = max(start + 60, int(rec[r1].get("end_ms", start + 120)))
        conf = min(
            float(rec[k].get("confidence", 0.0) or 0.0)
            for k in range(r0, r1 + 1)
        )
        rows[source_index].update(
            start_ms=start,
            end_ms=end,
            confidence=conf,
            language=rec[r0].get("language"),
            recognized_index=r0,
            alignment="lexical_anchor",
        )

    # Split one recognized token shared by several source words.
    grouped = {}
    for source_index, span in mapping.items():
        grouped.setdefault(span, []).append(source_index)
    for (r0, r1), indexes in grouped.items():
        indexes = sorted(indexes)
        if len(indexes) < 2:
            continue
        start = max(acoustic_t0, int(rec[r0]["start_ms"]))
        end = max(start + 100, int(rec[r1].get("end_ms", start + 180)))
        weights = [max(1, _r3813_syllable_count(provided[i].get("text") or "")) for i in indexes]
        total = sum(weights)
        consumed = 0
        cursor = start
        for pos, source_index in enumerate(indexes):
            consumed += weights[pos]
            nxt = end if pos == len(indexes)-1 else start + int(round((end-start)*consumed/total))
            rows[source_index]["start_ms"] = cursor
            rows[source_index]["end_ms"] = max(cursor + 45, nxt)
            cursor = nxt

    anchors = sorted(mapping)
    boundaries = [-1] + anchors + [len(rows)]

    for pos in range(len(boundaries)-1):
        left_source = boundaries[pos]
        right_source = boundaries[pos+1]
        gap = [i for i in range(left_source+1, right_source) if rows[i].get("start_ms") is None]
        if not gap:
            continue

        if left_source >= 0:
            left_time = int(rows[left_source]["end_ms"])
            left_rec_end = mapping[left_source][1]
        else:
            left_time = acoustic_t0
            left_rec_end = -1

        if right_source < len(rows):
            right_time = int(rows[right_source]["start_ms"])
            right_rec_start = mapping[right_source][0]
        else:
            right_rec_start = len(rec)
            right_time = max(
                left_time + 160 * len(gap),
                int(rec[-1].get("end_ms", rec[-1]["start_ms"] + 160)),
            )

        if right_time <= left_time:
            right_time = left_time + max(120, 80 * len(gap))

        recognized_times = [
            int(rec[k]["start_ms"])
            for k in range(left_rec_end+1, right_rec_start)
            if left_time <= int(rec[k].get("start_ms", 0)) <= right_time
        ]

        counts = [
            max(1, _r3813_syllable_count(provided[i].get("text") or ""))
            for i in gap
        ]
        total_syllables = max(1, sum(counts))
        consumed = 0
        for gpos, source_index in enumerate(gap):
            start_pos = consumed + 1
            consumed += counts[gpos]
            end_pos = min(total_syllables + 1, consumed + 1)
            start = _r3810_curve_sample(
                left_time, right_time, recognized_times, start_pos, total_syllables
            )
            end = _r3810_curve_sample(
                left_time, right_time, recognized_times, end_pos, total_syllables
            )
            start = max(left_time, min(right_time-1, start))
            end = max(start+45, min(right_time, end))
            rows[source_index].update(
                start_ms=start,
                end_ms=end,
                confidence=0.24 if recognized_times else 0.18,
                language=None,
                alignment="syllabic_acoustic_resample",
            )

    # Prevent the former +1ms cascade.
    previous = acoustic_t0 - 35
    for row in rows:
        start = int(row.get("start_ms") if row.get("start_ms") is not None else previous + 35)
        start = max(acoustic_t0, start, previous + 35)
        row["start_ms"] = start
        row["end_ms"] = max(start + 45, int(row.get("end_ms") or start + 120))
        previous = start

    for idx in range(len(rows)-1):
        here = int(rows[idx]["start_ms"])
        nxt = int(rows[idx+1]["start_ms"])
        rows[idx]["end_ms"] = max(here+35, min(int(rows[idx]["end_ms"]), max(here+35, nxt)))

    return rows


def align_provided_text(provided, recognized, first_vocal_onset_ms=None):
    if not provided:
        return []
    if not recognized:
        raise RuntimeError("Whisper returned no timed words")

    raw_t0 = (
        max(0, int(first_vocal_onset_ms))
        if first_vocal_onset_ms is not None
        else max(0, int(recognized[0]["start_ms"]))
    )

    mapping, rec = _r3810_sequential_mapping(provided, recognized, raw_t0)
    effective_t0, timing = _r3817a_effective_t0(provided, mapping, rec, raw_t0)
    rows = _r3810_apply_mapping(provided, mapping, rec, effective_t0)
    rows = _r3813_attach_syllables(rows, effective_t0)

    lexical = sum(1 for row in rows if row.get("alignment") == "lexical_anchor")
    resampled = sum(1 for row in rows if row.get("alignment") == "syllabic_acoustic_resample")
    print(
        f"[LYRICS] R38.17A vocal timeline: raw_trigger={raw_t0} ms; "
        f"effective_trigger={effective_t0} ms; source={len(provided)}; "
        f"recognized={len(rec)}; lexical={lexical}; resampled={resampled}; "
        f"method={timing.get('method')}",
        flush=True,
    )
    for row in rows:
        row["_r3817_timing"] = timing
    return rows


def _r3817_refine_syllable_nuclei(rows, vocal_audio_path):
    # Replace synthetic interval centers by a local energy maximum on lead_vocals.
    if not vocal_audio_path or not Path(vocal_audio_path).is_file():
        for row in rows:
            for syl in row.get("syllables") or []:
                syl["nucleus_method"] = "interval_center_fallback"
        return

    try:
        import numpy as np
        import whisper
        audio = whisper.load_audio(vocal_audio_path)
    except Exception:
        for row in rows:
            for syl in row.get("syllables") or []:
                syl["nucleus_method"] = "interval_center_fallback"
        return

    n = len(audio)
    frame = max(1, int(SAMPLE_RATE * 0.024))
    hop = max(1, int(SAMPLE_RATE * 0.008))

    for row in rows:
        for syl in row.get("syllables") or []:
            a_ms = int(syl.get("start_ms", 0) or 0)
            b_ms = int(syl.get("end_ms", a_ms+1) or (a_ms+1))
            a = max(0, int(a_ms * SAMPLE_RATE / 1000))
            b = min(n, int(b_ms * SAMPLE_RATE / 1000))
            if b-a < frame:
                syl["nucleus_ms"] = a_ms + max(0, b_ms-a_ms)//2
                syl["nucleus_method"] = "interval_center_short"
                continue

            best_score = -1.0
            best_center = (a+b)//2
            center = (a+b)/2.0
            half = max(1.0, (b-a)/2.0)
            for s in range(a, b-frame+1, hop):
                chunk = np.asarray(audio[s:s+frame], dtype=np.float32)
                rms = float(np.sqrt(np.mean(chunk*chunk) + 1e-12))
                c = s + frame/2.0
                score = rms * (1.0 - min(0.55, 0.16*abs(c-center)/half))
                if score > best_score:
                    best_score = score
                    best_center = int(round(c))
            nucleus_ms = int(round(best_center * 1000.0 / SAMPLE_RATE))
            syl["nucleus_ms"] = max(a_ms, min(b_ms, nucleus_ms))
            syl["nucleus_method"] = "local_vocal_rms_peak"

# R38.17C — leading-prefix-only lyric repair
# Post-anchor lyric timings are deliberately preserved byte-for-byte by this repair.

def _r3817c_prefix_syllables(rows, stop_index):
    previous_start = None
    for word_index in range(max(0, int(stop_index))):
        row = rows[word_index]
        syllables = _r3813_syllabify_french(row.get("text") or "")
        if not syllables:
            row["syllables"] = []
            continue
        word_start = int(row.get("start_ms") or 0)
        word_end = max(word_start + max(60, 45 * len(syllables)), int(row.get("end_ms") or word_start + 120))
        weights = [max(1, len(s)) for s in syllables]
        total = sum(weights)
        consumed = 0
        cursor = word_start
        items = []
        for syllable_index, (syl, weight) in enumerate(zip(syllables, weights)):
            consumed += weight
            end = word_end if syllable_index == len(syllables)-1 else word_start + int(round((word_end-word_start) * consumed / total))
            start = cursor
            end = max(start + 1, end)
            items.append({
                "text": syl,
                "syllable_index": syllable_index,
                "start_ms": start,
                "nucleus_ms": start + (end-start)//2,
                "end_ms": end,
                "confidence": round(float(row.get("confidence", 0.0) or 0.0), 4),
                "alignment": row.get("alignment"),
                "nucleus_method": "interval_center_pending_acoustic_refine",
            })
            cursor = end
            previous_start = start
        row["syllables"] = items


def _r3817c_strict_vocal_start(vocal_audio_path, lower_ms, upper_ms):
    if not vocal_audio_path or not Path(vocal_audio_path).is_file() or upper_ms <= lower_ms:
        return None
    try:
        import numpy as np
        import whisper
        audio = whisper.load_audio(vocal_audio_path)
    except Exception:
        return None

    a = max(0, int(lower_ms * SAMPLE_RATE / 1000))
    b = min(len(audio), int(upper_ms * SAMPLE_RATE / 1000))
    if b-a < int(0.30*SAMPLE_RATE):
        return None

    x = np.asarray(audio[a:b], dtype=np.float32)
    frame = max(1, int(0.030*SAMPLE_RATE))
    hop = max(1, int(0.010*SAMPLE_RATE))
    if len(x) < frame:
        return None
    sq = x*x
    kernel = np.ones(frame, dtype=np.float32)/float(frame)
    rms = np.sqrt(np.convolve(sq, kernel, mode="valid")[::hop] + 1e-12)
    db = 20.0*np.log10(rms + 1e-9)
    p35 = float(np.percentile(db, 35))
    p90 = float(np.percentile(db, 90))
    threshold = p35 + max(8.0, (p90-p35)*0.52)
    active = db >= threshold
    # Require a real sustained phrase, not one leakage spike.
    win = max(1, int(round(0.28/(hop/SAMPLE_RATE))))
    need = max(1, int(round(0.18/(hop/SAMPLE_RATE))))
    counts = np.convolve(active.astype(np.int16), np.ones(win,dtype=np.int16), mode="same")
    candidates = np.flatnonzero(counts >= need)
    if candidates.size == 0:
        return None
    idx = int(candidates[0])
    return int(round(lower_ms + idx*hop*1000.0/SAMPLE_RATE))


def _r3817c_repair_leading_prefix(rows, recognized, raw_vocal_onset_ms, vocal_audio_path):
    if not rows or not recognized:
        return None

    first_anchor = next(
        (i for i,row in enumerate(rows) if row.get("alignment") == "lexical_anchor"),
        None,
    )
    # Nothing useful to repair, or only one word before the first anchor.
    if first_anchor is None or first_anchor <= 1:
        return None

    anchor_ms = int(rows[first_anchor]["start_ms"])
    raw_t0 = max(0, int(raw_vocal_onset_ms or rows[0].get("start_ms") or 0))

    # Use Whisper timings as acoustic controls even when their text did not
    # lexically match the source.  These are far safer than stretching the
    # prefix from a possibly leaked RMS onset.
    controls = sorted({
        int(w.get("start_ms", 0) or 0)
        for w in recognized
        if raw_t0 <= int(w.get("start_ms", 0) or 0) < anchor_ms
        and float(w.get("confidence", 0.0) or 0.0) >= 0.10
    })

    strict_start = _r3817c_strict_vocal_start(
        vocal_audio_path,
        raw_t0,
        anchor_ms,
    )

    first_control = controls[0] if controls else None
    candidates = [v for v in (strict_start, first_control) if v is not None]
    if not candidates:
        # No objective evidence: do not alter the existing timeline.
        return None

    prefix_start = max(raw_t0, min(candidates))
    # Reject corrections that would not materially change the pathological
    # leading stretch.
    old_span = anchor_ms - int(rows[0].get("start_ms") or raw_t0)
    new_span = anchor_ms - prefix_start
    if new_span <= 0 or old_span <= 0:
        return None

    prefix = rows[:first_anchor]
    syllable_counts = [
        max(1, _r3813_syllable_count(row.get("text") or ""))
        for row in prefix
    ]
    total_syllables = max(1, sum(syllable_counts))

    # Controls strictly inside the repaired span.  The lexical anchor itself
    # remains immutable and is used only as the right boundary.
    acoustic_controls = [t for t in controls if prefix_start < t < anchor_ms]

    consumed = 0
    starts = []
    ends = []
    for idx, count in enumerate(syllable_counts):
        start_pos = consumed + 1
        consumed += count
        end_pos = min(total_syllables + 1, consumed + 1)
        start = _r3810_curve_sample(
            prefix_start, anchor_ms, acoustic_controls,
            start_pos, total_syllables,
        )
        end = _r3810_curve_sample(
            prefix_start, anchor_ms, acoustic_controls,
            end_pos, total_syllables,
        )
        starts.append(int(start))
        ends.append(int(end))

    # Guarantee meaningful monotonic spacing, but NEVER move the first lexical
    # anchor or anything after it.
    min_gap = 45
    for i in range(len(starts)):
        if i == 0:
            starts[i] = max(prefix_start, starts[i])
        else:
            starts[i] = max(starts[i], starts[i-1] + min_gap)

    # If controls were too compressed, backfill from the fixed anchor.
    latest_allowed = anchor_ms - min_gap
    for i in range(len(starts)-1, -1, -1):
        starts[i] = min(starts[i], latest_allowed)
        latest_allowed = starts[i] - min_gap

    if starts and starts[0] < prefix_start:
        shift = prefix_start - starts[0]
        starts = [s + shift for s in starts]

    for i,row in enumerate(prefix):
        start = starts[i]
        next_start = anchor_ms if i == len(prefix)-1 else starts[i+1]
        end = max(start + 35, min(max(start + 45, ends[i]), next_start))
        row["start_ms"] = start
        row["end_ms"] = end
        row["alignment"] = "leading_prefix_acoustic_repair"
        row["prefix_repair"] = {
            "raw_vocal_onset_ms": raw_t0,
            "prefix_start_ms": prefix_start,
            "fixed_anchor_index": first_anchor,
            "fixed_anchor_ms": anchor_ms,
            "whisper_controls": len(acoustic_controls),
            "strict_vocal_start_ms": strict_start,
        }

    _r3817c_prefix_syllables(rows, first_anchor)

    print(
        f"[LYRICS] R38.17C prefix repair: words={first_anchor}; "
        f"raw={raw_t0} ms; repaired_start={prefix_start} ms; "
        f"fixed_anchor={anchor_ms} ms; controls={len(acoustic_controls)}",
        flush=True,
    )
    return {
        "words_repaired": first_anchor,
        "raw_vocal_onset_ms": raw_t0,
        "repaired_start_ms": prefix_start,
        "fixed_anchor_ms": anchor_ms,
        "whisper_controls": len(acoustic_controls),
        "strict_vocal_start_ms": strict_start,
    }


def _r3817c_refine_syllable_nuclei(rows, vocal_audio_path):
    if not vocal_audio_path or not Path(vocal_audio_path).is_file():
        return
    try:
        import numpy as np
        import whisper
        audio = whisper.load_audio(vocal_audio_path)
    except Exception:
        return

    frame = max(1, int(SAMPLE_RATE*0.024))
    hop = max(1, int(SAMPLE_RATE*0.008))
    n = len(audio)

    for row in rows:
        for syl in row.get("syllables") or []:
            a_ms = int(syl.get("start_ms",0) or 0)
            b_ms = int(syl.get("end_ms",a_ms+1) or (a_ms+1))
            a = max(0, int(a_ms*SAMPLE_RATE/1000))
            b = min(n, int(b_ms*SAMPLE_RATE/1000))
            if b-a < frame:
                continue
            best_score = -1.0
            best_center = (a+b)//2
            center = (a+b)/2.0
            half = max(1.0,(b-a)/2.0)
            for s in range(a,b-frame+1,hop):
                chunk = np.asarray(audio[s:s+frame],dtype=np.float32)
                rms = float(np.sqrt(np.mean(chunk*chunk)+1e-12))
                c = s+frame/2.0
                score = rms*(1.0-min(0.50,0.14*abs(c-center)/half))
                if score > best_score:
                    best_score = score
                    best_center = int(round(c))
            nucleus_ms = int(round(best_center*1000.0/SAMPLE_RATE))
            syl["nucleus_ms"] = max(a_ms,min(b_ms,nucleus_ms))
            syl["nucleus_method"] = "local_vocal_rms_peak"

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--audio', required=True)
    parser.add_argument('--vocal-audio')
    parser.add_argument('--lyrics-file')
    parser.add_argument('--output', required=True)
    parser.add_argument('--progress-file')
    parser.add_argument('--mode', choices=['extract', 'align'], default='align')
    args = parser.parse_args()

    progress(args.progress_file, 3, 'load', 'Préparation LyricsLab')

    import torch
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA required for LyricsLab; CPU fallback disabled')

    import whisper

    model_path = choose_model_path()
    progress(args.progress_file, 8, 'model', f'Chargement {Path(model_path).name} sur CUDA')
    model = whisper.load_model(model_path, device='cuda')

    words, segments = transcribe_multilingual(model, args.audio, args.progress_file)
    if not words and not segments:
        raise RuntimeError('Whisper returned no lyrics')

    languages = []
    for row in segments:
        lang = row.get('language')
        if lang and lang not in languages:
            languages.append(lang)

    if args.mode == 'extract':
        progress(args.progress_file, 82, 'extract', 'Construction du texte proposé')
        text = extracted_text(segments)
        if not text:
            text = ' '.join(row['text'] for row in words).strip()
        if not text:
            raise RuntimeError('No extractable lyrics text')
        write_json(args.output, {
            'ok': True,
            'mode': 'extract',
            'version': 'r38.10-sequential-variable-timeline',
            'model': Path(model_path).name,
            'languages': languages,
            'text': text,
            'recognized_words': len(words),
        })
        progress(
            args.progress_file,
            100,
            'complete',
            'Paroles extraites',
            languages=languages,
        )
        return

    if not args.lyrics_file:
        raise RuntimeError('--lyrics-file is required in align mode')

    provided_text = Path(args.lyrics_file).read_text(encoding='utf-8')
    provided = source_tokens(provided_text)
    if not provided:
        raise RuntimeError('Lyrics text is empty')
    if not words:
        raise RuntimeError('Whisper returned no timed words')

    progress(args.progress_file, 82, 'align', 'Ancrage du texte fourni sur la timeline')
    vocal_onset_ms, onset_meta = detect_first_vocal_onset(args.vocal_audio)
    if vocal_onset_ms is None:
        vocal_onset_ms = int(words[0]['start_ms'])
        onset_meta = {'method':'whisper_first_word_fallback','found':True}
    print(f"[LYRICS] First vocal onset: {vocal_onset_ms} ms ({onset_meta.get('method')})", flush=True)
    progress(args.progress_file, 84, 'align', f'Ancrage initial à {vocal_onset_ms / 1000:.3f}s')
    rows = align_provided_text(provided, words, vocal_onset_ms)
    prefix_diagnostics = _r3817c_repair_leading_prefix(
        rows, words, vocal_onset_ms, args.vocal_audio
    )
    _r3817c_refine_syllable_nuclei(rows, args.vocal_audio)
    anchored_rows = [row for row in rows if row.get('start_ms') is not None]
    payload_words = [{
        'text': row['text'],
        'start_ms': int(row['start_ms']),
        'end_ms': int(row.get('end_ms') or int(row['start_ms']) + 120),
        'line_break_after': bool(row.get('line_break_after')),
        'section_label': row.get('section_label'),
        'section_type': row.get('section_type'),
        'confidence': round(float(row.get('confidence', 0.0)), 4),
        'language': row.get('language'),
        'alignment': row.get('alignment'),
        'recognized_index': row.get('recognized_index'),
        'syllables': row.get('syllables') or [],
    } for row in anchored_rows]
    payload_syllables = [
        dict(
            syllable,
            word_index=word_index,
            word_text=row['text'],
            line_break_after=(bool(row.get('line_break_after')) and syllable_index == len(row.get('syllables') or []) - 1),
            section_label=row.get('section_label'),
            section_type=row.get('section_type'),
        )
        for word_index, row in enumerate(anchored_rows)
        for syllable_index, syllable in enumerate(row.get('syllables') or [])
    ]

    write_json(args.output, {
        'ok': True,
        'mode': 'align',
        'version': 'r38.17c-leading-prefix-acoustic-repair',
        'model': Path(model_path).name,
        'languages': languages,
        'provided_words': len(provided),
        'recognized_words': len(words),
        'syllables_count': len(payload_syllables),
        'syllables': payload_syllables,
        'words': payload_words,
        'prefix_repair': prefix_diagnostics,
        'timing_diagnostics': (rows[0].get('_r3817_timing') if rows else None),
    })
    progress(
        args.progress_file,
        100,
        'complete',
        'Paroles ancrées sur la timeline',
        languages=languages,
    )

if __name__ == '__main__':
    main()
