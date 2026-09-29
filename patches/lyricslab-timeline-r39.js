/* EZScore R39 — LyricsLab renderer on the canonical ChordsLab musical timeline. */
(() => {
'use strict';
const Core=window.EZScoreTimelineCoreR39;if(!Core)return;
window.EZScoreLyricsTimelineR39={mount(root){
 const parse=v=>{try{return JSON.parse(v||'[]')}catch(_){return[]}};
 const sourceBeats=parse(root.dataset.beats),chords0=parse(root.dataset.chords),words=parse(root.dataset.lyrics);
 const timeline=Core.create({beats:sourceBeats,timeSignature:String(root.dataset.timeSignature||'4/4'),spacing:166,preserveSourcePosition:true});
 const beats=timeline.beats;if(!beats.length)return;
 let chords=chords0.slice().sort((a,b)=>Number(a.start_ms)-Number(b.start_ms));
 let currentProfile=String(root.querySelector('[data-lyrics-profile]')?.value||'intermediate');
 const capo=Number(root.dataset.capo||0),host=root.querySelector('[data-lyrics-measures]');if(!host)return;
 const NOTE={C:0,'C#':1,Db:1,D:2,'D#':3,Eb:3,E:4,F:5,'F#':6,Gb:6,G:7,'G#':8,Ab:8,A:9,'A#':10,Bb:10,B:11};
 const SH=['C','C#','D','D#','E','F','F#','G','G#','A','A#','B'],FL=['C','Db','D','Eb','E','F','Gb','G','Ab','A','Bb','B'];
 const shown=v=>{let c=String(v||'.').trim().replace(/^\[([^\]]+)\]$/,'$1').replace(/♭/g,'b');if(!c||c==='.')return'.';const m=/^([A-G](?:#|b)?)(.*)$/.exec(c);if(!m||NOTE[m[1]]===undefined)return c;const names=m[1].includes('b')?FL:SH;return names[(NOTE[m[1]]-capo+120)%12]+m[2]};
 const normaliseLabel=c=>String(c||'').trim().replace(/^\[([^\]]+)\]$/,'$1').replace(/^([A-G](?:#|b)?)maj$/,'$1');

 host.innerHTML='<div class="lyrics-ribbon-stage r39-shared-timeline" data-stage><div class="lyrics-reading-zone" data-reading-zone></div><div class="lyrics-ribbon-track" data-track><div class="lyrics-ribbon-chords" data-chords-lane></div><div class="lyrics-ribbon-syllables" data-syllables-lane></div></div></div>';
 const stage=host.querySelector('[data-stage]'),zone=host.querySelector('[data-reading-zone]'),track=host.querySelector('[data-track]'),chordLane=host.querySelector('[data-chords-lane]'),syllableLane=host.querySelector('[data-syllables-lane]');
 const syllables=Core.flattenSyllables(words),syllableNodes=[];
 const focusX=()=>Math.max(105,stage.clientWidth*.30);
 function activeSyllable(ms){let i=-1;for(let k=0;k<syllables.length;k++){if(syllables[k].nucleusMs<=ms)i=k;else break}return i}

 function buildSyllables(){
  syllableLane.innerHTML='';syllableNodes.length=0;
  syllables.forEach((s,i)=>{const e=document.createElement('span');e.className='lyrics-ribbon-syllable'+(s.fallback?' is-word-fallback':'');e.dataset.syllableIndex=String(i);e.dataset.wordIndex=String(s.wordIndex);e.dataset.beatSeq=String(timeline.beatPhaseAtMs(s.nucleusMs).beatIndex);e.style.left=timeline.timeToX(s.nucleusMs)+'px';e.textContent=s.display;e.title=`${s.nucleusMs} ms`;syllableLane.appendChild(e);syllableNodes.push(e)});
 }
 function buildChords(){
  chordLane.innerHTML='';
  timeline.chordProjection(chords,shown).forEach(slot=>{const left=timeline.xBeat(slot.seq),next=slot.seq+1<beats.length?timeline.xBeat(slot.seq+1):left+timeline.spacing,cell=document.createElement('button');cell.type='button';cell.className='lyrics-ribbon-beat'+(Number(slot.beat.display_beat_index)===0?' measure-start':'')+(slot.editable?' editable':'');cell.dataset.beatSeq=String(slot.seq);cell.dataset.startMs=String(slot.startMs);if(slot.beatId)cell.dataset.beatId=String(slot.beatId);if(slot.activeEventId)cell.dataset.activeEventId=String(slot.activeEventId);cell.style.left=left+'px';cell.style.width=Math.max(74,next-left)+'px';const c=document.createElement('strong');c.className='lyrics-ribbon-chord';c.textContent=slot.text;cell.setAttribute('aria-label',slot.text);cell.appendChild(c);if(Number(slot.beat.display_beat_index)===0){const m=document.createElement('small');m.className='lyrics-ribbon-measure';m.textContent='#'+(Number(slot.beat.display_measure_index||0)+1);cell.appendChild(m)}chordLane.appendChild(cell)});
 }
 async function editChord(button){
  const beatId=button.dataset.beatId;if(!beatId)return;
  const activeId=button.dataset.activeEventId||'',active=activeId?chords.find(e=>String(e.id)===String(activeId)):null,input=document.createElement('input');
  input.className='chord-inline-input lyrics-chord-inline-input';const label=button.getAttribute('aria-label')||'.';input.value=label==='-'?shown(active?.effective||active?.original||''):label;input.maxLength=32;button.replaceWith(input);input.focus();input.select();let done=false;
  const restore=()=>{if(done)return;done=true;buildChords();renderAt(lastTime,true)};
  const save=async()=>{if(done)return;let chord=normaliseLabel(input.value);if(!chord)chord='.';if(chord==='-'){restore();return}try{await Core.saveBeatOverride({urlTemplate:root.dataset.chordBeatEditUrlTemplate,beatId,token:root.dataset.chordEditToken,chord,profile:currentProfile});done=true;location.reload()}catch(error){console.error('LyricsLab chord edit failed',error);input.classList.add('is-error')}};
  input.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();save()}else if(e.key==='Escape'){e.preventDefault();restore()}});input.addEventListener('blur',save,{once:true});
 }
 chordLane.addEventListener('click',e=>{const b=e.target.closest('.lyrics-ribbon-beat.editable[data-beat-id]');if(b)editChord(b)});

 let lastTime=0,lastBeat=-2,lastSyllable=-2;
 function renderAt(sec,force=false){
  lastTime=Math.max(0,Number(sec)||0);const x=focusX(),metric=timeline.timeToX(lastTime*1000);zone.style.left=x+'px';track.style.transform=`translate3d(${x-metric}px,0,0)`;
  const bi=timeline.beatIndexAtMs(lastTime*1000);if(force||bi!==lastBeat){lastBeat=bi;chordLane.querySelectorAll('.current').forEach(e=>e.classList.remove('current'));chordLane.querySelector(`.lyrics-ribbon-beat[data-beat-seq="${bi}"]`)?.classList.add('current')}
  const si=activeSyllable(lastTime*1000);if(force||si!==lastSyllable){lastSyllable=si;syllableNodes.forEach((e,i)=>{e.classList.toggle('past',si>=0&&i<si);e.classList.toggle('current',i===si)})}
 }

 const profileSelect=root.querySelector('[data-lyrics-profile]'),profileDataUrlTemplate=root.dataset.profileDataUrlTemplate||'',profileSaveUrl=root.dataset.profileSaveUrl||'',profileToken=root.dataset.profileToken||'';
 profileSelect?.addEventListener('change',async()=>{currentProfile=String(profileSelect.value||'intermediate');profileSelect.disabled=true;try{if(profileSaveUrl&&profileToken){const saved=await fetch(profileSaveUrl,{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','Accept':'application/json'},body:JSON.stringify({_token:profileToken,profile:currentProfile})});if(!saved.ok)throw new Error(`profile_save_http_${saved.status}`)}if(profileDataUrlTemplate){const response=await fetch(profileDataUrlTemplate.replace('__PROFILE__',encodeURIComponent(currentProfile)),{headers:{Accept:'application/json'},credentials:'same-origin',cache:'no-store'});if(!response.ok)throw new Error(`profile_http_${response.status}`);const data=await response.json();if(!Array.isArray(data.events))throw new Error('invalid_profile_payload');chords=data.events.slice().sort((a,b)=>Number(a.start_ms)-Number(b.start_ms));buildChords();renderAt(lastTime,true)}}catch(error){console.error('LyricsLab profile switch failed',error);location.reload()}finally{profileSelect.disabled=false}});
 document.querySelector('[data-stem-mixer]')?.addEventListener('ezscore:audio-timeupdate',e=>renderAt(Number(e.detail?.time||0)));

 const progress=document.querySelector('[data-lyrics-progress]'),statusUrl=progress?.dataset.statusUrl||'',progressBar=progress?.querySelector('progress'),progressLabel=progress?.querySelector('[data-lyrics-progress-text]'),progressPercent=progress?.querySelector('[data-lyrics-progress-percent]');
 async function poll(){if(!statusUrl)return;try{const response=await fetch(statusUrl,{headers:{Accept:'application/json'},cache:'no-store',credentials:'same-origin'});if(response.ok){const data=await response.json(),status=String(data.status||''),pct=Math.max(0,Math.min(100,Number(data.progress||0)));if(status==='queued'||status==='running'){progress.hidden=false;if(progressBar)progressBar.value=pct;if(progressPercent)progressPercent.textContent=`${Math.round(pct)}%`;if(progressLabel)progressLabel.textContent=status==='queued'?'En attente du Worker…':(data.mode==='extract'?'Extraction automatique des paroles…':'Analyse / ancrage des paroles sur la timeline…')}else if(status==='failed'){progress.hidden=false;if(progressPercent)progressPercent.textContent='Erreur';if(progressLabel)progressLabel.textContent='Analyse des paroles en échec. Voir le journal du Worker.'}else if(status==='completed'){if(progressBar)progressBar.value=100;if(progressPercent)progressPercent.textContent='100%';if(progressLabel)progressLabel.textContent=String(data.mode||'align')==='extract'?'Extraction terminée':'Analyse terminée';const key=`ezscore.lyrics.job.reloaded.${data.job_id}`;if(data.job_id&&sessionStorage.getItem(key)!=='1'){sessionStorage.setItem(key,'1');setTimeout(()=>location.reload(),180);return}setTimeout(()=>{progress.hidden=true},700)}else progress.hidden=true}}catch(_){}setTimeout(poll,900)}

 buildChords();buildSyllables();const lastMs=Math.max(Number(beats.at(-1)?.start_ms||0),Number(syllables.at(-1)?.endMs||0));track.style.width=Math.max(2600,timeline.timeToX(lastMs)+timeline.spacing*8)+'px';renderAt(0,true);window.addEventListener('resize',()=>renderAt(lastTime,true));poll();
 root.dataset.timelineEngine='ezscore-r39-canonical';root.dataset.lyricTimingUnit='syllable';
}};
})();
