"""Compact 3-track Analyse player: MP3 + chord MIDI + vocal MIDI."""

from __future__ import annotations

import base64

import streamlit as st

from ezscore.midi.web_player import (
    DEFAULT_SOUNDFONT_URL,
    _SOUND_FONT_FALLBACK_URLS,
    _LIBFLUID_URL,
    _JS_SYNTH_URL,
    _audio_mime,
)


_PLAYER_HTML = """
<div class="ez-analysis-player">
  <div class="ez-player-identity">
    <div>
      <div class="ez-player-title"></div>
      <div class="ez-player-artist"></div>
    </div>
  </div>

  <audio class="ez-song" controls preload="metadata"></audio>

  <div class="ez-volumes">
    <label>
      Volume chanson
      <input class="ez-song-volume" type="range"
             min="0" max="1" step="0.01" value="0.85">
    </label>
    <label>
      Volume accords MIDI
      <input class="ez-chord-volume" type="range"
             min="0" max="1" step="0.01" value="0.65">
    </label>
    <label class="ez-vocal-volume-wrap">
      Volume chant MIDI
      <input class="ez-vocal-volume" type="range"
             min="0" max="1" step="0.01" value="0.78">
    </label>
  </div>

  <div class="ez-actions">
    <button class="ez-init" type="button">Charger le synthé MIDI</button>
  </div>

  <div class="ez-state">Synthé non chargé</div>

  <div class="ez-hint">
    MP3 maître · accords canal 1 · chant canal 2 · SoundFont navigateur
  </div>
</div>
"""


_PLAYER_CSS = """
:host { display:block; width:100%; }
.ez-analysis-player {
  box-sizing:border-box;
  width:100%;
  border:1px solid color-mix(in srgb, var(--st-text-color) 24%, transparent);
  border-radius:10px;
  padding:12px 14px;
  background:color-mix(in srgb, var(--st-text-color) 4%, transparent);
  color:var(--st-text-color);
  font-family:var(--st-font);
}
.ez-player-identity { margin-bottom:10px; }
.ez-player-title {
  font-size:18px;
  font-weight:800;
  line-height:1.1;
}
.ez-player-artist {
  margin-top:3px;
  font-size:13px;
  opacity:.72;
}
.ez-song { width:100%; }
.ez-volumes {
  display:grid;
  grid-template-columns:repeat(3, minmax(0, 1fr));
  gap:12px;
  margin-top:10px;
}
.ez-volumes label {
  display:flex;
  flex-direction:column;
  gap:4px;
  font-size:12px;
}
.ez-volumes input { width:100%; }
.ez-actions {
  display:flex;
  align-items:center;
  gap:12px;
  margin-top:9px;
}
.ez-init {
  min-height:34px;
  padding:5px 10px;
  border-radius:7px;
  border:1px solid color-mix(in srgb, var(--st-text-color) 35%, transparent);
  background:color-mix(in srgb, var(--st-text-color) 8%, transparent);
  color:var(--st-text-color);
  cursor:pointer;
}
.ez-init:disabled { opacity:.65; cursor:wait; }
.ez-state {
  margin-top:8px;
  font-size:12px;
  opacity:.88;
}
.ez-hint {
  margin-top:10px;
  font-size:11px;
  opacity:.68;
}
.ez-hidden { display:none !important; }

@media(max-width:780px) {
  .ez-volumes { grid-template-columns:1fr; }
}
"""


_PLAYER_JS = r"""
export default function(component) {
  const data = component.data || {};
  const root = component.parentElement;

  const audio = root.querySelector(".ez-song");
  const initButton = root.querySelector(".ez-init");
  const state = root.querySelector(".ez-state");
  const songVolume = root.querySelector(".ez-song-volume");
  const chordVolume = root.querySelector(".ez-chord-volume");
  const vocalVolume = root.querySelector(".ez-vocal-volume");
  const vocalVolumeWrap = root.querySelector(".ez-vocal-volume-wrap");
  const title = root.querySelector(".ez-player-title");
  const artist = root.querySelector(".ez-player-artist");

  if (!audio || !initButton || !state || !songVolume || !chordVolume || !vocalVolume) {
    return;
  }

  const chordEvents = Array.isArray(data.chord_events) ? data.chord_events : [];
  const vocalEvents = Array.isArray(data.vocal_events) ? data.vocal_events : [];
  const hasVocal = vocalEvents.some((event) => event.kind === "note_on");

  if (!hasVocal && vocalVolumeWrap) {
    vocalVolumeWrap.classList.add("ez-hidden");
  }

  audio.src = "data:" + data.mime + ";base64," + data.audio_base64;
  audio.volume = Number(songVolume.value);

  if (title) title.textContent = String(data.title || "");
  if (artist) artist.textContent = String(data.artist || "");

  const chordProgram = Number(data.chord_program || 0);
  const vocalProgram = Number(data.vocal_program || 65);

  let context = null;
  let synth = null;
  let soundFontId = null;
  let synthNode = null;
  let chordCursor = 0;
  let vocalCursor = 0;
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

  function lowerBound(events, time) {
    let low = 0;
    let high = events.length;
    while (low < high) {
      const middle = (low + high) >> 1;
      if (Number(events[middle].time) < time) low = middle + 1;
      else high = middle;
    }
    return low;
  }

  function ccVolume(channel, value) {
    if (!synth || !synth.midiControl) return;
    const midiValue = Math.max(0, Math.min(127, Math.round(Number(value) * 127)));
    try {
      synth.midiControl(channel, 7, midiValue);
    } catch (_) {}
  }

  function applyProgramsAndVolumes() {
    if (!synth || soundFontId === null) return;
    synth.midiProgramSelect(0, soundFontId, 0, chordProgram);
    synth.midiProgramSelect(1, soundFontId, 0, vocalProgram);
    ccVolume(0, chordVolume.value);
    ccVolume(1, vocalVolume.value);
  }

  function silence() {
    if (!synth) return;
    try {
      synth.midiAllNotesOff();
      synth.midiAllSoundsOff();
    } catch (_) {}
  }

  function resetAt(time) {
    silence();
    applyProgramsAndVolumes();

    const t = Math.max(0, Number(time) - 0.003);
    chordCursor = lowerBound(chordEvents, t);
    vocalCursor = lowerBound(vocalEvents, t);
    lastMediaTime = Number(time);
  }

  function sendEvent(event, channel) {
    if (!synth) return;

    if (event.kind === "program") {
      applyProgramsAndVolumes();
      return;
    }

    if (event.kind === "note_on") {
      synth.midiNoteOn(
        channel,
        Number(event.data1),
        Number(event.data2 || 0)
      );
      return;
    }

    if (event.kind === "note_off") {
      synth.midiNoteOff(channel, Number(event.data1));
    }
  }

  function pumpEvents(events, channel, cursorName, time) {
    let cursor = cursorName === "chord" ? chordCursor : vocalCursor;

    while (
      cursor < events.length &&
      Number(events[cursor].time) <= time + 0.008
    ) {
      const event = events[cursor++];
      if (
        Number(event.time) >= time - 0.035 ||
        event.kind === "program"
      ) {
        sendEvent(event, channel);
      }
    }

    if (cursorName === "chord") chordCursor = cursor;
    else vocalCursor = cursor;
  }

  function pump() {
    if (!ready || audio.paused || audio.ended) return;

    const time = audio.currentTime;

    if (
      time + 0.04 < lastMediaTime ||
      Math.abs(time - lastMediaTime) > 0.35
    ) {
      resetAt(time);
    }

    lastMediaTime = time;
    pumpEvents(chordEvents, 0, "chord", time);

    if (hasVocal) {
      pumpEvents(vocalEvents, 1, "vocal", time);
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
          window.__ezscoreSoundFonts[url] = fetch(
            url,
            { cache: "force-cache" }
          )
            .then(function(response) {
              if (!response.ok) {
                throw new Error("SoundFont HTTP " + response.status);
              }
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
      if (context && context.state === "suspended") {
        await context.resume();
      }
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

        context = new (
          window.AudioContext || window.webkitAudioContext
        )({ latencyHint: "interactive" });

        synth = new window.JSSynth.Synthesizer();
        synth.init(context.sampleRate, {
          initialGain: 1.0,
          reverbActive: false,
          chorusActive: false
        });

        synthNode = synth.createAudioNode(context, 512);
        synthNode.connect(context.destination);

        state.textContent = "Chargement du SoundFont…";

        const bytes = await fetchSoundFont();
        if (disposed) return;

        soundFontId = await synth.loadSFont(bytes.slice(0));
        applyProgramsAndVolumes();

        ready = true;
        initButton.disabled = false;
        initButton.textContent = "Synthé MIDI prêt";

        state.textContent = hasVocal
          ? (
              "Prêt · accords : " + String(data.chord_instrument_label || "") +
              " · chant : " + String(data.vocal_instrument_label || "")
            )
          : (
              "Prêt · accords : " + String(data.chord_instrument_label || "") +
              " · chant MIDI non analysé"
            );
      } catch (error) {
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
      if (context && context.state === "suspended") {
        await context.resume();
      }
    } catch (_) {}
  }

  async function onPlay() {
    if (!ready) {
      audio.pause();
      resumeAfterInit = true;
      state.textContent = "Chargement automatique du synthé MIDI…";

      try {
        await initializeSynth();

        if (disposed || !ready || !resumeAfterInit) {
          return;
        }

        resumeAfterInit = false;
        resetAt(audio.currentTime);
        await audio.play();
      } catch (_) {
        resumeAfterInit = false;
      }

      return;
    }

    if (context && context.state === "suspended") {
      await context.resume();
    }

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

  function onSongVolume() {
    audio.volume = Number(songVolume.value);
  }

  function onChordVolume() {
    ccVolume(0, chordVolume.value);
  }

  function onVocalVolume() {
    ccVolume(1, vocalVolume.value);
  }

  initButton.addEventListener("click", onInitialize);
  songVolume.addEventListener("input", onSongVolume);
  chordVolume.addEventListener("input", onChordVolume);
  vocalVolume.addEventListener("input", onVocalVolume);

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
    chordVolume.removeEventListener("input", onChordVolume);
    vocalVolume.removeEventListener("input", onVocalVolume);

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


_ANALYSIS_PLAYER = st.components.v2.component(
    "ezscore.analysis_three_track_player",
    html=_PLAYER_HTML,
    css=_PLAYER_CSS,
    js=_PLAYER_JS,
    isolate_styles=True,
)


def render_analysis_midi_player(
    *,
    audio_bytes: bytes,
    extension: str,
    chord_events,
    chord_instrument_label: str,
    chord_program: int,
    vocal_events=None,
    vocal_instrument_label: str = "Alto Sax",
    vocal_program: int = 65,
    title: str = "",
    artist: str = "",
    soundfont_url: str = DEFAULT_SOUNDFONT_URL,
    key: str | None = None,
):
    """Render the compact synchronized 3-track analysis player."""
    chord_events = list(chord_events or [])
    vocal_events = list(vocal_events or [])

    if not chord_events:
        return

    soundfont_urls = [str(soundfont_url)]
    for fallback in _SOUND_FONT_FALLBACK_URLS:
        if fallback not in soundfont_urls:
            soundfont_urls.append(fallback)

    _ANALYSIS_PLAYER(
        data={
            "audio_base64": base64.b64encode(audio_bytes).decode("ascii"),
            "mime": _audio_mime(extension),
            "chord_events": chord_events,
            "vocal_events": vocal_events,
            "chord_instrument_label": str(chord_instrument_label),
            "chord_program": int(chord_program),
            "vocal_instrument_label": str(vocal_instrument_label),
            "vocal_program": int(vocal_program),
            "title": str(title or ""),
            "artist": str(artist or ""),
            "soundfont_url": str(soundfont_url),
            "soundfont_urls": soundfont_urls,
            "libfluid_url": _LIBFLUID_URL,
            "jssynth_url": _JS_SYNTH_URL,
        },
        key=key,
        width="stretch",
        height=305,
    )
