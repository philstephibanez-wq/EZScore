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
  <div class="ez-player-identity">
    <img class="ez-player-cover" alt="">
    <div class="ez-player-titles">
      <div class="ez-player-title"></div>
      <div class="ez-player-artist"></div>
    </div>
  </div>
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
  <div class="ez-measure-strip">
    <div class="ez-measure-track"></div>
  </div>
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
.ez-player-identity {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 10px;
}
.ez-player-cover {
  width: 72px;
  height: 72px;
  object-fit: cover;
  border-radius: 8px;
  display: none;
  flex: 0 0 auto;
}
.ez-player-cover.has-cover { display: block; }
.ez-player-title {
  font-size: 18px;
  font-weight: 800;
  line-height: 1.1;
}
.ez-player-artist {
  margin-top: 3px;
  font-size: 13px;
  opacity: .72;
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
.ez-measure-strip {
  position:relative;
  overflow:hidden;
  width:100%;
  min-height:245px;
  margin-top:10px;
  padding:8px 0 10px;
}
.ez-measure-track {
  display:flex;
  align-items:flex-start;
  gap:16px;
  will-change:transform;
  transition:transform 220ms ease;
}
.ez-measure-card {
  box-sizing:border-box;
  flex:0 0 300px;
  min-height:205px;
  padding:12px 14px 14px;
  border:1px solid rgba(150,160,175,.38);
  border-radius:12px;
  background:rgba(127,127,127,.055);
  opacity:.68;
  transition:opacity .16s, transform .16s, background .16s, border-color .16s;
}
.ez-measure-card.active {
  opacity:1;
  transform:scale(1.035);
  background:rgba(77,163,255,.14);
  border:2px solid rgba(77,163,255,.95);
}
.ez-measure-card.past{opacity:.40}
.ez-measure-card.future{opacity:.72}
.ez-measure-number{text-align:right;font-size:11px;font-weight:800;opacity:.48}
.ez-measure-diagram{display:flex;justify-content:center;min-height:0;margin-top:-3px}
.ez-measure-diagram:empty{display:none}
.ez-measure-chord{text-align:center;font-size:34px;line-height:1.05;font-weight:900;min-height:38px;margin-top:4px}
.ez-measure-beats{display:grid;gap:8px;margin:14px auto 0}
.ez-beat-cell {
  display:flex;
  align-items:center;
  justify-content:center;
  min-width:0;
  min-height:42px;
  padding:3px 6px;
  border-radius:8px;
  border:1px solid rgba(150,160,175,.28);
  font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  font-size:24px;
  font-weight:900;
  opacity:.58;
}
.ez-beat-cell.elapsed{opacity:.82;background:rgba(77,163,255,.08)}
.ez-beat-cell.current {
  opacity:1;
  color:#fff;
  background:#2679d8;
  border-color:#69adff;
  box-shadow:0 0 0 2px rgba(77,163,255,.22);
}
.ez-measure-lyric{margin-top:13px;min-height:38px;text-align:center;font-size:15px;line-height:1.25;opacity:.90}
.ez-midi-hint { margin-top: 8px; font-size: 11px; opacity: 0.68; }
@media(max-width:900px){.ez-measure-card{flex-basis:260px}}
@media(max-width:640px){
  .ez-midi-player{padding:10px}
  .ez-measure-strip{min-height:230px}
  .ez-measure-track{gap:10px}
  .ez-measure-card{flex-basis:220px;min-height:190px;padding:9px}
  .ez-measure-chord{font-size:29px}
  .ez-beat-cell{font-size:21px;min-height:38px;padding:2px 4px}
  .ez-measure-lyric{font-size:13px}
  .ez-measure-diagram svg{width:96px;height:122px}
}
"""

_PLAYER_JS = r"""
export default function(component) {
  const data = component.data || {};
  const root = component.parentElement;
  const audio = root.querySelector(".ez-midi-song");
  const initButton = root.querySelector(".ez-midi-init");
  const state = root.querySelector(".ez-midi-state");
  const strip = root.querySelector(".ez-measure-strip");
  const measureTrack = root.querySelector(".ez-measure-track");
  const songVolume = root.querySelector(".ez-midi-song-volume");
  const synthVolume = root.querySelector(".ez-midi-synth-volume");
  const cover = root.querySelector(".ez-player-cover");
  const title = root.querySelector(".ez-player-title");
  const artist = root.querySelector(".ez-player-artist");

  if (!audio || !initButton || !state || !strip || !measureTrack || !songVolume || !synthVolume) {
    return;
  }

  audio.src = "data:" + data.mime + ";base64," + data.audio_base64;
  audio.volume = Number(songVolume.value);

  if (title) title.textContent = String(data.title || "");
  if (artist) artist.textContent = String(data.artist || "");
  if (cover && data.cover && data.cover.base64 && data.cover.mime) {
    cover.src = "data:" + data.cover.mime + ";base64," + data.cover.base64;
    cover.alt = "Pochette de " + String(data.title || "la chanson");
    cover.classList.add("has-cover");
  }
  state.textContent = "Synthé non chargé · Instrument : " + data.instrument_label;

  const events = Array.isArray(data.midi_events) ? data.midi_events : [];
  const measures = Array.isArray(data.player_measures) ? data.player_measures : [];
  const showDiagrams = Boolean(data.show_diagrams);
  const program = Number(data.program || 0);
  const cards = [];

  measures.forEach((measure) => {
    const card = document.createElement("div");
    card.className = "ez-measure-card future";

    const number = document.createElement("div");
    number.className = "ez-measure-number";
    number.textContent = "Mesure " + measure.measure;

    const diagram = document.createElement("div");
    diagram.className = "ez-measure-diagram";

    const chord = document.createElement("div");
    chord.className = "ez-measure-chord";
    chord.textContent = measure.primary_chord || "—";

    const beats = document.createElement("div");
    beats.className = "ez-measure-beats";
    const count = Math.max(1, (measure.beat_tokens || []).length);
    beats.style.gridTemplateColumns = "repeat(" + count + ", minmax(0,1fr))";

    const beatNodes = (measure.beat_tokens || []).map((token) => {
      const beat = document.createElement("div");
      beat.className = "ez-beat-cell";
      beat.textContent = token || "-";
      beats.appendChild(beat);
      return beat;
    });

    const lyric = document.createElement("div");
    lyric.className = "ez-measure-lyric";
    lyric.textContent = measure.lyric || "";

    card.append(number, diagram, chord, beats, lyric);
    measureTrack.appendChild(card);
    cards.push({ card, diagram, chord, beatNodes });
  });

  let activeMeasureIndex = -1;
  let activeBeatIndex = -1;

  function findMeasureIndex(time) {
    if (!measures.length) return -1;
    let low = 0, high = measures.length - 1, answer = 0;
    while (low <= high) {
      const middle = (low + high) >> 1;
      if (Number(measures[middle].time) <= time) {
        answer = middle;
        low = middle + 1;
      } else {
        high = middle - 1;
      }
    }
    return answer;
  }

  function findBeatIndex(measure, time) {
    const starts = Array.isArray(measure.beat_times) ? measure.beat_times : [];
    if (!starts.length) return 0;
    let answer = 0;
    for (let index = 0; index < starts.length; index += 1) {
      if (Number(starts[index]) <= time) answer = index;
      else break;
    }
    return answer;
  }

  function centerMeasure(index) {
    const card = cards[index]?.card;
    if (!card) return;
    const stripWidth = strip.clientWidth;
    const cardWidth = card.offsetWidth;
    const gap = parseFloat(getComputedStyle(measureTrack).gap || "0");
    const offset = index * (cardWidth + gap) - (stripWidth - cardWidth) / 2;
    measureTrack.style.transform = "translateX(" + (-offset) + "px)";
  }

  function updateVisual(time) {
    const measureIndex = findMeasureIndex(time);
    if (measureIndex < 0) return;
    const measure = measures[measureIndex];
    const beatIndex = findBeatIndex(measure, time);

    if (measureIndex !== activeMeasureIndex) {
      activeMeasureIndex = measureIndex;
      activeBeatIndex = -1;
      cards.forEach((entry, index) => {
        entry.card.classList.toggle("active", index === measureIndex);
        entry.card.classList.toggle("past", index < measureIndex);
        entry.card.classList.toggle("future", index > measureIndex);
        if (index !== measureIndex) entry.diagram.innerHTML = "";
      });
      centerMeasure(measureIndex);
    }

    if (beatIndex !== activeBeatIndex) {
      activeBeatIndex = beatIndex;
      const active = cards[measureIndex];
      active.beatNodes.forEach((node, index) => {
        node.classList.toggle("elapsed", index < beatIndex);
        node.classList.toggle("current", index === beatIndex);
      });
      active.chord.textContent = String(
        measure.beat_chords?.[beatIndex] || measure.primary_chord || "—"
      );
      const diagram = showDiagrams
        ? String(measure.beat_diagrams?.[beatIndex] || "")
        : "";
      if (active.diagram.dataset.value !== diagram) {
        active.diagram.dataset.value = diagram;
        active.diagram.innerHTML = diagram;
      }
    }
  }

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
    updateVisual(Number(time));
  }

  function sendEvent(event) {
    if (!synth) return;
    if (event.kind === "program") {
      selectProgram();
      return;
    }
    if (event.kind === "note_on") {
      synth.midiNoteOn(0, Number(event.data1), Number(event.data2 || 0));
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
    updateVisual(time);
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
    lyrics_words=None,
    player_measures=None,
    chord_diagrams=None,
    show_diagrams: bool = False,
    cover=None,
    title: str = "",
    artist: str = "",
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
            "lyrics_words": list(lyrics_words or []),
            "player_measures": list(player_measures or []),
            "chord_diagrams": dict(chord_diagrams or {}),
            "show_diagrams": bool(show_diagrams),
            "cover": dict(cover or {}),
            "title": str(title or ""),
            "artist": str(artist or ""),
            "soundfont_url": str(soundfont_url),
            "soundfont_urls": soundfont_urls,
            "libfluid_url": _LIBFLUID_URL,
            "jssynth_url": _JS_SYNTH_URL,
        },
        key=key,
        width="stretch",
        height=760 if show_diagrams else 560,
    )
