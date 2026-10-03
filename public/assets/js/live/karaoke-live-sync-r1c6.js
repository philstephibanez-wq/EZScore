/* EZScore R1.C14B — low-latency Session Karaoke conductor -> LiveRun state. */
(() => {
'use strict';

const cfg = document.querySelector('[data-karaoke-live-sync]');
if (!cfg) return;

const mixer = document.querySelector('[data-stem-mixer]');
const diagram = document.querySelector('[data-chordslab-diagram]');
const songId = Number(cfg.dataset.songId || 0);
const url = cfg.dataset.syncUrl || '';
const token = cfg.dataset.syncToken || '';
if (!songId || !url || !token) return;

let state = {
  playing: false,
  positionMs: 0,
  playbackRate: Number(mixer?.querySelector('[data-mixer-rate]')?.value || 1),
  diagramEnabled: Boolean(diagram?.checked),
};
let lastSentAt = 0;
let inFlight = false;
let pending = false;
let pendingForce = false;
let seq = 0;
let lastProbeAt = 0;

async function send(force = false, reason = 'heartbeat') {
  const now = performance.now();
  // Position heartbeats are only corrections. Transport controls are force-sent.
  if (!force && now - lastSentAt < 700) {
    pending = true;
    return;
  }
  if (inFlight) {
    pending = true;
    pendingForce = pendingForce || force;
    return;
  }

  inFlight = true;
  pending = false;
  pendingForce = false;
  lastSentAt = now;
  const started = performance.now();
  const currentSeq = ++seq;

  try {
    const response = await fetch(url, {
      method: 'POST',
      credentials: 'same-origin',
      cache: 'no-store',
      headers: {'Accept':'application/json','Content-Type':'application/json'},
      body: JSON.stringify({
        _token: token,
        song_id: songId,
        playing: state.playing,
        position_ms: Math.max(0, Math.round(state.positionMs)),
        playback_rate: state.playbackRate,
        diagram_enabled: state.diagramEnabled,
        client_seq: currentSeq,
      }),
    });
    const elapsed = performance.now() - started;
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    if (force || performance.now() - lastProbeAt > 3000) {
      lastProbeAt = performance.now();
      console.debug('[EZSYNC chef]', {
        reason, seq: currentSeq, rtt_ms: Math.round(elapsed),
        playing: state.playing, position_ms: Math.round(state.positionMs),
        diagram: state.diagramEnabled
      });
    }
  } catch (error) {
    console.warn('[EZSYNC chef] POST failed', reason, error);
  } finally {
    inFlight = false;
    if (pending) {
      const forceNext = pendingForce;
      pending = false;
      pendingForce = false;
      window.setTimeout(() => send(forceNext, forceNext ? 'queued-control' : 'queued-heartbeat'), 0);
    }
  }
}

send(true, 'open');

if (!mixer) return;

let duration = 0;
mixer.addEventListener('ezscore:audio-timeupdate', (event) => {
  state.positionMs = Math.max(0, Number(event.detail?.time || 0) * 1000);
  duration = Math.max(0, Number(event.detail?.duration || 0));
  send(false, 'timeupdate');
});

mixer.querySelector('[data-mixer-play]')?.addEventListener('click', () => {
  state.playing = true;
  send(true, 'play');
}, true);

mixer.querySelector('[data-mixer-pause]')?.addEventListener('click', () => {
  state.playing = false;
  send(true, 'pause');
}, true);

mixer.querySelector('[data-mixer-stop]')?.addEventListener('click', () => {
  state.playing = false;
  state.positionMs = 0;
  send(true, 'stop');
}, true);

mixer.querySelector('[data-mixer-seek]')?.addEventListener('input', (event) => {
  if (duration > 0) {
    state.positionMs = (Number(event.currentTarget.value || 0) / 1000) * duration * 1000;
    send(true, 'seek');
  }
}, true);

mixer.querySelector('[data-mixer-rate]')?.addEventListener('change', (event) => {
  state.playbackRate = Number(event.currentTarget.value || 1);
  send(true, 'rate');
}, true);

diagram?.addEventListener('change', () => {
  state.diagramEnabled = Boolean(diagram.checked);
  send(true, 'diagram');
}, true);

window.addEventListener('pagehide', () => {
  state.playing = false;
  send(true, 'pagehide');
}, {once:true});
})();
