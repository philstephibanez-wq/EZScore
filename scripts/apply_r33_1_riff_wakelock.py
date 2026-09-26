#!/usr/bin/env python3
from __future__ import annotations
from datetime import datetime
from pathlib import Path
import re
import shutil

ROOT=Path(__file__).resolve().parents[1]
PAYLOAD=ROOT/'scripts'/'_payload'
BACKUP=ROOT/'var'/'backup'/('r33-1a-riff-wakelock-'+datetime.now().strftime('%Y%m%d-%H%M%S'))

def backup(p):
    p=Path(p)
    if not p.exists(): return
    d=BACKUP/p.relative_to(ROOT)
    d.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(p,d)

def save(p,text,label):
    p=Path(p);old=p.read_text(encoding='utf-8')
    if old==text:
        print('[OK]',label,': already applied');return
    backup(p);p.write_text(text,encoding='utf-8',newline='\n');print('[OK]',label)

def install(rel):
    s=PAYLOAD/rel;d=ROOT/rel;c=s.read_text(encoding='utf-8')
    if d.exists() and d.read_text(encoding='utf-8')==c:
        print('[OK]',rel,': already applied');return
    backup(d);d.parent.mkdir(parents=True,exist_ok=True);d.write_text(c,encoding='utf-8',newline='\n');print('[OK]',rel)

def snip(n): return (PAYLOAD/'snippets'/n).read_text(encoding='utf-8')

def patch_js():
    p=ROOT/'public/assets/js/chordslab.js';t=p.read_text(encoding='utf-8')
    if 'ezscore:chord-current' in t:
        print('[OK] centered event already applied');return

    # R33 was delivered in compact/minified form. Patch that exact structure first.
    compact="if(slot){slot.classList.add('is-current');const m=slot.closest('.chord-measure');m?.classList.add('is-current');m?.scrollIntoView({behavior:'smooth',inline:'center',block:'nearest'})}"
    compact_new="if(slot){slot.classList.add('is-current');const m=slot.closest('.chord-measure');m?.classList.add('is-current');root.dispatchEvent(new CustomEvent('ezscore:chord-current',{detail:{beatSeq:seq,timeMs:ms}}))}"
    if compact in t:
        save(p,t.replace(compact,compact_new,1),'centered prompter event (compact R33)')
        return

    # Also support the formatted development variant.
    old=snip('highlight_old.txt');new=snip('highlight_new.txt')
    if old in t:
        save(p,t.replace(old,new,1),'centered prompter event (formatted R33)')
        return

    # Last safe fallback: locate only the current-slot block, remove scrollIntoView,
    # and emit the R33.1 event. Refuse if the expected structures are absent.
    if 'const slot=measuresEl.querySelector(`.chord-slot[data-beat-seq="${seq}"]`);' in t:
        pattern=re.compile(r"if\(slot\)\{slot\.classList\.add\('is-current'\);const m=slot\.closest\('\.chord-measure'\);m\?\.classList\.add\('is-current'\);(?:m\?\.scrollIntoView\(\{behavior:'smooth',inline:'center',block:'nearest'\}\))?\}")
        replacement="if(slot){slot.classList.add('is-current');const m=slot.closest('.chord-measure');m?.classList.add('is-current');root.dispatchEvent(new CustomEvent('ezscore:chord-current',{detail:{beatSeq:seq,timeMs:ms}}))}"
        patched,count=pattern.subn(replacement,t,count=1)
        if count==1:
            save(p,patched,'centered prompter event (structural fallback)')
            return

    raise RuntimeError('Unsupported chordslab.js variant: current-beat block not found. No unsafe edit was applied.')

def patch_template():
    p=ROOT/'templates/song/chordslab.html.twig';t=p.read_text(encoding='utf-8')
    if 'data-chordslab-wakelock' not in t:
        a="        <span class=\"stem-mixer-state\" data-mixer-state>{{ 'stems.mixer.ready'|trans({}, 'stems') }}</span>\n"
        if a not in t: raise RuntimeError('transport anchor not found')
        t=t.replace(a,a+snip('wakelock.html'),1)
    if 'chordslab-r33-1.js' not in t:
        candidates=[
            '<script src="/assets/js/chordslab.js?v=20260926r33"></script>\n',
            '<script src="/assets/js/chordslab.js?v=20260926r32"></script>\n',
        ]
        anchor=next((x for x in candidates if x in t),None)
        if anchor is None: raise RuntimeError('Chordslab script anchor not found')
        t=t.replace(anchor,anchor+'<script src="/assets/js/chordslab-r33-1.js?v=20260926r33_1a"></script>\n',1)
    t=t.replace('/assets/css/chordslab.css?v=20260926r32','/assets/css/chordslab.css?v=20260926r33_1a')
    t=t.replace('/assets/css/chordslab.css?v=20260926r33_1','/assets/css/chordslab.css?v=20260926r33_1a')
    save(p,t,'wake lock control')

def patch_css():
    p=ROOT/'public/assets/css/chordslab.css';t=p.read_text(encoding='utf-8')
    if 'R33.1 RiffStation-like centered prompter' in t:
        print('[OK] CSS already applied');return
    save(p,t.rstrip()+'\n'+snip('css_add.txt'),'centered prompter CSS')

def patch_trans():
    for loc,s in [('fr','trans_fr.txt'),('en','trans_en.txt')]:
        p=ROOT/'translations'/f'chordslab.{loc}.yaml';t=p.read_text(encoding='utf-8')
        if '  keep_awake:' in t:
            print(f'[OK] wake lock translation {loc}: already applied');continue
        save(p,t.rstrip()+'\n'+snip(s),f'wake lock translation {loc}')

def patch_docs():
    p=ROOT/'docs/CAHIER_DES_CHARGES.md'
    if p.is_file():
        t=p.read_text(encoding='utf-8');m='## 40. ChordsLab — analyse simplifiée type RiffStation et maintien écran'
        if m not in t: save(p,t.rstrip()+'\n'+snip('cdc_section.txt'),'CDC R33.1')
        else: print('[OK] CDC R33.1: already applied')
    p=ROOT/'recette.md'
    if p.is_file():
        t=p.read_text(encoding='utf-8');m='## 31. Recette R33.1 — accords simplifiés / prompteur centré / wake lock'
        if m not in t: save(p,t.rstrip()+'\n'+snip('recette_section.txt'),'recette R33.1')
        else: print('[OK] recette R33.1: already applied')

def main():
    for rel in ['analysis/chord_timeline_analysis.py','src/Service/ChordTimelineAnalysisService.php','public/assets/js/chordslab-r33-1.js']:
        install(rel)
    patch_js();patch_template();patch_css();patch_trans();patch_docs()
    print('[OK] Backup:',BACKUP)
    print('[OK] R33.1a applied.')

if __name__=='__main__': main()
