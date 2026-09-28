#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re
import shutil
import sys

ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
BACKUP = ROOT / 'var' / 'backup' / ('r38-7-' + datetime.now().strftime('%Y%m%d-%H%M%S'))


def read(rel: str) -> str:
    path = ROOT / rel
    if not path.is_file():
        raise RuntimeError(f'Missing required file: {rel}')
    return path.read_text(encoding='utf-8')


def backup(path: Path) -> None:
    if not path.exists():
        return
    dst = BACKUP / path.relative_to(ROOT)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, dst)


def save(rel: str, text: str) -> None:
    path = ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    old = path.read_text(encoding='utf-8') if path.exists() else None
    if old == text:
        print(f'[OK] {rel}: already applied')
        return
    if path.exists():
        backup(path)
    path.write_text(text, encoding='utf-8', newline='\n')
    print(f'[OK] {rel}')


ALIGN_BLOCK = r'''def interpolate_unmatched(rows: list[dict]) -> list[dict]:
    known = [i for i, row in enumerate(rows) if row.get('start_ms') is not None]
    if not known:
        raise RuntimeError('No acoustic anchor available for provided lyrics')

    for i, row in enumerate(rows):
        if row.get('start_ms') is not None:
            continue
        left = max((k for k in known if k < i), default=None)
        right = min((k for k in known if k > i), default=None)
        if left is None:
            continue
        if right is not None:
            span = max(1, right - left)
            ratio = (i - left) / span
            a = int(rows[left]['end_ms'])
            b = int(rows[right]['start_ms'])
            t = int(round(a + (b - a) * ratio))
            t = max(a, min(b, t))
            row.update(start_ms=t, end_ms=min(b, t + 140), confidence=0.30)
        else:
            t = int(rows[left]['end_ms']) + max(80, (i - left - 1) * 180)
            row.update(start_ms=t, end_ms=t + 160, confidence=0.20)
    return rows


def detect_first_vocal_onset(audio_path: str | None) -> tuple[int | None, dict]:
    """Detect first sustained vocal activity on the time-aligned lead-vocal stem.

    No external VAD dependency is introduced: this uses the already installed
    Whisper audio loader plus NumPy. The stem remains on the original song clock,
    therefore the returned timestamp is directly usable by LyricsLab.
    """
    if not audio_path or not Path(audio_path).is_file():
        return None, {'method': 'unavailable'}

    import numpy as np
    import whisper

    audio = whisper.load_audio(audio_path)
    if audio is None or len(audio) < SAMPLE_RATE // 4:
        return None, {'method': 'empty'}

    frame = max(1, int(SAMPLE_RATE * 0.030))
    hop = max(1, int(SAMPLE_RATE * 0.010))
    if len(audio) < frame:
        return None, {'method': 'too_short'}

    # RMS envelope on the isolated lead-vocal stem.
    sq = np.asarray(audio, dtype=np.float32) ** 2
    kernel = np.ones(frame, dtype=np.float32) / float(frame)
    rms = np.sqrt(np.convolve(sq, kernel, mode='valid')[::hop] + 1e-12)
    db = 20.0 * np.log10(rms + 1e-9)

    p20 = float(np.percentile(db, 20))
    p90 = float(np.percentile(db, 90))
    spread = max(6.0, p90 - p20)
    threshold = min(p90 - 5.0, p20 + max(10.0, spread * 0.38))

    # Require sustained activity: >= 120 ms active in a 180 ms window.
    active = db >= threshold
    window = max(1, int(round(0.180 / (hop / SAMPLE_RATE))))
    need = max(1, int(round(0.120 / (hop / SAMPLE_RATE))))
    counts = np.convolve(active.astype(np.int16), np.ones(window, dtype=np.int16), mode='same')
    candidates = np.flatnonzero(counts >= need)
    if candidates.size == 0:
        return None, {
            'method': 'rms_sustained', 'threshold_db': round(threshold, 2),
            'noise_db': round(p20, 2), 'active_db': round(p90, 2), 'found': False,
        }

    idx = int(candidates[0])
    # Walk back through the onset shoulder to avoid anchoring in the middle of the syllable.
    shoulder = threshold - 6.0
    while idx > 0 and db[idx - 1] >= shoulder:
        idx -= 1
    onset_ms = max(0, int(round((idx * hop) * 1000.0 / SAMPLE_RATE)))
    return onset_ms, {
        'method': 'rms_sustained', 'threshold_db': round(threshold, 2),
        'noise_db': round(p20, 2), 'active_db': round(p90, 2), 'found': True,
    }


def _token_similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    return difflib.SequenceMatcher(a=a, b=b, autojunk=False).ratio()


def align_provided_text(
    provided: list[dict],
    recognized: list[dict],
    first_vocal_onset_ms: int | None = None,
) -> list[dict]:
    """Anchor first source word acoustically, then align monotonically forward.

    This deliberately avoids a whole-song SequenceMatcher: repeated choruses must
    never relocate the first lyric anchor to a later occurrence.
    """
    if not provided:
        return []
    if not recognized and first_vocal_onset_ms is None:
        raise RuntimeError('No timed words or vocal onset available')

    rows = [dict(row, start_ms=None, end_ms=None, confidence=0.0, language=None) for row in provided]

    if first_vocal_onset_ms is None:
        first_vocal_onset_ms = int(recognized[0]['start_ms'])
        onset_method = 'whisper_first_word_fallback'
    else:
        onset_method = 'vocal_stem_acoustic_onset'

    onset = max(0, int(first_vocal_onset_ms))
    first_end = onset + 160
    first_lang = None
    cursor = 0

    # Find the earliest recognized token near/after the acoustic onset. It may be
    # textually wrong; it is used only to estimate duration/language and cursor.
    for ri, src in enumerate(recognized):
        if int(src.get('end_ms', 0)) < onset - 350:
            continue
        cursor = ri
        if int(src.get('start_ms', 0)) <= onset + 1800:
            first_end = max(onset + 100, int(src.get('end_ms', onset + 160)))
            first_lang = src.get('language')
        break

    rows[0].update(
        start_ms=onset,
        end_ms=first_end,
        confidence=1.0,
        language=first_lang,
        anchor=onset_method,
    )

    last_time = onset
    search_from = cursor
    for pi in range(1, len(provided)):
        target = provided[pi].get('norm') or ''
        if not target:
            continue

        best = None
        # Earliest plausible forward match wins. Limit by recognized-word count,
        # not elapsed seconds, so instrumental sections remain possible.
        stop = min(len(recognized), search_from + 36)
        same_section = provided[pi].get('section_label') == provided[pi - 1].get('section_label')
        max_start = last_time + (20000 if same_section else 10**12)
        for ri in range(search_from, stop):
            src = recognized[ri]
            src_start = int(src.get('start_ms', 0))
            if int(src.get('end_ms', 0)) < last_time - 120:
                continue
            # Inside one lyrical section, never jump tens of seconds to a later
            # repeated verse/chorus. Section boundaries may legitimately span solos.
            if src_start > max_start:
                break
            score = _token_similarity(target, src.get('norm') or '')
            if score >= 0.94:
                best = (ri, src, score)
                break
            if score >= 0.80 and (best is None or score > best[2]):
                best = (ri, src, score)

        if best is None:
            continue

        ri, src, score = best
        start = max(last_time, int(src['start_ms']))
        end = max(start + 80, int(src.get('end_ms', start + 120)))
        rows[pi].update(
            start_ms=start,
            end_ms=end,
            confidence=min(float(src.get('confidence', 0.0) or 0.0), score),
            language=src.get('language'),
        )
        last_time = start
        search_from = ri + 1

    rows = interpolate_unmatched(rows)

    # Final monotonicity guard.
    previous = -1
    for row in rows:
        if row.get('start_ms') is None:
            continue
        start = max(previous, int(row['start_ms']))
        end = max(start + 40, int(row.get('end_ms') or start + 120))
        row['start_ms'] = start
        row['end_ms'] = end
        previous = start
    return rows

'''


def patch_analyzer() -> None:
    rel = 'analysis/lyrics_timeline_analysis.py'
    text = read(rel)

    pattern = re.compile(r'def interpolate_unmatched\(.*?(?=def main\(\) -> None:)', re.S)
    if not pattern.search(text):
        raise RuntimeError('Analyzer alignment block not found; no unsafe edit applied.')
    text = pattern.sub(lambda _m: ALIGN_BLOCK, text, count=1)

    if "parser.add_argument('--vocal-audio')" not in text:
        anchor = "    parser.add_argument('--audio', required=True)\n"
        if anchor not in text:
            raise RuntimeError('Analyzer --audio parser anchor not found.')
        text = text.replace(anchor, anchor + "    parser.add_argument('--vocal-audio')\n", 1)

    old_call = re.compile(r"    progress\(args\.progress_file, 82, 'align', 'Ancrage du texte fourni sur la timeline'\)\n(?:    .*\n){0,8}?    rows = align_provided_text\([^\n]+\)\n")
    replacement = (
        "    progress(args.progress_file, 80, 'onset', 'Détection acoustique de la première entrée vocale')\n"
        "    vocal_onset_ms, onset_meta = detect_first_vocal_onset(args.vocal_audio)\n"
        "    if vocal_onset_ms is None:\n"
        "        vocal_onset_ms = int(words[0]['start_ms'])\n"
        "        onset_meta = {'method': 'whisper_first_word_fallback', 'found': True}\n"
        "    print(f\"[LYRICS] First vocal onset: {vocal_onset_ms} ms ({onset_meta.get('method')})\", flush=True)\n"
        "    progress(args.progress_file, 84, 'align', f'Ancrage initial à {vocal_onset_ms / 1000:.3f}s')\n"
        "    rows = align_provided_text(provided, words, vocal_onset_ms)\n"
    )
    if "detect_first_vocal_onset(args.vocal_audio)" not in text:
        text, count = old_call.subn(replacement, text, count=1)
        if count != 1:
            # R38.6 variants still contain the direct call even if progress text differs.
            direct = re.compile(r"^    rows = align_provided_text\(provided, words(?:, [^\n]+)?\)\s*$", re.M)
            if not direct.search(text):
                raise RuntimeError('Analyzer align call not found; no unsafe edit applied.')
            text = direct.sub(replacement.rstrip('\n'), text, count=1)

    marker = "        'recognized_words': len(words),\n        'words': payload_words,"
    if marker in text and "'vocal_onset_ms': vocal_onset_ms" not in text:
        text = text.replace(
            marker,
            "        'recognized_words': len(words),\n"
            "        'vocal_onset_ms': vocal_onset_ms,\n"
            "        'vocal_onset': onset_meta,\n"
            "        'words': payload_words,",
            1,
        )

    text = text.replace("'version': 'r36.1-large-v3-multilingual'", "'version': 'r38.7-acoustic-onset-monotonic'", 1)
    # Replace the second occurrence too when present.
    text = text.replace("'version': 'r36.1-large-v3-multilingual'", "'version': 'r38.7-acoustic-onset-monotonic'", 1)
    save(rel, text)


def patch_worker() -> None:
    rel = 'worker_app/lyrics_worker_r37.py'
    text = read(rel)
    if '--vocal-audio' not in text:
        anchor = "    if mode==\"align\":\n        lyrics_file=paths.get(\"lyrics_file\")\n"
        if anchor not in text:
            raise RuntimeError('Lyrics worker align anchor not found.')
        addition = (
            "    if mode==\"align\":\n"
            "        vocal_audio=paths.get(\"lead_vocals\")\n"
            "        if vocal_audio and Path(str(vocal_audio)).is_file():\n"
            "            command += [\"--vocal-audio\",str(vocal_audio)]\n"
            "            engine.log(f\"Détection onset vocal: lead_vocals -> {vocal_audio}\")\n\n"
        )
        text = text.replace(anchor, addition + anchor, 1)
    save(rel, text)


SHARED_CARD = '''<section class="panel chordslab-song-card"
         data-lab-song-card
         data-lab-beats="{{ (beat_events|default([]))|json_encode|e('html_attr') }}">
    <div><span>{{ 'song.title'|trans }}</span><strong>{{ song.title }}</strong></div>
    <div><span>{{ 'song.artist'|trans }}</span><strong>{{ song.artist }}</strong></div>
    <div><span>{{ 'chordslab.key'|trans({}, 'chordslab') }}</span><strong>{{ song.keySignature ?: '—' }}</strong></div>
    <div><span>{{ 'song.time_signature'|trans }}</span><strong>{{ song.timeSignature }}</strong></div>
    <div><span>{{ 'song.capo'|trans }}</span><strong>{{ song.capo }}</strong></div>
    <div class="chordslab-tempo-value"><span>Tempo</span><strong data-lab-tempo>Tempo = —</strong></div>
</section>
'''

SHARED_JS = '''(() => {
'use strict';
for(const card of document.querySelectorAll('[data-lab-song-card]')){
    const out=card.querySelector('[data-lab-tempo]');
    if(!out)continue;
    let beats=[];
    try{beats=JSON.parse(card.dataset.labBeats||'[]')}catch(_){beats=[]}
    if(!Array.isArray(beats)||beats.length<3){out.textContent='Tempo = —';continue}
    const deltas=[];
    for(let i=1;i<beats.length;i++){
        const d=Number(beats[i].start_ms)-Number(beats[i-1].start_ms);
        if(Number.isFinite(d)&&d>=180&&d<=2000)deltas.push(d);
    }
    if(!deltas.length){out.textContent='Tempo = —';continue}
    deltas.sort((a,b)=>a-b);
    const mid=Math.floor(deltas.length/2);
    const median=deltas.length%2?deltas[mid]:(deltas[mid-1]+deltas[mid])/2;
    const bpm=Math.round(60000/median);
    out.textContent=Number.isFinite(bpm)&&bpm>0?`Tempo = ${bpm}`:'Tempo = —';
}
})();
'''


def patch_shared_card() -> None:
    save('templates/song/components/_lab_song_card.html.twig', SHARED_CARD)
    save('public/assets/js/lab-song-card.js', SHARED_JS)

    chord_rel = 'templates/song/chordslab.html.twig'
    chord = read(chord_rel)
    card_pattern = re.compile(r'<section class="panel chordslab-song-card">.*?</section>', re.S)
    if card_pattern.search(chord):
        chord = card_pattern.sub("{% include 'song/components/_lab_song_card.html.twig' with {song:song, beat_events:beat_events} %}", chord, count=1)
    elif "_lab_song_card.html.twig" not in chord:
        raise RuntimeError('ChordsLab song card block not found.')
    if '/assets/js/lab-song-card.js' not in chord:
        marker = '{% block javascripts %}'
        if marker not in chord:
            raise RuntimeError('ChordsLab javascripts block not found.')
        chord = chord.replace(marker, marker + '\n<script src="/assets/js/lab-song-card.js?v=20260928r38_7"></script>', 1)
    save(chord_rel, chord)

    lyric_rel = 'templates/song/lyricslab.html.twig'
    lyric = read(lyric_rel)
    # Make the existing shared include explicit and give the prompter a stable song id.
    lyric = lyric.replace(
        "{% include 'song/components/_lab_song_card.html.twig' with {song:song} %}",
        "{% include 'song/components/_lab_song_card.html.twig' with {song:song, beat_events:beat_events} %}",
        1,
    )
    if 'data-song-id="{{ song.id }}"' not in lyric:
        lyric, n = re.subn(r'(\s+data-lyricslab\b)', r'\1\n         data-song-id="{{ song.id }}"', lyric, count=1)
        if n != 1:
            raise RuntimeError('LyricsLab data-lyricslab anchor not found.')
    if '/assets/js/lab-song-card.js' not in lyric:
        marker = '{% block javascripts %}'
        if marker not in lyric:
            raise RuntimeError('LyricsLab javascripts block not found.')
        lyric = lyric.replace(marker, marker + '\n<script src="/assets/js/lab-song-card.js?v=20260928r38_7"></script>', 1)
    lyric = re.sub(r'lyricslab-r37\.js\?v=[^\"\']+', 'lyricslab-r37.js?v=20260928r38_7', lyric, count=1)
    # R38.7 owns the shared card/tempo path; remove obsolete supplemental R38.6 runtime if present.
    lyric = re.sub(r'\s*<script[^>]+lyricslab-r38-6-fix\.js[^>]*></script>\s*', '\n', lyric, count=1)
    save(lyric_rel, lyric)


def patch_diagram_persistence() -> None:
    rel = 'public/assets/js/lyricslab-r37.js'
    text = read(rel)
    text = text.replace(
        "const diagramStorageKey=`ezscore:lyricslab:diagram:${location.pathname}`;",
        "const diagramStorageKey=`ezscore:lyricslab:diagram:${root.dataset.songId||location.pathname}`;",
        1,
    )
    save(rel, text)


def main() -> None:
    patch_analyzer()
    patch_worker()
    patch_shared_card()
    patch_diagram_persistence()
    print(f'[OK] Backup: {BACKUP}')
    print('R38_7_INSTALL_OK')


if __name__ == '__main__':
    main()
