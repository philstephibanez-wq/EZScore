/* EZScore R1.C14B — low-latency passive Display on canonical Karaoke timeline. */
(() => {
'use strict';

const root = document.querySelector('[data-live-karaoke-display]');
const Core = window.EZScoreTimelineCoreR39;
const Diagram = window.EZScoreChordDiagram;
if (!root || !Core) return;

const stateUrl = root.dataset.stateUrl || '';
const songUrlTemplate = root.dataset.songUrlTemplate || '';
if (!stateUrl || !songUrlTemplate) return;

const waiting = root.querySelector('[data-display-waiting]');
const songView = root.querySelector('[data-display-song]');
const title = root.querySelector('[data-display-song-title]');
const meta = root.querySelector('[data-display-song-meta]');
const host = root.querySelector('[data-display-prompter]');
const countdown = document.createElement('div');
countdown.className = 'display-karaoke-countdown';
countdown.hidden = true;
countdown.setAttribute('aria-live', 'polite');
root.appendChild(countdown);

let currentSongId = null;
let timeline = null;
let syllables = [];
let chordLane = null;
let syllableNodes = [];
let chordSlots = [];
let track = null;
let zone = null;
let diagramHost = null;
let lastState = null;
let raf = 0;

let anchorPositionMs = 0;
let anchorPerfMs = performance.now();
let anchorPlaying = false;
let anchorRate = 1;
let lastRevision = -1;
let lastProbeAt = 0;

const NOTE={C:0,'C#':1,Db:1,D:2,'D#':3,Eb:3,E:4,F:5,'F#':6,Gb:6,G:7,'G#':8,Ab:8,A:9,'A#':10,Bb:10,B:11};
const SH=['C','C#','D','D#','E','F','F#','G','G#','A','A#','B'];
const FL=['C','Db','D','Eb','E','F','Gb','G','Ab','A','Bb','B'];

function chordShown(value, capo) {
  let c=String(value||'.').trim().replace(/^\[([^\]]+)\]$/,'$1').replace(/♭/g,'b');
  if(!c||c==='.') return '.';
  const m=/^([A-G](?:#|b)?)(.*)$/.exec(c);
  if(!m||NOTE[m[1]]===undefined) return c;
  const names=m[1].includes('b')?FL:SH;
  return names[(NOTE[m[1]]-Number(capo||0)+120)%12]+m[2];
}

function collisionLayout() {
  if (!syllableNodes.length) return;
  syllableNodes.forEach(node => {
    node.style.removeProperty('--ez-display-font-scale');
    node.style.removeProperty('--ez-display-y-offset');
  });
  const items = syllableNodes.map(node => {
    const r = node.getBoundingClientRect();
    return {node,left:r.left,right:r.right,width:r.width,center:(r.left+r.right)/2};
  }).sort((a,b)=>a.center-b.center);

  const minGap = 6;
  let prev = null;
  for (const item of items) {
    if (!prev) { prev=item; continue; }
    const overlap=(prev.right+minGap)-item.left;
    if (overlap <= 0) { prev=item; continue; }

    const combined=Math.max(1,prev.width+item.width);
    const scale=Math.max(.72,1-Math.min(1,overlap/combined)*1.8);
    item.node.style.setProperty('--ez-display-font-scale', String(scale));
    let nr=item.node.getBoundingClientRect();

    if ((prev.right+minGap)-nr.left > 0) {
      const prevY = Number(prev.node.dataset.collisionRow || 0);
      const row = prevY === 1 ? 2 : 1;
      item.node.dataset.collisionRow = String(row);
      item.node.style.setProperty('--ez-display-y-offset', row === 1 ? '-18px' : '18px');
      nr=item.node.getBoundingClientRect();
    } else {
      item.node.dataset.collisionRow = '0';
    }
    prev={node:item.node,left:nr.left,right:nr.right,width:nr.width,center:(nr.left+nr.right)/2};
  }
}

function buildSong(data) {
  currentSongId = Number(data.id);
  title.textContent = data.title || '—';
  meta.textContent = [data.artist, data.time_signature].filter(Boolean).join(' · ');
  waiting.hidden = true;
  songView.hidden = false;

  timeline = Core.create({
    beats: data.beats || [],
    timeSignature: String(data.time_signature || '4/4'),
    spacing: 166,
    preserveSourcePosition: true,
  });
  syllables = Core.flattenSyllables(data.lyrics || []);
  syllableNodes = [];
  chordSlots = [];

  host.replaceChildren();
  const stage = document.createElement('div');
  stage.className = 'display-karaoke-stage';
  stage.dataset.stage = '';

  diagramHost = document.createElement('div');
  diagramHost.className = 'ez-chord-diagram display-current-chord-diagram';
  diagramHost.hidden = true;
  stage.appendChild(diagramHost);

  zone = document.createElement('div');
  zone.className = 'display-karaoke-zone';
  stage.appendChild(zone);

  track = document.createElement('div');
  track.className = 'display-karaoke-track';
  stage.appendChild(track);

  chordLane = document.createElement('div');
  chordLane.className = 'display-karaoke-chords';
  track.appendChild(chordLane);

  const lyricLane = document.createElement('div');
  lyricLane.className = 'display-karaoke-lyrics';
  track.appendChild(lyricLane);
  host.appendChild(stage);

  const focusX = () => Math.max(110, stage.clientWidth * .30);
  root._focusX = focusX;

  if (timeline.beats.length) {
    chordSlots = timeline.chordProjection(
      (data.chords || []).slice().sort((a,b)=>Number(a.start_ms)-Number(b.start_ms)),
      value => chordShown(value, data.capo)
    );
    chordSlots.forEach(slot => {
      const left = timeline.xBeat(slot.seq);
      const next = slot.seq + 1 < timeline.beats.length ? timeline.xBeat(slot.seq + 1) : left + timeline.spacing;
      const cell = document.createElement('div');
      cell.className = 'display-karaoke-beat';
      cell.dataset.beatSeq = String(slot.seq);
      cell.dataset.chord = String(slot.text || '.');
      cell.style.left = left + 'px';
      cell.style.width = Math.max(74, next-left) + 'px';
      cell.textContent = slot.text;
      chordLane.appendChild(cell);
    });
  }

  syllables.forEach((s,i) => {
    const node = document.createElement('span');
    node.className = 'display-karaoke-syllable';
    node.dataset.syllableIndex = String(i);
    node.dataset.collisionRow = '0';
    node.style.left = timeline.timeToX(s.nucleusMs) + 'px';
    node.textContent = s.display;
    lyricLane.appendChild(node);
    syllableNodes.push(node);
  });

  const lastMs = Math.max(
    Number(timeline.beats.at(-1)?.start_ms || 0),
    Number(syllables.at(-1)?.endMs || 0)
  );
  track.style.width = Math.max(2800, timeline.timeToX(lastMs) + timeline.spacing * 8) + 'px';
  requestAnimationFrame(collisionLayout);
  document.fonts?.ready?.then(()=>requestAnimationFrame(collisionLayout));
}

function ingestState(state, rttMs) {
  const rate = Number(state.playback_rate || 1);
  const serverNow = Number(state.server_now_ms || 0);
  const updated = Number(state.state_updated_at_ms || 0);
  let projected = Math.max(0, Number(state.position_ms || 0));

  if (state.playing && serverNow > 0 && updated > 0) {
    projected += Math.max(0, serverNow - updated) * rate;
    // Approximate one-way network transport from server response to this browser.
    projected += Math.max(0, rttMs * .5) * rate;
  }

  anchorPositionMs = projected;
  anchorPerfMs = performance.now();
  anchorPlaying = Boolean(state.playing);
  anchorRate = rate;
  lastState = state;
}

function currentPositionMs() {
  if (!anchorPlaying) return anchorPositionMs;
  return Math.max(0, anchorPositionMs + (performance.now() - anchorPerfMs) * anchorRate);
}

function renderCountdown(state) {
  const until = state?.countdown_ends_at ? Date.parse(state.countdown_ends_at) : NaN;
  if (!Number.isFinite(until)) {
    countdown.hidden = true;
    countdown.textContent = '';
    return;
  }
  const remainingMs = until - Date.now();
  if (remainingMs <= 0) {
    countdown.hidden = true;
    countdown.textContent = '';
    return;
  }
  countdown.hidden = false;
  countdown.textContent = String(Math.max(1, Math.ceil(remainingMs / 1000)));
}

function render(state) {
  renderCountdown(state);
  if (!timeline || !track || !zone) return;

  const ms = currentPositionMs();
  const x = root._focusX ? root._focusX() : 220;
  zone.style.left = x + 'px';
  track.style.transform = `translate3d(${x - timeline.timeToX(ms)}px,0,0)`;

  const beatIndex = timeline.beatIndexAtMs(ms);
  chordLane?.querySelectorAll('.current').forEach(el=>el.classList.remove('current'));
  const activeBeat = chordLane?.querySelector(`.display-karaoke-beat[data-beat-seq="${beatIndex}"]`);
  activeBeat?.classList.add('current');

  const chord = activeBeat?.dataset.chord || '.';
  if (diagramHost) {
    if (state.diagram_enabled && Diagram && chord && chord !== '.' && chord !== '-') {
      Diagram.render(diagramHost, chord);
      diagramHost.hidden = false;
    } else {
      diagramHost.hidden = true;
    }
  }

  let active=-1;
  for(let i=0;i<syllables.length;i++){
    if(syllables[i].nucleusMs <= ms) active=i;
    else break;
  }
  syllableNodes.forEach((el,i)=>{
    el.classList.toggle('past', active>=0 && i<active);
    el.classList.toggle('current', i===active);
  });
}

async function loadSong(songId) {
  const url = songUrlTemplate.replace('__SONG__', String(songId));
  const response = await fetch(url, {credentials:'same-origin', headers:{'Accept':'application/json'}, cache:'no-store'});
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  buildSong(await response.json());
}

async function poll() {
  const t0 = performance.now();
  try {
    const response = await fetch(stateUrl, {
      credentials:'same-origin',
      headers:{'Accept':'application/json'},
      cache:'no-store'
    });
    const rtt = performance.now() - t0;

    if (response.status === 403 || response.status === 404) {
      window.location.assign('/live/display-home');
      return;
    }
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const state = await response.json();

    if (state.active === false) {
      lastState = null;
      try { document.querySelectorAll('audio,video').forEach(media => media.pause()); } catch (_) {}
      window.location.assign('/live/display-home');
      return;
    }

    if (state.song_id) {
      if (Number(state.song_id) !== currentSongId) {
        await loadSong(Number(state.song_id));
      }
      ingestState(state, rtt);
      render(state);
    } else {
      currentSongId = null;
      lastState = state;
      anchorPlaying = false;
      waiting.hidden = false;
      songView.hidden = true;
    }

    if (Number(state.revision) !== lastRevision || performance.now() - lastProbeAt > 3000) {
      lastRevision = Number(state.revision);
      lastProbeAt = performance.now();
      console.debug('[EZSYNC display]', {
        revision: state.revision,
        rtt_ms: Math.round(rtt),
        playing: state.playing,
        stored_ms: state.position_ms,
        projected_ms: Math.round(currentPositionMs()),
        state_age_ms: Number(state.server_now_ms || 0) - Number(state.state_updated_at_ms || 0),
        diagram: Boolean(state.diagram_enabled)
      });
    }
  } catch (error) {
    console.warn('[EZSYNC display] poll failed', error);
  } finally {
    window.setTimeout(poll, 120);
  }
}

function frame() {
  if (lastState?.song_id) render(lastState);
  raf = requestAnimationFrame(frame);
}

poll();
raf = requestAnimationFrame(frame);
window.addEventListener('resize', ()=>requestAnimationFrame(collisionLayout));
window.addEventListener('pagehide', ()=>cancelAnimationFrame(raf), {once:true});
})();
