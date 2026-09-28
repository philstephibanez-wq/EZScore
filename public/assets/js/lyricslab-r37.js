(() => {
'use strict';

const root=document.querySelector('[data-lyricslab]');
if(!root)return;

const parse=value=>{try{return JSON.parse(value||'[]')}catch(_){return[]}};
const beats=parse(root.dataset.beats).sort((a,b)=>a.start_ms-b.start_ms);
const chords=parse(root.dataset.chords).sort((a,b)=>(a.start_ms-b.start_ms)||(a.id-b.id));
const lyrics=parse(root.dataset.lyrics).sort((a,b)=>(a.start_ms-b.start_ms)||(a.id-b.id));
const measuresEl=root.querySelector('[data-lyrics-measures]');
const capo=Number(root.dataset.capo||0);
if(!measuresEl)return;

const NOTE_TO_PC={C:0,'C#':1,Db:1,D:2,'D#':3,Eb:3,E:4,F:5,'F#':6,Gb:6,G:7,'G#':8,Ab:8,A:9,'A#':10,Bb:10,B:11};
const SHARP=['C','C#','D','D#','E','F','F#','G','G#','A','A#','B'];
const FLAT=['C','Db','D','Eb','E','F','Gb','G','Ab','A','Bb','B'];

function displayChord(value){
 const chord=String(value||'').trim().replace(/^\[([^\]]+)\]$/,'$1');
 if(!chord||chord==='.')return chord||'.';
 const m=/^([A-G](?:#|b)?)(.*)$/.exec(chord);if(!m)return chord;
 const pc=NOTE_TO_PC[m[1]];if(pc===undefined)return chord;
 const names=m[1].includes('b')?FLAT:SHARP;
 return names[(pc-capo+120)%12]+m[2];
}
function activeChord(ms){
 let current=null;
 for(const e of chords){if(e.start_ms<=ms)current=e;else break}
 return current;
}
function nextBeatStart(index){
 if(index+1<beats.length)return beats[index+1].start_ms;
 const delta=index>0?beats[index].start_ms-beats[index-1].start_ms:500;
 return beats[index].start_ms+Math.max(250,delta);
}
function build(){
 const measures=new Map();
 beats.forEach((beat,index)=>{
  const measureIndex=Number.isInteger(beat.measure_index)?beat.measure_index:0;
  if(!measures.has(measureIndex))measures.set(measureIndex,[]);
  const end=nextBeatStart(index);
  const exact=chords.find(e=>e.start_ms>=beat.start_ms&&e.start_ms<end);
  const active=exact||activeChord(beat.start_ms);
  let chordText='-';
  if(exact)chordText=displayChord(exact.effective||exact.original||'.');
  else if((active?.effective||active?.original||'')==='.')chordText='.';
  else if(Number(beat.beat_index||0)===0)chordText=displayChord(active?.effective||active?.original||'.');
  const words=lyrics.filter(w=>w.start_ms>=beat.start_ms&&w.start_ms<end);
  measures.get(measureIndex).push({beat,index,chordText,words});
 });
 measuresEl.innerHTML='';
 for(const [measureIndex,slots] of measures){
  const measure=document.createElement('div');
  measure.className='chord-measure';
  measure.dataset.measure=String(measureIndex);
  const number=document.createElement('small');
  number.className='chord-measure-number';
  number.textContent=String(Number(measureIndex)+1);
  measure.appendChild(number);
  const notation=document.createElement('div');
  notation.className='chord-measure-notation lyricslab-notation';
  for(const slot of slots){
   const cell=document.createElement('div');
   cell.className='chord-slot lyricslab-beat';
   cell.dataset.beatSeq=String(slot.index);
   cell.dataset.startMs=String(slot.beat.start_ms);
   cell.dataset.beat=String(slot.beat.beat_index??0);

   const chord=document.createElement('div');
   chord.className='lyricslab-chord';
   chord.textContent=slot.chordText;
   cell.appendChild(chord);

   const words=document.createElement('div');
   words.className='lyricslab-words';
   for(const word of slot.words){
    const b=document.createElement('button');
    b.type='button';
    b.className='lyricslab-word';
    b.textContent=word.effective||word.original||'';
    b.dataset.eventId=String(word.id);
    b.dataset.startMs=String(word.start_ms);
    b.dataset.endMs=String(word.end_ms||word.start_ms+160);
    words.appendChild(b);
   }
   cell.appendChild(words);
   notation.appendChild(cell);
  }
  measure.appendChild(notation);
  measuresEl.appendChild(measure);
 }
}
async function editWord(button){
 const id=button.dataset.eventId;if(!id)return;
 const input=document.createElement('input');
 input.className='lyricslab-word-input';
 input.value=button.textContent||'';
 button.replaceWith(input);input.focus();input.select();
 let done=false;
 const restore=()=>{if(done)return;done=true;build()};
 const save=async()=>{
  if(done)return;
  const text=input.value.trim();if(!text){restore();return}
  const url=root.dataset.editUrlTemplate.replace('__EVENT__',id);
  const response=await fetch(url,{
   method:'POST',credentials:'same-origin',
   headers:{'Content-Type':'application/json','Accept':'application/json'},
   body:JSON.stringify({_token:root.dataset.editToken,text})
  });
  if(!response.ok){input.classList.add('is-error');return}
  const data=await response.json();
  const event=lyrics.find(row=>String(row.id)===String(id));
  if(event){event.override=data.override;event.effective=data.effective}
  done=true;build();
 };
 input.addEventListener('keydown',e=>{
  if(e.key==='Enter'){e.preventDefault();save()}
  else if(e.key==='Escape'){e.preventDefault();restore()}
 });
 input.addEventListener('blur',save,{once:true});
}
measuresEl.addEventListener('click',e=>{
 const b=e.target.closest('.lyricslab-word[data-event-id]');
 if(b)editWord(b);
});

document.querySelector('[data-stem-mixer]')?.addEventListener('ezscore:audio-timeupdate',e=>{
 const ms=Number(e.detail?.time||0)*1000;
 let seq=-1;
 for(let i=0;i<beats.length;i++){if(beats[i].start_ms<=ms)seq=i;else break}
 measuresEl.querySelectorAll('.is-current').forEach(el=>el.classList.remove('is-current'));
 if(seq>=0){
  const cell=measuresEl.querySelector(`.chord-slot[data-beat-seq="${seq}"]`);
  cell?.classList.add('is-current');
  cell?.closest('.chord-measure')?.classList.add('is-current');
 }
 let currentWord=null;
 measuresEl.querySelectorAll('.lyricslab-word').forEach(word=>{
  const start=Number(word.dataset.startMs||0);
  const end=Number(word.dataset.endMs||start+160);
  const on=ms>=start&&ms<Math.max(end,start+120);
  word.classList.toggle('is-current',on);
  if(on)currentWord=word;
 });
 currentWord?.scrollIntoView({behavior:'smooth',inline:'center',block:'nearest'});
});

build();

const source=document.querySelector('[data-lyrics-source]');
const saveState=document.querySelector('[data-lyrics-save-state]');
let timer=null;
async function saveSource(){
 if(!source)return true;
 try{
  const response=await fetch(source.dataset.saveUrl,{
   method:'POST',credentials:'same-origin',
   headers:{'Content-Type':'application/json','Accept':'application/json'},
   body:JSON.stringify({_token:source.dataset.saveToken,text:source.value})
  });
  if(!response.ok)throw new Error(`source_http_${response.status}`);
  if(saveState)saveState.textContent='Enregistré';
  return true;
 }catch(_){
  if(saveState)saveState.textContent='Échec enregistrement';
  return false;
 }
}
source?.addEventListener('input',()=>{
 if(saveState)saveState.textContent='Modifié…';
 clearTimeout(timer);
 timer=setTimeout(saveSource,450);
});

const progress=document.querySelector('[data-lyrics-progress]');
const statusUrl=progress?.dataset.statusUrl||'';
const bar=progress?.querySelector('progress');
const label=progress?.querySelector('[data-lyrics-progress-text]');
const percent=progress?.querySelector('[data-lyrics-progress-percent]');
async function poll(){
 if(!statusUrl)return;
 try{
  const response=await fetch(statusUrl,{headers:{Accept:'application/json'},cache:'no-store',credentials:'same-origin'});
  if(response.ok){
   const data=await response.json();
   const status=String(data.status||'');
   const pct=Number(data.progress||0);
   if(status==='queued'||status==='running'){
    progress.hidden=false;
    if(bar)bar.value=pct;
    if(percent)percent.textContent=`${pct}%`;
    if(label)label.textContent=status==='queued'
      ? 'En attente du Worker…'
      : (data.mode==='extract'?'Extraction automatique des paroles…':'Ancrage des paroles sur la timeline…');
   }else if(status==='failed'){
    progress.hidden=false;
    if(percent)percent.textContent='Erreur';
    if(label)label.textContent=data.error||'Analyse des paroles en échec.';
   }else if(status==='completed'){
    const key=`ezscore.lyrics.job.reloaded.${data.job_id}`;
    if(data.job_id&&sessionStorage.getItem(key)!=='1'){
     sessionStorage.setItem(key,'1');
     location.reload();
     return;
    }
    progress.hidden=true;
   }else progress.hidden=true;
  }
 }catch(_){}
 setTimeout(poll,900);
}
poll();
})();
