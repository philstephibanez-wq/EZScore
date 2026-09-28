(() => {
'use strict';
const root=document.querySelector('[data-lyricslab]');if(!root)return;
const parse=v=>{try{return JSON.parse(v||'[]')}catch(_){return[]}};
const beats=parse(root.dataset.beats).sort((a,b)=>a.start_ms-b.start_ms);
const chords=parse(root.dataset.chords).sort((a,b)=>a.start_ms-b.start_ms);
const lyrics=parse(root.dataset.lyrics).sort((a,b)=>a.start_ms-b.start_ms);
const measuresEl=root.querySelector('[data-lyrics-measures]');
const capo=Number(root.dataset.capo||0);

const NOTE_TO_PC={C:0,'C#':1,Db:1,D:2,'D#':3,Eb:3,E:4,F:5,'F#':6,Gb:6,G:7,'G#':8,Ab:8,A:9,'A#':10,Bb:11};
NOTE_TO_PC.Bb=10; NOTE_TO_PC.B=11;
const SHARP=['C','C#','D','D#','E','F','F#','G','G#','A','A#','B'];

function displayChord(chord){
 if(!chord||chord==='.')return chord||'.';
 const m=/^([A-G](?:#|b)?)(.*)$/.exec(chord);if(!m)return chord;
 const pc=NOTE_TO_PC[m[1]];if(pc===undefined)return chord;
 return SHARP[(pc-capo+120)%12]+m[2];
}
function activeChord(ms){let c=null;for(const e of chords){if(e.start_ms<=ms)c=e;else break}return c}
function nextBeat(seq){return seq+1<beats.length?beats[seq+1].start_ms:beats[seq].start_ms+1000}

function build(){
 const byMeasure=new Map();
 beats.forEach((b,seq)=>{
  const mi=Number.isInteger(b.measure_index)?b.measure_index:0;
  if(!byMeasure.has(mi))byMeasure.set(mi,[]);
  const end=nextBeat(seq);
  const exact=chords.find(c=>c.start_ms>=b.start_ms&&c.start_ms<end);
  const active=exact||activeChord(b.start_ms);
  let chord='-';
  if(exact)chord=displayChord(exact.effective||exact.original||'.');
  else if((active?.effective||active?.original||'')==='.')chord='.';
  else if((b.beat_index??0)===0)chord=displayChord(active?.effective||active?.original||'.');
  const words=lyrics.filter(w=>w.start_ms>=b.start_ms&&w.start_ms<end);
  byMeasure.get(mi).push({beat:b,seq,chord,words});
 });

 measuresEl.innerHTML='';
 for(const [mi,slots] of byMeasure){
  const box=document.createElement('div');
  box.className='chord-measure';
  box.dataset.measure=String(mi);

  const number=document.createElement('small');
  number.className='chord-measure-number';
  number.textContent=String(Number(mi)+1);
  box.appendChild(number);

  const notation=document.createElement('div');
  notation.className='chord-measure-notation';

  for(const slot of slots){
   const cell=document.createElement('div');
   cell.className='chord-slot lyrics-beat-slot';
   cell.dataset.beatSeq=String(slot.seq);
   cell.dataset.startMs=String(slot.beat.start_ms);

   const chord=document.createElement('div');
   chord.className='lyrics-slot-chord';
   chord.textContent=slot.chord;
   cell.appendChild(chord);

   const words=document.createElement('div');
   words.className='lyrics-slot-words';
   slot.words.forEach(w=>{
    const b=document.createElement('button');
    b.type='button';
    b.className='lyrics-word';
    b.textContent=w.effective||w.original||'';
    b.dataset.eventId=String(w.id);
    b.dataset.startMs=String(w.start_ms);
    b.dataset.endMs=String(w.end_ms||w.start_ms+250);
    words.appendChild(b);
   });
   cell.appendChild(words);
   notation.appendChild(cell);
  }
  box.appendChild(notation);
  measuresEl.appendChild(box);
 }
}

async function editWord(button){
 const id=button.dataset.eventId;if(!id)return;
 const input=document.createElement('input');
 input.className='lyrics-word-input';
 input.value=button.textContent||'';
 button.replaceWith(input);input.focus();input.select();

 const save=async()=>{
  const text=input.value.trim();
  if(!text){build();return}
  const url=root.dataset.editUrlTemplate.replace('__EVENT__',id);
  const r=await fetch(url,{
   method:'POST',credentials:'same-origin',
   headers:{'Content-Type':'application/json','Accept':'application/json'},
   body:JSON.stringify({_token:root.dataset.editToken,text})
  });
  if(!r.ok){input.classList.add('is-error');return}
  const d=await r.json();
  const e=lyrics.find(x=>String(x.id)===String(id));
  if(e){e.override=d.override;e.effective=d.effective}
  build();
 };
 input.addEventListener('keydown',e=>{
  if(e.key==='Enter'){e.preventDefault();save()}
  if(e.key==='Escape'){e.preventDefault();build()}
 });
 input.addEventListener('blur',save,{once:true});
}

measuresEl.addEventListener('click',e=>{
 const b=e.target.closest('.lyrics-word[data-event-id]');
 if(b)editWord(b);
});

document.querySelector('[data-stem-mixer]')?.addEventListener('ezscore:audio-timeupdate',e=>{
 const ms=Number(e.detail?.time||0)*1000;
 let seq=-1;
 for(let i=0;i<beats.length;i++){if(beats[i].start_ms<=ms)seq=i;else break}

 measuresEl.querySelectorAll('.is-current').forEach(x=>x.classList.remove('is-current'));
 if(seq>=0){
  const slot=measuresEl.querySelector(`.chord-slot[data-beat-seq="${seq}"]`);
  slot?.classList.add('is-current');
  slot?.closest('.chord-measure')?.classList.add('is-current');
 }

 measuresEl.querySelectorAll('.lyrics-word').forEach(w=>{
  const a=Number(w.dataset.startMs||0),b=Number(w.dataset.endMs||a+250);
  w.classList.toggle('is-current',ms>=a&&ms<Math.max(b,a+120));
 });
 measuresEl.querySelector('.lyrics-word.is-current')?.scrollIntoView({behavior:'smooth',inline:'center',block:'nearest'});
});

build();

const source=document.querySelector('[data-lyrics-source]');
const saveState=document.querySelector('[data-lyrics-save-state]');
let timer=null;
source?.addEventListener('input',()=>{
 if(saveState)saveState.textContent='Modifié…';
 clearTimeout(timer);
 timer=setTimeout(async()=>{
  try{
   const r=await fetch(source.dataset.saveUrl,{
    method:'POST',credentials:'same-origin',
    headers:{'Content-Type':'application/json','Accept':'application/json'},
    body:JSON.stringify({_token:source.dataset.saveToken,text:source.value})
   });
   if(!r.ok)throw new Error();
   if(saveState)saveState.textContent='Enregistré';
  }catch(_){
   if(saveState)saveState.textContent='Échec enregistrement';
  }
 },550);
});

const progress=document.querySelector('[data-lyrics-progress]');
const statusUrl=progress?.dataset.statusUrl||'';
const pbar=progress?.querySelector('progress');
const ptext=progress?.querySelector('[data-lyrics-progress-text]');
const ppct=progress?.querySelector('[data-lyrics-progress-percent]');
async function poll(){
 if(!statusUrl)return;
 try{
  const r=await fetch(statusUrl,{headers:{Accept:'application/json'},cache:'no-store',credentials:'same-origin'});
  if(r.ok){
   const d=await r.json(),st=String(d.status||'');
   if(st==='queued'||st==='running'){
    progress.hidden=false;pbar.value=Number(d.progress||0);ppct.textContent=`${Number(d.progress||0)}%`;
    ptext.textContent=st==='queued'?'Analyse en attente du Worker…':'Analyse des paroles en cours…';
   }else if(st==='failed'){
    progress.hidden=false;ppct.textContent='Erreur';ptext.textContent=d.error||'Analyse en échec';
   }else if(st==='completed'){
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
