/* EZScore R1.C5 — read-only Karaoke renderer on canonical timeline. */
(() => {
'use strict';

const root = document.querySelector('[data-karaoke]');
const mixer = document.querySelector('[data-stem-mixer]');
const Core = window.EZScoreTimelineCoreR39;
if (!root || !Core) return;

const parse = value => {
  try { return JSON.parse(value || '[]'); } catch (_) { return []; }
};

const beats0 = parse(root.dataset.beats);
const chords0 = parse(root.dataset.chords);
const words = parse(root.dataset.lyrics);
const capo = Number(root.dataset.capo || 0);
const timeline = Core.create({
  beats: beats0,
  timeSignature: String(root.dataset.timeSignature || '4/4'),
  spacing: 166,
  preserveSourcePosition: true,
});
if (!timeline.beats.length) return;

const NOTE={C:0,'C#':1,Db:1,D:2,'D#':3,Eb:3,E:4,F:5,'F#':6,Gb:6,G:7,'G#':8,Ab:8,A:9,'A#':10,Bb:10,B:11};
const SH=['C','C#','D','D#','E','F','F#','G','G#','A','A#','B'];
const FL=['C','Db','D','Eb','E','F','Gb','G','Ab','A','Bb','B'];
const shown = value => {
  let c=String(value||'.').trim().replace(/^\[([^\]]+)\]$/,'$1').replace(/♭/g,'b');
  if(!c||c==='.') return '.';
  const m=/^([A-G](?:#|b)?)(.*)$/.exec(c);
  if(!m||NOTE[m[1]]===undefined) return c;
  const names=m[1].includes('b')?FL:SH;
  return names[(NOTE[m[1]]-capo+120)%12]+m[2];
};

const host = root.querySelector('[data-lyrics-measures]');
if (!host) return;

host.innerHTML =
  '<div class="lyrics-ribbon-stage r39-shared-timeline karaoke-ribbon-stage" data-stage>' +
    '<div class="lyrics-reading-zone" data-reading-zone></div>' +
    '<div class="lyrics-ribbon-track" data-track>' +
      '<div class="lyrics-ribbon-chords" data-chords-lane></div>' +
      '<div class="lyrics-ribbon-syllables" data-syllables-lane></div>' +
    '</div>' +
  '</div>';

const stage = host.querySelector('[data-stage]');
const zone = host.querySelector('[data-reading-zone]');
const track = host.querySelector('[data-track]');
const chordLane = host.querySelector('[data-chords-lane]');
const syllableLane = host.querySelector('[data-syllables-lane]');
const syllables = Core.flattenSyllables(words);
const syllableNodes = [];

const focusX = () => Math.max(105, stage.clientWidth * .30);

timeline.chordProjection(
  chords0.slice().sort((a,b)=>Number(a.start_ms)-Number(b.start_ms)),
  shown
).forEach(slot => {
  const left = timeline.xBeat(slot.seq);
  const next = slot.seq + 1 < timeline.beats.length ? timeline.xBeat(slot.seq + 1) : left + timeline.spacing;
  const cell = document.createElement('div');
  cell.className = 'lyrics-ribbon-beat' + (Number(slot.beat.display_beat_index) === 0 ? ' measure-start' : '');
  cell.dataset.beatSeq = String(slot.seq);
  cell.style.left = left + 'px';
  cell.style.width = Math.max(74, next-left) + 'px';

  const chord = document.createElement('strong');
  chord.className = 'lyrics-ribbon-chord';
  chord.textContent = slot.text;
  cell.appendChild(chord);

  if (Number(slot.beat.display_beat_index) === 0) {
    const measure = document.createElement('small');
    measure.className = 'lyrics-ribbon-measure';
    measure.textContent = '#' + (Number(slot.beat.display_measure_index || 0) + 1);
    cell.appendChild(measure);
  }
  chordLane.appendChild(cell);
});

syllables.forEach((s,i) => {
  const node = document.createElement('span');
  node.className = 'lyrics-ribbon-syllable' + (s.fallback ? ' is-word-fallback' : '');
  node.dataset.syllableIndex = String(i);
  node.style.left = timeline.timeToX(s.nucleusMs) + 'px';
  node.textContent = s.display;
  syllableLane.appendChild(node);
  syllableNodes.push(node);
});

function activeSyllable(ms) {
  let index = -1;
  for (let i=0;i<syllables.length;i++) {
    if (syllables[i].nucleusMs <= ms) index=i;
    else break;
  }
  return index;
}

let lastBeat=-2, lastSyllable=-2, lastTime=0;

function renderAt(sec, force=false) {
  lastTime = Math.max(0, Number(sec)||0);
  const ms = lastTime * 1000;
  const x = focusX();
  zone.style.left = x + 'px';
  track.style.transform = `translate3d(${x - timeline.timeToX(ms)}px,0,0)`;

  const beatIndex = timeline.beatIndexAtMs(ms);
  if (force || beatIndex !== lastBeat) {
    lastBeat = beatIndex;
    chordLane.querySelectorAll('.current').forEach(el=>el.classList.remove('current'));
    chordLane.querySelector(`.lyrics-ribbon-beat[data-beat-seq="${beatIndex}"]`)?.classList.add('current');
  }

  const syllableIndex = activeSyllable(ms);
  if (force || syllableIndex !== lastSyllable) {
    lastSyllable = syllableIndex;
    syllableNodes.forEach((el,i)=>{
      el.classList.toggle('past', syllableIndex >= 0 && i < syllableIndex);
      el.classList.toggle('current', i === syllableIndex);
    });
  }
}

const lastMs = Math.max(
  Number(timeline.beats.at(-1)?.start_ms || 0),
  Number(syllables.at(-1)?.endMs || 0)
);
track.style.width = Math.max(2600, timeline.timeToX(lastMs) + timeline.spacing * 8) + 'px';

mixer?.addEventListener('ezscore:audio-timeupdate', event => {
  renderAt(Number(event.detail?.time || 0));
});
mixer?.addEventListener('ezscore:request-seek', event => {
  renderAt(Number(event.detail?.time || lastTime), true);
});

renderAt(0, true);
window.addEventListener('resize', ()=>renderAt(lastTime, true));
root.dataset.timelineEngine = 'ezscore-r39-canonical';
root.dataset.karaokeMode = 'readonly';
})();
