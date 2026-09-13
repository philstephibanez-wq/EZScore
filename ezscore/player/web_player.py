"""MP3-only reading player for Grille and Paroles + accords views."""

from __future__ import annotations

import base64
import streamlit as st

from ezscore.player.cover import cover_payload
from ezscore.player.timeline import build_measure_timeline
from ezscore.guitar import get_voicing, load_show_diagrams, load_voicings, svg
from ezscore.transcription import extraire_mots


_HTML = """
<div class="ez-view-player">
  <div class="ez-player-identity">
    <img class="ez-player-cover" alt="">
    <div>
      <div class="ez-player-title"></div>
      <div class="ez-player-artist"></div>
    </div>
  </div>
  <audio class="ez-song" controls preload="metadata"></audio>

  <div class="ez-view-controls">
    <label>Vitesse
      <select class="ez-speed">
        <option value="0.5">0.5×</option>
        <option value="0.75">0.75×</option>
        <option value="0.9">0.9×</option>
        <option value="1" selected>1.0×</option>
        <option value="1.1">1.1×</option>
        <option value="1.25">1.25×</option>
        <option value="1.5">1.5×</option>
      </select>
    </label>
    <label class="ez-diagram-toggle">
      <input class="ez-show-diagrams" type="checkbox">
      Diagrammes guitare
    </label>
  </div>

  <div class="ez-measure-strip">
    <div class="ez-measure-track"></div>
  </div>

  <div class="ez-lyrics-strip">
    <div class="ez-lyrics-center"></div>
    <div class="ez-lyrics-track"></div>
  </div>
</div>
"""

_CSS = """
:host { display:block; width:100%; }
.ez-view-player {
  box-sizing:border-box;
  width:100%;
  padding:14px 16px;
  border:1px solid color-mix(in srgb,var(--st-text-color) 24%,transparent);
  border-radius:12px;
  background:color-mix(in srgb,var(--st-text-color) 4%,transparent);
  color:var(--st-text-color);
  font-family:var(--st-font);
}
.ez-player-identity{display:flex;align-items:center;gap:12px;margin-bottom:10px}
.ez-player-cover{display:none;width:76px;height:76px;border-radius:9px;object-fit:cover}
.ez-player-cover.has-cover{display:block}
.ez-player-title{font-size:19px;font-weight:800}
.ez-player-artist{font-size:13px;opacity:.72;margin-top:4px}
.ez-song{width:100%}

.ez-view-controls{
  display:flex;
  justify-content:flex-end;
  align-items:center;
  flex-wrap:wrap;
  gap:18px;
  margin:10px 0;
}
.ez-view-controls label{display:flex;align-items:center;gap:8px;font-size:13px;font-weight:700}
.ez-speed{min-height:38px;padding:4px 28px 4px 10px;border-radius:7px}
.ez-show-diagrams{width:18px;height:18px}

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
  min-height:190px;
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
.ez-measure-number {
  text-align:right;
  font-size:11px;
  font-weight:800;
  opacity:.48;
}
.ez-measure-diagram {
  display:flex;
  justify-content:center;
  min-height:0;
  margin-top:-3px;
}
.ez-measure-diagram:empty { display:none; }
.ez-measure-chord {
  text-align:center;
  font-size:34px;
  line-height:1.05;
  font-weight:900;
  min-height:38px;
  margin-top:4px;
}
.ez-measure-beats {
  display:grid;
  gap:8px;
  margin:14px auto 0;
}
.ez-beat-cell {
  display:flex;
  align-items:center;
  justify-content:center;
  min-width:0;
  min-height:42px;
  padding:3px 6px;
  border-radius:8px;
  border:1px solid rgba(150,160,175,.28);
  font-family:ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size:24px;
  font-weight:900;
  opacity:.58;
}
.ez-beat-cell.elapsed {
  opacity:.82;
  background:rgba(77,163,255,.08);
}
.ez-beat-cell.current {
  opacity:1;
  color:#fff;
  background:#2679d8;
  border-color:#69adff;
  box-shadow:0 0 0 2px rgba(77,163,255,.22);
}

.ez-lyrics-strip {
  position:relative;
  overflow:hidden;
  width:100%;
  height:76px;
  margin-top:8px;
  border-top:1px solid rgba(150,160,175,.22);
  border-bottom:1px solid rgba(150,160,175,.22);
  background:rgba(127,127,127,.035);
}
.ez-lyrics-center {
  position:absolute;
  top:0;
  bottom:0;
  left:50%;
  width:2px;
  background:rgba(77,163,255,.65);
  pointer-events:none;
  z-index:2;
}
.ez-lyrics-track {
  position:absolute;
  left:0;
  top:0;
  height:100%;
  display:flex;
  align-items:center;
  gap:14px;
  white-space:nowrap;
  will-change:transform;
}
.ez-lyric-word {
  display:inline-flex;
  align-items:center;
  min-height:38px;
  padding:5px 4px;
  font-size:22px;
  font-weight:650;
  opacity:.48;
  transition:opacity .10s, transform .10s, color .10s;
}
.ez-lyric-word.past{opacity:.30}
.ez-lyric-word.future{opacity:.65}
.ez-lyric-word.current{
  opacity:1;
  transform:scale(1.14);
  color:#69adff;
  font-weight:850;
}

@media(max-width:900px){
  .ez-measure-card{flex-basis:260px}
}
@media(max-width:640px){
  .ez-view-player{padding:10px}
  .ez-player-cover{width:58px;height:58px}
  .ez-view-controls{justify-content:space-between;gap:10px}
  .ez-measure-strip{min-height:225px}
  .ez-measure-track{gap:10px}
  .ez-measure-card{flex-basis:220px;min-height:175px;padding:9px}
  .ez-measure-chord{font-size:29px}
  .ez-beat-cell{font-size:21px;min-height:38px;padding:2px 4px}
  .ez-measure-diagram svg{width:96px;height:122px}
  .ez-lyrics-strip{height:68px}
  .ez-lyric-word{font-size:18px;gap:10px}
}
"""

_JS = r"""
export default function(component) {
  const data = component.data || {};
  const root = component.parentElement;
  const audio = root.querySelector(".ez-song");
  const speed = root.querySelector(".ez-speed");
  const showDiagramsControl = root.querySelector(".ez-show-diagrams");
  const strip = root.querySelector(".ez-measure-strip");
  const track = root.querySelector(".ez-measure-track");
  const lyricsStrip = root.querySelector(".ez-lyrics-strip");
  const lyricsTrack = root.querySelector(".ez-lyrics-track");
  const cover = root.querySelector(".ez-player-cover");
  const title = root.querySelector(".ez-player-title");
  const artist = root.querySelector(".ez-player-artist");
  const measures = Array.isArray(data.measures) ? data.measures : [];
  const words = Array.isArray(data.lyrics_words) ? data.lyrics_words : [];

  if (!audio || !strip || !track || !lyricsStrip || !lyricsTrack) return;

  audio.src = "data:" + data.mime + ";base64," + data.audio_base64;
  audio.preservesPitch = true;
  audio.webkitPreservesPitch = true;

  if (title) title.textContent = String(data.title || "");
  if (artist) artist.textContent = String(data.artist || "");
  if (cover && data.cover?.base64 && data.cover?.mime) {
    cover.src = "data:" + data.cover.mime + ";base64," + data.cover.base64;
    cover.classList.add("has-cover");
  }

  let showDiagrams = Boolean(data.show_diagrams);
  if (showDiagramsControl) showDiagramsControl.checked = showDiagrams;

  const cards = measures.map((measure) => {
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

    card.append(number, diagram, chord, beats);
    track.appendChild(card);
    return { card, diagram, chord, beatNodes };
  });

  const wordNodes = words.map((word) => {
    const node = document.createElement("span");
    node.className = "ez-lyric-word future";
    node.textContent = String(word.text || "").trim();
    lyricsTrack.appendChild(node);
    return node;
  });

  if (!words.length) lyricsStrip.style.display = "none";

  let raf = 0;
  let activeMeasure = -1;
  let activeBeat = -1;
  let activeWord = -1;

  function findMeasure(time) {
    if (!measures.length) return -1;
    let low = 0, high = measures.length - 1, answer = 0;
    while (low <= high) {
      const mid = (low + high) >> 1;
      if (Number(measures[mid].time) <= time) {
        answer = mid; low = mid + 1;
      } else {
        high = mid - 1;
      }
    }
    return answer;
  }

  function findBeat(measure, time) {
    const starts = Array.isArray(measure.beat_times) ? measure.beat_times : [];
    if (!starts.length) return 0;
    let answer = 0;
    for (let i = 0; i < starts.length; i += 1) {
      if (Number(starts[i]) <= time) answer = i;
      else break;
    }
    return answer;
  }

  function findWord(time) {
    if (!words.length) return -1;
    let low = 0, high = words.length - 1, answer = 0;
    while (low <= high) {
      const mid = (low + high) >> 1;
      if (Number(words[mid].start || 0) <= time) {
        answer = mid; low = mid + 1;
      } else {
        high = mid - 1;
      }
    }
    return answer;
  }

  function centerMeasure(index) {
    const card = cards[index]?.card;
    if (!card) return;
    const stripWidth = strip.clientWidth;
    const cardWidth = card.offsetWidth;
    const gap = parseFloat(getComputedStyle(track).gap || "0");
    const offset = index * (cardWidth + gap) - (stripWidth - cardWidth) / 2;
    track.style.transform = "translateX(" + (-offset) + "px)";
  }

  function renderLyrics(time) {
    const index = findWord(time);
    if (index < 0 || !wordNodes[index]) return;

    if (index !== activeWord) {
      activeWord = index;
      wordNodes.forEach((node, i) => {
        node.classList.toggle("current", i === index);
        node.classList.toggle("past", i < index);
        node.classList.toggle("future", i > index);
      });
    }

    const current = wordNodes[index];
    const next = wordNodes[index + 1];
    const currentCenter = current.offsetLeft + current.offsetWidth / 2;
    let targetCenter = currentCenter;
    if (next) {
      const start = Number(words[index].start || 0);
      const nextStart = Math.max(start + .04, Number(words[index + 1].start || start + .5));
      const progress = Math.max(0, Math.min(1, (time - start) / (nextStart - start)));
      const nextCenter = next.offsetLeft + next.offsetWidth / 2;
      targetCenter = currentCenter + (nextCenter - currentCenter) * progress;
    }
    lyricsTrack.style.transform =
      "translateX(" + (lyricsStrip.clientWidth / 2 - targetCenter) + "px)";
  }

  function refreshActiveDiagram() {
    if (activeMeasure < 0 || !cards[activeMeasure]) return;
    const measure = measures[activeMeasure];
    const active = cards[activeMeasure];
    const beatIndex = Math.max(0, activeBeat);
    const markup = showDiagrams
      ? String(measure.beat_diagrams?.[beatIndex] || "")
      : "";
    if (active.diagram.dataset.value !== markup) {
      active.diagram.dataset.value = markup;
      active.diagram.innerHTML = markup;
    }
  }

  function render() {
    const time = Number(audio.currentTime || 0);
    const measureIndex = findMeasure(time);

    if (measureIndex >= 0) {
      const measure = measures[measureIndex];
      const beatIndex = findBeat(measure, time);

      if (measureIndex !== activeMeasure) {
        activeMeasure = measureIndex;
        activeBeat = -1;
        cards.forEach((entry, index) => {
          entry.card.classList.toggle("active", index === measureIndex);
          entry.card.classList.toggle("past", index < measureIndex);
          entry.card.classList.toggle("future", index > measureIndex);
          if (index !== measureIndex && entry.diagram) {
            entry.diagram.dataset.value = "";
            entry.diagram.innerHTML = "";
          }
        });
        centerMeasure(measureIndex);
      }

      if (beatIndex !== activeBeat) {
        activeBeat = beatIndex;
        const active = cards[measureIndex];
        active.beatNodes.forEach((node, index) => {
          node.classList.toggle("elapsed", index < beatIndex);
          node.classList.toggle("current", index === beatIndex);
        });

        const chord = String(
          measure.beat_chords?.[beatIndex] || measure.primary_chord || "—"
        );
        active.chord.textContent = chord || "—";
        refreshActiveDiagram();
      }
    }

    renderLyrics(time);

    if (!audio.paused && !audio.ended) raf = requestAnimationFrame(render);
  }

  function onPlay(){ cancelAnimationFrame(raf); render(); }
  function onPause(){ cancelAnimationFrame(raf); render(); }
  function onSeek(){ render(); }
  function onResize(){
    if (activeMeasure >= 0) centerMeasure(activeMeasure);
    renderLyrics(Number(audio.currentTime || 0));
  }
  function onSpeed(){
    const value = Number(speed.value || 1);
    audio.playbackRate = value;
    audio.defaultPlaybackRate = value;
    audio.preservesPitch = true;
    audio.webkitPreservesPitch = true;
  }
  function onDiagrams(){
    showDiagrams = Boolean(showDiagramsControl?.checked);
    refreshActiveDiagram();
  }

  speed.addEventListener("change", onSpeed);
  if (showDiagramsControl) showDiagramsControl.addEventListener("change", onDiagrams);
  audio.addEventListener("play", onPlay);
  audio.addEventListener("pause", onPause);
  audio.addEventListener("seeked", onSeek);
  audio.addEventListener("timeupdate", onSeek);
  window.addEventListener("resize", onResize);

  onSpeed();
  render();

  return function() {
    cancelAnimationFrame(raf);
    speed.removeEventListener("change", onSpeed);
    if (showDiagramsControl) showDiagramsControl.removeEventListener("change", onDiagrams);
    audio.removeEventListener("play", onPlay);
    audio.removeEventListener("pause", onPause);
    audio.removeEventListener("seeked", onSeek);
    audio.removeEventListener("timeupdate", onSeek);
    window.removeEventListener("resize", onResize);
  };
}
"""

_COMPONENT = st.components.v2.component(
    "ezscore.view_player_r25",
    html=_HTML,
    css=_CSS,
    js=_JS,
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


def render_song_view_player(
    *,
    audio_bytes: bytes,
    extension: str,
    beats,
    beats_per_measure: int,
    resultat,
    audio_hash: str,
    title: str,
    artist: str,
    cover_path,
    key: str,
) -> None:
    words = extraire_mots(resultat)
    selections = load_voicings(audio_hash)
    show_diagrams = load_show_diagrams(audio_hash)

    symbols = []
    current = ""
    for beat in beats or []:
        raw = str(beat.get("accord", "") or "").strip()
        if raw == ".":
            current = ""
        elif raw != "-" and raw:
            current = raw
        if current and current not in symbols:
            symbols.append(current)

    diagram_map = {}
    for symbol in symbols:
        voicing = get_voicing(symbol, selections.get(symbol))
        if voicing is not None:
            diagram_map[symbol] = svg(symbol, voicing, width=112, height=142)

    measures = build_measure_timeline(
        beats=beats,
        lyrics_words=words,
        beats_per_measure=beats_per_measure,
        chord_diagrams=diagram_map,
    )

    _COMPONENT(
        data={
            "audio_base64": base64.b64encode(audio_bytes).decode("ascii"),
            "mime": _audio_mime(extension),
            "measures": measures,
            "lyrics_words": words,
            "show_diagrams": bool(show_diagrams),
            "cover": cover_payload(cover_path),
            "title": str(title or ""),
            "artist": str(artist or ""),
        },
        key=key,
        width="stretch",
        height=650,
    )
