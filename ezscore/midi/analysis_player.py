"""Compact MP3 + MIDI player dedicated to the Analyse view."""

from __future__ import annotations

import base64

import streamlit as st

from ezscore.midi.web_player import (
    DEFAULT_SOUNDFONT_URL,
    _SOUND_FONT_FALLBACK_URLS,
    _LIBFLUID_URL,
    _JS_SYNTH_URL,
    _PLAYER_JS,
    _audio_mime,
)


_COMPACT_HTML = """
<div class="ez-midi-player ez-analysis-player">
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

  <div class="ez-midi-actions">
    <button class="ez-midi-init" type="button">Charger le synthé MIDI</button>
  </div>

  <div class="ez-midi-state">Synthé non chargé</div>

  <!-- Required by the shared player JS, intentionally hidden in Analyse. -->
  <label class="ez-midi-diagram-toggle ez-analysis-hidden">
    <input class="ez-midi-show-diagrams" type="checkbox">
  </label>
  <div class="ez-measure-strip ez-analysis-hidden">
    <div class="ez-measure-track"></div>
  </div>
  <div class="ez-lyrics-strip ez-analysis-hidden">
    <div class="ez-lyrics-center"></div>
    <div class="ez-lyrics-track"></div>
  </div>

  <div class="ez-midi-hint">
    MP3 maître · FluidSynth + SoundFont intégrés au navigateur ·
    aucune sortie MIDI système requise.
  </div>
</div>
"""


_COMPACT_CSS = """
:host {
  display:block;
  width:100%;
}
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
.ez-player-identity {
  display:flex;
  align-items:center;
  gap:12px;
  margin-bottom:10px;
}
.ez-player-cover {
  width:58px;
  height:58px;
  object-fit:cover;
  border-radius:8px;
  display:none;
}
.ez-player-cover.has-cover { display:block; }
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
.ez-midi-song { width:100%; }

.ez-midi-controls {
  display:grid;
  grid-template-columns:1fr 1fr;
  gap:12px;
  margin-top:10px;
}
.ez-midi-controls label {
  display:flex;
  flex-direction:column;
  gap:4px;
  font-size:12px;
}
.ez-midi-controls input { width:100%; }

.ez-midi-actions {
  display:flex;
  align-items:center;
  gap:12px;
  margin-top:9px;
}
.ez-midi-init {
  min-height:34px;
  padding:5px 10px;
  border-radius:7px;
  border:1px solid color-mix(in srgb, var(--st-text-color) 35%, transparent);
  background:color-mix(in srgb, var(--st-text-color) 8%, transparent);
  color:var(--st-text-color);
  cursor:pointer;
}
.ez-midi-init:disabled { opacity:.65; cursor:wait; }

.ez-midi-state {
  margin-top:8px;
  font-size:12px;
  opacity:.88;
}
.ez-midi-hint {
  margin-top:10px;
  font-size:11px;
  opacity:.68;
}

.ez-analysis-hidden {
  display:none !important;
}

@media(max-width:640px) {
  .ez-analysis-player { padding:10px; }
  .ez-midi-controls { grid-template-columns:1fr; }
}
"""


_ANALYSIS_MIDI_COMPONENT = st.components.v2.component(
    "ezscore.midi_analysis_player",
    html=_COMPACT_HTML,
    css=_COMPACT_CSS,
    js=_PLAYER_JS,
    isolate_styles=True,
)


def render_analysis_midi_player(
    *,
    audio_bytes: bytes,
    extension: str,
    midi_events,
    instrument_label: str,
    program: int,
    title: str = "",
    artist: str = "",
    soundfont_url: str = DEFAULT_SOUNDFONT_URL,
    key: str | None = None,
):
    """Render a compact two-volume MP3 + MIDI player for Analyse."""
    if not midi_events:
        return

    soundfont_urls = [str(soundfont_url)]
    for fallback in _SOUND_FONT_FALLBACK_URLS:
        if fallback not in soundfont_urls:
            soundfont_urls.append(fallback)

    _ANALYSIS_MIDI_COMPONENT(
        data={
            "audio_base64": base64.b64encode(audio_bytes).decode("ascii"),
            "mime": _audio_mime(extension),
            "midi_events": list(midi_events),
            "instrument_label": str(instrument_label),
            "program": int(program),
            "lyrics_words": [],
            "player_measures": [],
            "chord_diagrams": {},
            "show_diagrams": False,
            "cover": {},
            "title": str(title or ""),
            "artist": str(artist or ""),
            "soundfont_url": str(soundfont_url),
            "soundfont_urls": soundfont_urls,
            "libfluid_url": _LIBFLUID_URL,
            "jssynth_url": _JS_SYNTH_URL,
        },
        key=key,
        width="stretch",
        height=285,
    )
