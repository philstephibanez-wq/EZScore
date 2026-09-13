"""MP3-only reading player for Grille and Paroles + accords views."""

from __future__ import annotations

import base64
import streamlit as st

from ezscore.player.ribbon import RIBBON_CSS
from ezscore.player.cover import cover_payload
from ezscore.player.timeline import build_player_timeline
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
  </div>
  <div class="ez-current">
    <div class="ez-current-diagram"></div>
    <div class="ez-current-chord">—</div>
    <div class="ez-current-beat"></div>
  </div>
  <div class="ez-ribbon">
    <div class="ez-ribbon-center"></div>
    <div class="ez-ribbon-track"></div>
  </div>
</div>
"""

_CSS = """
:host { display:block; width:100%; }
.ez-view-player {
  box-sizing:border-box; width:100%; padding:14px 16px;
  border:1px solid color-mix(in srgb,var(--st-text-color) 24%,transparent);
  border-radius:12px; background:color-mix(in srgb,var(--st-text-color) 4%,transparent);
  color:var(--st-text-color); font-family:var(--st-font);
}
.ez-player-identity{display:flex;align-items:center;gap:12px;margin-bottom:10px}
.ez-player-cover{display:none;width:76px;height:76px;border-radius:9px;object-fit:cover}
.ez-player-cover.has-cover{display:block}
.ez-player-title{font-size:19px;font-weight:800}.ez-player-artist{font-size:13px;opacity:.72;margin-top:4px}
.ez-song{width:100%}
.ez-view-controls{display:flex;justify-content:flex-end;margin:10px 0}
.ez-view-controls label{display:flex;align-items:center;gap:8px;font-size:13px;font-weight:700}
.ez-speed{min-height:38px;padding:4px 28px 4px 10px;border-radius:7px}
.ez-current{text-align:center;min-height:58px;margin:4px 0 2px}
.ez-current-diagram{display:flex;justify-content:center;min-height:0}
.ez-current-diagram:empty{display:none}
.ez-current-chord{font-size:34px;font-weight:900;line-height:1.05}
.ez-current-beat{font-size:13px;font-weight:800;opacity:.78;margin-top:4px}
.ez-ribbon{height:158px}
.ez-ribbon-track{top:11px}
.ez-ribbon-item{min-width:150px;padding:9px 12px;border-radius:10px;transition:opacity .12s,background .12s,transform .12s}
.ez-ribbon-item.active{background:rgba(77,163,255,.22);outline:2px solid rgba(77,163,255,.95);transform:scale(1.04);opacity:1}
.ez-ribbon-item.past{opacity:.45}.ez-ribbon-item.future{opacity:.78}
.ez-ribbon-beat{font-size:12px;font-weight:900;opacity:.72;margin-bottom:5px}
.ez-ribbon-chord{font-size:25px;min-height:31px}
.ez-ribbon-lyric{font-size:15px;line-height:1.2;white-space:normal;max-width:145px;min-height:38px}
@media(max-width:640px){
 .ez-view-player{padding:10px}.ez-player-cover{width:58px;height:58px}
 .ez-current-chord{font-size:29px}.ez-ribbon{height:145px}
 .ez-ribbon-item{min-width:118px;padding:7px 8px}
 .ez-ribbon-lyric{max-width:112px;font-size:13px}
}
""" + RIBBON_CSS

_JS = r"""
export default function(component) {
  const data = component.data || {};
  const root = component.parentElement;
  const audio = root.querySelector(".ez-song");
  const speed = root.querySelector(".ez-speed");
  const track = root.querySelector(".ez-ribbon-track");
  const currentChord = root.querySelector(".ez-current-chord");
  const currentBeat = root.querySelector(".ez-current-beat");
  const currentDiagram = root.querySelector(".ez-current-diagram");
  const cover = root.querySelector(".ez-player-cover");
  const title = root.querySelector(".ez-player-title");
  const artist = root.querySelector(".ez-player-artist");
  const items = Array.isArray(data.timeline) ? data.timeline : [];
  if (!audio || !track) return;

  audio.src = "data:" + data.mime + ";base64," + data.audio_base64;
  audio.preservesPitch = true;
  audio.webkitPreservesPitch = true;
  if (title) title.textContent = String(data.title || "");
  if (artist) artist.textContent = String(data.artist || "");
  if (cover && data.cover?.base64 && data.cover?.mime) {
    cover.src = "data:" + data.cover.mime + ";base64," + data.cover.base64;
    cover.classList.add("has-cover");
  }

  const nodes = items.map((item) => {
    const el = document.createElement("div");
    el.className = "ez-ribbon-item future";
    const beat = document.createElement("div");
    beat.className = "ez-ribbon-beat";
    beat.textContent = "Beat " + item.beat;
    const chord = document.createElement("div");
    chord.className = "ez-ribbon-chord";
    chord.textContent = item.chord_change ? (item.chord || "·") : "·";
    const lyric = document.createElement("div");
    lyric.className = "ez-ribbon-lyric";
    lyric.textContent = item.lyric || "";
    el.append(beat, chord, lyric);
    track.appendChild(el);
    return el;
  });

  let raf = 0;
  let activeIndex = -1;

  function findIndex(time) {
    if (!items.length) return -1;
    let low = 0, high = items.length - 1, answer = 0;
    while (low <= high) {
      const mid = (low + high) >> 1;
      if (Number(items[mid].time) <= time) { answer = mid; low = mid + 1; }
      else high = mid - 1;
    }
    return answer;
  }

  function render() {
    const time = Number(audio.currentTime || 0);
    const index = findIndex(time);
    if (index >= 0) {
      const item = items[index];
      const start = Number(item.time || 0);
      const end = Math.max(start + .02, Number(item.end || start + .5));
      const progress = Math.max(0, Math.min(1, (time - start) / (end - start)));
      const width = window.innerWidth <= 640 ? 118 : 150;
      const offset = (index + progress) * width;
      track.style.transform = "translateX(" + (-offset - width / 2) + "px)";

      if (index !== activeIndex) {
        activeIndex = index;
        nodes.forEach((node, i) => {
          node.classList.toggle("active", i === index);
          node.classList.toggle("past", i < index);
          node.classList.toggle("future", i > index);
        });
        if (currentChord) currentChord.textContent = item.chord || "—";
        if (currentBeat) currentBeat.textContent = "Mesure " + item.measure + " · beat " + item.beat;
        if (currentDiagram) currentDiagram.innerHTML = data.show_diagrams ? String(item.diagram || "") : "";
      }
    }
    if (!audio.paused && !audio.ended) raf = requestAnimationFrame(render);
  }

  function onPlay(){ cancelAnimationFrame(raf); render(); }
  function onPause(){ cancelAnimationFrame(raf); render(); }
  function onSeek(){ render(); }
  function onSpeed(){
    const value = Number(speed.value || 1);
    audio.playbackRate = value;
    audio.defaultPlaybackRate = value;
    audio.preservesPitch = true;
    audio.webkitPreservesPitch = true;
  }

  speed.addEventListener("change", onSpeed);
  audio.addEventListener("play", onPlay);
  audio.addEventListener("pause", onPause);
  audio.addEventListener("seeked", onSeek);
  audio.addEventListener("timeupdate", onSeek);
  onSpeed();
  render();

  return function() {
    cancelAnimationFrame(raf);
    speed.removeEventListener("change", onSpeed);
    audio.removeEventListener("play", onPlay);
    audio.removeEventListener("pause", onPause);
    audio.removeEventListener("seeked", onSeek);
    audio.removeEventListener("timeupdate", onSeek);
  };
}
"""

_COMPONENT = st.components.v2.component(
    "ezscore.view_player_r23",
    html=_HTML,
    css=_CSS,
    js=_JS,
    isolate_styles=True,
)


def _audio_mime(extension: str) -> str:
    return {
        ".mp3": "audio/mpeg", ".wav": "audio/wav", ".ogg": "audio/ogg",
        ".m4a": "audio/mp4", ".aac": "audio/aac", ".flac": "audio/flac",
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
            diagram_map[symbol] = svg(symbol, voicing, width=118, height=150)

    timeline = build_player_timeline(
        beats=beats,
        lyrics_words=words,
        beats_per_measure=beats_per_measure,
        chord_diagrams=diagram_map,
    )

    _COMPONENT(
        data={
            "audio_base64": base64.b64encode(audio_bytes).decode("ascii"),
            "mime": _audio_mime(extension),
            "timeline": timeline,
            "show_diagrams": bool(show_diagrams),
            "cover": cover_payload(cover_path),
            "title": str(title or ""),
            "artist": str(artist or ""),
        },
        key=key,
        width="stretch",
        height=560 if show_diagrams else 390,
    )
