(() => {
'use strict';
const root=document.querySelector('[data-chordslab]'); if(!root)return;
const parse=v=>{try{return JSON.parse(v||'[]')}catch(_){return[]}};
const profiles=parse(root.dataset.profiles);
let currentProfile=root.dataset.profile||'intermediate';
let events=(profiles[currentProfile]||parse(root.dataset.events)).sort((a,b)=>(a.start_ms-b.start_ms)||(a.id-b.id));
const beats=parse(root.dataset.beats).sort((a,b)=>a.start_ms-b.start_ms);
let capo=Number(root.dataset.capo||0), signature=root.dataset.timeSignature||'4/4';
const canonicalSignature=signature;
const timelineCore=()=>window.EZScoreTimelineCoreR39?.create({beats,timeSignature:signature,spacing:44,preserveSourcePosition:signature===canonicalSignature})||null;
const measuresEl=root.querySelector('[data-chordslab-measures]');
const stageEl=measuresEl?.closest('.chordslab-stage');
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
const noiseFilter=document.querySelector('[data-noise-filter]');
if(noiseFilter){
 noiseFilter.addEventListener('change',async()=>{
  const url=noiseFilter.dataset.saveUrl,token=noiseFilter.dataset.saveToken;if(!url||!token)return;
  try{const response=await fetch(url,{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','Accept':'application/json'},body:JSON.stringify({_token:token,enabled:noiseFilter.checked})});if(!response.ok)throw new Error(`noise_filter_http_${response.status}`)}catch(_){noiseFilter.checked=!noiseFilter.checked}
 });
}
if(!measuresEl||!beats.length)return;

const NOTE_TO_PC={C:0,'C#':1,Db:1,D:2,'D#':3,Eb:3,E:4,F:5,'F#':6,Gb:6,G:7,'G#':8,Ab:8,A:9,'A#':10,Bb:10,B:11};
const SHARP=['C','C#','D','D#','E','F','F#','G','G#','A','A#','B'];
const FLAT=['C','Db','D','Eb','E','F','Gb','G','Ab','A','Bb','B'];
const diagramLabel=diagramToggle?.closest('label');
if(diagramLabel)diagramLabel.classList.add('chordslab-diagram-inline');
installR342Styles();

function normaliseLabel(chord){
 if(!chord)return chord;
 chord=String(chord).trim().replace(/^\[([^\]]+)\]$/,'$1');
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

function buildProjection(){
 const core=timelineCore();
 if(core){
  const slots=core.chordProjection(events,displayChord),measures=[];
  for(const slot of slots){
   const measureIndex=Number(slot.beat.display_measure_index);
   let measure=measures.at(-1);
   if(!measure||measure.index!==measureIndex){measure={index:measureIndex,slots:[]};measures.push(measure)}
   measure.slots.push({seq:slot.seq,beatIndex:Number(slot.beat.display_beat_index),startMs:slot.startMs,text:slot.text,beatId:slot.beatId,eventId:slot.eventId,activeEventId:slot.activeEventId,editable:slot.editable});
  }
  return measures;
 }
 throw new Error('EZScore canonical timeline engine missing');
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
 const track=document.createElement('div');
 track.className='chordslab-measures-track';
 track.dataset.chordslabMeasuresTrack='1';
 measuresEl.appendChild(track);
 for(const measure of buildProjection()){
  const box=document.createElement('div');box.className='chord-measure';box.dataset.measure=String(measure.index);
  const number=document.createElement('small');number.className='chord-measure-number';number.textContent=String(measure.index+1);box.appendChild(number);
  const notation=document.createElement('div');notation.className='chord-measure-notation';
  for(const slot of measure.slots){
   const b=document.createElement('button');b.type='button';b.className='chord-slot';
   b.dataset.beatSeq=String(slot.seq);b.dataset.startMs=String(slot.startMs);b.dataset.beat=String(slot.beatIndex);
   if(slot.eventId)b.dataset.eventId=String(slot.eventId);
   if(slot.beatId)b.dataset.beatId=String(slot.beatId);
   if(slot.activeEventId)b.dataset.activeEventId=String(slot.activeEventId);
   b.innerHTML=formatChordHtml(slot.text); b.setAttribute('aria-label', slot.text);
   if(String(slot.text).length>=5)b.classList.add('is-long');
   if(String(slot.text).length>=7)b.classList.add('is-very-long');
   if(slot.editable){b.classList.add('editable');b.title='Modifier cet accord'}
   notation.appendChild(b);
  }
  box.appendChild(notation);track.appendChild(box);
 }
}


const focusTrack = new window.EZScoreFocusTrack(measuresEl,{
 track:()=>measuresEl.querySelector('[data-chordslab-measures-track]'),
 target:()=>diagramEl,
 fallbackRatio:()=>{
  if(window.matchMedia('(max-width:640px)').matches)return .38;
  if(window.matchMedia('(max-width:900px)').matches)return .30;
  return .25;
 }
});

function alignCurrentTime(slot,seq,ms){
 if(!slot)return;
 const next=measuresEl.querySelector(`.chord-slot[data-beat-seq="${seq+1}"]`);
 const t0=Number(slot.dataset.startMs||ms);
 const t1=next?Number(next.dataset.startMs||t0):t0;
 const progress=next&&t1>t0?Math.max(0,Math.min(1,(ms-t0)/(t1-t0))):0;
 focusTrack.alignBetween(slot,next,progress);
}

let lastPlaybackSeconds=0;
function highlightAt(seconds){
 lastPlaybackSeconds=Math.max(0,Number(seconds)||0);
 const ms=lastPlaybackSeconds*1000;const core=timelineCore();let seq=core?core.beatIndexAtMs(ms):-1;
 measuresEl.querySelectorAll('.is-current').forEach(el=>el.classList.remove('is-current'));
 if(seq<0){updateDiagram(null);return}
 const slot=measuresEl.querySelector(`.chord-slot[data-beat-seq="${seq}"]`);
 if(slot){slot.classList.add('is-current');const m=slot.closest('.chord-measure');m?.classList.add('is-current');alignCurrentTime(slot,seq,ms);root.dispatchEvent(new CustomEvent('ezscore:chord-current',{detail:{beatSeq:seq,timeMs:ms}}))}
 const active=activeEventAt(ms);updateDiagram(displayChord(active?.effective||active?.original||null));
}

function updateDiagram(chord){
 if(!diagramEl||!diagramToggle?.checked||!chord||chord==='.'){
  if(diagramEl){diagramEl.hidden=true;diagramEl.innerHTML=''}
  return;
 }
 diagramEl.classList.add('ez-chord-diagram');
 window.EZScoreChordDiagram.render(diagramEl,chord);
}

function escapeHtml(v){return String(v).replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[ch]))}

async function editSlot(button){
 const beatId=button.dataset.beatId;
 const activeEventId=button.dataset.activeEventId||'';
 if(!beatId)return;
 const active=activeEventId?events.find(e=>String(e.id)===String(activeEventId)):null;
 const input=document.createElement('input');
 input.className='chord-inline-input';
 const shown=button.getAttribute('aria-label')||'.';
 input.value=shown==='-' ? displayChord(active?.effective||active?.original||'') : shown;
 input.maxLength=32;
 button.replaceWith(input);input.focus();input.select();
 let finished=false;
 const restore=()=>{if(finished)return;finished=true;render()};
 const save=async()=>{
  if(finished)return;
  let chord=normaliseLabel(input.value.trim());
  if(!chord)chord='.';
  if(chord==='-'){restore();return}
  const url=(root.dataset.beatEditUrlTemplate||'').replace('__BEAT__',String(beatId));
  if(!url){input.classList.add('is-error');return}
  const response=await fetch(url,{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','Accept':'application/json'},body:JSON.stringify({_token:root.dataset.editToken,chord,profile:currentProfile})});
  if(!response.ok){input.classList.add('is-error');return}
  finished=true;
  window.location.reload();
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

measuresEl.addEventListener('click',e=>{
 const b=e.target.closest('.chord-slot.editable[data-beat-id]');
 if(b)editSlot(b);
});
const mixerRoot=document.querySelector('[data-stem-mixer]');
let manualSeeker=null,manualSeekerOutput=null,manualSeekerDragging=false;

function formatSeekerTime(sec){
 sec=Math.max(0,Number(sec)||0);
 const minutes=Math.floor(sec/60),seconds=sec-minutes*60;
 return `${minutes}:${seconds.toFixed(2).padStart(5,'0')}`;
}

function installManualSeeker(){
 if(!mixerRoot)return;
 const stage=measuresEl.closest('.chordslab-stage');
 if(!stage||root.querySelector('[data-chordslab-manual-seeker]'))return;

 const shell=document.createElement('div');
 shell.className='chordslab-manual-seeker';
 shell.innerHTML='<label><span>Position</span><input type="range" min="0" max="1" step="0.01" value="0" data-chordslab-manual-seeker aria-label="Position dans le morceau"><output data-chordslab-manual-seeker-time>0:00.00</output></label>';
 stage.insertAdjacentElement('beforebegin',shell);

 manualSeeker=shell.querySelector('[data-chordslab-manual-seeker]');
 manualSeekerOutput=shell.querySelector('[data-chordslab-manual-seeker-time]');
 const lastBeatSec=Math.max(0,Number(beats.at(-1)?.start_ms||0)/1000);
 manualSeeker.max=String(Math.max(1,lastBeatSec+2));

 const requestSeek=()=>{
  const max=Math.max(0,Number(manualSeeker.max||0));
  const sec=Math.max(0,Math.min(max,Number(manualSeeker.value)||0));
  if(manualSeekerOutput)manualSeekerOutput.textContent=formatSeekerTime(sec);
  mixerRoot.dispatchEvent(new CustomEvent('ezscore:request-seek',{detail:{time:sec}}));
  highlightAt(sec);
 };

 manualSeeker.addEventListener('pointerdown',()=>{manualSeekerDragging=true});
 manualSeeker.addEventListener('pointerup',()=>{manualSeekerDragging=false});
 manualSeeker.addEventListener('pointercancel',()=>{manualSeekerDragging=false});
 manualSeeker.addEventListener('input',requestSeek);
 manualSeeker.addEventListener('change',requestSeek);
}

installManualSeeker();
mixerRoot?.addEventListener('ezscore:audio-timeupdate',e=>{
 const sec=Math.max(0,Number(e.detail?.time||0));
 const duration=Math.max(0,Number(e.detail?.duration||0));
 if(manualSeeker){
  if(duration>0&&Math.abs(Number(manualSeeker.max||0)-duration)>.05)manualSeeker.max=String(duration);
  if(!manualSeekerDragging)manualSeeker.value=String(Math.min(sec,Number(manualSeeker.max||sec)));
 }
 if(manualSeekerOutput)manualSeekerOutput.textContent=formatSeekerTime(sec);
 highlightAt(sec);
});
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
function syncDiagramLayout(){
 const expanded=Boolean(diagramToggle?.checked);
 stageEl?.classList.toggle('is-diagram-collapsed',!expanded);
 if(!expanded){
  updateDiagram(null);
  return;
 }
 highlightAt(lastPlaybackSeconds);
}
diagramToggle?.addEventListener('change',syncDiagramLayout);
syncDiagramLayout();

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


