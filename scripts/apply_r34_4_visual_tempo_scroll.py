#!/usr/bin/env python3
from __future__ import annotations
from datetime import datetime
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[1]
BACKUP=ROOT/'var'/'backup'/('r34-4-visual-tempo-scroll-'+datetime.now().strftime('%Y%m%d-%H%M%S'))

CSS_BLOCK = r'''
/* R34.4 — chord typography / guitar toggle / tempo */
.chord-measure-notation .chord-slot.is-long,
.chord-measure-notation .chord-slot.is-very-long{
    font-size:14px!important;
    letter-spacing:normal!important;
}
.chord-measure-notation .chord-slot .chord-label-root{
    font-size:15px!important;
    font-weight:800!important;
    line-height:1!important;
    flex:0 0 auto!important;
}
.chord-measure-notation .chord-slot .chord-label-suffix{
    font-size:11px!important;
    line-height:1!important;
    margin-left:1px!important;
    flex:0 0 auto!important;
}
.chord-measure-notation .chord-slot .chord-quality-maj{
    font-size:8px!important;
    line-height:1!important;
    vertical-align:super!important;
    letter-spacing:0!important;
    margin:0 1px 0 0!important;
}
.chord-measure-notation .chord-slot .chord-label-bass{
    font-size:10px!important;
    line-height:1!important;
    margin-left:1px!important;
}
.chordslab-settings-grid .chordslab-diagram-toggle,
.chordslab-settings-grid .chordslab-diagram-inline{
    grid-column:1 / -1!important;
    display:flex!important;
    grid-template-columns:none!important;
    width:max-content!important;
    max-width:100%!important;
    align-items:center!important;
    gap:8px!important;
    padding:2px 0!important;
    margin:0!important;
}
.chordslab-settings-grid .chordslab-diagram-toggle>span,
.chordslab-settings-grid .chordslab-diagram-inline>span{
    display:inline!important;
    margin:0!important;
    white-space:nowrap!important;
    font-size:13px!important;
    line-height:1.2!important;
    font-weight:600!important;
    text-transform:none!important;
    letter-spacing:0!important;
    color:#eef5f8!important;
}
.chordslab-settings-grid .chordslab-diagram-toggle input[type=checkbox],
.chordslab-settings-grid .chordslab-diagram-inline input[type=checkbox]{
    margin:0!important;
    flex:0 0 auto!important;
}
.chordslab-settings-save-state{
    grid-column:1 / -1!important;
    margin-top:-4px!important;
    min-width:0!important;
    white-space:nowrap!important;
}
.chordslab-tempo-value{
    display:grid;
    gap:3px;
}
.chordslab-tempo-value span{
    font-size:10px;
    text-transform:uppercase;
    color:#91a3ad;
    letter-spacing:.05em;
}
.chordslab-tempo-value strong{font-size:15px;}
@media(max-width:640px){
    .chordslab-settings-grid .chordslab-diagram-toggle,
    .chordslab-settings-grid .chordslab-diagram-inline{width:100%!important}
    .chordslab-settings-grid .chordslab-diagram-toggle>span,
    .chordslab-settings-grid .chordslab-diagram-inline>span{white-space:normal!important}
}
'''

SCROLL_JS = r'''(() => {
'use strict';
const root=document.querySelector('[data-chordslab]');
const strip=root?.querySelector('[data-chordslab-measures]');
const keepAwake=document.querySelector('[data-chordslab-wakelock]');
const mixer=document.querySelector('[data-stem-mixer]');
if(!root||!strip)return;
let wakeLock=null;
let playbackActive=false;
const key='ezscore.chordslab.keepAwake';
function centerSlot(slot,smooth=true){
 if(!playbackActive||!slot)return;
 const sr=strip.getBoundingClientRect(),cr=slot.getBoundingClientRect();
 const delta=(cr.left+cr.width/2)-(sr.left+sr.width/2);
 if(Math.abs(delta)>2)strip.scrollBy({left:delta,behavior:smooth?'smooth':'auto'});
}
root.addEventListener('ezscore:chord-current',e=>{
 if(!playbackActive)return;
 const seq=e.detail?.beatSeq;
 if(seq===undefined||seq===null)return;
 centerSlot(strip.querySelector(`.chord-slot[data-beat-seq="${seq}"]`),true);
});
async function requestWakeLock(){
 if(!playbackActive||!keepAwake?.checked||!('wakeLock' in navigator)||document.visibilityState!=='visible')return;
 try{if(!wakeLock)wakeLock=await navigator.wakeLock.request('screen')}catch(_){wakeLock=null}
}
async function releaseWakeLock(){const w=wakeLock;wakeLock=null;if(w){try{await w.release()}catch(_){}}}
if(keepAwake){
 const saved=localStorage.getItem(key);
 keepAwake.checked=saved===null?true:saved==='1';
 keepAwake.addEventListener('change',()=>{
  localStorage.setItem(key,keepAwake.checked?'1':'0');
  if(keepAwake.checked)requestWakeLock();else releaseWakeLock();
 });
}
mixer?.querySelector('[data-mixer-play]')?.addEventListener('click',()=>{playbackActive=true;requestWakeLock()});
mixer?.querySelector('[data-mixer-pause]')?.addEventListener('click',()=>{playbackActive=false;releaseWakeLock()});
mixer?.querySelector('[data-mixer-stop]')?.addEventListener('click',()=>{playbackActive=false;releaseWakeLock()});
document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='visible')requestWakeLock();else releaseWakeLock()});
window.addEventListener('pagehide',releaseWakeLock);
window.addEventListener('beforeunload',releaseWakeLock);
})();
'''

TEMPO_JS = r'''
/* R34.4 tempo display: derived from canonical beat timeline, no reanalysis required */
(function installTempoDisplay(){
 const card=document.querySelector('.chordslab-song-card');
 const root=document.querySelector('[data-chordslab]');
 if(!card||!root||card.querySelector('[data-chordslab-tempo]'))return;
 let beats=[];
 try{beats=JSON.parse(root.dataset.beats||'[]')}catch(_){beats=[]}
 if(!Array.isArray(beats)||beats.length<3)return;
 const deltas=[];
 for(let i=1;i<beats.length;i++){
  const d=Number(beats[i].start_ms)-Number(beats[i-1].start_ms);
  if(Number.isFinite(d)&&d>=180&&d<=2000)deltas.push(d);
 }
 if(!deltas.length)return;
 deltas.sort((a,b)=>a-b);
 const mid=Math.floor(deltas.length/2);
 const median=deltas.length%2?deltas[mid]:(deltas[mid-1]+deltas[mid])/2;
 const tempo=Math.round(60000/median);
 if(!Number.isFinite(tempo)||tempo<=0)return;
 const box=document.createElement('div');
 box.className='chordslab-tempo-value';
 box.dataset.chordslabTempo='1';
 box.innerHTML=`<span>Tempo</span><strong>Tempo = ${tempo}</strong>`;
 card.appendChild(box);
})();
'''

def backup(path:Path):
    if not path.exists(): return
    dst=BACKUP/path.relative_to(ROOT)
    dst.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(path,dst)

def patch_css():
    path=ROOT/'public/assets/css/chordslab.css'
    text=path.read_text(encoding='utf-8')
    if 'R34.4 — chord typography / guitar toggle / tempo' in text:
        print('[OK] CSS R34.4 already applied'); return
    backup(path)
    path.write_text(text.rstrip()+"\n"+CSS_BLOCK+"\n",encoding='utf-8',newline='\n')
    print('[OK] public/assets/css/chordslab.css modified')

def patch_scroll():
    path=ROOT/'public/assets/js/chordslab-r33-1.js'
    current=path.read_text(encoding='utf-8') if path.exists() else ''
    if current==SCROLL_JS:
        print('[OK] scroll/wakelock JS already applied'); return
    backup(path)
    path.write_text(SCROLL_JS,encoding='utf-8',newline='\n')
    print('[OK] public/assets/js/chordslab-r33-1.js modified')

def patch_tempo():
    path=ROOT/'public/assets/js/chordslab.js'
    text=path.read_text(encoding='utf-8')
    marker='R34.4 tempo display: derived from canonical beat timeline'
    if marker in text:
        print('[OK] tempo JS already applied'); return
    backup(path)
    path.write_text(text.rstrip()+"\n"+TEMPO_JS+"\n",encoding='utf-8',newline='\n')
    print('[OK] public/assets/js/chordslab.js modified')

def main():
    patch_css(); patch_scroll(); patch_tempo()
    print('[OK] Backup:',BACKUP)
    print('[OK] R34.4 applied — 3 tracked source files modified.')

if __name__=='__main__':
    main()
