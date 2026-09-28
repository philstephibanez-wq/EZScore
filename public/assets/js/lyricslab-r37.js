(() => {
'use strict';
const root=document.querySelector('[data-lyricslab]'); if(!root)return;
const parse=v=>{try{return JSON.parse(v||'[]')}catch(_){return[]}};
const beats=parse(root.dataset.beats).sort((a,b)=>Number(a.start_ms)-Number(b.start_ms));
const chords=parse(root.dataset.chords).sort((a,b)=>Number(a.start_ms)-Number(b.start_ms));
const words=parse(root.dataset.lyrics).sort((a,b)=>Number(a.start_ms)-Number(b.start_ms));
const host=root.querySelector('[data-lyrics-measures]'); if(!host||!beats.length)return;
const capo=Number(root.dataset.capo||0);
const NOTE={C:0,'C#':1,Db:1,D:2,'D#':3,Eb:3,E:4,F:5,'F#':6,Gb:6,G:7,'G#':8,Ab:8,A:9,'A#':10,Bb:10,B:11};
const SH=['C','C#','D','D#','E','F','F#','G','G#','A','A#','B'],FL=['C','Db','D','Eb','E','F','Gb','G','Ab','A','Bb','B'];
const SHAPES={C:'x32010',Cm:'x35543',C7:'x32310',Cmaj7:'x32000',D:'xx0232',Dm:'xx0231',D7:'xx0212',E:'022100',Em:'022000',E7:'020100',F:'133211',Fmaj7:'xx3210',G:'320003',G7:'320001',A:'x02220',Am:'x02210',A7:'x02020',B:'x24442',Bm:'x24432',B7:'x21202'};
function shown(v){let c=String(v||'.').trim().replace(/^\[([^\]]+)\]$/,'$1').replace(/♭/g,'b');if(!c||c==='.')return'.';const m=/^([A-G](?:#|b)?)(.*)$/.exec(c);if(!m||NOTE[m[1]]===undefined)return c;const names=m[1].includes('b')?FL:SH;return names[(NOTE[m[1]]-capo+120)%12]+m[2]}
function payload(w){return w&&typeof w.payload==='object'&&w.payload?w.payload:{}}
function activeChord(ms){let x=null;for(const e of chords){if(Number(e.start_ms)<=ms)x=e;else break}return x}
function exactChord(a,b){return chords.find(e=>Number(e.start_ms)>=a&&Number(e.start_ms)<b)||null}
function activeWord(ms){let i=-1;for(let k=0;k<words.length;k++){if(Number(words[k].start_ms)<=ms)i=k;else break}return i}
const starts=beats.map(b=>Number(b.start_ms||0)/1000),gaps=[];
for(let i=1;i<starts.length;i++){const g=starts[i]-starts[i-1];if(g>.02)gaps.push(g)}
gaps.sort((a,b)=>a-b);const nominal=gaps.length?gaps[Math.floor(gaps.length/2)]:.5,spacing=166;
const firstStart=Math.max(0,starts[0]||0),firstX=firstStart/Math.max(.02,nominal)*spacing;
const xBeat=i=>firstX+i*spacing;
function beatIndex(t){if(t<starts[0])return-1;let lo=0,hi=starts.length-1,a=-1;while(lo<=hi){const m=(lo+hi)>>1;if(starts[m]<=t){a=m;lo=m+1}else hi=m-1}return a}
function rawMetric(t){t=Math.max(0,Number(t)||0);if(t<=starts[0])return firstStart>.001?firstX*(t/firstStart):0;const i=beatIndex(t);if(i<0)return 0;if(i>=starts.length-1)return xBeat(i)+(t-starts[i])/Math.max(.02,nominal)*spacing;const t0=starts[i],t1=Math.max(t0+.02,starts[i+1]);return xBeat(i)+Math.max(0,Math.min(1,(t-t0)/(t1-t0)))*spacing}

host.innerHTML='<div class="lyrics-ribbon-stage" data-stage><div class="lyrics-fixed-diagram" data-diagram hidden></div><div class="lyrics-reading-zone" data-reading-zone></div><div class="lyrics-ribbon-track" data-track><div class="lyrics-ribbon-chords" data-chords-lane></div><div class="lyrics-ribbon-words" data-words-lane></div></div></div>';
const stage=host.querySelector('[data-stage]'),zone=host.querySelector('[data-reading-zone]'),diagram=host.querySelector('[data-diagram]'),track=host.querySelector('[data-track]'),chordLane=host.querySelector('[data-chords-lane]'),wordLane=host.querySelector('[data-words-lane]');

const panel=root.closest('section'),title=panel?.querySelector('.chordslab-prompter-head h2'),sections=[];
words.forEach((w,i)=>{const l=String(payload(w).section_label||'').trim(),p=i?String(payload(words[i-1]).section_label||'').trim():'';if(l&&l!==p)sections.push({label:l,start:Number(w.start_ms||0)/1000})});
if(title){let nav=panel.querySelector('[data-section-nav]');if(!nav){nav=document.createElement('div');nav.className='lyrics-section-nav';nav.dataset.sectionNav='';title.insertAdjacentElement('afterend',nav)}nav.innerHTML='';sections.forEach((s,i)=>{const b=document.createElement('button');b.type='button';b.className='lyrics-section-chip';b.dataset.sectionIndex=String(i);b.textContent=s.label;b.onclick=()=>document.querySelector('[data-stem-mixer]')?.dispatchEvent(new CustomEvent('ezscore:request-seek',{detail:{time:s.start}}));nav.appendChild(b)})}

const header=root.querySelector('.chordslab-prompter-head');let toggle=root.querySelector('[data-lyrics-diagram-toggle]');
if(!toggle&&header){const l=document.createElement('label');l.className='lyrics-diagram-toggle';l.innerHTML='<input type="checkbox" data-lyrics-diagram-toggle> Diagramme d’accord';header.appendChild(l);toggle=l.querySelector('input')}
let showDiagram=Boolean(toggle?.checked);toggle?.addEventListener('change',()=>{showDiagram=toggle.checked;renderAt(lastTime,true)});
function esc(v){return String(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]))}
function drawDiagram(ch){if(!showDiagram||!ch||ch==='.'){diagram.hidden=true;diagram.innerHTML='';return}const base=String(ch).split('/')[0],shape=SHAPES[base];diagram.hidden=false;if(!shape){diagram.innerHTML='<strong>'+esc(ch)+'</strong><small>Diagramme non disponible</small>';return}let marks='';shape.split('').forEach((f,i)=>{const x=18+i*18;if(f==='x')marks+=`<text x="${x}" y="12" text-anchor="middle" font-size="10">×</text>`;else if(f==='0')marks+=`<circle cx="${x}" cy="10" r="4" fill="none" stroke="currentColor"/>`;else marks+=`<circle cx="${x}" cy="${27+(Number(f)-1)*18}" r="5" fill="currentColor"/>`});diagram.innerHTML=`<strong>${esc(ch)}</strong><svg viewBox="0 0 120 105"><g stroke="currentColor" fill="none"><path d="M18 18V90M36 18V90M54 18V90M72 18V90M90 18V90M108 18V90"/><path d="M18 18H108M18 36H108M18 54H108M18 72H108M18 90H108"/></g>${marks}</svg>`}

const wordNodes=[];words.forEach((w,i)=>{const e=document.createElement('span');e.className='lyrics-ribbon-word';e.dataset.wordIndex=String(i);e.dataset.rawX=String(rawMetric(Number(w.start_ms||0)/1000));e.textContent=String(w.effective||w.original||'');wordLane.appendChild(e);wordNodes.push(e)});
let anchors=[{raw:0,shift:0}];
function shiftFor(raw){if(raw<=anchors[0].raw)return anchors[0].shift;let lo=0,hi=anchors.length-1,left=0;while(lo<=hi){const m=(lo+hi)>>1;if(anchors[m].raw<=raw){left=m;lo=m+1}else hi=m-1}if(left>=anchors.length-1)return anchors[left].shift;const a=anchors[left],b=anchors[left+1],p=(raw-a.raw)/Math.max(.001,b.raw-a.raw);return a.shift+(b.shift-a.shift)*Math.max(0,Math.min(1,p))}
const visRaw=r=>r+shiftFor(r),visMetric=t=>visRaw(rawMetric(t));
function buildWarp(){let prevRight=-Infinity,shift=0;const a=[{raw:0,shift:0}];wordNodes.forEach(n=>{const raw=Number(n.dataset.rawX||0),w=Math.max(20,n.getBoundingClientRect().width||20),left=raw-w/2;if(Number.isFinite(prevRight))shift=Math.max(shift,prevRight+18-left);const center=raw+shift;n.style.left=center+'px';prevRight=center+w/2;a.push({raw,shift})});anchors=a;buildChords();const end=Math.max(starts.at(-1)||0,Number(words.at(-1)?.end_ms||0)/1000);track.style.width=Math.max(2600,visMetric(end)+spacing*8)+'px';renderAt(lastTime,true)}
function buildChords(){chordLane.innerHTML='';beats.forEach((b,i)=>{const s=Number(b.start_ms||0),n=i+1<beats.length?Number(beats[i+1].start_ms):s+nominal*1000,ex=exactChord(s,n),ac=ex||activeChord(s),bn=Number(b.beat_index||0);let text='-';if(ex)text=shown(ex.effective||ex.original||'.');else if((ac?.effective||ac?.original||'')==='.')text='.';else if(bn===0)text=shown(ac?.effective||ac?.original||'.');const left=visRaw(xBeat(i)),next=i+1<beats.length?visRaw(xBeat(i+1)):left+spacing,cell=document.createElement('div');cell.className='lyrics-ribbon-beat'+(bn===0?' measure-start':'');cell.dataset.beatSeq=String(i);cell.style.left=left+'px';cell.style.width=Math.max(74,next-left)+'px';const c=document.createElement('strong');c.className='lyrics-ribbon-chord';c.textContent=text;cell.appendChild(c);if(bn===0){const m=document.createElement('small');m.className='lyrics-ribbon-measure';m.textContent='#'+(Number(b.measure_index||0)+1);cell.appendChild(m)}chordLane.appendChild(cell)})}
function focusX(){return Math.max(105,stage.clientWidth*.30)}
let lastTime=0,lastBeat=-2,lastWord=-2,lastSection=-2,lastChord='';
function renderAt(sec,force=false){lastTime=Math.max(0,Number(sec)||0);const x=focusX();zone.style.left=x+'px';diagram.style.left=x+'px';track.style.transform=`translate3d(${x-visMetric(lastTime)}px,0,0)`;const bi=beatIndex(lastTime);if(force||bi!==lastBeat){lastBeat=bi;chordLane.querySelectorAll('.current').forEach(e=>e.classList.remove('current'));chordLane.querySelector(`.lyrics-ribbon-beat[data-beat-seq="${bi}"]`)?.classList.add('current')}const wi=activeWord(lastTime*1000);if(force||wi!==lastWord){lastWord=wi;wordNodes.forEach((e,i)=>{e.classList.toggle('past',wi>=0&&i<wi);e.classList.toggle('current',i===wi)})}const si=sections.reduce((a,s,i)=>s.start<=lastTime?i:a,-1);if(force||si!==lastSection){lastSection=si;panel?.querySelectorAll('.lyrics-section-chip.current').forEach(e=>e.classList.remove('current'));panel?.querySelector(`.lyrics-section-chip[data-section-index="${si}"]`)?.classList.add('current')}const ev=activeChord(lastTime*1000),ch=shown(ev?.effective||ev?.original||'.');if(force||ch!==lastChord){lastChord=ch;drawDiagram(ch)}}
document.querySelector('[data-stem-mixer]')?.addEventListener('ezscore:audio-timeupdate',e=>renderAt(e.detail?.time||0));
window.addEventListener('resize',buildWarp);requestAnimationFrame(buildWarp);document.fonts?.ready?.then(()=>requestAnimationFrame(buildWarp));setTimeout(buildWarp,150);

const source=document.querySelector('[data-lyrics-source]'),state=document.querySelector('[data-lyrics-save-state]');let timer=null;
async function save(){if(!source)return;try{const r=await fetch(source.dataset.saveUrl,{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','Accept':'application/json'},body:JSON.stringify({_token:source.dataset.saveToken,text:source.value})});if(!r.ok)throw 0;if(state)state.textContent='Enregistré'}catch(_){if(state)state.textContent='Échec enregistrement'}}
source?.addEventListener('input',()=>{if(state)state.textContent='Modifié…';clearTimeout(timer);timer=setTimeout(save,450)});
})();