from __future__ import annotations

"""R12c karaoke presentation layer.

This module deliberately reuses the validated R10 audio/STEM/EQ implementation
and only replaces the conductor presentation/control layer.
"""

from typing import Any
from pathlib import Path
import json

import streamlit as st

from ezscore.guitar import (
    choices as guitar_choices,
    get_voicing,
    load_show_diagrams,
    load_voicings,
    svg as guitar_svg,
)
from ezscore.player import karaoke_stem_webaudio as _base
from ezscore.player.media_metadata import duration_seconds


_AUDIO_HASH_BY_STORAGE_KEY: dict[str, str] = {}
_PREVIEW_DIR_BY_STORAGE_KEY: dict[str, Path] = {}
_MEDIA_DURATION_BY_STORAGE_KEY: dict[str, float] = {}


def _replace_once(source: str, old: str, new: str, label: str) -> str:
    if old not in source:
        raise RuntimeError(f"EZScore R11 patch point missing: {label}")
    return source.replace(old, new, 1)


_HTML = _base._HTML

_HTML = _replace_once(
    _HTML,
    """  <div class="transport">
    <button class="play" type="button">▶ Lecture</button>
    <button class="pause" type="button">⏸ Pause</button>
    <button class="stop" type="button">⏹ Stop</button>
    <span class="time">0:00 / 0:00</span>
  </div>
  <input class="seek" type="range" min="0" max="1" step="0.001" value="0">

""",
    "",
    "top transport",
)

_HTML = _replace_once(
    _HTML,
    """  <div class="meter-box">
    <strong>Mesure</strong>
    <input class="meter-num" type="number" min="1" step="1" value="4">
    <span>/</span>
    <input class="meter-den" type="number" min="1" step="1" value="4">
    <label>Groupement <input class="meter-group" type="text" placeholder="auto"></label>
    <span class="meter-state"></span>
  </div>

  <div class="karaoke">
""",
    """  <div class="meter-box">
    <label><strong>Mesure</strong>
      <select class="meter-signature">
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

    <label><strong>Vitesse</strong>
      <select class="playback-rate">
        <option value="0.75">0.75×</option>
        <option value="0.85">0.85×</option>
        <option value="1.00" selected>1.00×</option>
        <option value="1.10">1.10×</option>
        <option value="1.25">1.25×</option>
      </select>
    </label>

    <label class="diagram-toggle">
      <input class="show-diagrams" type="checkbox">
      Diagrammes guitare
    </label>

    <span class="meter-state"></span>
  </div>

  <div class="transport transport-karaoke">
    <button class="play" type="button">▶ Lecture</button>
    <button class="pause" type="button">⏸ Pause</button>
    <button class="stop" type="button">⏹ Stop</button>
    <span class="time">0:00 / 0:00</span>
  </div>
  <input class="seek" type="range" min="0" max="1" step="0.001" value="0">

  <div class="karaoke">
""",
    "meter / transport",
)

_HTML = _replace_once(
    _HTML,
    """    <div class="timeline-row chord-row">
      <div class="timeline-label">Accords</div>
""",
    """    <div class="current-diagram-row">
      <div class="timeline-label">Diagramme</div>
      <div class="current-diagram"></div>
    </div>

    <div class="current-chord-row">
      <div class="timeline-label">Accord</div>
      <div class="current-chord">—</div>
    </div>

    <div class="timeline-row chord-row">
      <div class="timeline-label">Accords</div>
""",
    "current chord rows",
)


_CSS = _base._CSS + r"""

/* R12c presentation controls */
.meter-box select {
  background:#1f232b;
  color:#f4f4f4;
  border:1px solid color-mix(in srgb, var(--st-text-color) 25%, transparent);
  border-radius:5px;
  padding:4px 7px;
  color-scheme:dark;
}
.meter-box select option {
  background:#1f232b;
  color:#f4f4f4;
}
.meter-box select:focus {
  outline:2px solid color-mix(in srgb, #4da3ff 70%, transparent);
  outline-offset:1px;
}
.meter-box label {
  display:flex;
  align-items:center;
  gap:6px;
}
.diagram-toggle {
  margin-left:4px;
  white-space:nowrap;
}
.transport-karaoke {
  margin-top:4px;
}
.playhead,
.future-hint {
  display:none !important;
}
.current-diagram-row,
.current-chord-row {
  display:grid;
  grid-template-columns:64px 1fr;
  align-items:center;
  position:relative;
}
.current-diagram-row {
  display:none;
  min-height:126px;
}
.current-diagram {
  position:absolute;
  left:38%;
  top:2px;
  transform:translateX(-50%);
  min-height:118px;
  width:112px;
  display:flex;
  align-items:center;
  justify-content:center;
  z-index:7;
}
.current-diagram svg {
  width:92px;
  height:auto;
  max-height:118px;
  display:block;
}
.diagram-unavailable {
  width:106px;
  padding:7px 5px;
  border:1px dashed color-mix(in srgb, var(--st-text-color) 30%, transparent);
  border-radius:7px;
  font-size:10px;
  opacity:.62;
  text-align:center;
}
.current-chord-row {
  min-height:54px;
}
.current-chord {
  position:absolute;
  left:38%;
  top:7px;
  transform:translateX(-50%);
  min-width:140px;
  text-align:center;
  font-family:Consolas,"Courier New",monospace;
  font-size:32px;
  font-weight:950;
  line-height:1;
  color:#f4f4f4;
}
"""


_JS = _base._JS

_JS = _replace_once(
    _JS,
    """  const meterDefault = data.meter_default || {signature:"4/4", grouping:""};
""",
    """  const meterDefault = data.meter_default || {signature:"4/4", grouping:""};
  const chordDiagrams = data.chord_diagrams || {};
""",
    "data chord diagrams",
)

_JS = _replace_once(
    _JS,
    """  const numInput = root.querySelector(".meter-num");
  const denInput = root.querySelector(".meter-den");
  const groupingInput = root.querySelector(".meter-group");
  const meterState = root.querySelector(".meter-state");
""",
    """  const meterSelect = root.querySelector(".meter-signature");
  const rateSelect = root.querySelector(".playback-rate");
  const showDiagramsInput = root.querySelector(".show-diagrams");
  const meterState = root.querySelector(".meter-state");
  const currentDiagramRow = root.querySelector(".current-diagram-row");
  const currentDiagramNode = root.querySelector(".current-diagram");
  const currentChordNode = root.querySelector(".current-chord");
""",
    "meter selectors",
)

_JS = _replace_once(
    _JS,
    """  let duration = 0;
  let raf = null;
""",
    """  let duration = 0;
  let raf = null;
  let playbackRate = 1.0;
  const visualDelay = 0.35;
  let showDiagrams = Boolean(data.show_diagrams_default);
""",
    "player state",
)

_JS = _replace_once(
    _JS,
    """  function currentTime() {
    if (!playing || !context) return position;
    return Math.max(
      0,
      Math.min(duration, position + (context.currentTime - startedAtContextTime))
    );
  }
""",
    """  function currentTime() {
    if (!playing || !context) return position;
    return Math.max(
      0,
      Math.min(
        duration,
        position + (context.currentTime - startedAtContextTime) * playbackRate
      )
    );
  }
""",
    "rate-aware clock",
)

meter_start = _JS.index("  // -------- Meter / presentation only --------")
lyrics_start = _JS.index("  // -------- Continuous lyrics geometry --------")
_JS = (
    _JS[:meter_start]
    + r"""  // -------- Meter / presentation only --------
  const allowedMeters = new Set([
    "2/4","3/4","4/4","5/4","6/8","7/8","9/8","12/8"
  ]);
  const defaultSignature = allowedMeters.has(String(meterDefault.signature || ""))
    ? String(meterDefault.signature)
    : "4/4";
  meterSelect.value = defaultSignature;
  rateSelect.value = "1.00";
  showDiagramsInput.checked = showDiagrams;

  const storageKey = "ezscore-karaoke-meter:" + String(data.storage_key || "default");
  try {
    const saved = JSON.parse(localStorage.getItem(storageKey) || "null");
    if (saved && allowedMeters.has(String(saved.signature || ""))) {
      meterSelect.value = String(saved.signature);
    }
  } catch (_) {}

  function defaultGrouping(n,d) {
    if (d >= 8 && n > 3 && n % 3 === 0) return Array(n/3).fill(3);
    if (d >= 8 && n === 5) return [2,3];
    if (d >= 8 && n === 7) return [2,2,3];
    if (d === 4 && n === 5) return [3,2];
    if (d === 4 && n === 7) return [4,3];
    return Array(n).fill(1);
  }

  function meter() {
    const parts = String(meterSelect.value || "4/4").split("/");
    const n = Math.max(1, Math.floor(Number(parts[0] || 4)));
    const d = Math.max(1, Math.floor(Number(parts[1] || 4)));
    const groups = defaultGrouping(n,d);
    const grouped = d >= 8 && groups.some(x => x > 1);
    return {
      n,d,groups,grouped,
      beatsPerMeasure: grouped ? groups.length : n
    };
  }

  let renderedMeterKey = "";
  function persistMeter() {
    const m = meter();
    try {
      localStorage.setItem(storageKey, JSON.stringify({
        signature:m.n + "/" + m.d
      }));
    } catch (_) {}
    meterState.textContent = m.grouped
      ? m.n + "/" + m.d + " · " + m.groups.join("+")
      : m.n + "/" + m.d;
    renderedMeterKey = "";
  }

"""
    + _JS[lyrics_start:]
)

lyrics_start = _JS.index("  // -------- Continuous lyrics geometry --------")
chords_start = _JS.index("  // -------- Chords / measure presentation --------")
_JS = (
    _JS[:lyrics_start]
    + r"""  // -------- One meter-aware geometry for ALL scrolling lanes --------
  /*
  Timestamps never change.
  The selected time signature only changes the visual measure grouping.
  One visual measure keeps a fixed width, so changing 4/4 -> 2/4 -> 9/8
  reflows chords AND lyrics together while preserving absolute time.
  */
  const measureSlotWidth = 318;

  function beatIndexAndProgress(time) {
    const t = Number(time || 0);
    if (!beats.length) return {index:0,progress:0};

    if (t <= Number(beats[0].start || 0)) {
      return {index:0,progress:0};
    }

    let low=0, high=beats.length-1, index=0;
    while (low<=high) {
      const mid=(low+high)>>1;
      if (Number(beats[mid].start || 0) <= t) {
        index=mid;
        low=mid+1;
      } else {
        high=mid-1;
      }
    }

    const beat=beats[index];
    const start=Number(beat.start || 0);
    const end=Math.max(start+.02,Number(beat.end || start+.5));
    const progress=Math.max(0,Math.min(1,(t-start)/(end-start)));
    return {index,progress};
  }

  function timelineVisualXForTime(time) {
    if (!beats.length) return Math.max(0,Number(time || 0))*74;

    const mp=meter();
    const bp=beatIndexAndProgress(time);
    const measureIndex=Math.floor(bp.index/mp.beatsPerMeasure);
    const localBeat=bp.index%mp.beatsPerMeasure;
    const measureProgress=(localBeat+bp.progress)/mp.beatsPerMeasure;

    return measureIndex*measureSlotWidth + measureProgress*measureSlotWidth;
  }

  function sharedTimelineWidth() {
    const mp=meter();
    const count=Math.max(1,Math.ceil(beats.length/mp.beatsPerMeasure));
    return count*measureSlotWidth+320;
  }

  function normalizedWords(input) {
    return (Array.isArray(input) ? input : [])
      .map(w => ({
        text:String(w.text || "").trim(),
        start:Number(w.start || 0),
        end:Number(w.end || w.start || 0),
      }))
      .filter(w => w.text && Number.isFinite(w.start) && Number.isFinite(w.end))
      .sort((a,b)=>a.start-b.start || a.end-b.end);
  }

  const leadWords = normalizedWords(leadInput);
  const backingWords = normalizedWords(backingInput);

  let leadNodes=[];
  let backingNodes=[];

  function isContractionSuffix(text) {
    return /^[\'’]/.test(String(text || "").trim());
  }

  function createLane(track, sourceWords) {
    track.innerHTML="";
    track.style.width=sharedTimelineWidth()+"px";

    const nodes=[];
    sourceWords.forEach((w,index) => {
      const span=document.createElement("span");
      span.className="lyric-token";
      span.textContent=w.text;

      let left=timelineVisualXForTime(w.start);

      // Typographic compaction only: Whisper may split contractions such as
      // "J" + "'avais" or "l" + "'amour" into separate timestamped tokens.
      // Keep both timestamps intact but visually glue the apostrophe suffix
      // to the previous token so lyrics remain readable.
      if (index > 0 && isContractionSuffix(w.text)) {
        const previous=nodes[index-1];
        if (previous) {
          const previousLeft=Number.parseFloat(previous.style.left || "0");
          left=previousLeft+previous.offsetWidth+1;
        }
      }

      span.style.left=left+"px";
      track.appendChild(span);
      nodes.push(span);
    });

    return nodes;
  }

  function rebuildLyricGeometry() {
    leadNodes=createLane(leadTrack,leadWords);
    backingNodes=createLane(backingTrack,backingWords);
    backingRow.style.display = backingWords.length ? "grid" : "none";
  }

  function activeWordIndex(sourceWords,time) {
    if (!sourceWords.length) return -1;
    let low=0,high=sourceWords.length-1,answer=-1;
    while (low<=high) {
      const mid=(low+high)>>1;
      if (sourceWords[mid].start<=time) {
        answer=mid;
        low=mid+1;
      } else {
        high=mid-1;
      }
    }
    if (answer<0) return -1;
    const w=sourceWords[answer];
    return time<=Math.max(w.end,w.start+.06) ? answer : -1;
  }

  function translateLyricTimeline(track,viewport,time) {
    if (!track || !viewport) return;
    const anchor=viewport.clientWidth*anchorRatio;
    track.style.transform=
      "translate3d(" +
      (anchor-timelineVisualXForTime(time)).toFixed(2) +
      "px,0,0)";
  }

  rebuildLyricGeometry();

"""
    + _JS[chords_start:]
)

chords_start = _JS.index("  // -------- Chords / measure presentation --------")
persist_call = _JS.index("  persistMeter();", chords_start)
_JS = (
    _JS[:chords_start]
    + r"""  // -------- Chords / measure presentation --------
  function measureNotation(measureIndex,m) {
    const startBeat=measureIndex*m.beatsPerMeasure;
    if (startBeat>=beats.length) return null;
    const beatSlice=beats.slice(startBeat,startBeat+m.beatsPerMeasure);
    if (!beatSlice.length) return null;

    let notation="";
    let prevChord=null;
    beatSlice.forEach((beat,localIndex) => {
      const chord=String(beat.chord || ".").trim() || ".";
      let token;
      if (chord === ".") token=".";
      else if (localIndex===0) token=chord;
      else if (chord===prevChord) token="-";
      else token=chord;

      if (m.grouped) {
        const count=Math.max(1,Number(m.groups[localIndex] || 1));
        if (token === ".") notation += ".".repeat(count);
        else if (token === "-") notation += "-".repeat(count);
        else notation += token + "-".repeat(Math.max(0,count-1));
      } else {
        notation += token;
      }
      prevChord=chord;
    });

    return {
      notation,
      start:Number(beatSlice[0].start || 0),
      end:Number(
        beatSlice[beatSlice.length-1].end ||
        beatSlice[beatSlice.length-1].start ||
        0
      ),
    };
  }

  let chordMeasures=[];
  let chordNodes=[];

  function rebuildChordTimeline() {
    const m=meter();
    const key=m.n+"/"+m.d+"|"+m.groups.join("+");
    if (key===renderedMeterKey && chordNodes.length) return;

    renderedMeterKey=key;
    chordTrack.innerHTML="";
    chordMeasures=[];
    chordNodes=[];

    const count=Math.ceil(beats.length/m.beatsPerMeasure);
    for (let i=0;i<count;i++) {
      const item=measureNotation(i,m);
      if (!item) continue;

      item.visualX=i*measureSlotWidth;
      item.visualWidth=measureSlotWidth;
      chordMeasures.push(item);

      const marker=document.createElement("span");
      marker.className="chord-marker";
      marker.textContent=item.notation;
      marker.style.left=item.visualX+"px";
      marker.style.width=Math.max(36,item.visualWidth-12)+"px";
      marker.style.boxSizing="border-box";
      marker.style.overflow="hidden";
      chordTrack.appendChild(marker);
      chordNodes.push(marker);
    }

    chordTrack.style.width=sharedTimelineWidth()+"px";
  }

  function chordVisualXForTime(time) {
    return timelineVisualXForTime(time);
  }

  function currentChordAtTime(time) {
    if (!beats.length) return ".";
    const t=Number(time || 0);
    if (t < Number(beats[0].start || 0)) return ".";

    const bp=beatIndexAndProgress(t);
    const index=Math.max(0,Math.min(beats.length-1,bp.index));
    return String(beats[index].chord || ".").trim() || ".";
  }

  function renderCurrentChord(time) {
    const chord=currentChordAtTime(time);
    currentChordNode.textContent=chord==="." ? "—" : chord;

    if (!showDiagrams) {
      currentDiagramRow.style.display="none";
      currentDiagramNode.innerHTML="";
      return;
    }

    currentDiagramRow.style.display="grid";
    const svg=chordDiagrams[chord] || "";
    if (svg) {
      currentDiagramNode.innerHTML=svg;
    } else {
      currentDiagramNode.innerHTML=
        '<div class="diagram-unavailable">Diagramme indisponible<br>' +
        String(chord==="." ? "—" : chord) +
        '</div>';
    }
  }

  function renderConductor(time) {
    rebuildChordTimeline();

    const chordAnchor=chordViewport.clientWidth*anchorRatio;
    chordTrack.style.transform =
      "translate3d(" +
      (chordAnchor-chordVisualXForTime(time)).toFixed(2) +
      "px,0,0)";

    translateLyricTimeline(leadTrack,leadViewport,time);
    if (backingWords.length) {
      translateLyricTimeline(backingTrack,backingViewport,time);
    }

    const currentLead=activeWordIndex(leadWords,time);
    leadNodes.forEach((node,i) => {
      node.classList.toggle("past", time>leadWords[i].end);
      node.classList.toggle("current", i===currentLead);
    });

    const currentBacking=activeWordIndex(backingWords,time);
    backingNodes.forEach((node,i) => {
      node.classList.toggle("past", time>backingWords[i].end);
      node.classList.toggle("current", i===currentBacking);
    });

    chordNodes.forEach((node,i) => {
      const item=chordMeasures[i];
      node.classList.toggle(
        "active",
        Boolean(item && time>=item.start && time<item.end)
      );
    });

    renderCurrentChord(time);
  }

  meterSelect.addEventListener("change",() => {
    persistMeter();
    rebuildLyricGeometry();
    rebuildChordTimeline();
    renderConductor(Math.max(0,currentTime()-visualDelay));
  });

  rateSelect.addEventListener("change",() => {
    playbackRate=Math.max(
      .75,
      Math.min(1.25,Number(rateSelect.value || 1))
    );
    setPlaybackRateOnMedia();
    renderConductor(Math.max(0,currentTime()-visualDelay));
  });

  showDiagramsInput.addEventListener("change",() => {
    showDiagrams=Boolean(showDiagramsInput.checked);
    renderCurrentChord(Math.max(0,currentTime()-visualDelay));
  });

"""
    + _JS[persist_call:]
)


# Visual follow delay only: audio clock remains authoritative.
_JS = _JS.replace(
    "renderConductor(position);",
    "renderConductor(Math.max(0,position-visualDelay));",
)
_JS = _JS.replace(
    "renderConductor(t);",
    "renderConductor(Math.max(0,t-visualDelay));",
)
_JS = _JS.replace(
    "renderConductor(Math.max(0,0-visualDelay));",
    "renderConductor(0);",
)


# Replace only the audio transport engine. Media elements provide native
# pitch-preserving playbackRate in Chromium/Edge/Firefox while WebAudio still
# provides the validated per-track EQ and gain graph.
_audio_start = _JS.index(
    "  // -------- WebAudio engine / proven 3-band crossover --------"
)
_audio_end = _JS.index("  tick();", _audio_start) + len("  tick();")

_MEDIA_ENGINE = r"""
  // -------- WebAudio EQ + HTMLMediaElement pitch-preserved transport --------
  let mediaElements = [];
  let mediaSources = [];
  let clockMedia = null;
  let lastDriftCheck = 0;

  function setPitchPreservation(media) {
    try { media.preservesPitch = true; } catch (_) {}
    try { media.webkitPreservesPitch = true; } catch (_) {}
    try { media.mozPreservesPitch = true; } catch (_) {}
  }

  function setPlaybackRateOnMedia() {
    mediaElements.forEach(media => {
      setPitchPreservation(media);
      try { media.playbackRate = playbackRate; } catch (_) {}
      try { media.defaultPlaybackRate = playbackRate; } catch (_) {}
    });
  }

  function waitMediaReady(media) {
    if (media.readyState >= 1 && Number.isFinite(media.duration)) {
      return Promise.resolve();
    }
    return new Promise((resolve,reject) => {
      const done=() => { cleanup(); resolve(); };
      const fail=() => { cleanup(); reject(new Error("Média audio indisponible")); };
      const cleanup=() => {
        media.removeEventListener("loadedmetadata",done);
        media.removeEventListener("canplay",done);
        media.removeEventListener("error",fail);
      };
      media.addEventListener("loadedmetadata",done,{once:true});
      media.addEventListener("canplay",done,{once:true});
      media.addEventListener("error",fail,{once:true});
      media.load();
    });
  }

  async function ensureReady() {
    if (ready) {
      if (context && context.state==="suspended") await context.resume();
      return;
    }

    playButton.disabled=true;
    playButton.textContent="Chargement audio…";

    context=new (window.AudioContext || window.webkitAudioContext)({
      latencyHint:"interactive"
    });
    masterGain=context.createGain();
    masterGain.gain.value=masterState;
    masterGain.connect(context.destination);

    trackNodes=[];
    mediaElements=[];
    mediaSources=[];

    for (let i=0;i<defs.length;i++) {
      const media=new Audio();
      media.preload="auto";
      media.src=String(defs[i].url || "");
      setPitchPreservation(media);
      await waitMediaReady(media);

      const sourceNode=context.createMediaElementSource(media);

      const lowEQ=context.createBiquadFilter();
      lowEQ.type="lowshelf";
      lowEQ.frequency.value=200;
      lowEQ.gain.value=0;

      const midEQ=context.createBiquadFilter();
      midEQ.type="peaking";
      midEQ.frequency.value=1000;
      midEQ.Q.value=.9;
      midEQ.gain.value=0;

      const highEQ=context.createBiquadFilter();
      highEQ.type="highshelf";
      highEQ.frequency.value=5000;
      highEQ.gain.value=0;

      const trackGain=context.createGain();

      sourceNode.connect(lowEQ);
      lowEQ.connect(midEQ);
      midEQ.connect(highEQ);
      highEQ.connect(trackGain);
      trackGain.connect(masterGain);

      mediaElements.push(media);
      mediaSources.push(sourceNode);
      trackNodes.push({lowEQ,midEQ,highEQ,trackGain});

      if (i===0) duration=Number(media.duration || 0);
    }

    clockMedia=mediaElements[0] || null;
    seek.max=String(Math.max(.001,duration));
    setPlaybackRateOnMedia();

    ready=true;
    trackState.forEach((_,i)=>applyTrackState(i,false));
    applyMasterState(false);

    playButton.disabled=false;
    playButton.textContent="▶ Lecture";
  }

  function currentTime() {
    if (clockMedia && Number.isFinite(clockMedia.currentTime)) {
      return Math.max(0,Math.min(duration,Number(clockMedia.currentTime)||0));
    }
    return Math.max(0,Math.min(duration,Number(position)||0));
  }

  function stopSources() {
    mediaElements.forEach(media => {
      try { media.pause(); } catch (_) {}
    });
  }

  function syncMediaTo(time) {
    const t=Math.max(0,Math.min(duration,Number(time)||0));
    mediaElements.forEach(media => {
      try {
        if (Math.abs((Number(media.currentTime)||0)-t) > .025) {
          media.currentTime=t;
        }
      } catch (_) {}
    });
    position=t;
  }

  async function startSources(offset) {
    const t=Math.max(0,Math.min(duration,Number(offset)||0));
    syncMediaTo(t);
    setPlaybackRateOnMedia();

    const promises=mediaElements.map(media => {
      try { return media.play(); }
      catch (_) { return Promise.resolve(); }
    });
    await Promise.all(promises);

    position=t;
    playing=true;
  }

  async function playAll() {
    await ensureReady();
    if (context.state==="suspended") await context.resume();
    if (playing) return;
    if (position>=duration-.01) position=0;
    await startSources(position);
  }

  function pauseAll() {
    if (!playing) return;
    position=currentTime();
    playing=false;
    stopSources();
  }

  function stopAll() {
    playing=false;
    stopSources();
    position=0;
    syncMediaTo(0);
    seek.value="0";
    renderConductor(0);
    timeLabel.textContent="0:00 / "+fmt(duration);
  }

  function seekTo(value) {
    position=Math.max(0,Math.min(duration,Number(value)||0));
    syncMediaTo(position);
    renderConductor(Math.max(0,position-visualDelay));
  }

  playButton.addEventListener("click",()=>playAll().catch(e => {
    playButton.disabled=false;
    playButton.textContent="▶ Lecture";
    console.error(e);
  }));
  pauseButton.addEventListener("click",pauseAll);
  stopButton.addEventListener("click",stopAll);
  seek.addEventListener("input",()=>seekTo(Number(seek.value || 0)));

  function correctStemDrift(t) {
    if (!playing || !clockMedia) return;
    const now=performance.now();
    if (now-lastDriftCheck < 500) return;
    lastDriftCheck=now;

    mediaElements.forEach((media,index) => {
      if (index===0) return;
      const drift=(Number(media.currentTime)||0)-t;
      if (Math.abs(drift) > .080) {
        try { media.currentTime=t; } catch (_) {}
      }
    });
  }

  function tick() {
    if (disposed) return;
    const t=currentTime();
    position=t;
    correctStemDrift(t);
    seek.value=String(t);
    timeLabel.textContent=fmt(t)+" / "+fmt(duration);
    renderConductor(Math.max(0,t-visualDelay));

    if (playing && t>=duration-.01) stopAll();
    raf=requestAnimationFrame(tick);
  }

  tick();
"""

_JS = _JS[:_audio_start] + _MEDIA_ENGINE + _JS[_audio_end:]


# Seeker fix: initialize duration from original preview metadata at mount time.
# This starts neither playback nor an AudioContext.
_JS = _replace_once(
    _JS,
    """  let mediaElements = [];
  let mediaSources = [];
  let clockMedia = null;
  let lastDriftCheck = 0;
""",
    """  let mediaElements = [];
  let mediaSources = [];
  let clockMedia = null;
  let lastDriftCheck = 0;
  let metadataMedia = null;
""",
    "seek metadata state",
)

_JS = _replace_once(
    _JS,
    """  async function ensureReady() {
""",
    r"""  function applySeekDuration(value) {
    const parsed = Number(value || 0);
    if (!Number.isFinite(parsed) || parsed <= 0) return false;

    duration = parsed;
    seek.max = String(Math.max(.001, duration));
    seek.value = String(Math.max(0, Math.min(duration, position)));
    timeLabel.textContent = fmt(position) + " / " + fmt(duration);
    return true;
  }

  function primeSeekMetadata() {
    // Primary source: duration measured server-side with ffprobe.
    // This avoids browser/network metadata differences (notably Edge online).
    const serverDuration = Number(data.media_duration || 0);
    applySeekDuration(serverDuration);

    // Browser metadata remains a secondary refinement/fallback.
    const original = defs.find(item => item.name === "original") || defs[0];
    const url = String(original?.url || "");
    if (!url) return;

    metadataMedia = new Audio();
    metadataMedia.preload = "metadata";
    metadataMedia.src = url;

    const accept = () => {
      applySeekDuration(Number(metadataMedia?.duration || 0));
    };

    metadataMedia.addEventListener("loadedmetadata", accept, {once:true});
    metadataMedia.addEventListener("durationchange", accept);
    try { metadataMedia.load(); } catch (_) {}
  }

  primeSeekMetadata();

  async function ensureReady() {
""",
    "seek metadata preload",
)


_COMPONENT_R12C = st.components.v2.component(
    "ezscore_karaoke_stem_player_r12c",
    html=_HTML,
    css=_CSS,
    js=_JS,
    isolate_styles=True,
)


def _build_chord_diagrams(
    audio_hash: str,
    beats: list[dict[str, Any]],
) -> dict[str, str]:
    saved_voicings = load_voicings(audio_hash)
    diagrams: dict[str, str] = {}

    for beat in beats:
        symbol = str(beat.get("chord", "") or "").strip()
        if not symbol or symbol == "." or symbol in diagrams:
            continue

        candidates = [symbol]
        if "/" in symbol:
            base_symbol = symbol.split("/", 1)[0].strip()
            if base_symbol and base_symbol not in candidates:
                candidates.append(base_symbol)

        selected = None
        selected_symbol = None

        for candidate in candidates:
            available = guitar_choices(candidate)
            if not available:
                continue

            saved_name = (
                saved_voicings.get(symbol)
                or saved_voicings.get(candidate)
            )
            selected = get_voicing(
                candidate,
                saved_name if saved_name else available[0].name,
            )
            if selected is not None:
                selected_symbol = candidate
                break

        if selected is None or selected_symbol is None:
            continue

        # Keep the actual current chord as the diagram title, while using the
        # deterministic base voicing for slash chords when needed.
        diagrams[symbol] = guitar_svg(
            symbol,
            selected,
            width=92,
            height=118,
        )

    return diagrams


def _component_with_r12c_data(*, data: dict[str, Any], **kwargs):
    payload = dict(data or {})
    storage_key = str(payload.get("storage_key", "") or "")
    audio_hash = _AUDIO_HASH_BY_STORAGE_KEY.get(storage_key, "")
    payload["media_duration"] = float(
        _MEDIA_DURATION_BY_STORAGE_KEY.get(storage_key, 0.0) or 0.0
    )

    # Non-regression guard: Chœurs / vocalises are persisted independently.
    # If the base render yields an empty lane, reconstruct it from the cached
    # vocal-stem Whisper pass without reanalysis.
    if not list(payload.get("backing_words", []) or []):
        preview_dir = _PREVIEW_DIR_BY_STORAGE_KEY.get(storage_key)
        lead_words = list(payload.get("lead_words", []) or [])
        if preview_dir is not None and lead_words:
            cache_path = Path(preview_dir).parent / "whisper_vocals_small.json"
            if cache_path.is_file():
                try:
                    vocal_payload = json.loads(
                        cache_path.read_text(encoding="utf-8")
                    )
                    merged = _base._merge_vocal_gap_words(
                        lead_words,
                        list(vocal_payload.get("words", []) or []),
                    )
                    payload["backing_words"] = _base._supplement_only_words(
                        lead_words,
                        merged,
                    )
                except Exception:
                    pass

    if audio_hash:
        beats = list(payload.get("beats", []) or [])
        try:
            payload["chord_diagrams"] = _build_chord_diagrams(
                audio_hash,
                beats,
            )
        except Exception:
            payload["chord_diagrams"] = {}

        try:
            payload["show_diagrams_default"] = bool(
                load_show_diagrams(audio_hash)
            )
        except Exception:
            payload["show_diagrams_default"] = False
    else:
        payload["chord_diagrams"] = {}
        payload["show_diagrams_default"] = False

    return _COMPONENT_R12C(data=payload, **kwargs)


_base._COMPONENT = _component_with_r12c_data


def render_player(
    source,
    stems,
    *,
    preview_dir,
    key: str,
    words=None,
) -> None:
    storage_key = str(key)
    _AUDIO_HASH_BY_STORAGE_KEY[storage_key] = preview_dir.parent.name
    _PREVIEW_DIR_BY_STORAGE_KEY[storage_key] = Path(preview_dir)
    _MEDIA_DURATION_BY_STORAGE_KEY[storage_key] = duration_seconds(Path(source))
    return _base.render_player(
        source,
        stems,
        preview_dir=preview_dir,
        key=key,
        words=words,
    )
