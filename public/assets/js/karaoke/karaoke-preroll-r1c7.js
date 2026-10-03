/* EZScore R1.C7 — Karaoke pre-roll, solo + Session. */
(() => {
'use strict';

const karaoke = document.querySelector('[data-karaoke]');
if (!karaoke) return;

const mixer = document.querySelector('[data-stem-mixer]');
const play = mixer?.querySelector('[data-mixer-play]');
const stop = mixer?.querySelector('[data-mixer-stop]');
const setting = document.querySelector('[data-karaoke-preroll-seconds]');
const sync = document.querySelector('[data-karaoke-live-sync]');

if (!play) return;

let lastTime = 0;
let bypass = false;
let countdownTimer = 0;
let countdownEnd = 0;

const overlay = document.createElement('div');
overlay.className = 'karaoke-preroll-overlay';
overlay.hidden = true;
overlay.setAttribute('aria-live', 'assertive');
overlay.setAttribute('aria-label', 'Compte à rebours');
karaoke.appendChild(overlay);

const secondsValue = () => {
  const value = Number(setting?.value || 5);
  return Math.max(1, Math.min(30, Number.isFinite(value) ? Math.round(value) : 5));
};

const postSessionCountdown = async (seconds) => {
  if (!sync?.dataset.syncUrl || !sync?.dataset.syncToken || !sync?.dataset.songId) return;
  try {
    await fetch(sync.dataset.syncUrl, {
      method: 'POST',
      credentials: 'same-origin',
      headers: {'Accept':'application/json','Content-Type':'application/json'},
      body: JSON.stringify({
        _token: sync.dataset.syncToken,
        song_id: Number(sync.dataset.songId),
        playing: false,
        position_ms: 0,
        playback_rate: Number(mixer?.querySelector('[data-mixer-rate]')?.value || 1),
        countdown_seconds: seconds,
      }),
    });
  } catch (_) {
    // Display sync is best effort; local conductor countdown still proceeds.
  }
};

const clearCountdown = () => {
  window.clearInterval(countdownTimer);
  countdownTimer = 0;
  countdownEnd = 0;
  overlay.hidden = true;
  overlay.textContent = '';
};

const draw = () => {
  if (!countdownEnd) return;
  const remaining = countdownEnd - Date.now();
  if (remaining <= 0) {
    clearCountdown();
    bypass = true;
    play.click();
    queueMicrotask(() => { bypass = false; });
    return;
  }
  overlay.hidden = false;
  overlay.textContent = String(Math.max(1, Math.ceil(remaining / 1000)));
};

const startCountdown = async () => {
  clearCountdown();
  const seconds = secondsValue();
  countdownEnd = Date.now() + seconds * 1000;
  await postSessionCountdown(seconds);
  draw();
  countdownTimer = window.setInterval(draw, 100);
};

play.addEventListener('click', (event) => {
  if (bypass) return;

  // Pre-roll only for a real start from the beginning. Resume after Pause is immediate.
  if (lastTime > 0.25) return;

  event.preventDefault();
  event.stopImmediatePropagation();
  startCountdown();
}, true);

mixer?.addEventListener('ezscore:audio-timeupdate', (event) => {
  lastTime = Math.max(0, Number(event.detail?.time || 0));
});

stop?.addEventListener('click', () => {
  lastTime = 0;
  clearCountdown();
}, true);

mixer?.querySelector('[data-mixer-seek]')?.addEventListener('input', () => {
  // stems-mixer emits audio time updates after seeking; keep current value until then.
  clearCountdown();
}, true);

window.addEventListener('pagehide', clearCountdown, {once:true});
})();
