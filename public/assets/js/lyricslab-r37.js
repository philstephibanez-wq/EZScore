(() => {
'use strict';
const root=document.querySelector('[data-lyricslab]'); if(!root)return;
const parse=v=>{try{return JSON.parse(v||'[]')}catch(_){return[]}};
const chords=parse(root.dataset.chords).sort((a,b)=>a.start_ms-b.start_ms);
const words=parse(root.dataset.lyrics).sort((a,b)=>a.start_ms-b.start_ms);
const host=root.querySelector('[data-lyrics-measures]'); if(!host)return;
const capo=Number(root.dataset.capo||0);
const NOTE={C:0,'C#':1,Db:1,D:2,'D#':3,Eb:3,E:4,F:5,'F#':6,Gb:6,G:7,'G#':8,Ab:8,A:9,'A#':10,Bb:10,B:11};
const SH=['C','C#','D','D#','E','F','F#','G','G#','A','A#','B'],FL=['C','Db','D','Eb','E','F','Gb','G','Ab','A','Bb','B'];
function shown(v){let c=String(v||'.').trim();if(!c||c==='.')return'.';const m=/^([A-G](?:#|b)?)(.*)$/.exec(c);if(!m||NOTE[m[1]]===undefined)return c;const names=m[1].includes('b')?FL:SH;return names[(NOTE[m[1]]-capo+120)%12]+m[2]}
function activeChord(ms){let x=null;for(const e of chords){if(e.start_ms<=ms)x=e;else break}return x}
function payload(w){return w&&typeof w.payload==='object'&&w.payload?w.payload:{}}

host.innerHTML=`<div class="lyrics-simple-prompter">
<div class="lyrics-simple-section" data-section>&nbsp;</div>
<div class="lyrics-simple-chord-wrap"><div class="lyrics-simple-chord-label">Accord courant</div><div class="lyrics-simple-chord" data-chord>.</div></div>
<div class="lyrics-simple-line" data-line></div></div>`;

const sectionEl=host.querySelector('[data-section]'),chordEl=host.querySelector('[data-chord]'),lineEl=host.querySelector('[data-line]');
const header=root.querySelector('.chordslab-prompter-head');
if(header&&!root.querySelector('[data-lyrics-diagram-toggle]')){
 const l=document.createElement('label');l.className='lyrics-simple-diagram-toggle';
 l.innerHTML='<input type="checkbox" data-lyrics-diagram-toggle> Diagramme d’accord';
 header.appendChild(l);
}

const lines=[];let cur=[];
words.forEach((w,i)=>{cur.push(i);if(payload(w).line_break_after){lines.push(cur);cur=[]}});
if(cur.length)lines.push(cur);
const lineByWord=new Map();lines.forEach((l,li)=>l.forEach(i=>lineByWord.set(i,li)));
function activeWord(ms){let i=-1;for(let k=0;k<words.length;k++){if(Number(words[k].start_ms)<=ms)i=k;else break}return i}
function drawLine(i){
 lineEl.innerHTML='';if(i<0)return;
 const li=lineByWord.get(i);if(!Number.isInteger(li))return;
 for(const k of lines[li]){
   const s=document.createElement('span');s.className='lyrics-simple-word';
   s.textContent=words[k].effective||words[k].original||'';
   if(k<i)s.classList.add('past');if(k===i)s.classList.add('current');
   lineEl.appendChild(s);
 }
}
let lastW=-2,lastC='',lastS='';
function render(sec){
 const ms=(Number(sec)||0)*1000,w=activeWord(ms),ce=activeChord(ms),c=shown(ce?.effective||ce?.original||'.'),s=w>=0?String(payload(words[w]).section_label||''):'';
 if(w!==lastW){lastW=w;drawLine(w)}
 if(c!==lastC){lastC=c;chordEl.textContent=c}
 if(s!==lastS){lastS=s;sectionEl.textContent=s||'\u00a0'}
}
document.querySelector('[data-stem-mixer]')?.addEventListener('ezscore:audio-timeupdate',e=>render(e.detail?.time||0));
render(0);

const source=document.querySelector('[data-lyrics-source]'),state=document.querySelector('[data-lyrics-save-state]');
let timer=null;
async function save(){if(!source)return;try{const r=await fetch(source.dataset.saveUrl,{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','Accept':'application/json'},body:JSON.stringify({_token:source.dataset.saveToken,text:source.value})});if(!r.ok)throw 0;if(state)state.textContent='Enregistré'}catch(_){if(state)state.textContent='Échec enregistrement'}}
source?.addEventListener('input',()=>{if(state)state.textContent='Modifié…';clearTimeout(timer);timer=setTimeout(save,450)});

const progress=document.querySelector('[data-lyrics-progress]');
const statusUrl=progress?.dataset.statusUrl||'';
const bar=progress?.querySelector('progress');
const label=progress?.querySelector('[data-lyrics-progress-text]');
const percent=progress?.querySelector('[data-lyrics-progress-percent]');
async function poll(){
 if(!statusUrl)return;
 try{
  const r=await fetch(statusUrl,{headers:{Accept:'application/json'},cache:'no-store',credentials:'same-origin'});
  if(r.ok){
   const d=await r.json(),s=String(d.status||''),p=Number(d.progress||0);
   if(s==='queued'||s==='running'){
    progress.hidden=false;if(bar)bar.value=p;if(percent)percent.textContent=`${p}%`;
    if(label)label.textContent=s==='queued'?'En attente du Worker…':(d.mode==='extract'?'Extraction automatique des paroles…':'Ancrage du texte sur la timeline…');
   }else if(s==='failed'){
    progress.hidden=false;if(percent)percent.textContent='Erreur';if(label)label.textContent=d.error||'Analyse des paroles en échec.';
   }else if(s==='completed'){
    const key=`ezscore.lyrics.job.reloaded.${d.job_id}`;
    if(d.job_id&&sessionStorage.getItem(key)!=='1'){sessionStorage.setItem(key,'1');location.reload();return}
    progress.hidden=true;
   }else progress.hidden=true;
  }
 }catch(_){}
 setTimeout(poll,900);
}
poll();
})();