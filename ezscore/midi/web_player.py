"""Integrated online SoundFont MIDI editor player for EZScore."""

from __future__ import annotations

import base64

import streamlit as st

DEFAULT_SOUNDFONT_URL = (
    "https://raw.githubusercontent.com/mrbumpy409/GeneralUser-GS/"
    "main/GeneralUser-GS.sf2"
)
_SOUND_FONT_FALLBACK_URLS = (
    DEFAULT_SOUNDFONT_URL,
    "https://cdn.jsdelivr.net/gh/planet-s/generaluser-gs@master/generaluser-gs.sf2",
)

_LIBFLUID_URL = (
    "https://cdn.jsdelivr.net/npm/js-synthesizer@1.13.0/"
    "externals/libfluidsynth-2.4.6.js"
)
_JS_SYNTH_URL = (
    "https://cdn.jsdelivr.net/npm/js-synthesizer@1.13.0/"
    "dist/js-synthesizer.min.js"
)

_PLAYER_HTML = """
<div class="ez-midi-player">
  <audio class="ez-midi-song" controls preload="metadata"></audio>
  <div class="ez-midi-controls">
    <label>
      Volume chanson
      <input class="ez-midi-song-volume" type="range"
             min="0" max="1" step="0.01" value="0.85">
    </label>
    <label>
      Volume MIDI
      <input class="ez-midi-synth-volume" type="range"
             min="0" max="2" step="0.01" value="0.65">
    </label>
  </div>
  <button class="ez-midi-init" type="button">Charger le synthé MIDI</button>
  <div class="ez-midi-state">Synthé non chargé</div>
  <div class="ez-midi-now">Accord : —</div>
  <div class="ez-midi-hint">
    MP3 maître · FluidSynth + SoundFont intégrés au navigateur ·
    aucune sortie MIDI système requise.
  </div>
</div>
"""

_PLAYER_CSS = """
:host { display: block; width: 100%; }
.ez-midi-player {
  box-sizing: border-box;
  width: 100%;
  border: 1px solid color-mix(in srgb, var(--st-text-color) 24%, transparent);
  border-radius: 10px;
  padding: 12px 14px;
  background: color-mix(in srgb, var(--st-text-color) 4%, transparent);
  color: var(--st-text-color);
  font-family: var(--st-font);
}
.ez-midi-song { width: 100%; }
.ez-midi-controls {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-top: 10px;
}
.ez-midi-controls label {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
}
.ez-midi-controls input { width: 100%; }
.ez-midi-init {
  margin-top: 9px;
  min-height: 34px;
  padding: 5px 10px;
  border-radius: 7px;
  border: 1px solid color-mix(in srgb, var(--st-text-color) 35%, transparent);
  background: color-mix(in srgb, var(--st-text-color) 8%, transparent);
  color: var(--st-text-color);
  cursor: pointer;
}
.ez-midi-init:disabled { opacity: 0.65; cursor: wait; }
.ez-midi-state { margin-top: 8px; font-size: 12px; opacity: 0.88; }
.ez-midi-now { margin-top: 6px; font-size: 15px; font-weight: 700; }
.ez-midi-hint { margin-top: 5px; font-size: 11px; opacity: 0.68; }
"""

_PLAYER_JS = r"""
export default function(component) {
  const data = component.data || {};
  const root = component.parentElement;
  const audio = root.querySelector(".ez-midi-song");
  const initButton = root.querySelector(".ez-midi-init");
  const state = root.querySelector(".ez-midi-state");
  const now = root.querySelector(".ez-midi-now");
  const songVolume = root.querySelector(".ez-midi-song-volume");
  const synthVolume = root.querySelector(".ez-midi-synth-volume");

  if (!audio || !initButton || !state || !now || !songVolume || !synthVolume) {
    return;
  }

  audio.src = "data:" + data.mime + ";base64," + data.audio_base64;
  audio.volume = Number(songVolume.value);
  state.textContent = "Synthé non chargé · Instrument : " + data.instrument_label;

  const events = Array.isArray(data.midi_events) ? data.midi_events : [];
  const program = Number(data.program || 0);

  let context = null;
  let synth = null;
  let soundFontId = null;
  let synthNode = null;
  let cursor = 0;
  let scheduler = null;
  let lastMediaTime = 0;
  let ready = false;
  let disposed = false;
  let initializing = null;
  let resumeAfterInit = false;

  window.__ezscoreMidiScripts = window.__ezscoreMidiScripts || {};
  window.__ezscoreSoundFonts = window.__ezscoreSoundFonts || {};

  function loadScript(url) {
    if (window.__ezscoreMidiScripts[url]) {
      return window.__ezscoreMidiScripts[url];
    }
    window.__ezscoreMidiScripts[url] = new Promise(function(resolve, reject) {
      const selector = 'script[data-ezscore-midi-src="' + url + '"]';
      const existing = document.querySelector(selector);
      if (existing) {
        if (existing.dataset.loaded === "1") {
          resolve();
        } else {
          existing.addEventListener("load", resolve, { once: true });
          existing.addEventListener("error", reject, { once: true });
        }
        return;
      }
      const script = document.createElement("script");
      script.src = url;
      script.async = true;
      script.dataset.ezscoreMidiSrc = url;
      script.addEventListener("load", function() {
        script.dataset.loaded = "1";
        resolve();
      }, { once: true });
      script.addEventListener("error", function() {
        reject(new Error("Impossible de charger " + url));
      }, { once: true });
      document.head.appendChild(script);
    });
    return window.__ezscoreMidiScripts[url];
  }

  function lowerBound(time) {
    let low = 0;
    let high = events.length;
    while (low < high) {
      const middle = (low + high) >> 1;
      if (Number(events[middle].time) < time) low = middle + 1;
      else high = middle;
    }
    return low;
  }

  function silence() {
    if (!synth) return;
    try {
      synth.midiAllNotesOff();
      synth.midiAllSoundsOff();
    } catch (_) {}
  }

  function selectProgram() {
    if (synth && soundFontId !== null) {
      synth.midiProgramSelect(0, soundFontId, 0, program);
    }
  }

  function resetAt(time) {
    silence();
    selectProgram();
    cursor = lowerBound(Math.max(0, Number(time) - 0.003));
    lastMediaTime = Number(time);
    now.textContent = "Accord : —";
  }

  function sendEvent(event) {
    if (!synth) return;
    if (event.kind === "program") {
      selectProgram();
      return;
    }
    if (event.kind === "note_on") {
      synth.midiNoteOn(0, Number(event.data1), Number(event.data2 || 0));
      if (event.chord) now.textContent = "Accord : " + event.chord;
      return;
    }
    if (event.kind === "note_off") {
      synth.midiNoteOff(0, Number(event.data1));
    }
  }

  function pump() {
    if (!ready || audio.paused || audio.ended) return;
    const time = audio.currentTime;
    if (time + 0.04 < lastMediaTime || Math.abs(time - lastMediaTime) > 0.35) {
      resetAt(time);
    }
    lastMediaTime = time;
    while (cursor < events.length && Number(events[cursor].time) <= time + 0.008) {
      const event = events[cursor++];
      if (Number(event.time) >= time - 0.035 || event.kind === "program") {
        sendEvent(event);
      }
    }
  }

  function startScheduler() {
    if (scheduler !== null) clearInterval(scheduler);
    scheduler = window.setInterval(pump, 8);
    pump();
  }

  function stopScheduler() {
    if (scheduler !== null) {
      clearInterval(scheduler);
      scheduler = null;
    }
  }

  async function fetchSoundFont() {
    const urls = Array.isArray(data.soundfont_urls) && data.soundfont_urls.length
      ? data.soundfont_urls
      : [data.soundfont_url];
    let lastError = null;

    for (const url of urls) {
      if (!url) continue;
      try {
        if (!window.__ezscoreSoundFonts[url]) {
          window.__ezscoreSoundFonts[url] = fetch(url, { cache: "force-cache" })
            .then(function(response) {
              if (!response.ok) throw new Error("SoundFont HTTP " + response.status);
              return response.arrayBuffer();
            })
            .catch(function(error) {
              delete window.__ezscoreSoundFonts[url];
              throw error;
            });
        }
        return await window.__ezscoreSoundFonts[url];
      } catch (error) {
        lastError = error;
      }
    }

    throw lastError || new Error("SoundFont indisponible");
  }

  async function initializeSynth() {
    if (ready) {
      if (context && context.state === "suspended") await context.resume();
      return;
    }
    if (initializing) return initializing;

    initializing = (async function() {
      initButton.disabled = true;
      state.textContent = "Chargement du moteur FluidSynth…";
      try {
        await loadScript(data.libfluid_url);
        await loadScript(data.jssynth_url);
        if (!window.JSSynth || !window.JSSynth.Synthesizer) {
          throw new Error("js-synthesizer n'est pas disponible");
        }
        await window.JSSynth.waitForReady();
        if (disposed) return;

        context = new (window.AudioContext || window.webkitAudioContext)({
          latencyHint: "interactive"
        });
        synth = new window.JSSynth.Synthesizer();
        synth.init(context.sampleRate, {
          initialGain: Number(synthVolume.value),
          reverbActive: false,
          chorusActive: false
        });
        synthNode = synth.createAudioNode(context, 512);
        synthNode.connect(context.destination);

        state.textContent = "Chargement du SoundFont…";
        const bytes = await fetchSoundFont();
        if (disposed) return;
        soundFontId = await synth.loadSFont(bytes.slice(0));
        selectProgram();

        ready = true;
        initButton.disabled = false;
        initButton.textContent = "Synthé MIDI prêt";
        state.textContent = "Prêt · " + data.instrument_label;
      } catch (error) {
        console.error("EZScore MIDI player:", error);
        initButton.disabled = false;
        state.textContent = "Erreur synthé : " + (
          error && error.message ? error.message : String(error)
        );
        throw error;
      } finally {
        initializing = null;
      }
    })();

    return initializing;
  }

  async function onInitialize() {
    try {
      await initializeSynth();
      if (context && context.state === "suspended") await context.resume();
    } catch (_) {}
  }

  function onSongVolume() {
    audio.volume = Number(songVolume.value);
  }

  function onSynthVolume() {
    if (synth) synth.setGain(Number(synthVolume.value));
  }

  async function onPlay() {
    if (!ready) {
      audio.pause();
      resumeAfterInit = true;
      state.textContent = "Chargement automatique du synthé MIDI…";
      try {
        await initializeSynth();
        if (disposed || !ready || !resumeAfterInit) return;
        resumeAfterInit = false;
        resetAt(audio.currentTime);
        await audio.play();
      } catch (_) {
        resumeAfterInit = false;
      }
      return;
    }

    if (context && context.state === "suspended") await context.resume();
    resetAt(audio.currentTime);
    startScheduler();
  }

  function onPause() {
    stopScheduler();
    silence();
  }

  function onSeeking() {
    stopScheduler();
    silence();
  }

  function onSeeked() {
    if (ready) resetAt(audio.currentTime);
    if (ready && !audio.paused) startScheduler();
  }

  initButton.addEventListener("click", onInitialize);
  songVolume.addEventListener("input", onSongVolume);
  synthVolume.addEventListener("input", onSynthVolume);
  audio.addEventListener("play", onPlay);
  audio.addEventListener("pause", onPause);
  audio.addEventListener("ended", onPause);
  audio.addEventListener("seeking", onSeeking);
  audio.addEventListener("seeked", onSeeked);

  return function() {
    disposed = true;
    resumeAfterInit = false;
    stopScheduler();
    silence();
    initButton.removeEventListener("click", onInitialize);
    songVolume.removeEventListener("input", onSongVolume);
    synthVolume.removeEventListener("input", onSynthVolume);
    audio.removeEventListener("play", onPlay);
    audio.removeEventListener("pause", onPause);
    audio.removeEventListener("ended", onPause);
    audio.removeEventListener("seeking", onSeeking);
    audio.removeEventListener("seeked", onSeeked);
    try { if (synthNode) synthNode.disconnect(); } catch (_) {}
    try { if (synth) synth.close(); } catch (_) {}
    try { if (context) context.close(); } catch (_) {}
  };
}
"""

_MIDI_PLAYER_COMPONENT = st.components.v2.component(
    "ezscore.midi_editor_player",
    html=_PLAYER_HTML,
    css=_PLAYER_CSS,
    js=_PLAYER_JS,
    isolate_styles=True,
)


def _audio_mime(extension: str) -> str:
    return {
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".ogg": "audio/ogg",
        ".m4a": "audio/mp4",
        ".aac": "audio/aac",
        ".flac": "audio/flac",
    }.get(str(extension or "").lower(), "audio/mpeg")


def render_editor_midi_player(
    audio_bytes: bytes,
    extension: str,
    midi_events,
    instrument_label: str,
    program: int,
    soundfont_url: str = DEFAULT_SOUNDFONT_URL,
    *,
    key: str | None = None,
):
    """Render the online MP3 + SoundFont MIDI editor player.

    The original MP3 remains the transport clock. FluidSynth runs entirely in
    the browser through a Streamlit Components v2 component. The MP3 itself is
    deliberately *not* wrapped in a MediaElementSourceNode: Components v2 can
    rerender the same <audio> element and browsers forbid associating one media
    element with multiple MediaElementSourceNodes over its lifetime.
    """
    if not midi_events:
        return

    soundfont_urls = [str(soundfont_url)]
    for fallback in _SOUND_FONT_FALLBACK_URLS:
        if fallback not in soundfont_urls:
            soundfont_urls.append(fallback)

    _MIDI_PLAYER_COMPONENT(
        data={
            "audio_base64": base64.b64encode(audio_bytes).decode("ascii"),
            "mime": _audio_mime(extension),
            "midi_events": midi_events,
            "instrument_label": str(instrument_label),
            "program": int(program),
            "soundfont_url": str(soundfont_url),
            "soundfont_urls": soundfont_urls,
            "libfluid_url": _LIBFLUID_URL,
            "jssynth_url": _JS_SYNTH_URL,
        },
        key=key,
        width="stretch",
        height=250,
    )
