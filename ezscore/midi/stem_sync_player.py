"""Synchronized original-audio + STEM-derived MIDI player.

The HTML audio element is the only clock. MIDI events are scheduled against
audio.currentTime. MIDI never drives or shifts the canonical timeline.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import streamlit as st

from ezscore.player.media_url import register_media_url

DEFAULT_SOUNDFONT_URL = (
    "https://raw.githubusercontent.com/mrbumpy409/GeneralUser-GS/"
    "main/GeneralUser-GS.sf2"
)
SOUNDFONT_FALLBACKS = (
    DEFAULT_SOUNDFONT_URL,
    "https://cdn.jsdelivr.net/gh/planet-s/generaluser-gs@master/generaluser-gs.sf2",
)
LIBFLUID_URL = (
    "https://cdn.jsdelivr.net/npm/js-synthesizer@1.13.0/"
    "externals/libfluidsynth-2.4.6.js"
)
JSSYNTH_URL = (
    "https://cdn.jsdelivr.net/npm/js-synthesizer@1.13.0/"
    "dist/js-synthesizer.min.js"
)

_HTML = """
<div class="stem-midi-sync">
  <audio class="song" controls preload="metadata"></audio>

  <div class="row master-row">
    <div class="label">MP3 original</div>
    <label><input class="audio-on" type="checkbox" checked> Actif</label>
    <input class="audio-volume vol-audio" type="range" min="0" max="1" step="0.01" value="0.80">
    <span class="audio-value">80%</span>
  </div>

  <div class="midi-actions">
    <button class="init" type="button">Charger le synthé MIDI</button>
    <span class="state">Synthé non chargé</span>
  </div>

  <div class="midi-table">
    <div class="head">Piste MIDI</div>
    <div class="head">ON</div>
    <div class="head">Volume</div>
    <div class="head">Instrument</div>

    <div class="label">Chant</div>
    <label><input class="vocal-on" type="checkbox" checked> Actif</label>
    <input class="vocal-volume vol-vocal" type="range" min="0" max="1.5" step="0.01" value="0.80">
    <select class="vocal-program" aria-label="Instrument MIDI chant"></select>

    <div class="label">Accords</div>
    <label><input class="chords-on" type="checkbox" checked> Actif</label>
    <input class="chords-volume vol-chords" type="range" min="0" max="1.5" step="0.01" value="0.70">
    <select class="chords-program" aria-label="Instrument MIDI accords"></select>

    <div class="label">Batterie</div>
    <label><input class="drums-on" type="checkbox" checked> Actif</label>
    <input class="drums-volume vol-drums" type="range" min="0" max="1.5" step="0.01" value="0.70">
    <select class="drums-program" aria-label="Kit MIDI batterie"></select>
  </div>

  <div class="track-status"></div>
  <div class="hint">
    MP3 original = horloge maître · Chant / Accords / Batterie suivent audio.currentTime.
  </div>
</div>
"""

_CSS = """
:host{display:block;width:100%}
.stem-midi-sync{
  box-sizing:border-box;width:100%;
  border:1px solid color-mix(in srgb,var(--st-text-color) 24%,transparent);
  border-radius:10px;padding:12px;
  background:color-mix(in srgb,var(--st-text-color) 4%,transparent);
  color:var(--st-text-color);font-family:var(--st-font);
}
.song{width:100%}
.row{
  display:grid;grid-template-columns:150px 80px 1fr 50px;
  gap:10px;align-items:center;margin-top:10px;
}
.midi-actions{display:flex;align-items:center;gap:12px;margin:12px 0}
.init{
  min-height:34px;padding:5px 10px;border-radius:7px;
  border:1px solid color-mix(in srgb,var(--st-text-color) 35%,transparent);
  background:color-mix(in srgb,var(--st-text-color) 8%,transparent);
  color:var(--st-text-color);cursor:pointer
}
.state{font-size:12px;opacity:.8}
.midi-table{
  display:grid;
  grid-template-columns:150px 80px minmax(180px,1fr) 120px;
  gap:9px 12px;align-items:center;
}
.head{font-size:11px;font-weight:800;opacity:.65}
.label{font-weight:800}
.midi-table input[type="range"],.row input[type="range"]{width:100%}
.midi-table select{
  width:100%;min-height:34px;border-radius:6px;
  border:1px solid #64748b;
  background:#111827;
  color:#f8fafc;
  padding:4px 8px;
  color-scheme:dark;
  font-weight:650;
}
.midi-table select:focus{
  outline:2px solid #60a5fa;
  outline-offset:1px;
}
.midi-table select option{
  background:#111827;
  color:#f8fafc;
}
.vol-audio{accent-color:#4da3ff}
.vol-vocal{accent-color:#9b59b6}
.vol-chords{accent-color:#e67e22}
.vol-drums{accent-color:#2ecc71}
.hint{margin-top:12px;font-size:11px;opacity:.68}
@media(max-width:700px){
  .row,.midi-table{grid-template-columns:1fr}
  .head{display:none}
}
"""

_JS = r"""
export default function(component) {
  const data = component.data || {};
  const root = component.parentElement;

  const audio = root.querySelector(".song");
  const audioOn = root.querySelector(".audio-on");
  const audioVolume = root.querySelector(".audio-volume");
  const audioValue = root.querySelector(".audio-value");
  const initButton = root.querySelector(".init");
  const state = root.querySelector(".state");

  const vocalOn = root.querySelector(".vocal-on");
  const chordsOn = root.querySelector(".chords-on");
  const drumsOn = root.querySelector(".drums-on");
  const vocalVolume = root.querySelector(".vocal-volume");
  const chordsVolume = root.querySelector(".chords-volume");
  const drumsVolume = root.querySelector(".drums-volume");
  const vocalProgram = root.querySelector(".vocal-program");
  const chordsProgram = root.querySelector(".chords-program");
  const drumsProgram = root.querySelector(".drums-program");
  const trackStatus = root.querySelector(".track-status");

  const availableTracks = new Set(Array.isArray(data.available_tracks) ? data.available_tracks : []);
  const pendingTracks = new Set(Array.isArray(data.pending_tracks) ? data.pending_tracks : []);

  audio.src = String(data.audio_url || "");
  audio.volume = Number(audioVolume.value);

  const tracks = data.tracks || {};

  function applyAvailability() {
    const controls = {
      vocal: [vocalOn, vocalVolume],
      chords: [chordsOn, chordsVolume],
      drums: [drumsOn, drumsVolume],
    };
    for (const [name, items] of Object.entries(controls)) {
      const available = availableTracks.has(name);
      items.forEach((item) => { item.disabled = !available; });
      if (!available) items[0].checked = false;
    }
    if (trackStatus) {
      const ready = Array.from(availableTracks).join(", ") || "aucune";
      const pending = Array.from(pendingTracks).join(", ");
      trackStatus.textContent = pending
        ? ("Pistes prêtes : " + ready + " · en cours : " + pending)
        : ("Pistes prêtes : " + ready);
    }
  }
  applyAvailability();

  const allEvents = []
    .concat((tracks.vocal || []).map(e => ({...e, track:"vocal"})))
    .concat((tracks.chords || []).map(e => ({...e, track:"chords"})))
    .concat((tracks.drums || []).map(e => ({...e, track:"drums"})))
    .sort((a,b) => Number(a.time||0)-Number(b.time||0));

  let context = null;
  let synth = null;
  let soundFontId = null;
  let node = null;
  let ready = false;
  let initializing = null;
  let scheduler = null;
  let cursor = 0;
  let lastTime = 0;
  let disposed = false;

  window.__ezscoreMidiScripts = window.__ezscoreMidiScripts || {};
  window.__ezscoreSoundFonts = window.__ezscoreSoundFonts || {};

  const melodicPrograms = [
    [0,"000 — Piano"],[4,"004 — Electric Piano"],[24,"024 — Nylon Guitar"],[25,"025 — Steel Guitar"],
    [27,"027 — Clean Guitar"],[28,"028 — Muted Guitar"],[32,"032 — Acoustic Bass"],[33,"033 — Finger Bass"],
    [40,"040 — Violin"],[41,"041 — Viola"],[42,"042 — Cello"],[48,"048 — Strings"],[52,"052 — Choir Aahs"],
    [53,"053 — Voice Oohs"],[54,"054 — Synth Voice"],[64,"064 — Soprano Sax"],[65,"065 — Alto Sax"],
    [66,"066 — Tenor Sax"],[67,"067 — Baritone Sax"],[73,"073 — Flute"],[80,"080 — Square Lead"],
    [81,"081 — Saw Lead"],[88,"088 — Fantasia"]
  ];
  const drumKits = [
    [0,"000 — Standard Kit"],[8,"008 — Room Kit"],[16,"016 — Power Kit"],[24,"024 — Electronic Kit"],
    [25,"025 — TR-808 Kit"],[32,"032 — Jazz Kit"],[40,"040 — Brush Kit"],[48,"048 — Orchestra Kit"]
  ];

  function fillSelect(node, entries, selected) {
    node.innerHTML = "";
    entries.forEach(([value,label]) => {
      const option = document.createElement("option");
      option.value = String(value);
      option.textContent = label;
      if (Number(value) === Number(selected)) option.selected = true;
      node.appendChild(option);
    });
  }
  fillSelect(vocalProgram, melodicPrograms, 53);
  fillSelect(chordsProgram, melodicPrograms, 27);
  fillSelect(drumsProgram, drumKits, 0);

  function trackEnabled(name) {
    if (name === "vocal") return Boolean(vocalOn.checked);
    if (name === "chords") return Boolean(chordsOn.checked);
    if (name === "drums") return Boolean(drumsOn.checked);
    return false;
  }

  function trackGain(name) {
    if (name === "vocal") return Number(vocalVolume.value);
    if (name === "chords") return Number(chordsVolume.value);
    if (name === "drums") return Number(drumsVolume.value);
    return 1.0;
  }

  function loadScript(url) {
    if (window.__ezscoreMidiScripts[url]) return window.__ezscoreMidiScripts[url];
    window.__ezscoreMidiScripts[url] = new Promise((resolve,reject) => {
      const script = document.createElement("script");
      script.src = url;
      script.async = true;
      script.onload = resolve;
      script.onerror = reject;
      document.head.appendChild(script);
    });
    return window.__ezscoreMidiScripts[url];
  }

  async function fetchSoundFont() {
    let lastError = null;
    for (const url of (data.soundfont_urls || [])) {
      try {
        if (!window.__ezscoreSoundFonts[url]) {
          window.__ezscoreSoundFonts[url] = fetch(url,{cache:"force-cache"})
            .then(r => {
              if (!r.ok) throw new Error("SoundFont HTTP " + r.status);
              return r.arrayBuffer();
            })
            .catch(err => {
              delete window.__ezscoreSoundFonts[url];
              throw err;
            });
        }
        return await window.__ezscoreSoundFonts[url];
      } catch (err) {
        lastError = err;
      }
    }
    throw lastError || new Error("SoundFont indisponible");
  }

  function lowerBound(time) {
    let low=0, high=allEvents.length;
    while(low<high){
      const mid=(low+high)>>1;
      if(Number(allEvents[mid].time||0)<time) low=mid+1;
      else high=mid;
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

  function setVolumes() {
    if (!synth || soundFontId === null) return;
    const values = {
      0: Math.max(0,Math.min(127,Math.round(trackGain("vocal")*84))),
      1: Math.max(0,Math.min(127,Math.round(trackGain("chords")*84))),
      9: Math.max(0,Math.min(127,Math.round(trackGain("drums")*84))),
    };
    for (const [ch,val] of Object.entries(values)) {
      try { synth.midiControl(Number(ch),7,Number(val)); } catch (_) {}
    }
  }

  function selectPrograms() {
    if (!synth || soundFontId === null) return;
    synth.midiProgramSelect(0, soundFontId, 0, Number(vocalProgram.value || 53));
    synth.midiProgramSelect(1, soundFontId, 0, Number(chordsProgram.value || 27));
    // General MIDI percussion kits live on bank 128, channel 10.
    synth.midiProgramSelect(9, soundFontId, 128, Number(drumsProgram.value || 0));
  }

  function resetAt(time) {
    silence();
    selectPrograms();
    setVolumes();
    cursor = lowerBound(Math.max(0,Number(time)-0.003));
    lastTime = Number(time);
  }

  function sendEvent(event) {
    if (!synth || !trackEnabled(event.track)) return;
    const ch = Number(event.channel || 0);

    if (event.kind === "program") {
      // Instrument selectors are authoritative in the editor player.
      return;
    }

    if (event.kind === "note_on") {
      synth.midiNoteOn(ch,Number(event.note),Number(event.velocity||0));
      return;
    }
    if (event.kind === "note_off") {
      synth.midiNoteOff(ch,Number(event.note));
    }
  }

  function pump() {
    if (!ready || audio.paused || audio.ended) return;
    const t = audio.currentTime;

    if (t + 0.04 < lastTime || Math.abs(t-lastTime) > 0.35) {
      resetAt(t);
    }
    lastTime = t;

    while(cursor < allEvents.length && Number(allEvents[cursor].time||0) <= t + 0.008) {
      const event = allEvents[cursor++];
      if (Number(event.time||0) >= t - 0.035 || event.kind === "program") {
        sendEvent(event);
      }
    }
  }

  function startScheduler() {
    if (scheduler !== null) clearInterval(scheduler);
    scheduler = window.setInterval(pump,8);
    pump();
  }

  function stopScheduler() {
    if (scheduler !== null) {
      clearInterval(scheduler);
      scheduler = null;
    }
  }

  async function initialize() {
    if (ready) {
      if (context && context.state === "suspended") await context.resume();
      return;
    }
    if (initializing) return initializing;

    initializing = (async () => {
      initButton.disabled = true;
      state.textContent = "Chargement FluidSynth…";
      try {
        await loadScript(data.libfluid_url);
        await loadScript(data.jssynth_url);
        if (!window.JSSynth || !window.JSSynth.Synthesizer) {
          throw new Error("js-synthesizer indisponible");
        }
        await window.JSSynth.waitForReady();

        context = new (window.AudioContext || window.webkitAudioContext)({
          latencyHint:"interactive"
        });
        synth = new window.JSSynth.Synthesizer();
        synth.init(44100);

        const sf = await fetchSoundFont();
        soundFontId = synth.loadSFont(sf);

        node = synth.createAudioNode(context,8192);
        node.connect(context.destination);

        selectPrograms();
        setVolumes();
        ready = true;
        state.textContent = "Synthé MIDI prêt";
        initButton.textContent = "Synthé MIDI chargé";
        resetAt(audio.currentTime);
      } catch (err) {
        state.textContent = "Erreur synthé : " + (err?.message || String(err));
        initButton.disabled = false;
        initializing = null;
        throw err;
      }
    })();

    return initializing;
  }

  audio.addEventListener("play", async () => {
    try {
      await initialize();
      if (context.state === "suspended") await context.resume();
      resetAt(audio.currentTime);
      startScheduler();
    } catch (_) {
      audio.pause();
    }
  });
  audio.addEventListener("pause", () => {
    stopScheduler();
    silence();
  });
  audio.addEventListener("seeking", () => {
    if (ready) resetAt(audio.currentTime);
  });
  audio.addEventListener("ended", () => {
    stopScheduler();
    silence();
  });

  audioOn.addEventListener("change", () => {
    audio.muted = !audioOn.checked;
  });
  audioVolume.addEventListener("input", () => {
    audio.volume = Number(audioVolume.value);
    audioValue.textContent = Math.round(audio.volume*100) + "%";
  });

  for (const control of [vocalOn,chordsOn,drumsOn]) {
    control.addEventListener("change", () => {
      if (ready) {
        silence();
        resetAt(audio.currentTime);
      }
    });
  }
  for (const control of [vocalVolume,chordsVolume,drumsVolume]) {
    control.addEventListener("input", () => {
      if (ready) setVolumes();
    });
  }

  for (const control of [vocalProgram,chordsProgram,drumsProgram]) {
    control.addEventListener("change", () => {
      if (ready) {
        silence();
        selectPrograms();
        resetAt(audio.currentTime);
      }
    });
  }

  initButton.addEventListener("click", () => initialize().catch(() => {}));

  return function() {
    disposed = true;
    stopScheduler();
    silence();
    try { if (node) node.disconnect(); } catch (_) {}
    try { if (context) context.close(); } catch (_) {}
  };
}
"""

_COMPONENT = st.components.v2.component(
    "ezscore_stem_midi_sync_player",
    html=_HTML,
    css=_CSS,
    js=_JS,
    isolate_styles=True,
)


def render_stem_midi_sync_player(
    *,
    audio_path: Path,
    midi_metadata: dict[str, Any],
    key: str,
) -> None:
    suffix = str(Path(audio_path).suffix or ".mp3").lower()
    mime = {
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".ogg": "audio/ogg",
        ".m4a": "audio/mp4",
    }.get(suffix, "application/octet-stream")

    audio_url = register_media_url(
        Path(audio_path),
        coordinates=f"{key}:master-audio",
        mimetype=mime,
    )

    tracks = dict(midi_metadata.get("browser_events", {}) or {})
    if not tracks:
        raise RuntimeError(
            "Aucun événement MIDI navigateur disponible pour le lecteur synchronisé."
        )

    if not midi_metadata.get("available_tracks"):
        inferred = [
            name for name in ("vocal", "chords", "drums")
            if list(tracks.get(name, []) or [])
        ]
        midi_metadata = dict(midi_metadata)
        midi_metadata["available_tracks"] = inferred
        midi_metadata["pending_tracks"] = []

    _COMPONENT(
        data={
            "audio_url": audio_url,
            "tracks": tracks,
            "available_tracks": list(midi_metadata.get("available_tracks", []) or []),
            "pending_tracks": list(midi_metadata.get("pending_tracks", []) or []),
            "soundfont_urls": list(SOUNDFONT_FALLBACKS),
            "libfluid_url": LIBFLUID_URL,
            "jssynth_url": JSSYNTH_URL,
        },
        key=key,
        width="stretch",
        height=390,
    )
