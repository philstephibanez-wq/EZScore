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
    tmp = p.with_suffix(p.suffix + '.tmp')
    tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')
    tmp.replace(p)

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
    s=line.strip()
    if not s:
        return None
    m=re.fullmatch(r'\[([^\[\]\r\n]{1,80})\]',s)
    if m:
        return m.group(1).strip()
    m=re.fullmatch(r'([^\r\n:]{1,48}):',s)
    if m:
        candidate=m.group(1).strip()
        if normalise_section_type(candidate)!='section':
            return candidate
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

def interpolate_unmatched(rows: list[dict]) -> list[dict]:
    known = [i for i, row in enumerate(rows) if row.get('start_ms') is not None]
    if not known:
        return rows

    for i, row in enumerate(rows):
        if row.get('start_ms') is not None:
            continue
        left = max((k for k in known if k < i), default=None)
        right = min((k for k in known if k > i), default=None)

        if left is not None and right is not None:
            span = max(1, right - left)
            ratio = (i - left) / span
            a = rows[left]['end_ms']
            b = rows[right]['start_ms']
            t = int(round(a + (b - a) * ratio))
            row.update(start_ms=t, end_ms=t + 120, confidence=0.35)
        elif left is not None:
            t = rows[left]['end_ms'] + max(80, (i - left - 1) * 180)
            row.update(start_ms=t, end_ms=t + 160, confidence=0.25)
        elif right is not None:
            t = max(0, rows[right]['start_ms'] - max(160, (right - i) * 180))
            row.update(start_ms=t, end_ms=min(rows[right]['start_ms'], t + 160), confidence=0.25)

    return rows

def align_provided_text(provided: list[dict], recognized: list[dict]) -> list[dict]:
    a = [row['norm'] for row in provided]
    b = [row['norm'] for row in recognized]
    matcher = difflib.SequenceMatcher(a=a, b=b, autojunk=False)

    rows = [dict(row, start_ms=None, end_ms=None, confidence=0.0, language=None) for row in provided]

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            for di, dj in zip(range(i1, i2), range(j1, j2)):
                src = recognized[dj]
                rows[di].update(
                    start_ms=src['start_ms'],
                    end_ms=src['end_ms'],
                    confidence=src.get('confidence', 0.0),
                    language=src.get('language'),
                )
        elif tag == 'replace':
            n = min(i2 - i1, j2 - j1)
            for off in range(n):
                src = recognized[j1 + off]
                rows[i1 + off].update(
                    start_ms=src['start_ms'],
                    end_ms=src['end_ms'],
                    confidence=max(0.2, src.get('confidence', 0.0) * 0.60),
                    language=src.get('language'),
                )

    return interpolate_unmatched(rows)

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--audio', required=True)
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
            'version': 'r36.1-large-v3-multilingual',
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
    rows = align_provided_text(provided, words)

    payload_words = [{
        'text': row['text'],
        'start_ms': int(row.get('start_ms') or 0),
        'end_ms': int(row.get('end_ms') or (row.get('start_ms') or 0) + 120),
        'line_break_after': bool(row.get('line_break_after')),
        'section_label': row.get('section_label'),
        'section_type': row.get('section_type'),
        'confidence': round(float(row.get('confidence', 0.0)), 4),
        'language': row.get('language'),
    } for row in rows]

    write_json(args.output, {
        'ok': True,
        'mode': 'align',
        'version': 'r36.1-large-v3-multilingual',
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
