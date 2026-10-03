/* EZScore R1.C6 — Session Karaoke conductor -> LiveRun state. */
(() => {
'use strict';

const cfg = document.querySelector('[data-karaoke-live-sync]');
if (!cfg) return;

const mixer = document.querySelector('[data-stem-mixer]');
const songId = Number(cfg.dataset.songId || 0);
const url = cfg.dataset.syncUrl || '';
const token = cfg.dataset.syncToken || '';
if (!songId || !url || !token) return;

let state = {
  playing: false,
  positionMs: 0,
  playbackRate: Number(mixer?.querySelector('[data-mixer-rate]')?.value || 1),
};
let lastSentAt = 0;
let inFlight = false;
let pending = false;

async function send(force = false) {
  const now = Date.now();
  if (!force && now - lastSentAt < 420) {
    pending = true;
    return;
  }
  if (inFlight) {
    pending = true;
    return;
  }

  inFlight = true;
  pending = false;
  lastSentAt = now;

  try {
    await fetch(url, {
      method: 'POST',
      credentials: 'same-origin',
      headers: {'Accept':'application/json','Content-Type':'application/json'},
      body: JSON.stringify({
        _token: token,
        song_id: songId,
        playing: state.playing,
        position_ms: Math.max(0, Math.round(state.positionMs)),
        playback_rate: state.playbackRate,
      }),
    });
  } catch (_) {
    // Best effort POC; next event retries.
  } finally {
    inFlight = false;
    if (pending) window.setTimeout(() => send(true), 30);
  }
}

send(true);

if (!mixer) return;

let duration = 0;
mixer.addEventListener('ezscore:audio-timeupdate', (event) => {
  state.positionMs = Math.max(0, Number(event.detail?.time || 0) * 1000);
  duration = Math.max(0, Number(event.detail?.duration || 0));
  send(false);
});

mixer.querySelector('[data-mixer-play]')?.addEventListener('click', () => {
  state.playing = true;
  send(true);
}, true);

mixer.querySelector('[data-mixer-pause]')?.addEventListener('click', () => {
  state.playing = false;
  send(true);
}, true);

mixer.querySelector('[data-mixer-stop]')?.addEventListener('click', () => {
  state.playing = false;
  state.positionMs = 0;
  send(true);
}, true);

mixer.querySelector('[data-mixer-seek]')?.addEventListener('input', (event) => {
  if (duration > 0) {
    state.positionMs = (Number(event.currentTarget.value || 0) / 1000) * duration * 1000;
    send(true);
  }
}, true);

mixer.querySelector('[data-mixer-rate]')?.addEventListener('change', (event) => {
  state.playbackRate = Number(event.currentTarget.value || 1);
  send(true);
}, true);

const rootCleanup = () => {
  state.playing = false;
  send(true);
};
window.addEventListener('pagehide', rootCleanup, {once:true});
})();
