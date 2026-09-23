"""Step 1 Riffstation-style STEM auditor.

Representation layer only.  Musical truth is loaded from
``ezscore.analysis.riffstation_step1``.  No lyric data is accepted here.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit as st

from ezscore.analysis.riffstation_step1 import (
    SUPPORTED_SIGNATURES,
    analyze as analyze_step1,
    effective_signature,
    load as load_step1,
    timeline_beats_per_measure,
)
from ezscore.analysis.stems import STEM_NAMES
from ezscore.guitar import (
    choices as guitar_choices,
    get_voicing,
    load_show_diagrams,
    load_voicings,
    save_show_diagrams,
    svg as guitar_svg,
)
from ezscore.notation import accord_forme_capo
from ezscore.persistence import (
    current_song_settings_payload,
    load_song_preferences,
    save_song_preferences,
    list_song_catalog,
)
from ezscore.player.media_url import register_media_url


_HTML = r"""
<div class="riffstation-step1">
  <div class="song-card">
    <div class="song-id">
      <div class="song-title"></div>
      <div class="song-meta"></div>
    </div>
    <div class="song-controls">
      <label class="compact-control">Mode
        <select class="work-mode" aria-label="Mode de travail">
          <option value="Analyse">Analyse</option>
          <option value="Édition">Édition</option>
          <option value="Player">Player</option>
        </select>
      </label>
      <label class="compact-control">Time sig
        <select class="signature-mode" aria-label="Time signature Step 1">
          <option value="Auto">Auto</option>
          <option value="2/4">2/4</option>
          <option value="3/4">3/4</option>
          <option value="4/4">4/4</option>
          <option value="5/4">5/4</option>
          <option value="6/8">6/8</option>
          <option value="7/8">7/8</option>
          <option value="9/8">9/8</option>
          <option value="12/8">12/8</option>
        </select>
      </label>
      <label class="compact-control">Capo
        <select class="capo-select" aria-label="Capo Step 1"></select>
      </label>
      <label class="compact-control">Vitesse
        <select class="speed" aria-label="Vitesse de lecture">
          <option value="0.50">0,50×</option>
          <option value="0.75">0,75×</option>
          <option value="1.00" selected>1,00×</option>
          <option value="1.25">1,25×</option>
          <option value="1.50">1,50×</option>
        </select>
      </label>
      <label class="diagram-toggle">
        <input class="diagram-checkbox" type="checkbox"> Diagramme
      </label>
    </div>
  </div>

  <div class="transport">
    <button class="play" type="button">▶ Lecture</button>
    <button class="pause" type="button">⏸ Pause</button>
    <button class="stop" type="button">⏹ Stop</button>
    <span class="time">0:00 / 0:00</span>
  </div>
  <input class="seek" type="range" min="0" max="1" step="0.001" value="0">

  <div class="mixer-head">
    <div>Piste</div><div>ON</div><div>Volume</div>
    <div>Graves</div><div>Médiums</div><div>Aigus</div><div></div>
  </div>
  <div class="tracks"></div>

  <div class="master-row">
    <div class="master-name">Master</div>
    <div class="master-value">100%</div>
    <input class="master-volume master-control" type="range" min="0" max="1.25" step="0.01" value="1">
  </div>

  <div class="conductor-window">
    <div class="playhead"></div>
    <div class="diagram-float"></div>
    <div class="conductor-canvas">
      <div class="beat-grid"></div>
      <div class="chord-track"></div>
    </div>
  </div>
  <div class="media-host" aria-hidden="true"></div>

  <div class="hint">
    Step 1 = Riffstation + STEM. La timeline audio reste immuable ; seule sa représentation défile sous la mire.
  </div>
</div>
"""

_CSS = r"""
:host { display:block; width:100%; }
.riffstation-step1 {
  box-sizing:border-box; width:100%;
  border:1px solid color-mix(in srgb,var(--st-text-color) 25%,transparent);
  border-radius:10px; padding:12px;
  background:color-mix(in srgb,var(--st-text-color) 4%,transparent);
  color:var(--st-text-color); font-family:var(--st-font);
}
.song-card {
  display:flex; justify-content:space-between; align-items:flex-end; gap:18px;
  padding:10px 12px 12px; margin-bottom:12px;
  border:1px solid color-mix(in srgb,var(--st-text-color) 18%,transparent);
  border-radius:9px; background:color-mix(in srgb,var(--st-text-color) 3%,transparent);
}
.song-id { min-width:220px; flex:1 1 auto; }
.song-title { font-size:20px; font-weight:900; line-height:1.15; }
.song-meta { margin-top:4px; font-size:12px; opacity:.72; }
.song-controls { display:flex; gap:9px; align-items:flex-end; flex-wrap:wrap; justify-content:flex-end; }
.transport { display:flex; align-items:center; gap:8px; flex-wrap:wrap; }
.transport button, .eq-reset, .speed, .signature-mode, .capo-select, .work-mode {
  min-height:30px; border-radius:7px;
  border:1px solid color-mix(in srgb,var(--st-text-color) 35%,transparent);
  background:color-mix(in srgb,var(--st-text-color) 8%,transparent);
  color:var(--st-text-color); padding:4px 8px;
}
.transport button { cursor:pointer; }
.compact-control, .diagram-toggle {
  display:flex; flex-direction:column; align-items:flex-start; gap:4px;
  font-size:11px; font-weight:750;
}
.diagram-toggle { flex-direction:row; align-items:center; min-height:30px; padding-bottom:2px; }
.time { margin-left:auto; font-variant-numeric:tabular-nums; font-size:12px; opacity:.78; }
.seek { width:100%; margin:10px 0 14px; }
.mixer-head, .track {
  display:grid;
  grid-template-columns:minmax(90px,1.2fr) 52px minmax(115px,1.3fr)
                        minmax(90px,1fr) minmax(90px,1fr) minmax(90px,1fr) 64px;
  gap:8px; align-items:center;
}
.mixer-head { font-size:11px; font-weight:800; opacity:.65; padding:0 4px 5px; }
.tracks { display:grid; gap:3px; }
.track { padding:5px 4px; border-top:1px solid color-mix(in srgb,var(--st-text-color) 12%,transparent); }
.track-name { font-weight:800; }
.track-toggle { display:flex; align-items:center; gap:5px; font-size:11px; }
.control-cell { display:grid; grid-template-columns:1fr auto; gap:5px; align-items:center; }
.control-cell input[type="range"] { width:100%; min-width:0; }
.control-value { width:42px; text-align:right; font-size:10px; opacity:.72; font-variant-numeric:tabular-nums; }
.eq-reset { font-size:10px; cursor:pointer; }
.master-row {
  display:grid; grid-template-columns:82px 48px 1fr; gap:8px; align-items:center;
  margin-top:12px; padding-top:10px;
  border-top:1px solid color-mix(in srgb,var(--st-text-color) 18%,transparent);
}
.master-name { font-weight:900; }
.master-value { font-size:11px; opacity:.75; font-variant-numeric:tabular-nums; }
.master-volume { width:100%; }
.conductor-window {
  --playhead-x:28%;
  position:relative; overflow:hidden; height:230px; margin-top:14px;
  border-radius:9px; background:color-mix(in srgb,var(--st-text-color) 5%,transparent);
  border:1px solid color-mix(in srgb,var(--st-text-color) 12%,transparent);
}
.playhead {
  position:absolute; z-index:20; left:var(--playhead-x); top:0; bottom:0; width:2px;
  background:#4da3ff; box-shadow:0 0 0 1px color-mix(in srgb,#4da3ff 20%,transparent);
  pointer-events:none;
}
.diagram-float {
  position:absolute; z-index:25; top:8px; left:var(--playhead-x); transform:translateX(-50%);
  width:112px; height:120px; display:none; align-items:center; justify-content:center;
  background:color-mix(in srgb,var(--st-background-color) 94%,transparent);
  border:1px solid color-mix(in srgb,var(--st-text-color) 16%,transparent);
  border-radius:8px; pointer-events:none;
}
.diagram-float.visible { display:flex; }
.diagram-float svg { max-width:104px; max-height:114px; }
.conductor-canvas { position:absolute; left:0; top:0; height:100%; will-change:transform; }
.beat-grid, .chord-track { position:absolute; left:0; right:0; top:140px; height:72px; }
.beat-line { position:absolute; top:0; bottom:0; width:1px; background:color-mix(in srgb,var(--st-text-color) 15%,transparent); }
.beat-line.measure { width:2px; background:color-mix(in srgb,#4da3ff 42%,transparent); }
.chord-token {
  position:absolute; top:20px; transform:translateX(-50%);
  padding:4px 7px; border-radius:6px; font-weight:850; font-size:16px;
  white-space:nowrap; opacity:.62;
  transition:opacity 50ms linear, transform 50ms linear, background 50ms linear;
}
.chord-token.past { opacity:.24; }
.chord-token.current { opacity:1; transform:translateX(-50%) scale(1.08); background:color-mix(in srgb,#4da3ff 22%,transparent); }
.hint { margin-top:8px; font-size:11px; opacity:.68; }
.media-host { display:none; }
@media(max-width:950px) {
  .song-card { align-items:flex-start; flex-direction:column; }
  .song-controls { justify-content:flex-start; }
  .mixer-head { display:none; }
  .track { grid-template-columns:1fr 58px; }
  .track-name { grid-column:1; }
  .track-toggle { grid-column:2; justify-self:end; }
  .control-cell, .eq-reset { grid-column:1 / -1; }
  .eq-reset { justify-self:start; }
}
"""

_JS = r"""
export default function(component) {
  const data = component.data || {};
  const root = component.parentElement;
  const defs = Array.isArray(data.tracks) ? data.tracks : [];
  const beats = Array.isArray(data.beats) ? data.beats : [];
  const diagrams = data.chord_diagrams || {};
  const pxPerSecond = Number(data.px_per_second || 118);
  const bpb = Number(data.beats_per_measure || 1);

  const playButton = root.querySelector('.play');
  const pauseButton = root.querySelector('.pause');
  const stopButton = root.querySelector('.stop');
  const workModeSelect = root.querySelector('.work-mode');
  const signatureSelect = root.querySelector('.signature-mode');
  const capoSelect = root.querySelector('.capo-select');
  const speedSelect = root.querySelector('.speed');
  const diagramCheckbox = root.querySelector('.diagram-checkbox');
  const seek = root.querySelector('.seek');
  const timeLabel = root.querySelector('.time');
  const tracksNode = root.querySelector('.tracks');
  const masterVolume = root.querySelector('.master-volume');
  const masterValue = root.querySelector('.master-value');
  const windowNode = root.querySelector('.conductor-window');
  const canvas = root.querySelector('.conductor-canvas');
  const grid = root.querySelector('.beat-grid');
  const chordTrack = root.querySelector('.chord-track');
  const diagramNode = root.querySelector('.diagram-float');
  const mediaHost = root.querySelector('.media-host');
  const songTitleNode = root.querySelector('.song-title');
  const songMetaNode = root.querySelector('.song-meta');


  const trackState = defs.map(track => ({
    enabled:Boolean(track.enabled), volume:Number(track.volume ?? .8),
    low:Number(track.low ?? 0), mid:Number(track.mid ?? 0), high:Number(track.high ?? 0),
  }));
  let masterState = 1.0;
  let playbackRate = 1.0;
  const initialWorkMode = String(data.work_mode || 'Analyse');
  const initialSignatureMode = String(data.signature_mode || 'Auto');
  workModeSelect.value = initialWorkMode;
  songTitleNode.textContent = String(data.song_title || 'Morceau');
  songMetaNode.textContent = [String(data.song_artist || '').trim(), String(data.song_editor || '').trim() ? ('Éditeur : ' + String(data.song_editor || '').trim()) : ''].filter(Boolean).join(' · ');
  const initialCapo = Math.max(0, Math.min(12, Number(data.capo) || 0));
  signatureSelect.value = initialSignatureMode;
  for (let c = 0; c <= 12; c += 1) {
    const option = document.createElement('option');
    option.value = String(c);
    option.textContent = c === 0 ? '0 — sans capo' : String(c);
    capoSelect.appendChild(option);
  }
  capoSelect.value = String(initialCapo);
  let context = null;
  let masterGain = null;
  let media = [];
  let nodes = [];
  let ready = false;
  let playing = false;
  let disposed = false;
  let raf = null;
  let duration = Number(data.duration_hint || 0);
  let activeBeat = -1;
  let showDiagrams = Boolean(component.state?.show_diagrams ?? data.show_diagrams);

  function fmt(seconds) {
    const t = Math.max(0, Number(seconds) || 0);
    return Math.floor(t / 60) + ':' + String(Math.floor(t % 60)).padStart(2,'0');
  }
  function dbToLinear(db) { return Math.pow(10, Number(db || 0) / 20); }
  function compensationFor(state) {
    const avg=(dbToLinear(state.low)+dbToLinear(state.mid)+dbToLinear(state.high))/3;
    return (!Number.isFinite(avg)||avg<=.0001) ? 1 : Math.max(.72,Math.min(1.25,1/avg));
  }
  function masterTime() { return media.length ? Number(media[0].currentTime || 0) : 0; }

  function applyTrackState(index, smooth=true) {
    if (!ready || !nodes[index] || !context) return;
    const state=trackState[index], n=nodes[index], now=context.currentTime;
    const target=(state.enabled ? state.volume : 0)*compensationFor(state);
    const set=(param,value)=> smooth ? param.setTargetAtTime(value,now,.015) : (param.value=value);
    set(n.lowGain.gain,dbToLinear(state.low));
    set(n.midGain.gain,dbToLinear(state.mid));
    set(n.highGain.gain,dbToLinear(state.high));
    set(n.trackGain.gain,target);
  }
  function applyMasterState(smooth=true) {
    if (!ready || !masterGain || !context) return;
    const now=context.currentTime;
    if (smooth) masterGain.gain.setTargetAtTime(masterState,now,.015);
    else masterGain.gain.value=masterState;
  }

  function waitMetadata(audio) {
    if (Number.isFinite(audio.duration) && audio.duration > 0) return Promise.resolve();
    return new Promise((resolve,reject)=>{
      const done=()=>{cleanup();resolve();};
      const fail=()=>{cleanup();reject(new Error('Média audio illisible'));};
      const cleanup=()=>{audio.removeEventListener('loadedmetadata',done);audio.removeEventListener('error',fail);};
      audio.addEventListener('loadedmetadata',done,{once:true});
      audio.addEventListener('error',fail,{once:true});
      audio.load();
    });
  }

  async function ensureReady() {
    if (ready) { if (context.state==='suspended') await context.resume(); return; }
    playButton.disabled=true; playButton.textContent='Chargement audio…';
    context=new (window.AudioContext||window.webkitAudioContext)({latencyHint:'interactive'});
    masterGain=context.createGain(); masterGain.connect(context.destination);

    media=[]; nodes=[];
    for (let i=0;i<defs.length;i+=1) {
      const audio=document.createElement('audio');
      audio.preload='auto'; audio.src=String(defs[i].url||'');
      audio.crossOrigin='anonymous';
      audio.preservesPitch=true; audio.mozPreservesPitch=true; audio.webkitPreservesPitch=true;
      audio.playbackRate=playbackRate;
      mediaHost.appendChild(audio);
      await waitMetadata(audio);

      const src=context.createMediaElementSource(audio);
      const lowLP=context.createBiquadFilter(); lowLP.type='lowpass'; lowLP.frequency.value=250; lowLP.Q.value=.707;
      const midHP=context.createBiquadFilter(); midHP.type='highpass'; midHP.frequency.value=250; midHP.Q.value=.707;
      const midLP=context.createBiquadFilter(); midLP.type='lowpass'; midLP.frequency.value=4000; midLP.Q.value=.707;
      const highHP=context.createBiquadFilter(); highHP.type='highpass'; highHP.frequency.value=4000; highHP.Q.value=.707;
      const lowGain=context.createGain(), midGain=context.createGain(), highGain=context.createGain();
      const bandSum=context.createGain(), trackGain=context.createGain();
      src.connect(lowLP); src.connect(midHP); src.connect(highHP);
      lowLP.connect(lowGain); lowGain.connect(bandSum);
      midHP.connect(midLP); midLP.connect(midGain); midGain.connect(bandSum);
      highHP.connect(highGain); highGain.connect(bandSum);
      bandSum.connect(trackGain); trackGain.connect(masterGain);
      media.push(audio); nodes.push({src,lowLP,midHP,midLP,highHP,lowGain,midGain,highGain,bandSum,trackGain});
    }
    duration=Number(media[0]?.duration || duration || 0);
    seek.max=String(Math.max(.001,duration));
    ready=true;
    trackState.forEach((_,i)=>applyTrackState(i,false)); applyMasterState(false);
    playButton.disabled=false; playButton.textContent='▶ Lecture';
  }

  async function playAll() {
    await ensureReady();
    if (context.state==='suspended') await context.resume();
    if (masterTime() >= duration-.01) seekTo(0);
    const base=masterTime();
    media.forEach(a=>{ a.currentTime=base; a.playbackRate=playbackRate; });
    const results=await Promise.allSettled(media.map(a=>a.play()));
    const rejected=results.find(x=>x.status==='rejected');
    if (rejected) throw rejected.reason;
    playing=true;
  }
  function pauseAll() { media.forEach(a=>a.pause()); playing=false; }
  function stopAll() { media.forEach(a=>{a.pause();a.currentTime=0;}); playing=false; renderAt(0); }
  function seekTo(value) {
    const t=Math.max(0,Math.min(duration,Number(value)||0));
    media.forEach(a=>{ try{a.currentTime=t;}catch(_){} });
    renderAt(t);
  }
  function setRate(rate) {
    playbackRate=Math.max(.5,Math.min(1.5,Number(rate)||1));
    media.forEach(a=>{ a.preservesPitch=true; a.mozPreservesPitch=true; a.webkitPreservesPitch=true; a.playbackRate=playbackRate; });
  }

  function makeSlider(index,field,min,max,step,suffix) {
    const wrap=document.createElement('div'); wrap.className='control-cell';
    const slider=document.createElement('input'); slider.type='range'; slider.min=min; slider.max=max; slider.step=step; slider.value=trackState[index][field];
    const value=document.createElement('span'); value.className='control-value';
    const refresh=()=>{const v=Number(slider.value);value.textContent=suffix==='dB'?((v>0?'+':'')+v.toFixed(0)+' dB'):(Math.round(v*100)+'%');};
    slider.addEventListener('input',()=>{trackState[index][field]=Number(slider.value);refresh();applyTrackState(index,true);});
    refresh(); wrap.append(slider,value); return {wrap,slider,value};
  }

  defs.forEach((track,index)=>{
    const row=document.createElement('div'); row.className='track';
    const name=document.createElement('div'); name.className='track-name'; name.textContent=String(track.label||track.name||'Track');
    const toggleWrap=document.createElement('label'); toggleWrap.className='track-toggle';
    const toggle=document.createElement('input'); toggle.type='checkbox'; toggle.checked=trackState[index].enabled;
    const toggleText=document.createElement('span'); toggleText.textContent='Actif';
    toggle.addEventListener('change',()=>{trackState[index].enabled=Boolean(toggle.checked);applyTrackState(index,true);});
    toggleWrap.append(toggle,toggleText);
    const volume=makeSlider(index,'volume',0,1.25,.01,'%');
    const low=makeSlider(index,'low',-6,6,1,'dB'), mid=makeSlider(index,'mid',-6,6,1,'dB'), high=makeSlider(index,'high',-6,6,1,'dB');
    const reset=document.createElement('button'); reset.type='button'; reset.className='eq-reset'; reset.textContent='Reset EQ';
    reset.addEventListener('click',()=>{for(const f of ['low','mid','high'])trackState[index][f]=0;for(const o of [low,mid,high]){o.slider.value='0';o.value.textContent='0 dB';}applyTrackState(index,true);});
    row.append(name,toggleWrap,volume.wrap,low.wrap,mid.wrap,high.wrap,reset); tracksNode.appendChild(row);
  });
  masterVolume.addEventListener('input',()=>{masterState=Number(masterVolume.value);masterValue.textContent=Math.round(masterState*100)+'%';applyMasterState(true);});

  const beatSpacing=Math.max(86,Number(data.beat_spacing || 104));
  const beatStarts=beats.map(beat=>Number(beat.start||0));
  const intervals=[];
  for(let i=1;i<beatStarts.length;i+=1){ const d=beatStarts[i]-beatStarts[i-1]; if(Number.isFinite(d)&&d>.02) intervals.push(d); }
  intervals.sort((a,b)=>a-b);
  const nominalInterval=intervals.length ? intervals[Math.floor(intervals.length/2)] : .5;
  const firstBeatStart=beatStarts.length ? Math.max(0,beatStarts[0]) : 0;
  const firstBeatX=(firstBeatStart/Math.max(.02,nominalInterval))*beatSpacing;
  const xForBeatIndex=index=>firstBeatX+(index*beatSpacing);
  function metricXAtTime(value) {
    const t=Math.max(0,Number(value)||0);
    if(!beatStarts.length) return (t/Math.max(.02,nominalInterval))*beatSpacing;
    if(t<=beatStarts[0]) return firstBeatX*(beatStarts[0]>.001 ? t/beatStarts[0] : 1);
    let lo=0,hi=beatStarts.length-1,idx=0;
    while(lo<=hi){ const mid=(lo+hi)>>1; if(beatStarts[mid]<=t){idx=mid;lo=mid+1;}else hi=mid-1; }
    if(idx>=beatStarts.length-1) return xForBeatIndex(idx)+((t-beatStarts[idx])/Math.max(.02,nominalInterval))*beatSpacing;
    const t0=beatStarts[idx], t1=Math.max(t0+.02,beatStarts[idx+1]);
    const phase=Math.max(0,Math.min(1,(t-t0)/(t1-t0)));
    return xForBeatIndex(idx)+(phase*beatSpacing);
  }
  const trackWidth=Math.max(1400,xForBeatIndex(Math.max(0,beats.length-1))+beatSpacing*6);
  canvas.style.width=trackWidth+'px'; grid.style.width=trackWidth+'px'; chordTrack.style.width=trackWidth+'px';
  const chordNodes=[];
  beats.forEach((beat,index)=>{
    const x=xForBeatIndex(index);
    const line=document.createElement('span'); line.className='beat-line'+(index%bpb===0?' measure':''); line.style.left=x+'px'; grid.appendChild(line);
    const token=document.createElement('span'); token.className='chord-token'; token.style.left=x+'px'; token.textContent=String(beat.chord||'.');
    token.title='Beat '+(index+1); chordTrack.appendChild(token); chordNodes.push(token);
  });

  function findBeatIndex(t) {
    if (!beats.length) return -1;
    if (Number(t || 0) < Number(beats[0].start || 0)) return -1;
    let lo=0,hi=beats.length-1,ans=-1;
    while(lo<=hi){
      const mid=(lo+hi)>>1;
      if(Number(beats[mid].start||0)<=t){ans=mid;lo=mid+1;}else hi=mid-1;
    }
    return ans;
  }
  function updateDiagram(index) {
    const chord=index>=0 ? String(beats[index]?.chord||'') : '';
    const svg=showDiagrams ? String(diagrams[chord]||'') : '';
    diagramNode.innerHTML=svg; diagramNode.classList.toggle('visible',Boolean(svg));
  }
  function renderAt(t) {
    const time=Math.max(0,Number(t)||0); seek.value=String(time); timeLabel.textContent=fmt(time)+' / '+fmt(duration);
    const playheadX=windowNode.clientWidth*.28;
    const px=playheadX-metricXAtTime(time); canvas.style.transform='translateX('+px+'px)';
    const index=findBeatIndex(time);
    if(index!==activeBeat){activeBeat=index;chordNodes.forEach((n,i)=>{n.classList.toggle('past',i<index);n.classList.toggle('current',i===index);});updateDiagram(index);}
  }
  function syncFollowers() {
    if (!playing || media.length<2) return;
    const t=masterTime();
    for(let i=1;i<media.length;i+=1){ if(Math.abs(Number(media[i].currentTime||0)-t)>.060){ try{media[i].currentTime=t;}catch(_){} } }
  }
  function tick() {
    if(disposed)return;
    const t=masterTime(); renderAt(t); syncFollowers();
    if(playing && duration>0 && t>=duration-.02){stopAll();}
    raf=requestAnimationFrame(tick);
  }

  workModeSelect.addEventListener('change',()=>{component.setStateValue('work_mode',String(workModeSelect.value||'Analyse'));});
  diagramCheckbox.checked=showDiagrams;
  diagramCheckbox.addEventListener('change',()=>{showDiagrams=Boolean(diagramCheckbox.checked);component.setStateValue('show_diagrams',showDiagrams);updateDiagram(activeBeat);});
  signatureSelect.addEventListener('change',()=>{
    component.setStateValue('signature_mode',String(signatureSelect.value||'Auto'));
  });
  capoSelect.addEventListener('change',()=>{
    component.setStateValue('capo',Number(capoSelect.value||0));
  });
  speedSelect.addEventListener('change',()=>setRate(speedSelect.value));
  playButton.addEventListener('click',()=>{playAll().catch(err=>{playButton.disabled=false;playButton.textContent='▶ Lecture';root.querySelector('.hint').textContent='Erreur audio: '+String(err?.message||err);});});
  pauseButton.addEventListener('click',pauseAll); stopButton.addEventListener('click',stopAll);
  seek.addEventListener('input',()=>seekTo(seek.value));
  window.addEventListener('resize',()=>renderAt(masterTime()));
  renderAt(0); tick();

  return function(){disposed=true;if(raf!==null)cancelAnimationFrame(raf);media.forEach(a=>{try{a.pause();a.src='';}catch(_){}});try{if(context)context.close();}catch(_){}};
}
"""


_COMPONENT = st.components.v2.component(
    "ezscore_step1_riffstation_stems_v2",
    html=_HTML,
    css=_CSS,
    js=_JS,
    isolate_styles=True,
)


def _build_diagrams(audio_hash: str, beats: list[dict[str, Any]]) -> dict[str, str]:
    saved = load_voicings(audio_hash)
    diagrams: dict[str, str] = {}
    for beat in beats:
        symbol = str(beat.get("chord", "") or "").strip()
        if not symbol or symbol in {".", "-", "?", "^"} or symbol in diagrams:
            continue
        candidates = [symbol]
        if "/" in symbol:
            base_symbol = symbol.split("/", 1)[0].strip()
            if base_symbol and base_symbol not in candidates:
                candidates.append(base_symbol)
        for candidate in candidates:
            available = guitar_choices(candidate)
            if not available:
                continue
            selected = saved.get(symbol) or saved.get(candidate)
            voicing = get_voicing(candidate, selected if selected else available[0].name)
            if voicing is None:
                continue
            diagrams[symbol] = guitar_svg(symbol, voicing, width=92, height=118)
            break
    return diagrams


def _display_beats(raw: list[dict[str, Any]], capo: int) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for beat in raw:
        item = dict(beat)
        real = str(item.get("chord", ".") or ".").strip() or "."
        item["real_chord"] = real
        item["chord"] = accord_forme_capo(real, capo)
        result.append(item)
    return result


def render_step1_riffstation(
    *,
    source: Path,
    stems: dict[str, Path],
    preview_dir: Path,
    key: str,
) -> None:
    """Render the autonomous Step 1 workflow. No lyric input exists here."""
    source = Path(source)
    preview_dir = Path(preview_dir)
    work_dir = preview_dir.parent
    audio_hash = work_dir.name

    # Step 1 owns the song cartouche and its controls. Hide the historical
    # left song panel while Analyse/Step 1 is mounted; it is restored on rerun
    # when the user switches to Édition or Player.
    st.markdown(
        """
        <style>
        section[data-testid="stSidebar"] { display:none !important; }
        [data-testid="stSidebarCollapsedControl"] { display:none !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    if "drums" not in stems:
        st.error("Step 1 impossible: stem Batterie absent.")
        return

    from ezscore.player.stem_webaudio import prepare_browser_previews

    timeline = None
    try:
        timeline = load_step1(work_dir)
    except Exception as exc:
        st.error(f"Cache Step 1 invalide: {exc}")

    if timeline is None:
        # Step 1 is a workflow, not an extra button: once the stems exist,
        # rhythm + harmony + meter are built immediately and persisted.
        with st.status("Construction Riffstation Step 1…", expanded=True) as status:
            status.write("Rythme : batterie / madmom-infer")
            status.write("Harmonie : audio original / lv-chordia")
            status.write("Time signature : accents batterie ; timestamps inchangés")
            try:
                analyze_step1(
                    source=source,
                    drums_path=Path(stems["drums"]),
                    work_dir=work_dir,
                    force=True,
                )
            except Exception as exc:
                status.update(
                    label="Analyse musicale Step 1 en erreur.",
                    state="error",
                    expanded=True,
                )
                st.error(f"{type(exc).__name__}: {exc}")
                return
            status.update(
                label="Timeline musicale Step 1 prête.",
                state="complete",
                expanded=False,
            )
        st.rerun()

    detected = str(timeline.get("detected_signature", "") or "").strip()
    stored_preferences = load_song_preferences(audio_hash) or {}
    stored_settings = dict(stored_preferences.get("settings", {}) or {})
    selected_mode = str(
        stored_settings.get(
            "signature_mode",
            st.session_state.get("setting_signature_mode", "Auto"),
        )
        or "Auto"
    ).strip()
    capo = max(
        0,
        min(
            12,
            int(
                stored_preferences.get(
                    "capo",
                    st.session_state.get("capo_live", 0),
                )
                or 0
            ),
        ),
    )
    try:
        signature = effective_signature(selected=selected_mode, detected=detected)
        beats_per_measure = timeline_beats_per_measure(signature)
    except Exception as exc:
        st.error(f"Time signature invalide: {exc}")
        return

    display_beats = _display_beats(list(timeline.get("beats", []) or []), capo)
    if not display_beats:
        st.error("Timeline Step 1 vide: aucun beat/accord à auditer.")
        return

    meter_info = dict(timeline.get("meter_detection", {}) or {})
    confidence = float(meter_info.get("confidence", 0.0) or 0.0)
    st.caption(
        f"Riffstation + STEM · time sig détectée {detected} ({confidence:.0%}) · "
        "timeline audio immuable."
    )

    preview_stems = dict(stems)
    previews = prepare_browser_previews(source, preview_stems, preview_dir)
    tracks: list[dict[str, Any]] = []

    def pack(name: str, label: str, path: Path, enabled: bool, volume: float) -> None:
        preview = previews[name]
        tracks.append(
            {
                "name": name,
                "label": label,
                "url": register_media_url(
                    preview,
                    coordinates=f"{key}:step1:{name}",
                    mimetype="audio/mpeg",
                ),
                "enabled": enabled,
                "volume": volume,
                "low": 0.0,
                "mid": 0.0,
                "high": 0.0,
            }
        )

    pack("original", "Original", source, True, 0.72)
    labels = {
        "vocals": "Voix",
        "drums": "Batterie",
        "bass": "Basse",
        "guitar": "Guitare",
        "piano": "Piano",
        "other": "Other",
    }
    defaults = {
        "vocals": (True, 0.82),
        "drums": (False, 0.72),
        "bass": (False, 0.72),
        "guitar": (False, 0.72),
        "piano": (False, 0.72),
        "other": (False, 0.72),
    }
    for name in STEM_NAMES:
        if name in stems and name in previews:
            enabled, volume = defaults.get(name, (False, 0.72))
            pack(name, labels.get(name, name), Path(stems[name]), enabled, volume)

    for name, label, enabled, volume in (
        ("lead_vocals", "Chant principal", False, 0.82),
        ("backing_vocals", "Chœurs", False, 0.72),
    ):
        if name in stems and name in previews:
            pack(name, label, Path(stems[name]), enabled, volume)

    song = next(
        (
            dict(item)
            for item in list_song_catalog(sort_by="title")
            if str(item.get("audio_hash", "")) == str(audio_hash)
        ),
        {},
    )
    song_title = str(song.get("title", "") or source.stem).strip() or source.stem
    song_artist = str(song.get("artist", "") or "").strip()
    song_editor = str(song.get("editor", "") or "").strip()
    work_mode_key = f"ez_work_mode_{audio_hash[:12]}"
    work_mode = str(st.session_state.get(work_mode_key, "Analyse") or "Analyse")

    try:
        show_diagrams = bool(load_show_diagrams(audio_hash))
    except Exception:
        show_diagrams = False
    try:
        diagrams = _build_diagrams(audio_hash, display_beats)
    except Exception:
        diagrams = {}

    last_end = max(float(item.get("end", item.get("start", 0.0)) or 0.0) for item in display_beats)
    result = _COMPONENT(
        data={
            "tracks": tracks,
            "beats": display_beats,
            "song_title": song_title,
            "song_artist": song_artist,
            "song_editor": song_editor,
            "work_mode": work_mode,
            "signature": signature,
            "signature_mode": selected_mode,
            "detected_signature": detected,
            "beats_per_measure": int(beats_per_measure),
            "capo": int(capo),
            "chord_diagrams": diagrams,
            "show_diagrams": show_diagrams,
            "duration_hint": float(last_end),
            "px_per_second": 118,
        },
        default={
            "work_mode": work_mode,
            "show_diagrams": show_diagrams,
            "signature_mode": selected_mode,
            "capo": int(capo),
        },
        key=(
            f"step1_riffstation_{audio_hash[:12]}_"
            f"{signature.replace('/', '_')}_capo{capo}_{len(display_beats)}"
        ),
        on_work_mode_change=lambda: None,
        on_signature_mode_change=lambda: None,
        on_capo_change=lambda: None,
        on_show_diagrams_change=lambda: None,
        width="stretch",
        height=730,
    )

    requested_work_mode = str(
        getattr(result, "work_mode", work_mode) or work_mode
    ).strip()
    if requested_work_mode not in {"Analyse", "Édition", "Player"}:
        requested_work_mode = work_mode
    if requested_work_mode != work_mode:
        st.session_state[work_mode_key] = requested_work_mode
        st.rerun()

    requested_signature_mode = str(
        getattr(result, "signature_mode", selected_mode) or selected_mode
    ).strip()
    requested_capo = max(
        0,
        min(12, int(getattr(result, "capo", capo) or 0)),
    )

    if (
        requested_signature_mode != selected_mode
        or requested_capo != capo
    ):
        # Persist through the existing song-preference contract. The pending
        # hook synchronizes EZScore global state before widgets are rebuilt.
        settings = current_song_settings_payload()
        settings.update(stored_settings)
        settings["signature_mode"] = requested_signature_mode
        save_song_preferences(
            audio_hash=audio_hash,
            capo=requested_capo,
            settings=settings,
        )
        st.session_state["_pending_song_preferences"] = {
            "capo": requested_capo,
            "settings": settings,
        }
        st.rerun()

    current_show = bool(getattr(result, "show_diagrams", show_diagrams))
    if current_show != show_diagrams:
        try:
            save_show_diagrams(audio_hash, current_show)
        except Exception:
            pass

    with st.expander("Diagnostic Step 1", expanded=False):
        st.write(
            {
                "detected_signature": detected,
                "effective_signature": signature,
                "signature_mode": selected_mode,
                "beats_per_measure": beats_per_measure,
                "beat_count": len(display_beats),
                "tempo": float(timeline.get("tempo", 0.0) or 0.0),
                "engines": dict(timeline.get("analysis_engines", {}) or {}),
            }
        )
        if st.button(
            "↻ Recalculer l'analyse musicale Step 1",
            key=f"step1_reanalyse_{audio_hash[:12]}",
            width="stretch",
        ):
            with st.spinner("Recalcul Step 1…"):
                analyze_step1(
                    source=source,
                    drums_path=Path(stems["drums"]),
                    work_dir=work_dir,
                    force=True,
                )
            st.rerun()
