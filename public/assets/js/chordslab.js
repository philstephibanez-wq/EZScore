(() => {
'use strict';
const root=document.querySelector('[data-chordslab]'); if(!root)return;
const parse=v=>{try{return JSON.parse(v||'[]')}catch(_){return[]}};
const events=parse(root.dataset.events).sort((a,b)=>(a.start_ms-b.start_ms)||(a.id-b.id));
const beats=parse(root.dataset.beats).sort((a,b)=>a.start_ms-b.start_ms);
let capo=Number(root.dataset.capo||0), signature=root.dataset.timeSignature||'4/4';
const measuresEl=root.querySelector('[data-chordslab-measures]');
const diagramEl=root.querySelector('[data-chord-diagram]');
const diagramToggle=document.querySelector('[data-chordslab-diagram]');
const capoSelect=document.querySelector('[data-chordslab-capo]');
const timeSigSelect=document.querySelector('[data-chordslab-timesig]');
if(!measuresEl||!events.length||!beats.length)return;

const NOTE_TO_PC={C:0,'C#':1,Db:1,D:2,'D#':3,Eb:3,E:4,F:5,'F#':6,Gb:6,G:7,'G#':8,Ab:8,A:9,'A#':10,Bb:10,B:11};
const SHARP=['C','C#','D','D#','E','F','F#','G','G#','A','A#','B'];
const FLAT=['C','Db','D','Eb','E','F','Gb','G','Ab','A','Bb','B'];
const SHAPES={C:'x32010',Cm:'x35543',C7:'x32310',D:'xx0232',Dm:'xx0231',D7:'xx0212',E:'022100',Em:'022000',E7:'020100',F:'133211',Fm:'133111',F7:'131211',G:'320003',Gm:'355333',G7:'320001',A:'x02220',Am:'x02210',A7:'x02020',B:'x24442',Bm:'x24432',B7:'x21202'};

function parseSignature(value){const m=/^(\d+)\/(\d+)$/.exec(value);return m?{num:Math.max(1,Number(m[1])),den:Number(m[2])}:{num:4,den:4}}
function displayChord(chord){
 if(!chord||chord==='.')return chord||'.';
 const m=/^([A-G](?:#|b)?)(.*)$/.exec(chord); if(!m)return chord;
 const pc=NOTE_TO_PC[m[1]]; if(pc===undefined)return chord;
 const shown=(pc-capo+120)%12;
 return (m[1].includes('b')?FLAT:SHARP)[shown]+m[2];
}
function activeEventAt(ms){let current=null;for(const e of events){if(e.start_ms<=ms)current=e;else break}return current}
function eventStartingNear(ms,nextMs){return events.find(e=>e.start_ms>=ms&&e.start_ms<nextMs)||null}

const canonicalSignature=signature;
function buildProjection(){
 const sig=parseSignature(signature), measures=[]; let measure=null;
 const useCanonical=signature===canonicalSignature;
 beats.forEach((beat,seq)=>{
  const measureIndex=useCanonical&&Number.isInteger(beat.measure_index)?beat.measure_index:Math.floor(seq/sig.num);
  const beatIndex=useCanonical&&Number.isInteger(beat.beat_index)?beat.beat_index:seq%sig.num;
  if(!measure||measure.index!==measureIndex){measure={index:measureIndex,slots:[]};measures.push(measure)}
  const nextMs=seq+1<beats.length?beats[seq+1].start_ms:beat.start_ms+1000;
  const exact=eventStartingNear(beat.start_ms,nextMs), active=exact||activeEventAt(beat.start_ms);
  let text='-';
  if(exact)text=displayChord(exact.effective||exact.original||'.');
  else if(beatIndex===0)text=displayChord(active?.effective||active?.original||'.');
  measure.slots.push({seq,beatIndex,startMs:beat.start_ms,text,eventId:active?.id||null,editable:text!=='-'&&text!=='.'&&!!active?.id});
 });
 return measures;
}

function render(){
 measuresEl.innerHTML='';
 for(const measure of buildProjection()){
  const box=document.createElement('div'); box.className='chord-measure'; box.dataset.measure=String(measure.index);
  const number=document.createElement('small'); number.className='chord-measure-number'; number.textContent=String(measure.index+1); box.appendChild(number);
  const notation=document.createElement('div'); notation.className='chord-measure-notation';
  for(const slot of measure.slots){
   const b=document.createElement('button'); b.type='button'; b.className='chord-slot';
   b.dataset.beatSeq=String(slot.seq); b.dataset.startMs=String(slot.startMs); b.dataset.beat=String(slot.beatIndex);
   if(slot.eventId)b.dataset.eventId=String(slot.eventId);
   b.textContent=slot.text;
   if(slot.editable){b.classList.add('editable');b.title='Modifier cet accord'}
   notation.appendChild(b);
  }
  box.appendChild(notation);measuresEl.appendChild(box);
 }
}

function highlightAt(seconds){
 const ms=seconds*1000; let seq=-1;
 for(let i=0;i<beats.length;i++){if(beats[i].start_ms<=ms)seq=i;else break}
 measuresEl.querySelectorAll('.is-current').forEach(el=>el.classList.remove('is-current'));
 if(seq<0){updateDiagram(null);return}
 const slot=measuresEl.querySelector(`.chord-slot[data-beat-seq="${seq}"]`);
 if(slot){slot.classList.add('is-current');const m=slot.closest('.chord-measure');m?.classList.add('is-current');root.dispatchEvent(new CustomEvent('ezscore:chord-current',{detail:{beatSeq:seq,timeMs:ms}}))}
 const active=activeEventAt(ms); updateDiagram(displayChord(active?.effective||active?.original||null));
}

function updateDiagram(chord){
 if(!diagramEl||!diagramToggle?.checked||!chord||chord==='.'){if(diagramEl)diagramEl.hidden=true;return}
 diagramEl.hidden=false; const simple=chord.replace(/\/.*$/,''),shape=SHAPES[simple];
 if(!shape){diagramEl.innerHTML=`<strong>${escapeHtml(chord)}</strong><small>Diagramme non disponible</small>`;return}
 let marks='';
 shape.split('').forEach((fret,i)=>{const x=18+i*18;if(fret==='x')marks+=`<text x="${x}" y="12" text-anchor="middle" font-size="10">×</text>`;else if(fret==='0')marks+=`<circle cx="${x}" cy="10" r="4" fill="none" stroke="currentColor"/>`;else marks+=`<circle cx="${x}" cy="${27+(Number(fret)-1)*18}" r="5" fill="currentColor"/>`});
 diagramEl.innerHTML=`<strong>${escapeHtml(chord)}</strong><svg viewBox="0 0 120 105" role="img" aria-label="${escapeHtml(chord)}"><g stroke="currentColor" fill="none"><path d="M18 18V90M36 18V90M54 18V90M72 18V90M90 18V90M108 18V90"/><path d="M18 18H108M18 36H108M18 54H108M18 72H108M18 90H108"/></g>${marks}</svg>`;
}
function escapeHtml(v){return String(v).replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[ch]))}

async function editEvent(eventId,button){
 const event=events.find(e=>String(e.id)===String(eventId)); if(!event)return;
 const input=document.createElement('input');input.className='chord-inline-input';input.value=event.effective||event.original||'';input.maxLength=32;button.replaceWith(input);input.focus();input.select();
 let finished=false;
 const restore=()=>{if(finished)return;finished=true;render()};
 const save=async()=>{
  if(finished)return;
  const chord=input.value.trim(),current=event.effective||event.original||'';
  if(!chord||chord===current){restore();return}
  const url=root.dataset.editUrlTemplate.replace('__EVENT__',String(eventId));
  const response=await fetch(url,{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','Accept':'application/json'},body:JSON.stringify({_token:root.dataset.editToken,chord})});
  if(!response.ok){input.classList.add('is-error');return}
  const data=await response.json();event.override=data.override;event.effective=data.effective;finished=true;render();
 };
 input.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();save()}if(e.key==='Escape'){e.preventDefault();restore()}});
 input.addEventListener('blur',save,{once:true});
}

measuresEl.addEventListener('click',e=>{const b=e.target.closest('.chord-slot.editable[data-event-id]');if(b)editEvent(b.dataset.eventId,b)});
document.querySelector('[data-stem-mixer]')?.addEventListener('ezscore:audio-timeupdate',e=>highlightAt(Number(e.detail?.time||0)));
capoSelect?.addEventListener('change',()=>{capo=Number(capoSelect.value||0);render()});
timeSigSelect?.addEventListener('change',()=>{signature=timeSigSelect.value||'4/4';render()});
diagramToggle?.addEventListener('change',()=>{if(!diagramToggle.checked&&diagramEl)diagramEl.hidden=true});
render();
})();
