(() => {
'use strict';
const root = document.querySelector('[data-lyricslab]');
if (!root) return;
const parse = v => { try { return JSON.parse(v || '[]'); } catch (_) { return []; } };
const payload = row => row && typeof row.payload === 'object' && row.payload ? row.payload : {};
const beats = parse(root.dataset.beats).slice().sort((a,b) => Number(a.start_ms ?? payload(a).start_ms ?? 0) - Number(b.start_ms ?? payload(b).start_ms ?? 0));

function median(values) {
  if (!values.length) return null;
  const sorted = values.slice().sort((a,b) => a-b);
  const m = Math.floor(sorted.length/2);
  return sorted.length % 2 ? sorted[m] : (sorted[m-1] + sorted[m]) / 2;
}
function tempoFromBeats() {
  for (const beat of beats) {
    const p = payload(beat);
    for (const raw of [beat.tempo_bpm, beat.bpm, p.tempo_bpm, p.bpm]) {
      const bpm = Number(raw);
      if (Number.isFinite(bpm) && bpm >= 30 && bpm <= 260) return bpm;
    }
  }
  const times = beats.map(b => Number(b.start_ms ?? payload(b).start_ms)).filter(Number.isFinite).sort((a,b)=>a-b);
  const gaps = [];
  for (let i=1;i<times.length;i++) {
    const d = times[i]-times[i-1];
    if (d >= 230 && d <= 2000) gaps.push(d);
  }
  const ms = median(gaps);
  return ms ? 60000/ms : null;
}
function fmt(bpm) {
  if (!Number.isFinite(bpm)) return '—';
  const rounded = Math.round(bpm);
  return Math.abs(bpm-rounded) < 0.08 ? String(rounded) : bpm.toFixed(1);
}
const bpm = tempoFromBeats();
const card = root.querySelector('.lab-song-card');
if (card && !card.querySelector('[data-lyricslab-tempo]')) {
  const box = document.createElement('div');
  box.dataset.lyricslabTempo = '';
  box.innerHTML = '<span>TEMPO</span><strong>' + fmt(bpm) + ' BPM</strong>';
  card.appendChild(box);
}
const profile = root.querySelector('.lyricslab-profile');
if (profile && !profile.querySelector('[data-lyricslab-tempo-inline]')) {
  const badge = document.createElement('b');
  badge.dataset.lyricslabTempoInline = '';
  badge.textContent = 'Tempo ' + fmt(bpm) + ' BPM';
  profile.appendChild(badge);
}

const toggle = root.querySelector('[data-lyrics-diagram-toggle]');
const songId = String(root.dataset.songId || '').trim();
if (toggle && songId) {
  const stableKey = `ezscore:lyricslab:diagram:v2:${songId}`;
  const legacyKey = `ezscore:lyricslab:diagram:${window.location.pathname}`;
  let stored = null;
  try { stored = localStorage.getItem(stableKey); } catch (_) {}
  if (stored === null) {
    try {
      const legacy = localStorage.getItem(legacyKey);
      if (legacy !== null) stored = legacy;
    } catch (_) {}
  }
  if (stored === '0' || stored === '1') {
    const desired = stored === '1';
    if (toggle.checked !== desired) {
      toggle.checked = desired;
      toggle.dispatchEvent(new Event('change', {bubbles:true}));
    }
  } else {
    try { localStorage.setItem(stableKey, toggle.checked ? '1' : '0'); } catch (_) {}
  }
  toggle.addEventListener('change', () => {
    try { localStorage.setItem(stableKey, toggle.checked ? '1' : '0'); } catch (_) {}
  });
}
})();
