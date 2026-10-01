#!/usr/bin/env python3
from pathlib import Path
import re, sys
ROOT=Path(sys.argv[1] if len(sys.argv)>1 else r"H:\EZScore_v1").resolve()
ASSETS=Path(__file__).resolve().parent/'r38_13_assets'
JS=ROOT/'public/assets/js/lyricslab-r37.js'; PY=ROOT/'analysis/lyrics_timeline_analysis.py'; TWIG=ROOT/'templates/song/lyricslab.html.twig'
def asset(name): return (ASSETS/name).read_text(encoding='utf-8')
def once(text,old,new,label):
    n=text.count(old)
    if n!=1: raise RuntimeError(f"{label}: expected 1 anchor, found {n}")
    return text.replace(old,new,1)

def patch_js():
    s=JS.read_text(encoding='utf-8')
    if 'R38.13 canonical ChordsLab projection' in s: print('R38_13_JS_ALREADY_INSTALLED'); return
    if 'const displayStarts=words.map' in s or 'dataDisplayStart' in s: raise RuntimeError('R38.11/R38.12 detected; restore R38.10')
    s=once(s,"const beats=parse(root.dataset.beats).sort((a,b)=>Number(a.start_ms)-Number(b.start_ms));",asset('js_projection.txt'),'JS projection')
    s=once(s,"const left=xBeat(i),next=i+1<beats.length?xBeat(i+1):left+spacing,cell=document.createElement('div');cell.className='lyrics-ribbon-beat'+(bn===0?' measure-start':'');","const displayBeatIndex=Number(b.display_beat_index??bn),left=xBeat(i),next=i+1<beats.length?xBeat(i+1):left+spacing,cell=document.createElement('div');cell.className='lyrics-ribbon-beat'+(displayBeatIndex===0?' measure-start':'');",'JS boundary')
    s=once(s,"if(bn===0){const m=document.createElement('small');m.className='lyrics-ribbon-measure';m.textContent='#'+(Number(b.measure_index||0)+1);cell.appendChild(m)}","if(displayBeatIndex===0){const m=document.createElement('small');m.className='lyrics-ribbon-measure';m.textContent='#'+(Number(b.display_measure_index??b.measure_index??0)+1);cell.appendChild(m)}",'JS measure label')
    JS.write_text(s,encoding='utf-8'); print('R38_13_JS_OK')

def patch_py():
    s=PY.read_text(encoding='utf-8')
    if 'def _r3813_syllabify_french' in s: print('R38_13_PY_ALREADY_INSTALLED'); return
    s=once(s,asset('py_tokens_old.txt'),asset('py_tokens_new.txt'),'PY punctuation')
    anchor='def _r3810_curve_sample(left_time: int, right_time: int, recognized_times: list[int], position: int, count: int) -> int:\n'
    s=once(s,anchor,asset('py_helpers.txt')+anchor,'PY syllable helpers')
    s=once(s,asset('py_gap_old.txt'),asset('py_gap_new.txt'),'PY syllabic gaps')
    s=once(s,'    lexical = sum(1 for row in rows if row.get("alignment") == "lexical_anchor")\n    resampled = sum(1 for row in rows if row.get("alignment") == "acoustic_resample")','    rows = _r3813_attach_syllables(rows, acoustic_t0)\n    lexical = sum(1 for row in rows if row.get("alignment") == "lexical_anchor")\n    resampled = sum(1 for row in rows if row.get("alignment") in {"acoustic_resample", "syllabic_acoustic_resample"})','PY attach')
    s=once(s,asset('py_payload_old.txt'),asset('py_payload_new.txt'),'PY payload')
    old="        'version': 'r38.10-sequential-variable-timeline',\n        'model': Path(model_path).name,\n        'languages': languages,\n        'provided_words': len(provided),\n        'recognized_words': len(words),\n        'words': payload_words,\n    })"
    new="        'version': 'r38.13-canonical-grid-syllabic-timeline',\n        'model': Path(model_path).name,\n        'languages': languages,\n        'provided_words': len(provided),\n        'recognized_words': len(words),\n        'syllables_count': len(payload_syllables),\n        'syllables': payload_syllables,\n        'words': payload_words,\n    })"
    s=once(s,old,new,'PY output')
    PY.write_text(s,encoding='utf-8'); print('R38_13_PY_OK')

def patch_twig():
    s=TWIG.read_text(encoding='utf-8')
    if '20260928r38_13' in s: print('R38_13_TWIG_ALREADY_INSTALLED'); return
    s,n=re.subn(r'(/assets/js/lyricslab-r37\.js\?v=)[^"\']+',r'\g<1>20260928r38_13',s,count=1)
    if n!=1: raise RuntimeError(f'Twig cache buster: found {n}')
    TWIG.write_text(s,encoding='utf-8'); print('R38_13_TWIG_OK')

for p in (JS,PY,TWIG):
    if not p.is_file(): raise SystemExit(f'Missing: {p}')
patch_js(); patch_py(); patch_twig(); print('R38_13_INSTALL_OK')
