#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re, shutil, sys

ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
BACKUP = ROOT / 'var' / 'backup' / ('r38-8-' + datetime.now().strftime('%Y%m%d-%H%M%S'))

def read(rel):
    p=ROOT/rel
    if not p.is_file(): raise RuntimeError(f'Missing required file: {rel}')
    return p.read_text(encoding='utf-8')

def backup(p):
    if not p.exists(): return
    dst=BACKUP/p.relative_to(ROOT)
    dst.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(p,dst)

def save(rel,text):
    p=ROOT/rel
    old=p.read_text(encoding='utf-8') if p.exists() else None
    if old==text:
        print(f'[OK] {rel}: already applied'); return
    if p.exists(): backup(p)
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(text,encoding='utf-8',newline='\n')
    print(f'[OK] {rel}')

def replace_function(text,name,replacement):
    m=re.search(rf'(?m)^def {re.escape(name)}\s*\(',text)
    if not m: return text,False
    nxt=re.search(r'(?m)^def [A-Za-z_]\w*\s*\(',text[m.end():])
    end=m.end()+nxt.start() if nxt else len(text)
    return text[:m.start()]+replacement.rstrip()+'\n\n'+text[end:],True

HELPERS = r'''def detect_first_vocal_onset(audio_path: str | None) -> tuple[int | None, dict]:
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
    return rows'''
ALIGN = r'''def align_provided_text(provided: list[dict], recognized: list[dict], first_vocal_onset_ms: int | None = None) -> list[dict]:
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
    return rows'''

def patch_analyzer():
    rel='analysis/lyrics_timeline_analysis.py'
    text=read(rel)
    # Remove any previous experimental helper functions if present.
    for name in ['detect_first_vocal_onset','_r387_token_similarity','_r388_similarity','_r388_fill_unmatched']:
        text,_=replace_function(text,name,'')
    text,ok=replace_function(text,'align_provided_text',ALIGN)
    if not ok: raise RuntimeError('align_provided_text() not found; no unsafe edit applied.')
    pos=text.find('def align_provided_text(')
    text=text[:pos]+HELPERS+'\n\n'+text[pos:]
    if "parser.add_argument('--vocal-audio')" not in text and 'parser.add_argument("--vocal-audio")' not in text:
        m=re.search(r'(?m)^(\s*)parser\.add_argument\(([\'\"])--audio\2,\s*required=True\)\s*$',text)
        if not m: raise RuntimeError('Analyzer --audio parser anchor not found.')
        insertion=m.group(0)+'\n'+m.group(1)+"parser.add_argument('--vocal-audio')"
        text=text[:m.start()]+insertion+text[m.end():]
    calls=list(re.finditer(r'(?m)^(?P<i>\s*)rows\s*=\s*align_provided_text\(provided,\s*words(?:,\s*[^\n\)]*)?\)\s*$',text))
    if not calls: raise RuntimeError('Analyzer align call not found.')
    c=calls[-1]; i=c.group('i')
    block=(i+"vocal_onset_ms, onset_meta = detect_first_vocal_onset(args.vocal_audio)\n"
           +i+"if vocal_onset_ms is None:\n"
           +i+"    vocal_onset_ms = int(words[0]['start_ms'])\n"
           +i+"    onset_meta = {'method':'whisper_first_word_fallback','found':True}\n"
           +i+"print(f\"[LYRICS] First vocal onset: {vocal_onset_ms} ms ({onset_meta.get('method')})\", flush=True)\n"
           +i+"progress(args.progress_file, 84, 'align', f'Ancrage initial à {vocal_onset_ms / 1000:.3f}s')\n"
           +i+"rows = align_provided_text(provided, words, vocal_onset_ms)")
    text=text[:c.start()]+block+text[c.end():]
    text=text.replace("'version': 'r36.1-large-v3-multilingual'","'version': 'r38.8-acoustic-anchor'")
    save(rel,text)

def patch_worker():
    rel='worker_app/lyrics_worker_r37.py'; text=read(rel)
    if '"--vocal-audio"' not in text and "'--vocal-audio'" not in text:
        m=re.search(r'(?m)^(\s*)if mode=="align":\s*\n\1\s+lyrics_file=paths\.get\("lyrics_file"\)',text)
        if not m: raise RuntimeError('Worker align anchor not found.')
        i=m.group(1)
        add=(i+'if mode=="align":\n'+i+'    vocal_audio=paths.get("lead_vocals")\n'+i+'    if vocal_audio and Path(str(vocal_audio)).is_file():\n'+i+'        command += ["--vocal-audio",str(vocal_audio)]\n'+i+'        engine.log(f"Détection onset vocal: lead_vocals -> {vocal_audio}")\n\n')
        text=text[:m.start()]+add+text[m.start():]
    save(rel,text)

def patch_ui():
    card_rel='templates/song/components/_lab_song_card.html.twig'
    card='''<section class="panel chordslab-song-card" data-lab-song-card data-lab-beats="{{ (beat_events|default([]))|json_encode|e('html_attr') }}">\n    <div><span>{{ 'song.title'|trans }}</span><strong>{{ song.title }}</strong></div>\n    <div><span>{{ 'song.artist'|trans }}</span><strong>{{ song.artist }}</strong></div>\n    <div><span>{{ 'chordslab.key'|trans({}, 'chordslab') }}</span><strong>{{ song.keySignature ?: '—' }}</strong></div>\n    <div><span>{{ 'song.time_signature'|trans }}</span><strong>{{ song.timeSignature }}</strong></div>\n    <div><span>{{ 'song.capo'|trans }}</span><strong>{{ song.capo }}</strong></div>\n    <div class="chordslab-tempo-value"><span>Tempo</span><strong data-lab-tempo>Tempo = —</strong></div>\n</section>\n'''
    save(card_rel,card)
    js='''(() => {\n\'use strict\';\nfor(const card of document.querySelectorAll(\'[data-lab-song-card]\')){\n const out=card.querySelector(\'[data-lab-tempo]\'); if(!out)continue;\n let beats=[]; try{beats=JSON.parse(card.dataset.labBeats||\'[]\')}catch(_){beats=[]}\n if(!Array.isArray(beats)||beats.length<3){out.textContent=\'Tempo = —\';continue}\n const d=[]; for(let i=1;i<beats.length;i++){const x=Number(beats[i].start_ms)-Number(beats[i-1].start_ms);if(Number.isFinite(x)&&x>=180&&x<=2000)d.push(x)}\n if(!d.length){out.textContent=\'Tempo = —\';continue} d.sort((a,b)=>a-b); const m=Math.floor(d.length/2); const med=d.length%2?d[m]:(d[m-1]+d[m])/2; const bpm=Math.round(60000/med); out.textContent=Number.isFinite(bpm)&&bpm>0?`Tempo = ${bpm}`:\'Tempo = —\';\n}\n})();\n'''
    save('public/assets/js/lab-song-card.js',js)
    chord_rel='templates/song/chordslab.html.twig'; chord=read(chord_rel)
    if "_lab_song_card.html.twig" not in chord:
        chord,n=re.subn(r'<section class="panel chordslab-song-card">.*?</section>',"{% include 'song/components/_lab_song_card.html.twig' with {song:song, beat_events:beat_events} %}",chord,count=1,flags=re.S)
        if n!=1: raise RuntimeError('ChordsLab card block not found.')
    if '/assets/js/lab-song-card.js' not in chord:
        chord=chord.replace('{% block javascripts %}','{% block javascripts %}\n<script src="/assets/js/lab-song-card.js?v=20260928r38_8"></script>',1)
    save(chord_rel,chord)
    lyr_rel='templates/song/lyricslab.html.twig'; lyr=read(lyr_rel)
    lyr=lyr.replace("{% include 'song/components/_lab_song_card.html.twig' with {song:song} %}","{% include 'song/components/_lab_song_card.html.twig' with {song:song, beat_events:beat_events} %}",1)
    if 'data-song-id="{{ song.id }}"' not in lyr:
        lyr,n=re.subn(r'(\s+data-lyricslab\b)',r'\1\n         data-song-id="{{ song.id }}"',lyr,count=1)
        if n!=1: raise RuntimeError('LyricsLab root anchor not found.')
    if '/assets/js/lab-song-card.js' not in lyr:
        lyr=lyr.replace('{% block javascripts %}','{% block javascripts %}\n<script src="/assets/js/lab-song-card.js?v=20260928r38_8"></script>',1)
    lyr=re.sub(r'lyricslab-r37\.js\?v=[^"\']+','lyricslab-r37.js?v=20260928r38_8',lyr,count=1)
    save(lyr_rel,lyr)
    jsrel='public/assets/js/lyricslab-r37.js'; t=read(jsrel)
    t=t.replace('const diagramStorageKey=`ezscore:lyricslab:diagram:${location.pathname}`;','const diagramStorageKey=`ezscore:lyricslab:diagram:${root.dataset.songId||location.pathname}`;',1)
    save(jsrel,t)

def main():
    patch_analyzer(); patch_worker(); patch_ui()
    print(f'[OK] Backup: {BACKUP}')
    print('R38_8_INSTALL_OK')

if __name__=='__main__': main()
