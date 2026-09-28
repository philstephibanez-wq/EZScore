(() => {
'use strict';
const root=document.querySelector('[data-lyricslab]'); if(!root)return;
const parse=v=>{try{return JSON.parse(v||'[]')}catch(_){return[]}};
const chords=parse(root.dataset.chords).sort((a,b)=>a.start_ms-b.start_ms);
const words=parse(root.dataset.lyrics).sort((a,b)=>a.start_ms-b.start_ms);
const host=root.querySelector('[data-lyrics-measures]'); if(!host)return;
const capo=Number(root.dataset.capo||0);
const NOTE={C:0,'C#':1,Db:1,D:2,'D#':3,Eb:3,E:4,F:5,'F#':6,Gb:6,G:7,'G#':8,Ab:8,A:9,'A#':10,Bb:10,B:11};
const SH=['C','C#','D','D#','E','F','F#','G','G#','A','A#','B'], FL=['C','Db','D','Eb','E','F','Gb','G','Ab','A','Bb','B'];
const SHAPES={C:'x32010',Cm:'x35543',C7:'x32310',Cmaj7:'x32000',D:'xx0232',Dm:'xx0231',D7:'xx0212',E:'022100',Em:'022000',E7:'020100',F:'133211',Fmaj7:'xx3210',G:'320003',G7:'320001',A:'x02220',Am:'x02210',A7:'x02020',B:'x24442',Bm:'x24432',B7:'x21202'};
function shown(v){let c=String(v||'.').trim();if(!c||c==='.')return'.';const m=/^([A-G](?:#|b)?)(.*)$/.exec(c);if(!m||NOTE[m[1]]===undefined)return c;const names=m[1].includes('b')?FL:SH;return names[(NOTE[m[1]]-capo+120)%12]+m[2]}
function activeChord(ms){let x=null;for(const e of chords){if(e.start_ms<=ms)x=e;else break}return x}
function payload(w){return w&&typeof w.payload==='object'&&w.payload?w.payload:{}}
host.innerHTML=`<div class="lyrics-simple-prompter"><div class="lyrics-simple-section" data-section>&nbsp;</div><div class="lyrics-simple-diagram" data-diagram hidden></div><div class="lyrics-simple-chord-wrap"><div class="lyrics-simple-chord-label">Accord courant</div><div class="lyrics-simple-chord" data-chord>.</div></div><div class="lyrics-simple-line" data-line></div></div>`;
const sectionEl=host.querySelector('[data-section]'),diagramEl=host.querySelector('[data-diagram]'),chordEl=host.querySelector('[data-chord]'),lineEl=host.querySelector('[data-line]');
const header=root.querySelector('.chordslab-prompter-head');
const lbl=document.createElement('label');lbl.className='lyrics-simple-diagram-toggle';lbl.innerHTML='<input type="checkbox" data-lyrics-diagram-toggle> Diagramme d’accord';header?.appendChild(lbl);
const toggle=lbl.querySelector('input');let showDiagram=false;toggle?.addEventListener('change',()=>{showDiagram=toggle.checked;render(lastT)});
const lines=[];let cur=[];words.forEach((w,i)=>{cur.push(i);if(payload(w).line_break_after){lines.push(cur);cur=[]}});if(cur.length)lines.push(cur);
const lineByWord=new Map();lines.forEach((l,li)=>l.forEach(i=>lineByWord.set(i,li)));
function activeWord(ms){let i=-1;for(let k=0;k<words.length;k++){if(words[k].start_ms<=ms)i=k;else break}return i}
function drawLine(i){lineEl.innerHTML='';if(i<0)return;const li=lineByWord.get(i);if(!Number.isInteger(li))return;for(const k of lines[li]){const s=document.createElement('span');s.className='lyrics-simple-word';s.textContent=words[k].effective||words[k].original||'';if(k<i)s.classList.add('past');if(k===i)s.classList.add('current');lineEl.appendChild(s)}}
function esc(v){return String(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]))}
function drawDiagram(ch){if(!showDiagram||!ch||ch==='.'){diagramEl.hidden=true;diagramEl.innerHTML='';return}const base=String(ch).split('/')[0],shape=SHAPES[base];diagramEl.hidden=false;if(!shape){diagramEl.innerHTML=`<strong>${esc(ch)}</strong><small>Diagramme non disponible</small>`;return}let marks='';shape.split('').forEach((f,i)=>{const x=18+i*18;if(f==='x')marks+=`<text x="${x}" y="12" text-anchor="middle" font-size="10">×</text>`;else if(f==='0')marks+=`<circle cx="${x}" cy="10" r="4" fill="none" stroke="currentColor"/>`;else marks+=`<circle cx="${x}" cy="${27+(Number(f)-1)*18}" r="5" fill="currentColor"/>`});diagramEl.innerHTML=`<strong>${esc(ch)}</strong><svg viewBox="0 0 120 105"><g stroke="currentColor" fill="none"><path d="M18 18V90M36 18V90M54 18V90M72 18V90M90 18V90M108 18V90"/><path d="M18 18H108M18 36H108M18 54H108M18 72H108M18 90H108"/></g>${marks}</svg>`}
let lastW=-2,lastC='',lastS='',lastT=0;
function render(sec){lastT=Number(sec)||0;const ms=lastT*1000,w=activeWord(ms),ce=activeChord(ms),c=shown(ce?.effective||ce?.original||'.'),s=w>=0?String(payload(words[w]).section_label||''):'';if(w!==lastW){lastW=w;drawLine(w)}if(c!==lastC){lastC=c;chordEl.textContent=c}if(s!==lastS){lastS=s;sectionEl.textContent=s||'\\u00a0'}drawDiagram(c)}
document.querySelector('[data-stem-mixer]')?.addEventListener('ezscore:audio-timeupdate',e=>render(e.detail?.time||0));render(0);
const source=document.querySelector('[data-lyrics-source]'),state=document.querySelector('[data-lyrics-save-state]');let timer=null;
async function save(){if(!source)return;try{const r=await fetch(source.dataset.saveUrl,{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','Accept':'application/json'},body:JSON.stringify({_token:source.dataset.saveToken,text:source.value})});if(!r.ok)throw 0;if(state)state.textContent='Enregistré'}catch(_){if(state)state.textContent='Échec enregistrement'}}
source?.addEventListener('input',()=>{if(state)state.textContent='Modifié…';clearTimeout(timer);timer=setTimeout(save,450)});
})();