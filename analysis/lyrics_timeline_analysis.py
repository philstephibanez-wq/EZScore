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
        words=re.findall(r'\S+',line)
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

def align_provided_text(provided: list[dict], recognized: list[dict], first_vocal_onset_ms: int | None = None) -> list[dict]:
    if not provided:
        return []
    if not recognized and first_vocal_onset_ms is None:
        raise RuntimeError("No timed words or vocal onset available")

    rows=[dict(row,start_ms=None,end_ms=None,confidence=0.0,language=None) for row in provided]
    if first_vocal_onset_ms is None:
        first_vocal_onset_ms=int(recognized[0]["start_ms"])
        anchor_method="whisper_first_word_fallback"
    else:
        anchor_method="vocal_stem_acoustic_onset"

    onset=max(0,int(first_vocal_onset_ms))
    first_end=onset+160
    first_lang=None
    cursor=0

    for ri,src in enumerate(recognized):
        if int(src.get("end_ms",0)) < onset-350:
            continue
        cursor=ri
        if int(src.get("start_ms",0)) <= onset+1800:
            first_end=max(onset+100,int(src.get("end_ms",onset+160)))
            first_lang=src.get("language")
        break

    rows[0].update(start_ms=onset,end_ms=first_end,confidence=1.0,language=first_lang,anchor=anchor_method)

    last_time=onset
    search_from=cursor
    for pi in range(1,len(provided)):
        target=provided[pi].get("norm") or ""
        if not target:
            continue
        best=None
        stop=min(len(recognized),search_from+40)
        same_section=provided[pi].get("section_label")==provided[pi-1].get("section_label")
        max_start=last_time+(20000 if same_section else 10**12)
        for ri in range(search_from,stop):
            src=recognized[ri]
            s=int(src.get("start_ms",0))
            if int(src.get("end_ms",0)) < last_time-120:
                continue
            if s>max_start:
                break
            score=_r388_similarity(target,src.get("norm") or "")
            if score>=0.94:
                best=(ri,src,score); break
            if score>=0.80 and (best is None or score>best[2]):
                best=(ri,src,score)
        if best is None:
            continue
        ri,src,score=best
        start=max(last_time,int(src["start_ms"]))
        end=max(start+80,int(src.get("end_ms",start+120)))
        rows[pi].update(start_ms=start,end_ms=end,confidence=min(float(src.get("confidence",0.0) or 0.0),score),language=src.get("language"))
        last_time=start
        search_from=ri+1

    rows=_r388_fill_unmatched(rows)
    prev=-1
    for row in rows:
        if row.get("start_ms") is None:
            continue
        s=max(prev,int(row["start_ms"]))
        e=max(s+40,int(row.get("end_ms") or s+120))
        row["start_ms"]=s; row["end_ms"]=e; prev=s
    return rows

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
            'version': 'r38.8-acoustic-anchor',
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
    } for row in anchored_rows]

    write_json(args.output, {
        'ok': True,
        'mode': 'align',
        'version': 'r38.8-acoustic-anchor',
        'model': Path(model_path).name,
        'languages': languages,
        'provided_words': len(provided),
        'recognized_words': len(words),
        'words': payload_words,
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
