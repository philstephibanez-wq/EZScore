#!/usr/bin/env python3
from __future__ import annotations
from datetime import datetime
from pathlib import Path
import re, shutil, sys

ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
BACKUP = ROOT / 'var' / 'backup' / ('r38-7a-' + datetime.now().strftime('%Y%m%d-%H%M%S'))

def read(rel):
    p=ROOT/rel
    if not p.is_file(): raise RuntimeError(f'Missing required file: {rel}')
    return p.read_text(encoding='utf-8')

def backup(p):
    if not p.exists(): return
    dst=BACKUP/p.relative_to(ROOT); dst.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(p,dst)

def save(rel,text):
    p=ROOT/rel; p.parent.mkdir(parents=True,exist_ok=True)
    old=p.read_text(encoding='utf-8') if p.exists() else None
    if old==text: print(f'[OK] {rel}: already applied'); return
    if p.exists(): backup(p)
    p.write_text(text,encoding='utf-8',newline='\n'); print(f'[OK] {rel}')

def replace_func(text,name,replacement):
    m=re.search(rf'(?m)^def {re.escape(name)}\s*\(',text)
    if not m: return text,False
    n=re.search(r'(?m)^def [A-Za-z_]\w*\s*\(',text[m.end():])
    end=m.end()+n.start() if n else len(text)
    return text[:m.start()]+replacement.rstrip()+'\n\n'+text[end:],True

INTERPOLATE='''def interpolate_unmatched(rows: list[dict]) -> list[dict]:
    known=[i for i,row in enumerate(rows) if row.get('start_ms') is not None]
    if not known: raise RuntimeError('No acoustic anchor available for provided lyrics')
    for i,row in enumerate(rows):
        if row.get('start_ms') is not None: continue
        left=max((k for k in known if k<i),default=None); right=min((k for k in known if k>i),default=None)
        if left is None: continue
        if right is not None:
            span=max(1,right-left); ratio=(i-left)/span; a=int(rows[left]['end_ms']); b=int(rows[right]['start_ms'])
            t=max(a,min(b,int(round(a+(b-a)*ratio))))
            row.update(start_ms=t,end_ms=max(t+40,min(b,t+140)),confidence=0.30)
        else:
            t=int(rows[left]['end_ms'])+max(80,(i-left-1)*180); row.update(start_ms=t,end_ms=t+160,confidence=0.20)
    return rows
'''

HELPERS='''def detect_first_vocal_onset(audio_path: str | None) -> tuple[int | None, dict]:
    if not audio_path or not Path(audio_path).is_file(): return None, {'method':'unavailable','found':False}
    import numpy as np, whisper
    audio=whisper.load_audio(audio_path)
    if audio is None or len(audio)<SAMPLE_RATE//4: return None, {'method':'empty','found':False}
    frame=max(1,int(SAMPLE_RATE*0.030)); hop=max(1,int(SAMPLE_RATE*0.010))
    sq=np.asarray(audio,dtype=np.float32)**2
    kernel=np.ones(frame,dtype=np.float32)/float(frame)
    rms=np.sqrt(np.convolve(sq,kernel,mode='valid')[::hop]+1e-12)
    db=20.0*np.log10(rms+1e-9)
    p20=float(np.percentile(db,20)); p90=float(np.percentile(db,90)); spread=max(6.0,p90-p20)
    threshold=min(p90-5.0,p20+max(10.0,spread*0.38))
    active=db>=threshold; window=max(1,int(round(0.180/(hop/SAMPLE_RATE)))); need=max(1,int(round(0.120/(hop/SAMPLE_RATE))))
    counts=np.convolve(active.astype(np.int16),np.ones(window,dtype=np.int16),mode='same')
    candidates=np.flatnonzero(counts>=need)
    if candidates.size==0: return None, {'method':'rms_sustained','found':False,'threshold_db':round(threshold,2)}
    idx=int(candidates[0]); shoulder=threshold-6.0
    while idx>0 and db[idx-1]>=shoulder: idx-=1
    onset_ms=max(0,int(round((idx*hop)*1000.0/SAMPLE_RATE)))
    return onset_ms, {'method':'rms_sustained','found':True,'threshold_db':round(threshold,2)}

def _r387_token_similarity(a: str,b: str)->float:
    if not a or not b:return 0.0
    if a==b:return 1.0
    return difflib.SequenceMatcher(a=a,b=b,autojunk=False).ratio()
'''

ALIGN='''def align_provided_text(provided: list[dict], recognized: list[dict], first_vocal_onset_ms: int | None = None) -> list[dict]:
    if not provided:return []
    if not recognized and first_vocal_onset_ms is None: raise RuntimeError('No timed words or vocal onset available')
    rows=[dict(row,start_ms=None,end_ms=None,confidence=0.0,language=None) for row in provided]
    onset=max(0,int(first_vocal_onset_ms if first_vocal_onset_ms is not None else recognized[0]['start_ms']))
    anchor_method='vocal_stem_acoustic_onset' if first_vocal_onset_ms is not None else 'whisper_first_word_fallback'
    first_end=onset+160; first_lang=None; cursor=0
    for ri,src in enumerate(recognized):
        if int(src.get('end_ms',0))<onset-350: continue
        cursor=ri
        if int(src.get('start_ms',0))<=onset+1800:
            first_end=max(onset+100,int(src.get('end_ms',onset+160))); first_lang=src.get('language')
        break
    rows[0].update(start_ms=onset,end_ms=first_end,confidence=1.0,language=first_lang,anchor=anchor_method)
    last_time=onset; search_from=cursor
    for pi in range(1,len(provided)):
        target=provided[pi].get('norm') or ''
        if not target: continue
        best=None; stop=min(len(recognized),search_from+36)
        same_section=provided[pi].get('section_label')==provided[pi-1].get('section_label')
        max_start=last_time+(20000 if same_section else 10**12)
        for ri in range(search_from,stop):
            src=recognized[ri]; src_start=int(src.get('start_ms',0))
            if int(src.get('end_ms',0))<last_time-120: continue
            if src_start>max_start: break
            score=_r387_token_similarity(target,src.get('norm') or '')
            if score>=0.94: best=(ri,src,score); break
            if score>=0.80 and (best is None or score>best[2]): best=(ri,src,score)
        if best is None: continue
        ri,src,score=best; start=max(last_time,int(src['start_ms'])); end=max(start+80,int(src.get('end_ms',start+120)))
        rows[pi].update(start_ms=start,end_ms=end,confidence=min(float(src.get('confidence',0.0) or 0.0),score),language=src.get('language'))
        last_time=start; search_from=ri+1
    rows=interpolate_unmatched(rows)
    previous=-1
    for row in rows:
        if row.get('start_ms') is None: continue
        start=max(previous,int(row['start_ms'])); end=max(start+40,int(row.get('end_ms') or start+120)); row['start_ms']=start; row['end_ms']=end; previous=start
    return rows
'''

def patch_analyzer():
    rel='analysis/lyrics_timeline_analysis.py'; text=read(rel)
    text,ok=replace_func(text,'interpolate_unmatched',INTERPOLATE)
    if not ok: raise RuntimeError('interpolate_unmatched() not found; no unsafe edit applied.')
    for name in ('detect_first_vocal_onset','_r387_token_similarity','_token_similarity'):
        text,_=replace_func(text,name,'')
    text,ok=replace_func(text,'align_provided_text',ALIGN)
    if not ok: raise RuntimeError('align_provided_text() not found; no unsafe edit applied.')
    pos=text.find('def align_provided_text('); text=text[:pos]+HELPERS.rstrip()+'\n\n'+text[pos:]
    if '--vocal-audio' not in text:
        m=re.search(r'(?m)^(\s*)parser\.add_argument\([\'\"]--audio[\'\"],\s*required=True\)\s*$',text)
        if not m: raise RuntimeError('Analyzer --audio parser anchor not found.')
        text=text[:m.end()]+"\n"+m.group(1)+"parser.add_argument('--vocal-audio')"+text[m.end():]
    call=re.search(r'(?m)^(?P<indent>\s*)rows\s*=\s*align_provided_text\(provided,\s*words(?:,\s*[^\n\)]*)?\)\s*$',text)
    if not call: raise RuntimeError('Analyzer align call not found; no unsafe edit applied.')
    ind=call.group('indent')
    block=(f"{ind}progress(args.progress_file,80,'onset','Détection acoustique de la première entrée vocale')\n"
           f"{ind}vocal_onset_ms,onset_meta=detect_first_vocal_onset(args.vocal_audio)\n"
           f"{ind}if vocal_onset_ms is None:\n{ind}    vocal_onset_ms=int(words[0]['start_ms'])\n{ind}    onset_meta={{'method':'whisper_first_word_fallback','found':True}}\n"
           f"{ind}print(f\"[LYRICS] First vocal onset: {{vocal_onset_ms}} ms ({{onset_meta.get('method')}})\",flush=True)\n"
           f"{ind}progress(args.progress_file,84,'align',f'Ancrage initial à {{vocal_onset_ms/1000:.3f}}s')\n"
           f"{ind}rows=align_provided_text(provided,words,vocal_onset_ms)")
    text=text[:call.start()]+block+text[call.end():]
    matches=list(re.finditer(r"(?m)^(\s*)'recognized_words': len\(words\),\s*$",text))
    if matches and "'vocal_onset_ms': vocal_onset_ms" not in text:
        pm=matches[-1]; extra=pm.group(0)+'\n'+pm.group(1)+"'vocal_onset_ms': vocal_onset_ms,\n"+pm.group(1)+"'vocal_onset': onset_meta,"
        text=text[:pm.start()]+extra+text[pm.end():]
    text=text.replace("'version': 'r36.1-large-v3-multilingual'","'version': 'r38.7a-acoustic-onset-monotonic'")
    save(rel,text)

def patch_worker():
    rel='worker_app/lyrics_worker_r37.py'; text=read(rel)
    if '--vocal-audio' not in text:
        m=re.search(r'(?m)^(\s*)if mode=="align":\s*\n\1\s+lyrics_file=paths\.get\("lyrics_file"\)',text)
        if not m: raise RuntimeError('Lyrics worker align anchor not found.')
        ind=m.group(1); block=(f'{ind}if mode=="align":\n{ind}    vocal_audio=paths.get("lead_vocals")\n{ind}    if vocal_audio and Path(str(vocal_audio)).is_file():\n{ind}        command += ["--vocal-audio",str(vocal_audio)]\n{ind}        engine.log(f"Détection onset vocal: lead_vocals -> {{vocal_audio}}")\n\n')
        text=text[:m.start()]+block+text[m.start():]
    save(rel,text)

CARD='''<section class="panel chordslab-song-card" data-lab-song-card data-lab-beats="{{ (beat_events|default([]))|json_encode|e('html_attr') }}">\n    <div><span>{{ 'song.title'|trans }}</span><strong>{{ song.title }}</strong></div>\n    <div><span>{{ 'song.artist'|trans }}</span><strong>{{ song.artist }}</strong></div>\n    <div><span>{{ 'chordslab.key'|trans({}, 'chordslab') }}</span><strong>{{ song.keySignature ?: '—' }}</strong></div>\n    <div><span>{{ 'song.time_signature'|trans }}</span><strong>{{ song.timeSignature }}</strong></div>\n    <div><span>{{ 'song.capo'|trans }}</span><strong>{{ song.capo }}</strong></div>\n    <div class="chordslab-tempo-value"><span>Tempo</span><strong data-lab-tempo>Tempo = —</strong></div>\n</section>\n'''
JS='''(()=>{'use strict';for(const card of document.querySelectorAll('[data-lab-song-card]')){const out=card.querySelector('[data-lab-tempo]');if(!out)continue;let beats=[];try{beats=JSON.parse(card.dataset.labBeats||'[]')}catch(_){beats=[]}if(!Array.isArray(beats)||beats.length<3){out.textContent='Tempo = —';continue}const deltas=[];for(let i=1;i<beats.length;i++){const d=Number(beats[i].start_ms)-Number(beats[i-1].start_ms);if(Number.isFinite(d)&&d>=180&&d<=2000)deltas.push(d)}if(!deltas.length){out.textContent='Tempo = —';continue}deltas.sort((a,b)=>a-b);const m=Math.floor(deltas.length/2),median=deltas.length%2?deltas[m]:(deltas[m-1]+deltas[m])/2,bpm=Math.round(60000/median);out.textContent=Number.isFinite(bpm)&&bpm>0?`Tempo = ${bpm}`:'Tempo = —'}})();\n'''

def patch_ui():
    save('templates/song/components/_lab_song_card.html.twig',CARD); save('public/assets/js/lab-song-card.js',JS)
    rel='templates/song/chordslab.html.twig'; t=read(rel)
    if '_lab_song_card.html.twig' not in t:
        t,n=re.subn(r'<section class="panel chordslab-song-card">.*?</section>',"{% include 'song/components/_lab_song_card.html.twig' with {song:song, beat_events:beat_events} %}",t,count=1,flags=re.S)
        if n!=1: raise RuntimeError('ChordsLab song card block not found.')
    if '/assets/js/lab-song-card.js' not in t:t=t.replace('{% block javascripts %}','{% block javascripts %}\n<script src="/assets/js/lab-song-card.js?v=20260928r38_7a"></script>',1)
    save(rel,t)
    rel='templates/song/lyricslab.html.twig'; t=read(rel)
    t=t.replace("{% include 'song/components/_lab_song_card.html.twig' with {song:song} %}","{% include 'song/components/_lab_song_card.html.twig' with {song:song, beat_events:beat_events} %}",1)
    if 'data-song-id="{{ song.id }}"' not in t:t,n=re.subn(r'(\s+data-lyricslab\b)',r'\1\n         data-song-id="{{ song.id }}"',t,count=1)
    if '/assets/js/lab-song-card.js' not in t:t=t.replace('{% block javascripts %}','{% block javascripts %}\n<script src="/assets/js/lab-song-card.js?v=20260928r38_7a"></script>',1)
    t=re.sub(r'lyricslab-r37\.js\?v=[^"\']+','lyricslab-r37.js?v=20260928r38_7a',t,count=1)
    t=re.sub(r'\s*<script[^>]+lyricslab-r38-6-fix\.js[^>]*></script>\s*','\n',t,count=1)
    save(rel,t)
    rel='public/assets/js/lyricslab-r37.js'; t=read(rel)
    t=t.replace("const diagramStorageKey=`ezscore:lyricslab:diagram:${location.pathname}`;","const diagramStorageKey=`ezscore:lyricslab:diagram:${root.dataset.songId||location.pathname}`;",1)
    save(rel,t)

def main():
    patch_analyzer(); patch_worker(); patch_ui(); print(f'[OK] Backup: {BACKUP}'); print('R38_7A_INSTALL_OK')
if __name__=='__main__': main()
