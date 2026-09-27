(() => {
'use strict';
const root=document.querySelector('[data-chordslab]'); if(!root)return;
const parse=v=>{try{return JSON.parse(v||'[]')}catch(_){return[]}};
const profiles=parse(root.dataset.profiles);
let currentProfile=root.dataset.profile||'intermediate';
let events=(profiles[currentProfile]||parse(root.dataset.events)).sort((a,b)=>(a.start_ms-b.start_ms)||(a.id-b.id));
const beats=parse(root.dataset.beats).sort((a,b)=>a.start_ms-b.start_ms);
let capo=Number(root.dataset.capo||0), signature=root.dataset.timeSignature||'4/4';
const measuresEl=root.querySelector('[data-chordslab-measures]');
const diagramEl=root.querySelector('[data-chord-diagram]');
const diagramToggle=document.querySelector('[data-chordslab-diagram]');
const capoSelect=document.querySelector('[data-chordslab-capo]');
const timeSigSelect=document.querySelector('[data-chordslab-timesig]');
const profileSelect=document.querySelector('[data-chordslab-profile]');
const profileBadge=document.querySelector('[data-chord-profile-badge]');
const profileCount=document.querySelector('[data-chord-profile-count]');
const settingsForm=document.querySelector('[data-chord-settings-form]');
const settingsState=document.querySelector('[data-chord-settings-state]');
const analyzeForm=document.querySelector('[data-chord-analyze-form]');
const analyzeDialog=document.querySelector('[data-chord-analyze-dialog]');
const analyzeCancel=analyzeDialog?.querySelector('[data-chord-analyze-cancel]');
const analyzeConfirm=analyzeDialog?.querySelector('[data-chord-analyze-confirm]');
if(!measuresEl||!beats.length)return;

const NOTE_TO_PC={C:0,'C#':1,Db:1,D:2,'D#':3,Eb:3,E:4,F:5,'F#':6,Gb:6,G:7,'G#':8,Ab:8,A:9,'A#':10,Bb:10,B:11};
const SHARP=['C','C#','D','D#','E','F','F#','G','G#','A','A#','B'];
const FLAT=['C','Db','D','Eb','E','F','Gb','G','Ab','A','Bb','B'];
const SHAPES={
 C:'x32010',Cm:'x35543',C7:'x32310',Cmaj7:'x32000',Cadd9:'x32030',Cm7:'x35343',Csus2:'x30033',Csus4:'x33011',
 D:'xx0232',Dm:'xx0231',D7:'xx0212',Dmaj7:'xx0222',Dm7:'xx0211',Dadd9:'xx0230',Dsus2:'xx0230',Dsus4:'xx0233',
 E:'022100',Em:'022000',E7:'020100',Emaj7:'021100',Em7:'022030',Esus4:'022200',
 F:'133211',Fm:'133111',F7:'131211',Fmaj7:'xx3210',Fadd9:'103211',Fm7:'131111',Fsus4:'133311',
 G:'320003',Gm:'355333',G7:'320001',Gmaj7:'320002',Gadd9:'320203',Gsus4:'330013',G6:'320000',
 A:'x02220',Am:'x02210',A7:'x02020',Amaj7:'x02120',Am7:'x02010',Aadd9:'x02420',Asus2:'x02200',Asus4:'x02230',
 B:'x24442',Bm:'x24432',B7:'x21202',Bmaj7:'x24342',Bm7:'x20202',Bsus4:'x24452'
};

const diagramLabel=diagramToggle?.closest('label');
if(diagramLabel)diagramLabel.classList.add('chordslab-diagram-inline');
installR342Styles();

function normaliseLabel(chord){
 if(!chord)return chord;
 return chord.replace(/^([A-G](?:#|b)?)maj$/,'$1');
}
function parseSignature(value){const m=/^(\d+)\/(\d+)$/.exec(value);return m?{num:Math.max(1,Number(m[1])),den:Number(m[2])}:{num:4,den:4}}
function displayChord(chord){
 chord=normaliseLabel(chord);
 if(!chord||chord==='.')return chord||'.';
 const m=/^([A-G](?:#|b)?)(.*)$/.exec(chord); if(!m)return chord;
 const pc=NOTE_TO_PC[m[1]]; if(pc===undefined)return chord;
 const shown=(pc-capo+120)%12;
 return (m[1].includes('b')?FLAT:SHARP)[shown]+m[2];
}
function splitChordLabel(chord){
 const text=String(chord||'').trim();
 if(!text||text==='-'||text==='.')return {raw:text,root:text,suffix:'',bass:''};
 const slash=text.split('/');
 const head=slash.shift()||'';
 const bass=slash.length?'/'+slash.join('/') : '';
 const m=/^([A-G](?:#|b)?)(.*)$/.exec(head);
 if(!m)return {raw:text,root:text,suffix:'',bass};
 return {raw:text,root:m[1],suffix:m[2]||'',bass};
}
function formatChordHtml(chord){
 const parts=splitChordLabel(chord);
 if(!parts.raw||parts.raw==='-'||parts.raw==='.')return escapeHtml(parts.raw||'.');
 const suffix=escapeHtml(parts.suffix)
  .replace(/maj/g,'<span class="chord-quality-maj">maj</span>');
 return `<span class="chord-label-root">${escapeHtml(parts.root)}</span><span class="chord-label-suffix">${suffix}</span>${parts.bass?`<span class="chord-label-bass">${escapeHtml(parts.bass)}</span>`:''}`;
}
function installR342Styles(){
 if(document.getElementById('ezscore-r34-2-style'))return;
 const style=document.createElement('style');
 style.id='ezscore-r34-2-style';
 style.textContent=`/* R34.2 rich chord labels / diagram polish */
 .chord-slot{display:flex;align-items:center;justify-content:center;gap:0;overflow:hidden}
 .chord-label-root{font-size:1em;font-weight:800;line-height:1}
 .chord-label-suffix{font-size:1em;line-height:1}
 .chord-quality-maj{display:inline-block;font-size:.62em;line-height:1;vertical-align:super;letter-spacing:.04em;text-transform:none;opacity:.95;margin-inline:1px 0}
 .chord-label-bass{font-size:.8em;opacity:.9;margin-left:1px}
 [data-chord-diagram] strong{display:inline-flex;align-items:flex-start;gap:0;line-height:1.05}
 .chordslab-diagram-inline{display:inline-flex!important;align-items:center!important;gap:10px;white-space:nowrap;min-height:38px}
 .chordslab-diagram-inline>span{display:inline!important;margin:0!important;font-size:14px!important;line-height:1.1!important;text-transform:none!important;letter-spacing:0!important}
 .chordslab-diagram-inline input[type="checkbox"]{margin:0}
 .chordslab-diagram-inline .form-check-label,.chordslab-diagram-inline .checkbox-label{display:inline!important;white-space:nowrap}
 `;
 document.head.appendChild(style);
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

function profileLabel(profile){
 return ({beginner:'Débutant',intermediate:'Intermédiaire',expert:'Expert'})[profile]||profile;
}
function updateProfileIndicator(){
 if(profileBadge)profileBadge.textContent=profileLabel(currentProfile);
 if(profileCount)profileCount.textContent=`${events.length} accords`;
}

async function loadProfile(profile){
 const template=root.dataset.profileDataUrlTemplate||'';
 if(!template){
  events=(profiles[profile]||[]).slice().sort((a,b)=>(a.start_ms-b.start_ms)||(a.id-b.id));
  updateProfileIndicator();
  render();
  return;
 }
 const url=template.replace('__PROFILE__',encodeURIComponent(profile));
 const response=await fetch(url,{headers:{Accept:'application/json'},credentials:'same-origin',cache:'no-store'});
 if(!response.ok)throw new Error(`profile_http_${response.status}`);
 const data=await response.json();
 if(!Array.isArray(data.events))throw new Error('invalid_profile_payload');
 events=data.events.slice().sort((a,b)=>(a.start_ms-b.start_ms)||(a.id-b.id));
 profiles[profile]=events.slice();
 if(profileCount)profileCount.textContent=`${Number(data.count||events.length)} accords`;
 if(profileBadge)profileBadge.textContent=profileLabel(profile);
 render();
}

async function autoSaveSettings(){
 if(!settingsForm)return;
 if(settingsState)settingsState.textContent='Enregistrement…';
 try{
  const response=await fetch(settingsForm.action,{
   method:'POST',
   body:new FormData(settingsForm),
   credentials:'same-origin',
   headers:{Accept:'application/json'}
  });
  if(!response.ok)throw new Error(`settings_http_${response.status}`);
  if(settingsState)settingsState.textContent='Enregistré';
 }catch(_){
  if(settingsState)settingsState.textContent='Échec enregistrement';
 }
}

function render(){
 measuresEl.innerHTML='';
 for(const measure of buildProjection()){
  const box=document.createElement('div');box.className='chord-measure';box.dataset.measure=String(measure.index);
  const number=document.createElement('small');number.className='chord-measure-number';number.textContent=String(measure.index+1);box.appendChild(number);
  const notation=document.createElement('div');notation.className='chord-measure-notation';
  for(const slot of measure.slots){
   const b=document.createElement('button');b.type='button';b.className='chord-slot';
   b.dataset.beatSeq=String(slot.seq);b.dataset.startMs=String(slot.startMs);b.dataset.beat=String(slot.beatIndex);
   if(slot.eventId)b.dataset.eventId=String(slot.eventId);
   b.innerHTML=formatChordHtml(slot.text); b.setAttribute('aria-label', slot.text);
   if(String(slot.text).length>=5)b.classList.add('is-long');
   if(String(slot.text).length>=7)b.classList.add('is-very-long');
   if(slot.editable){b.classList.add('editable');b.title='Modifier cet accord'}
   notation.appendChild(b);
  }
  box.appendChild(notation);measuresEl.appendChild(box);
 }
}

function highlightAt(seconds){
 const ms=seconds*1000;let seq=-1;
 for(let i=0;i<beats.length;i++){if(beats[i].start_ms<=ms)seq=i;else break}
 measuresEl.querySelectorAll('.is-current').forEach(el=>el.classList.remove('is-current'));
 if(seq<0){updateDiagram(null);return}
 const slot=measuresEl.querySelector(`.chord-slot[data-beat-seq="${seq}"]`);
 if(slot){slot.classList.add('is-current');const m=slot.closest('.chord-measure');m?.classList.add('is-current');root.dispatchEvent(new CustomEvent('ezscore:chord-current',{detail:{beatSeq:seq,timeMs:ms}}))}
 const active=activeEventAt(ms);updateDiagram(displayChord(active?.effective||active?.original||null));
}

function updateDiagram(chord){
 if(!diagramEl||!diagramToggle?.checked||!chord||chord==='.'){if(diagramEl)diagramEl.hidden=true;return}
 diagramEl.hidden=false;const simple=chord.replace(/\/.*$/,''),shape=SHAPES[simple];
 if(!shape){diagramEl.innerHTML=`<strong class="chord-diagram-title">${formatChordHtml(chord)}</strong><small>Diagramme non disponible</small>`;return}
 let marks='';
 shape.split('').forEach((fret,i)=>{const x=18+i*18;if(fret==='x')marks+=`<text x="${x}" y="12" text-anchor="middle" font-size="10">×</text>`;else if(fret==='0')marks+=`<circle cx="${x}" cy="10" r="4" fill="none" stroke="currentColor"/>`;else marks+=`<circle cx="${x}" cy="${27+(Number(fret)-1)*18}" r="5" fill="currentColor"/>`});
 diagramEl.innerHTML=`<strong class="chord-diagram-title">${formatChordHtml(chord)}</strong><svg viewBox="0 0 120 105" role="img" aria-label="${escapeHtml(chord)}"><g stroke="currentColor" fill="none"><path d="M18 18V90M36 18V90M54 18V90M72 18V90M90 18V90M108 18V90"/><path d="M18 18H108M18 36H108M18 54H108M18 72H108M18 90H108"/></g>${marks}</svg>`;
}
function escapeHtml(v){return String(v).replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[ch]))}

async function editEvent(eventId,button){
 const event=events.find(e=>String(e.id)===String(eventId));if(!event)return;
 const input=document.createElement('input');input.className='chord-inline-input';input.value=event.effective||event.original||'';input.maxLength=32;button.replaceWith(input);input.focus();input.select();
 let finished=false;
 const restore=()=>{if(finished)return;finished=true;render()};
 const save=async()=>{
  if(finished)return;
  let chord=normaliseLabel(input.value.trim()),current=normaliseLabel(event.effective||event.original||'');
  if(!chord||chord===current){restore();return}
  const url=root.dataset.editUrlTemplate.replace('__EVENT__',String(eventId));
  const response=await fetch(url,{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','Accept':'application/json'},body:JSON.stringify({_token:root.dataset.editToken,chord,profile:currentProfile})});
  if(!response.ok){input.classList.add('is-error');return}
  const data=await response.json();event.override=data.override;event.effective=data.effective;finished=true;render();
 };
 input.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();save()}if(e.key==='Escape'){e.preventDefault();restore()}});
 input.addEventListener('blur',save,{once:true});
}

async function persistProfile(profile){
 const url=root.dataset.profileUrl,token=root.dataset.profileToken;
 if(!url||!token)return;
 try{
  await fetch(url,{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','Accept':'application/json'},body:JSON.stringify({_token:token,profile})});
 }catch(_){}
}

measuresEl.addEventListener('click',e=>{const b=e.target.closest('.chord-slot.editable[data-event-id]');if(b)editEvent(b.dataset.eventId,b)});
document.querySelector('[data-stem-mixer]')?.addEventListener('ezscore:audio-timeupdate',e=>highlightAt(Number(e.detail?.time||0)));
capoSelect?.addEventListener('change',()=>{capo=Number(capoSelect.value||0);render();autoSaveSettings()});
timeSigSelect?.addEventListener('change',()=>{signature=timeSigSelect.value||'4/4';render();autoSaveSettings()});
profileSelect?.addEventListener('change',async()=>{
 currentProfile=profileSelect.value||'intermediate';
 root.dataset.profile=currentProfile;
 profileSelect.disabled=true;
 try{
  await loadProfile(currentProfile);
  await persistProfile(currentProfile);
 }catch(error){
  console.error('ChordsLab profile switch failed',error);
  events=(profiles[currentProfile]||[]).slice().sort((a,b)=>(a.start_ms-b.start_ms)||(a.id-b.id));
  updateProfileIndicator();
  render();
 }finally{
  profileSelect.disabled=false;
 }
});
diagramToggle?.addEventListener('change',()=>{if(!diagramToggle.checked&&diagramEl)diagramEl.hidden=true});

if(analyzeForm&&analyzeDialog){
 analyzeForm.addEventListener('submit',e=>{
  if(analyzeForm.dataset.confirmed==='1')return;
  e.preventDefault();
  if(typeof analyzeDialog.showModal==='function')analyzeDialog.showModal();
 });
 analyzeCancel?.addEventListener('click',()=>analyzeDialog.close());
 analyzeConfirm?.addEventListener('click',()=>{
  analyzeForm.dataset.confirmed='1';
  analyzeDialog.close();
  const button=analyzeForm.querySelector('button[type="submit"]');
  if(button){button.disabled=true;button.textContent='Analyse en cours…'}
  analyzeForm.submit();
 });
 analyzeDialog.addEventListener('click',e=>{if(e.target===analyzeDialog)analyzeDialog.close()});
}

updateProfileIndicator();
render();
})();


