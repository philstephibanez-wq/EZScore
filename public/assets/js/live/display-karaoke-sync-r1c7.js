/* EZScore R1.C7 — passive Display follows canonical Karaoke timeline. */
(() => {
'use strict';

const root = document.querySelector('[data-live-karaoke-display]');
const Core = window.EZScoreTimelineCoreR39;
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
let track = null;
let zone = null;
let lastState = null;
let raf = 0;

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

  host.innerHTML =
    '<div class="display-karaoke-stage" data-stage>' +
      '<div class="display-karaoke-zone" data-zone></div>' +
      '<div class="display-karaoke-track" data-track>' +
        '<div class="display-karaoke-chords" data-chords></div>' +
        '<div class="display-karaoke-lyrics" data-lyrics></div>' +
      '</div>' +
    '</div>';

  const stage = host.querySelector('[data-stage]');
  zone = host.querySelector('[data-zone]');
  track = host.querySelector('[data-track]');
  chordLane = host.querySelector('[data-chords]');
  const lyricLane = host.querySelector('[data-lyrics]');

  const focusX = () => Math.max(110, stage.clientWidth * .30);
  root._focusX = focusX;

  if (timeline.beats.length) {
    timeline.chordProjection(
      (data.chords || []).slice().sort((a,b)=>Number(a.start_ms)-Number(b.start_ms)),
      value => chordShown(value, data.capo)
    ).forEach(slot => {
      const left = timeline.xBeat(slot.seq);
      const next = slot.seq + 1 < timeline.beats.length ? timeline.xBeat(slot.seq + 1) : left + timeline.spacing;
      const cell = document.createElement('div');
      cell.className = 'display-karaoke-beat';
      cell.dataset.beatSeq = String(slot.seq);
      cell.style.left = left + 'px';
      cell.style.width = Math.max(74, next-left) + 'px';
      cell.textContent = slot.text;
      chordLane.appendChild(cell);
    });
  }

  syllables.forEach((s,i) => {
    const node = document.createElement('span');
    node.className = 'display-karaoke-syllable';
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
}

function positionMs(state) {
  let ms = Math.max(0, Number(state.position_ms || 0));
  if (state.playing && state.updated_at) {
    const updated = Date.parse(state.updated_at);
    if (Number.isFinite(updated)) {
      ms += Math.max(0, Date.now() - updated) * Number(state.playback_rate || 1);
    }
  }
  return ms;
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
  const ms = positionMs(state);
  const x = root._focusX ? root._focusX() : 220;
  zone.style.left = x + 'px';
  track.style.transform = `translate3d(${x - timeline.timeToX(ms)}px,0,0)`;

  const beatIndex = timeline.beatIndexAtMs(ms);
  chordLane?.querySelectorAll('.current').forEach(el=>el.classList.remove('current'));
  chordLane?.querySelector(`.display-karaoke-beat[data-beat-seq="${beatIndex}"]`)?.classList.add('current');

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
  const response = await fetch(url, {credentials:'same-origin', headers:{'Accept':'application/json'}});
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  buildSong(await response.json());
}

async function poll() {
  try {
    const response = await fetch(stateUrl, {credentials:'same-origin', headers:{'Accept':'application/json'}, cache:'no-store'});
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

    lastState = state;

    if (state.song_id) {
      if (Number(state.song_id) !== currentSongId) {
        await loadSong(Number(state.song_id));
      }
      render(state);
    } else {
      currentSongId = null;
      waiting.hidden = false;
      songView.hidden = true;
    }
  } catch (_) {
    // Keep last visual state; retry automatically.
  } finally {
    window.setTimeout(poll, 450);
  }
}

function frame() {
  if (lastState?.song_id && lastState?.playing) render(lastState);
  raf = requestAnimationFrame(frame);
}

poll();
raf = requestAnimationFrame(frame);
window.addEventListener('pagehide', ()=>cancelAnimationFrame(raf), {once:true});
})();
