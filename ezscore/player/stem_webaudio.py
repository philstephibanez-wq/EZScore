from __future__ import annotations

import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import streamlit as st

from ezscore.player.media_url import register_media_url

from ezscore.analysis.stems import STEM_NAMES


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def _preview_target(path: Path, preview_dir: Path) -> Path:
    preview_dir.mkdir(parents=True, exist_ok=True)
    return preview_dir / f"{path.stem}.browser64.mp3"


def _preview_is_current(source: Path, target: Path) -> bool:
    return (
        target.is_file()
        and target.stat().st_size > 0
        and target.stat().st_mtime_ns >= source.stat().st_mtime_ns
    )


def make_browser_preview(path: Path, preview_dir: Path) -> Path:
    """Build one compact MP3 copy used only by the browser mixer."""
    target = _preview_target(path, preview_dir)

    if _preview_is_current(path, target):
        return target

    if not ffmpeg_available():
        raise RuntimeError(
            "FFmpeg est requis pour créer les copies MP3 légères du lecteur."
        )

    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(path),
        "-vn",
        "-map_metadata",
        "-1",
        "-codec:a",
        "libmp3lame",
        "-b:a",
        "64k",
        "-ar",
        "44100",
        str(target),
    ]
    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    if proc.returncode != 0 or not target.is_file():
        raise RuntimeError(
            "Impossible de créer la pré-écoute MP3 pour "
            f"{path.name}:\n{proc.stdout or ''}"
        )
    return target


def prepare_browser_previews(
    source: Path,
    stems: dict[str, Path],
    preview_dir: Path,
) -> dict[str, Path]:
    """Prepare original + stems browser previews in parallel."""
    preview_dir.mkdir(parents=True, exist_ok=True)
    inputs = {"original": source, **stems}

    result: dict[str, Path] = {}
    pending: dict[str, Path] = {}

    for name, path in inputs.items():
        target = _preview_target(path, preview_dir)
        if _preview_is_current(path, target):
            result[name] = target
        else:
            pending[name] = path

    if not pending:
        return result

    status = st.status(
        f"Préparation du lecteur : {len(pending)} piste(s) à compresser…",
        expanded=True,
    )
    progress = st.progress(0.0)
    done = 0

    workers = min(4, max(1, len(pending)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(make_browser_preview, path, preview_dir): name
            for name, path in pending.items()
        }
        for future in as_completed(futures):
            name = futures[future]
            result[name] = future.result()
            done += 1
            progress.progress(done / len(pending))
            status.write(f"✓ {name}")

    progress.empty()
    status.update(
        label="Préparation du lecteur terminée.",
        state="complete",
        expanded=False,
    )
    return result


_PLAYER_HTML = """
<div class="stem-player">
  <div class="transport">
    <button class="play" type="button">▶ Lecture</button>
    <button class="pause" type="button">⏸ Pause</button>
    <button class="stop" type="button">⏹ Stop</button>
    <span class="time">0:00 / 0:00</span>
  </div>

  <input class="seek" type="range" min="0" max="1" step="0.001" value="0">

  <div class="mixer-head">
    <div>Piste</div><div>ON</div><div>Volume</div>
    <div>Graves</div><div>Médiums</div><div>Aigus</div><div></div>
  </div>
  <div class="tracks"></div>

  <div class="master-row">
    <div class="master-name">Master</div>
    <div class="master-value">100%</div>
    <input class="master-volume master-control" type="range" min="0" max="1.25" step="0.01" value="1">
  </div>

  <div class="lyrics-wrap">
    <div class="lyrics-title">Paroles synchronisées</div>
    <div class="lyrics-strip"><div class="lyrics-track"></div></div>
  </div>

  <div class="hint">
    WebAudio : crossover 3 bandes · compensation de niveau · réglages en temps réel.
  </div>
</div>
"""

_PLAYER_CSS = """
:host { display:block; width:100%; }
.stem-player {
  box-sizing:border-box; width:100%;
  border:1px solid color-mix(in srgb, var(--st-text-color) 25%, transparent);
  border-radius:10px; padding:12px;
  background:color-mix(in srgb, var(--st-text-color) 4%, transparent);
  color:var(--st-text-color); font-family:var(--st-font);
}
.transport { display:flex; align-items:center; gap:8px; flex-wrap:wrap; }
.transport button, .eq-reset {
  min-height:30px; border-radius:7px;
  border:1px solid color-mix(in srgb, var(--st-text-color) 35%, transparent);
  background:color-mix(in srgb, var(--st-text-color) 8%, transparent);
  color:var(--st-text-color); cursor:pointer; padding:4px 8px;
}
.time { margin-left:auto; font-variant-numeric:tabular-nums; font-size:12px; opacity:.75; }
.seek { width:100%; margin:10px 0 14px; }

.mixer-head, .track {
  display:grid;
  grid-template-columns:minmax(82px,1.2fr) 52px minmax(110px,1.3fr)
                        minmax(90px,1fr) minmax(90px,1fr) minmax(90px,1fr) 64px;
  gap:8px; align-items:center;
}
.mixer-head { font-size:11px; font-weight:800; opacity:.65; padding:0 4px 5px; }
.tracks { display:grid; gap:3px; }
.track {
  padding:5px 4px;
  border-top:1px solid color-mix(in srgb, var(--st-text-color) 12%, transparent);
}
.track-name { font-weight:800; }
.track-toggle { display:flex; align-items:center; gap:5px; font-size:11px; }

.control-cell { display:grid; grid-template-columns:1fr auto; gap:5px; align-items:center; }
.control-cell input[type="range"] { width:100%; min-width:0; }
.volume-control input[type="range"],
.master-control {
  accent-color:#4da3ff;
}
.low-control input[type="range"] {
  accent-color:#e67e22;
}
.mid-control input[type="range"] {
  accent-color:#9b59b6;
}
.high-control input[type="range"] {
  accent-color:#2ecc71;
}
.control-value {
  width:42px; text-align:right; font-size:10px; opacity:.72;
  font-variant-numeric:tabular-nums;
}
.eq-reset { font-size:10px; }

.master-row {
  display:grid; grid-template-columns:82px 48px 1fr;
  gap:8px; align-items:center; margin-top:12px; padding-top:10px;
  border-top:1px solid color-mix(in srgb, var(--st-text-color) 18%, transparent);
}
.master-name { font-weight:900; }
.master-value { font-size:11px; opacity:.75; font-variant-numeric:tabular-nums; }
.master-volume { width:100%; }

.lyrics-wrap {
  margin-top:14px; padding-top:10px;
  border-top:1px solid color-mix(in srgb, var(--st-text-color) 18%, transparent);
}
.lyrics-title { font-size:12px; font-weight:700; opacity:.8; margin-bottom:6px; }
.lyrics-strip {
  position:relative; overflow:hidden; min-height:62px; border-radius:8px;
  background:color-mix(in srgb, var(--st-text-color) 5%, transparent);
}
.lyrics-track {
  position:absolute; left:50%; top:50%; transform:translate(0,-50%);
  white-space:nowrap; transition:transform 80ms linear;
}
.lyric-word {
  display:inline-block; margin:0 5px; font-size:18px; opacity:.30;
  transition:opacity 80ms linear, transform 80ms linear;
}
.lyric-word.past { opacity:.48; }
.lyric-word.current { opacity:1; font-weight:800; transform:scale(1.08); }
.hint { margin-top:10px; font-size:11px; opacity:.68; }

@media(max-width:950px) {
  .mixer-head { display:none; }
  .track { grid-template-columns:1fr 58px; }
  .track-name { grid-column:1; }
  .track-toggle { grid-column:2; justify-self:end; }
  .control-cell, .eq-reset { grid-column:1 / -1; }
  .eq-reset { justify-self:start; }
}
"""

_PLAYER_JS = r"""
export default function(component) {
  const data = component.data || {};
  const root = component.parentElement;

  const playButton = root.querySelector(".play");
  const pauseButton = root.querySelector(".pause");
  const stopButton = root.querySelector(".stop");
  const seek = root.querySelector(".seek");
  const timeLabel = root.querySelector(".time");
  const tracksNode = root.querySelector(".tracks");
  const masterVolume = root.querySelector(".master-volume");
  const masterValue = root.querySelector(".master-value");
  const lyricsWrap = root.querySelector(".lyrics-wrap");
  const lyricsStrip = root.querySelector(".lyrics-strip");
  const lyricsTrack = root.querySelector(".lyrics-track");

  const defs = Array.isArray(data.tracks) ? data.tracks : [];
  const words = Array.isArray(data.words) ? data.words : [];

  // Authoritative UI state exists before any AudioContext/node creation.
  const trackState = defs.map((track) => ({
    enabled: Boolean(track.enabled),
    volume: Number(track.volume ?? 0.8),
    low: Number(track.low ?? 0),
    mid: Number(track.mid ?? 0),
    high: Number(track.high ?? 0),
  }));
  let masterState = 1.0;

  let context = null;
  let decoded = [];
  let trackNodes = [];
  let masterGain = null;
  let sources = [];
  let ready = false;
  let playing = false;
  let disposed = false;
  let position = 0;
  let startedAtContextTime = 0;
  let duration = 0;
  let raf = null;
  let activeWordIndex = -1;

  function fmt(seconds) {
    seconds = Math.max(0, Number(seconds) || 0);
    const m = Math.floor(seconds / 60);
    const sec = Math.floor(seconds % 60);
    return m + ":" + String(sec).padStart(2, "0");
  }

  function currentTime() {
    if (!playing || !context) return position;
    return Math.max(0, Math.min(duration, position + (context.currentTime - startedAtContextTime)));
  }

  function dbToLinear(db) {
    return Math.pow(10, Number(db || 0) / 20);
  }

  function compensationFor(state) {
    const avg = (
      dbToLinear(state.low) +
      dbToLinear(state.mid) +
      dbToLinear(state.high)
    ) / 3;
    if (!Number.isFinite(avg) || avg <= 0.0001) return 1.0;
    return Math.max(0.72, Math.min(1.25, 1 / avg));
  }

  function applyTrackState(index, smooth = true) {
    if (!ready || !trackNodes[index] || !context) return;
    const state = trackState[index];
    const nodes = trackNodes[index];
    const now = context.currentTime;

    const enabledGain = state.enabled ? state.volume : 0;
    const comp = compensationFor(state);

    const setValue = (param, value) => {
      if (smooth) param.setTargetAtTime(value, now, 0.015);
      else param.value = value;
    };

    setValue(nodes.lowGain.gain, dbToLinear(state.low));
    setValue(nodes.midGain.gain, dbToLinear(state.mid));
    setValue(nodes.highGain.gain, dbToLinear(state.high));
    setValue(nodes.trackGain.gain, enabledGain * comp);
  }

  function applyMasterState(smooth = true) {
    if (!ready || !masterGain || !context) return;
    const now = context.currentTime;
    if (smooth) masterGain.gain.setTargetAtTime(masterState, now, 0.015);
    else masterGain.gain.value = masterState;
  }

  async function ensureReady() {
    if (ready) {
      if (context.state === "suspended") await context.resume();
      return;
    }

    playButton.disabled = true;
    playButton.textContent = "Chargement audio…";

    context = new (window.AudioContext || window.webkitAudioContext)({latencyHint:"interactive"});
    masterGain = context.createGain();
    masterGain.gain.value = masterState;
    masterGain.connect(context.destination);

    decoded = [];
    trackNodes = [];

    for (let i = 0; i < defs.length; i += 1) {
      const response = await fetch(String(defs[i].url || ""), {cache:"force-cache"});
      if (!response.ok) {
        throw new Error(
          "HTTP média " + response.status + " pour " + String(defs[i].label || defs[i].name || "piste")
        );
      }
      const audioBytes = await response.arrayBuffer();
      const buffer = await context.decodeAudioData(audioBytes);
      decoded.push(buffer);

      const lowLP = context.createBiquadFilter();
      lowLP.type = "lowpass";
      lowLP.frequency.value = 250;
      lowLP.Q.value = 0.707;

      const midHP = context.createBiquadFilter();
      midHP.type = "highpass";
      midHP.frequency.value = 250;
      midHP.Q.value = 0.707;

      const midLP = context.createBiquadFilter();
      midLP.type = "lowpass";
      midLP.frequency.value = 4000;
      midLP.Q.value = 0.707;

      const highHP = context.createBiquadFilter();
      highHP.type = "highpass";
      highHP.frequency.value = 4000;
      highHP.Q.value = 0.707;

      const lowGain = context.createGain();
      const midGain = context.createGain();
      const highGain = context.createGain();
      const bandSum = context.createGain();
      const trackGain = context.createGain();

      lowLP.connect(lowGain);
      lowGain.connect(bandSum);

      midHP.connect(midLP);
      midLP.connect(midGain);
      midGain.connect(bandSum);

      highHP.connect(highGain);
      highGain.connect(bandSum);

      bandSum.connect(trackGain);
      trackGain.connect(masterGain);

      trackNodes.push({
        lowLP, midHP, midLP, highHP,
        lowGain, midGain, highGain,
        bandSum, trackGain,
      });
      if (i === 0) duration = Number(buffer.duration || 0);
    }

    seek.max = String(Math.max(0.001, duration));
    ready = true;

    // Re-apply latest UI state after decoding, fixing pre-play mute/volume races.
    trackState.forEach((_, i) => applyTrackState(i, false));
    applyMasterState(false);

    playButton.disabled = false;
    playButton.textContent = "▶ Lecture";
  }

  function stopSources() {
    sources.forEach((source) => {
      try { source.stop(); } catch (_) {}
      try { source.disconnect(); } catch (_) {}
    });
    sources = [];
  }

  function startSources(offset) {
    stopSources();
    const when = context.currentTime + 0.030;

    sources = decoded.map((buffer, index) => {
      const source = context.createBufferSource();
      source.buffer = buffer;
      source.connect(trackNodes[index].lowLP);
      source.connect(trackNodes[index].midHP);
      source.connect(trackNodes[index].highHP);
      const safeOffset = Math.max(
        0,
        Math.min(Number(offset) || 0, Math.max(0, buffer.duration - 0.001))
      );
      source.start(when, safeOffset);
      return source;
    });

    position = Math.max(0, Math.min(duration, Number(offset) || 0));
    startedAtContextTime = when;
    playing = true;
  }

  async function playAll() {
    await ensureReady();
    if (context.state === "suspended") await context.resume();
    if (playing) return;
    if (position >= duration - 0.01) position = 0;
    startSources(position);
  }

  function pauseAll() {
    if (!playing) return;
    position = currentTime();
    playing = false;
    stopSources();
  }

  function stopAll() {
    playing = false;
    stopSources();
    position = 0;
    seek.value = "0";
    renderLyrics(0);
    timeLabel.textContent = "0:00 / " + fmt(duration);
  }

  function seekTo(time) {
    const t = Math.max(0, Math.min(duration, Number(time) || 0));
    position = t;
    if (playing) startSources(t);
    renderLyrics(t);
  }

  function makeSlider(index, field, min, max, step, suffix, categoryClass = "") {
    const wrap = document.createElement("div");
    wrap.className = "control-cell" + (categoryClass ? " " + categoryClass : "");

    const slider = document.createElement("input");
    slider.type = "range";
    slider.min = String(min);
    slider.max = String(max);
    slider.step = String(step);
    slider.value = String(trackState[index][field]);

    const value = document.createElement("span");
    value.className = "control-value";

    function renderValue() {
      const v = Number(slider.value);
      value.textContent = suffix === "dB"
        ? ((v > 0 ? "+" : "") + v.toFixed(0) + " dB")
        : (Math.round(v * 100) + "%");
    }

    slider.addEventListener("input", () => {
      trackState[index][field] = Number(slider.value);
      renderValue();
      applyTrackState(index, true);
    });

    renderValue();
    wrap.append(slider, value);
    return {wrap, slider, value};
  }

  defs.forEach((track, index) => {
    const row = document.createElement("div");
    row.className = "track";

    const name = document.createElement("div");
    name.className = "track-name";
    name.textContent = String(track.label || track.name || "Track");

    const toggleWrap = document.createElement("label");
    toggleWrap.className = "track-toggle";
    const toggle = document.createElement("input");
    toggle.type = "checkbox";
    toggle.checked = trackState[index].enabled;
    const toggleText = document.createElement("span");
    toggleText.textContent = "Actif";
    toggle.addEventListener("change", () => {
      trackState[index].enabled = Boolean(toggle.checked);
      applyTrackState(index, true);
    });
    toggleWrap.append(toggle, toggleText);

    const volume = makeSlider(index, "volume", 0, 1.25, 0.01, "%", "volume-control");
    const low = makeSlider(index, "low", -6, 6, 1, "dB", "low-control");
    const mid = makeSlider(index, "mid", -6, 6, 1, "dB", "mid-control");
    const high = makeSlider(index, "high", -6, 6, 1, "dB", "high-control");

    const reset = document.createElement("button");
    reset.type = "button";
    reset.className = "eq-reset";
    reset.textContent = "Reset EQ";
    reset.addEventListener("click", () => {
      trackState[index].low = 0;
      trackState[index].mid = 0;
      trackState[index].high = 0;
      low.slider.value = "0";
      mid.slider.value = "0";
      high.slider.value = "0";
      low.value.textContent = "0 dB";
      mid.value.textContent = "0 dB";
      high.value.textContent = "0 dB";
      applyTrackState(index, true);
    });

    row.append(name, toggleWrap, volume.wrap, low.wrap, mid.wrap, high.wrap, reset);
    tracksNode.appendChild(row);
  });

  masterVolume.addEventListener("input", () => {
    masterState = Number(masterVolume.value);
    masterValue.textContent = Math.round(masterState * 100) + "%";
    applyMasterState(true);
  });

  const lyricNodes = words.map((word) => {
    const span = document.createElement("span");
    span.className = "lyric-word";
    span.textContent = String(word.text || "").trim();
    lyricsTrack.appendChild(span);
    return span;
  });
  if (!words.length) lyricsWrap.style.display = "none";

  function findWordIndex(time) {
    if (!words.length) return -1;
    let low = 0, high = words.length - 1, answer = 0;
    while (low <= high) {
      const middle = (low + high) >> 1;
      if (Number(words[middle].start || 0) <= time) {
        answer = middle; low = middle + 1;
      } else high = middle - 1;
    }
    return answer;
  }

  function renderLyrics(time) {
    if (!words.length) return;
    const index = findWordIndex(time);
    if (index < 0 || !lyricNodes[index]) return;

    if (index !== activeWordIndex) {
      activeWordIndex = index;
      lyricNodes.forEach((node, i) => {
        node.classList.toggle("past", i < index);
        node.classList.toggle("current", i === index);
      });
    }

    const current = lyricNodes[index];
    const next = lyricNodes[index + 1];
    const currentCenter = current.offsetLeft + current.offsetWidth / 2;
    let targetCenter = currentCenter;

    if (next) {
      const start = Number(words[index].start || 0);
      const nextStart = Math.max(start + 0.04, Number(words[index + 1].start || start + 0.5));
      const progress = Math.max(0, Math.min(1, (time - start) / (nextStart - start)));
      const nextCenter = next.offsetLeft + next.offsetWidth / 2;
      targetCenter = currentCenter + (nextCenter - currentCenter) * progress;
    }

    lyricsTrack.style.transform =
      "translate(" + (lyricsStrip.clientWidth / 2 - targetCenter) + "px,-50%)";
  }

  function tick() {
    if (disposed) return;
    const t = currentTime();
    seek.value = String(t);
    timeLabel.textContent = fmt(t) + " / " + fmt(duration);
    renderLyrics(t);
    if (playing && t >= duration - 0.01) stopAll();
    raf = requestAnimationFrame(tick);
  }

  playButton.addEventListener("click", playAll);
  pauseButton.addEventListener("click", pauseAll);
  stopButton.addEventListener("click", stopAll);
  seek.addEventListener("input", () => seekTo(Number(seek.value || 0)));

  tick();

  return function() {
    disposed = true;
    if (raf !== null) cancelAnimationFrame(raf);
    stopSources();
    try { if (context) context.close(); } catch (_) {}
  };
}
"""

_STEM_PLAYER = st.components.v2.component(
    "ezscore_stem_analysis_player",
    html=_PLAYER_HTML,
    css=_PLAYER_CSS,
    js=_PLAYER_JS,
    isolate_styles=True,
)


def render_player(
    source: Path,
    stems: dict[str, Path],
    *,
    preview_dir: Path,
    key: str,
    words: list[dict[str, Any]] | None = None,
) -> None:
    # Analyse > Step 1 is now the autonomous Riffstation + STEM surface.
    # The historical caller still passes `words`; Step 1 deliberately ignores
    # them and never instantiates a lyric lane. Other callers retain the legacy
    # renderer below.
    if str(key).startswith("ezstem_player_"):
        from ezscore.player.step1_riffstation import render_step1_riffstation

        render_step1_riffstation(
            source=Path(source),
            stems=dict(stems),
            preview_dir=Path(preview_dir),
            key=str(key),
        )
        return

    """Step 1 facade: Riffstation + stems, intentionally without lyrics.

    The old low-level assets above are kept byte-for-byte compatible for the
    existing Step 2 conductor.  Only this public Step 1 entry point delegates
    to the dedicated Riffstation workflow.
    """
    from ezscore.player.step1_riffstation import render_step1_riffstation

    render_step1_riffstation(
        source=source,
        stems=stems,
        preview_dir=preview_dir,
        key=key,
    )
