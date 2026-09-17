from __future__ import annotations

import json
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import numpy as np
import streamlit as st

from ezscore.analysis.stems import STEM_NAMES
from ezscore.player.media_url import register_media_url


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
    target = _preview_target(path, preview_dir)
    if _preview_is_current(path, target):
        return target

    if not ffmpeg_available():
        raise RuntimeError("FFmpeg est requis pour créer les copies MP3 du lecteur.")

    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(path), "-vn", "-map_metadata", "-1",
        "-codec:a", "libmp3lame", "-b:a", "64k", "-ar", "44100",
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
            f"Impossible de créer la pré-écoute MP3 pour {path.name}:\\n"
            + (proc.stdout or "")
        )
    return target


def prepare_browser_previews(
    source: Path,
    stems: dict[str, Path],
    preview_dir: Path,
) -> dict[str, Path]:
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
    workers = min(4, max(1, len(pending)))
    done = 0

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


def _conductor_cache_path(preview_dir: Path) -> Path:
    return preview_dir.parent / "karaoke_conductor.json"


def _meter_defaults(preview_dir: Path) -> dict[str, Any]:
    structure_path = preview_dir.parent / "structure_analysis.json"
    if structure_path.is_file():
        try:
            structure = json.loads(structure_path.read_text(encoding="utf-8"))
            meter = dict(structure.get("meter", {}) or {})
            return {
                "signature": str(
                    meter.get("signature")
                    or structure.get("signature")
                    or "4/4"
                ),
                "grouping": str(meter.get("grouping", "") or ""),
            }
        except Exception:
            pass
    return {"signature": "4/4", "grouping": ""}



def _vocal_whisper_cache_path(preview_dir: Path) -> Path:
    return preview_dir.parent / "whisper_vocals_small.json"


def _merge_vocal_gap_words(
    original_words: list[dict[str, Any]],
    vocal_words: list[dict[str, Any]],
    *,
    min_gap: float = 1.10,
    edge_guard: float = 0.32,
) -> list[dict[str, Any]]:
    """Use the vocal-stem pass only inside gaps left by the original pass.

    The original Whisper timeline remains authoritative. The vocal-stem pass
    supplements pre-roll/post-roll and long omissions such as sung "la la la".
    """
    original = sorted(
        [
            {
                "start": float(w.get("start", 0.0) or 0.0),
                "end": float(w.get("end", w.get("start", 0.0)) or 0.0),
                "text": str(w.get("text", "") or "").strip(),
            }
            for w in original_words
            if str(w.get("text", "") or "").strip()
        ],
        key=lambda w: (w["start"], w["end"]),
    )
    vocal = sorted(
        [
            {
                "start": float(w.get("start", 0.0) or 0.0),
                "end": float(w.get("end", w.get("start", 0.0)) or 0.0),
                "text": str(w.get("text", "") or "").strip(),
                "confidence": float(w.get("confidence", 1.0) or 0.0),
            }
            for w in vocal_words
            if str(w.get("text", "") or "").strip()
            and float(w.get("confidence", 1.0) or 0.0) >= 0.30
        ],
        key=lambda w: (w["start"], w["end"]),
    )

    if not original:
        return [
            {"start": w["start"], "end": w["end"], "text": w["text"]}
            for w in vocal
        ]
    if not vocal:
        return original

    gaps: list[tuple[float, float]] = []
    first_start = float(original[0]["start"])
    if first_start >= min_gap:
        gaps.append((0.0, max(0.0, first_start - edge_guard)))

    for left, right in zip(original, original[1:]):
        gap_start = float(left["end"])
        gap_end = float(right["start"])
        if gap_end - gap_start >= min_gap:
            gaps.append((gap_start + edge_guard, gap_end - edge_guard))

    # The end is intentionally open; only use actual vocal words found later.
    last_end = float(original[-1]["end"])
    gaps.append((last_end + edge_guard, float("inf")))

    additions: list[dict[str, Any]] = []
    for word in vocal:
        center = (word["start"] + word["end"]) / 2.0
        if any(g0 <= center <= g1 for g0, g1 in gaps):
            additions.append(
                {
                    "start": word["start"],
                    "end": word["end"],
                    "text": word["text"],
                }
            )

    merged = sorted(original + additions, key=lambda w: (w["start"], w["end"]))
    return merged


def _ensure_vocal_whisper_supplement(
    source: Path,
    stems: dict[str, Path],
    preview_dir: Path,
    original_words: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """One-time Whisper pass on the isolated vocal stem.

    This specifically repairs sung material that the original-mix pass can
    omit (intro vocalises, repeated "la/na/oh", etc.). Results are cached.
    """
    vocals = stems.get("vocals")
    if vocals is None or not Path(vocals).is_file():
        return list(original_words)

    cache_path = _vocal_whisper_cache_path(preview_dir)
    payload: dict[str, Any] | None = None

    if cache_path.is_file():
        try:
            payload = json.loads(cache_path.read_text(encoding="utf-8"))
        except Exception:
            payload = None

    if payload is None:
        import torch
        # Reuse the exact cached Whisper-small instance already used by step 2.
        from ezscore.ui.stem_lab_analysis import _whisper_small

        device = "cuda" if torch.cuda.is_available() else "cpu"
        model = _whisper_small(device)
        result = model.transcribe(
            str(vocals),
            word_timestamps=True,
            fp16=(device == "cuda"),
            verbose=False,
            condition_on_previous_text=False,
            initial_prompt=(
                "Transcribe the sung lyrics faithfully, including repeated "
                "vocalisations such as la la la, na na na, oh and ah."
            ),
        )

        vocal_words: list[dict[str, Any]] = []
        for segment in result.get("segments", []) or []:
            no_speech = float(segment.get("no_speech_prob", 0.0) or 0.0)
            avg_logprob = float(segment.get("avg_logprob", 0.0) or 0.0)
            if no_speech > 0.65 or avg_logprob < -1.35:
                continue

            for word in segment.get("words", []) or []:
                text_value = str(word.get("word", "") or "").strip()
                start = float(word.get("start", 0.0) or 0.0)
                end = float(word.get("end", start) or start)
                probability = float(word.get("probability", 1.0) or 0.0)
                if text_value and end > start and probability >= 0.30:
                    vocal_words.append(
                        {
                            "start": start,
                            "end": end,
                            "text": text_value,
                            "confidence": probability,
                        }
                    )

        payload = {
            "engine": "openai-whisper",
            "model": "small",
            "source": "vocals",
            "language": str(result.get("language", "") or ""),
            "words": vocal_words,
        }
        cache_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    return _merge_vocal_gap_words(
        list(original_words),
        list(payload.get("words", []) or []),
    )


def _cache_is_current(
    cache_path: Path,
    source: Path,
    drums_path: Path,
) -> bool:
    if not cache_path.is_file():
        return False
    try:
        cache_mtime = cache_path.stat().st_mtime_ns
        return (
            cache_mtime >= source.stat().st_mtime_ns
            and cache_mtime >= drums_path.stat().st_mtime_ns
        )
    except OSError:
        return False


def _build_conductor_timeline(
    source: Path,
    stems: dict[str, Path],
    preview_dir: Path,
) -> dict[str, Any]:
    """Build/cache the absolute musical timeline needed by the karaoke view.

    This deliberately does not depend on the old automatic block detector.
    Rhythm and harmony remain independent absolute-time tracks.
    """
    drums = Path(stems["drums"])
    cache_path = _conductor_cache_path(preview_dir)

    if _cache_is_current(cache_path, source, drums):
        try:
            payload = json.loads(cache_path.read_text(encoding="utf-8"))
            if payload.get("beats"):
                return payload
        except Exception:
            pass

    from ezscore.analysis.chords_quality import (
        analyze_chords_absolute,
        chord_for_interval,
    )

    # Preview conductor priority:
    # 1. Reuse the canonical beat timeline if step 3 has already produced it.
    # 2. Otherwise try the HQ rhythm engine.
    # 3. If madmom-infer is unavailable/broken, build a *provisional* beat grid
    #    from the drums stem with librosa. This is intentionally limited to the
    #    immediate karaoke preview after Whisper; the canonical analysis still
    #    remains the HQ pipeline when available.
    rhythm_engine = ""
    beat_times: list[float] = []
    tempo = 0.0

    structure_path = preview_dir.parent / "structure_analysis.json"
    if structure_path.is_file():
        try:
            structure = json.loads(structure_path.read_text(encoding="utf-8"))
            beat_timeline = list(structure.get("beat_timeline", []) or [])
            beat_times = [
                float(item.get("time", 0.0) or 0.0)
                for item in beat_timeline
                if item.get("time") is not None
            ]
            beat_times = sorted(set(beat_times))
            tempo = float(structure.get("tempo", 0.0) or 0.0)
            if len(beat_times) >= 2:
                rhythm_engine = str(
                    (structure.get("analysis_engines", {}) or {}).get("rhythm", "")
                    or "structure-cache"
                )
        except Exception:
            beat_times = []
            tempo = 0.0

    if len(beat_times) < 2:
        try:
            from ezscore.analysis.rhythm_quality import analyze_beats
            rhythm = analyze_beats(drums)
            beat_times = [float(x) for x in (rhythm.get("beats", []) or [])]
            tempo = float(rhythm.get("tempo", 0.0) or 0.0)
            rhythm_engine = str(rhythm.get("engine", "") or "")
        except Exception as exc:
            # Deliberate preview-only fallback: the user asked to see a
            # synchronized conductor immediately after lyrics analysis.
            import librosa
            y, sr = librosa.load(str(drums), sr=22050, mono=True)
            onset_env = librosa.onset.onset_strength(y=y, sr=sr)
            tempo_est, beat_frames = librosa.beat.beat_track(
                onset_envelope=onset_env,
                sr=sr,
                units="frames",
            )
            beat_times_np = librosa.frames_to_time(beat_frames, sr=sr)
            beat_times = [float(x) for x in beat_times_np.tolist()]
            try:
                tempo = float(np.asarray(tempo_est).reshape(-1)[0])
            except Exception:
                tempo = 0.0
            rhythm_engine = "librosa-preview-fallback"
            if len(beat_times) < 2:
                raise RuntimeError(
                    "Impossible de construire même la timeline rythmique "
                    f"provisoire : {exc}"
                ) from exc

    if tempo <= 1.0 and len(beat_times) >= 2:
        intervals = np.diff(np.asarray(beat_times, dtype=float))
        intervals = intervals[intervals > 1e-6]
        if intervals.size:
            tempo = 60.0 / float(np.median(intervals))

    if len(beat_times) < 2:
        raise RuntimeError("Timeline rythmique insuffisante pour le conducteur.")

    chord_payload = analyze_chords_absolute(
        source,
        cache_path=preview_dir.parent / "chord_analysis_lv_chordia.json",
        force=False,
    )
    chord_segments = list(chord_payload.get("segments", []) or [])
    if not chord_segments:
        raise RuntimeError("Timeline harmonique vide pour le conducteur.")

    default_interval = 60.0 / max(1.0, tempo)
    beats: list[dict[str, Any]] = []
    for index, start in enumerate(beat_times):
        end = (
            beat_times[index + 1]
            if index + 1 < len(beat_times)
            else start + default_interval
        )
        chord, raw_chord, overlap = chord_for_interval(
            chord_segments, start, end
        )
        normalized = str(chord or "N").strip()
        if normalized in {"", "N", "NC", "N.C.", "no_chord"}:
            normalized = "."
        beats.append(
            {
                "index": index,
                "start": round(start, 6),
                "end": round(float(end), 6),
                "chord": normalized,
                "raw_chord": str(raw_chord or ""),
                "overlap": round(float(overlap or 0.0), 6),
            }
        )

    payload = {
        "version": 1,
        "tempo": tempo,
        "beats": beats,
        "rhythm_engine": rhythm_engine,
        "harmony_engine": str(chord_payload.get("engine", "") or ""),
        "meter_default": _meter_defaults(preview_dir),
    }
    cache_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return payload


_HTML = r"""
<div class="ezk-root">
  <div class="transport">
    <button class="play" type="button">▶ Lecture</button>
    <button class="pause" type="button">⏸ Pause</button>
    <button class="stop" type="button">⏹ Stop</button>
    <span class="time">0:00 / 0:00</span>
  </div>
  <input class="seek" type="range" min="0" max="1" step="0.001" value="0">

  <div class="meter-box">
    <strong>Mesure</strong>
    <input class="meter-num" type="number" min="1" step="1" value="4">
    <span>/</span>
    <input class="meter-den" type="number" min="1" step="1" value="4">
    <label>Groupement <input class="meter-group" type="text" placeholder="auto"></label>
    <span class="meter-state"></span>
  </div>

  <div class="karaoke">
    <div class="line previous"></div>
    <div class="chords"></div>
    <div class="line current"></div>
    <div class="line next"></div>
  </div>

  <details class="mixer-details">
    <summary>Mixeur STEM</summary>
    <div class="tracks"></div>
    <div class="master-row">
      <strong>Master</strong>
      <input class="master-volume" type="range" min="0" max="1.25" step="0.01" value="1">
      <span class="master-value">100%</span>
    </div>
  </details>

  <div class="hint">
    Audio original = horloge maître · paroles Whisper + accords HQ sur la même timeline.
  </div>
</div>
"""

_CSS = r"""
:host { display:block; width:100%; }
.ezk-root {
  box-sizing:border-box; width:100%;
  border:1px solid color-mix(in srgb, var(--st-text-color) 24%, transparent);
  border-radius:12px; padding:12px;
  background:color-mix(in srgb, var(--st-text-color) 3%, transparent);
  color:var(--st-text-color); font-family:var(--st-font);
}
.transport { display:flex; gap:8px; align-items:center; flex-wrap:wrap; }
.transport button {
  min-height:32px; border-radius:7px;
  border:1px solid color-mix(in srgb, var(--st-text-color) 35%, transparent);
  background:color-mix(in srgb, var(--st-text-color) 8%, transparent);
  color:var(--st-text-color); cursor:pointer; padding:4px 9px;
}
.time { margin-left:auto; font-size:12px; opacity:.75; font-variant-numeric:tabular-nums; }
.seek { width:100%; margin:10px 0; }
.meter-box {
  display:flex; align-items:center; gap:6px; flex-wrap:wrap;
  font-size:12px; margin:4px 0 12px;
  padding:7px 9px; border-radius:8px;
  background:color-mix(in srgb, var(--st-text-color) 5%, transparent);
}
.meter-box input {
  background:color-mix(in srgb, var(--st-text-color) 5%, transparent);
  color:var(--st-text-color);
  border:1px solid color-mix(in srgb, var(--st-text-color) 25%, transparent);
  border-radius:5px; padding:3px 5px;
}
.meter-num,.meter-den { width:52px; }
.meter-group { width:92px; }
.meter-state { opacity:.68; margin-left:auto; }

.karaoke {
  min-height:248px; display:flex; flex-direction:column;
  justify-content:center; overflow:hidden; border-radius:10px;
  padding:18px 12px;
  background:color-mix(in srgb, var(--st-text-color) 5%, transparent);
}
.line {
  text-align:center; line-height:1.34;
  transition:opacity 100ms linear, transform 100ms linear;
}
.line.previous,.line.next {
  min-height:34px; font-size:20px; opacity:.25;
}
.line.current {
  min-height:54px; font-size:31px; font-weight:760; opacity:1;
}
.word { display:inline; margin-right:.28em; opacity:.48; }
.word.past { opacity:.82; }
.word.active {
  opacity:1; font-weight:900;
  text-decoration:underline;
  text-decoration-thickness:3px;
  text-underline-offset:5px;
}
.chords {
  position:relative; height:44px; margin:4px 0 2px;
  font-family:Consolas,"Courier New",monospace;
  font-size:21px; font-weight:900; white-space:nowrap;
}
.chord-marker {
  position:absolute; transform:translateX(-10%);
  padding:2px 5px; border-radius:5px;
  background:color-mix(in srgb, #4da3ff 16%, transparent);
}
.chord-marker.active {
  background:color-mix(in srgb, #4da3ff 38%, transparent);
  transform:translateX(-10%) scale(1.06);
}
.mixer-details { margin-top:12px; }
.mixer-details summary { cursor:pointer; font-weight:800; }
.tracks { margin-top:8px; display:grid; gap:5px; }
.track {
  display:grid; grid-template-columns:minmax(90px,1fr) 58px minmax(120px,2fr);
  gap:8px; align-items:center; font-size:12px;
  padding:4px 0; border-top:1px solid color-mix(in srgb, var(--st-text-color) 10%, transparent);
}
.track input[type="range"], .master-volume { width:100%; }
.master-row {
  display:grid; grid-template-columns:90px 1fr 55px; gap:8px;
  align-items:center; margin-top:8px;
}
.master-value { text-align:right; font-size:11px; opacity:.72; }
.hint { margin-top:10px; font-size:11px; opacity:.65; }
"""

_JS = r"""
export default function(component) {
  const data = component.data || {};
  const root = component.parentElement;

  const tracksDef = Array.isArray(data.tracks) ? data.tracks : [];
  const words = Array.isArray(data.words) ? data.words : [];
  const beats = Array.isArray(data.beats) ? data.beats : [];
  const meterDefault = data.meter_default || {signature:"4/4", grouping:""};

  const playBtn = root.querySelector(".play");
  const pauseBtn = root.querySelector(".pause");
  const stopBtn = root.querySelector(".stop");
  const seek = root.querySelector(".seek");
  const timeLabel = root.querySelector(".time");
  const tracksNode = root.querySelector(".tracks");
  const masterSlider = root.querySelector(".master-volume");
  const masterValue = root.querySelector(".master-value");
  const numInput = root.querySelector(".meter-num");
  const denInput = root.querySelector(".meter-den");
  const groupingInput = root.querySelector(".meter-group");
  const meterState = root.querySelector(".meter-state");
  const prevLine = root.querySelector(".previous");
  const currentLine = root.querySelector(".current");
  const nextLine = root.querySelector(".next");
  const chordsNode = root.querySelector(".chords");

  const meterParts = String(meterDefault.signature || "4/4").split("/");
  numInput.value = String(Math.max(1, Number(meterParts[0] || 4)));
  denInput.value = String(Math.max(1, Number(meterParts[1] || 4)));
  groupingInput.value = String(meterDefault.grouping || "");

  const storageKey = "ezscore-karaoke-meter:" + String(data.storage_key || "default");
  try {
    const saved = JSON.parse(localStorage.getItem(storageKey) || "null");
    if (saved) {
      numInput.value = String(saved.numerator || numInput.value);
      denInput.value = String(saved.denominator || denInput.value);
      groupingInput.value = String(saved.grouping || groupingInput.value);
    }
  } catch (_) {}

  let context = null;
  let decoded = [];
  let nodes = [];
  let masterGain = null;
  let sources = [];
  let ready = false;
  let playing = false;
  let position = 0;
  let startedAt = 0;
  let duration = 0;
  let disposed = false;
  let raf = null;
  let lineIndex = -1;

  const trackState = tracksDef.map((x) => ({
    enabled: Boolean(x.enabled),
    volume: Number(x.volume ?? .8)
  }));

  function fmt(value) {
    const t = Math.max(0, Number(value) || 0);
    const m = Math.floor(t / 60);
    return m + ":" + String(Math.floor(t % 60)).padStart(2, "0");
  }

  function currentTime() {
    if (!playing || !context) return position;
    return Math.max(0, Math.min(duration, position + context.currentTime - startedAt));
  }

  function parseGrouping(n, d, text) {
    const raw = String(text || "").trim();
    if (raw) {
      const groups = raw.split("+").map(x => Number(x.trim())).filter(x => x > 0);
      if (groups.length && groups.reduce((a,b)=>a+b,0) === n) return groups;
    }
    if (d >= 8 && n > 3 && n % 3 === 0) return Array(n/3).fill(3);
    if (d >= 8 && n === 5) return [2,3];
    if (d >= 8 && n === 7) return [2,2,3];
    if (d === 4 && n === 5) return [3,2];
    if (d === 4 && n === 7) return [4,3];
    return Array(n).fill(1);
  }

  function meter() {
    const n = Math.max(1, Math.floor(Number(numInput.value || 4)));
    const d = Math.max(1, Math.floor(Number(denInput.value || 4)));
    const groups = parseGrouping(n, d, groupingInput.value);
    const grouped = d >= 8 && groups.some(x => x > 1);
    const beatsPerMeasure = grouped ? groups.length : n;
    return {n, d, groups, grouped, beatsPerMeasure};
  }

  function persistMeter() {
    const m = meter();
    try {
      localStorage.setItem(storageKey, JSON.stringify({
        numerator:m.n, denominator:m.d, grouping:groupingInput.value
      }));
    } catch (_) {}
    meterState.textContent =
      m.n + "/" + m.d + " · " +
      (groupingInput.value.trim() || m.groups.join("+"));
    renderConductor(currentTime(), true);
  }

  [numInput, denInput, groupingInput].forEach((el) => {
    el.addEventListener("change", persistMeter);
    el.addEventListener("input", persistMeter);
  });

  function buildLines() {
    if (!words.length) return [];
    const lines = [];
    let current = [];
    let lastEnd = null;

    function flush() {
      if (!current.length) return;
      lines.push({
        words: current,
        start: Number(current[0].start || 0),
        end: Number(current[current.length-1].end || current[current.length-1].start || 0)
      });
      current = [];
    }

    words.forEach((w) => {
      const text = String(w.text || "").trim();
      if (!text) return;
      const start = Number(w.start || 0);
      const end = Number(w.end || start);
      const gap = lastEnd === null ? 0 : start - lastEnd;
      if (current.length && (gap > 1.05 || current.length >= 10)) flush();
      current.push({...w, text, start, end});
      lastEnd = end;
      if (/[.!?;:]$/.test(text) && current.length >= 4) flush();
    });
    flush();
    return lines;
  }

  const lines = buildLines();
  // `lines` must exist before persistMeter() triggers renderConductor().
  persistMeter();

  function lineAt(time) {
    if (!lines.length) return -1;
    // Never show a future lyric line during a genuine instrumental/vocal gap.
    // A recovered vocalisation line will naturally occupy this interval.
    if (time < lines[0].start - 1.0) return -1;
    for (let i=0;i<lines.length;i++) {
      if (time >= lines[i].start - .15 && time <= lines[i].end + .45) return i;
      if (time < lines[i].start) {
        const previous = i - 1;
        if (previous >= 0 && time <= lines[previous].end + 1.2) return previous;
        return -1;
      }
    }
    if (time <= lines[lines.length - 1].end + 1.2) return lines.length - 1;
    return -1;
  }

  function renderLine(node, line, time, active) {
    node.innerHTML = "";
    if (!line) return;
    line.words.forEach((w) => {
      const span = document.createElement("span");
      span.className = "word";
      if (time >= w.end) span.classList.add("past");
      if (active && time >= w.start && time < Math.max(w.end, w.start + .04)) {
        span.classList.add("active");
      }
      span.textContent = w.text;
      node.appendChild(span);
    });
  }

  function measureNotation(measureIndex, m) {
    const startBeat = measureIndex * m.beatsPerMeasure;
    if (startBeat >= beats.length) return null;
    const beatSlice = beats.slice(startBeat, startBeat + m.beatsPerMeasure);
    if (!beatSlice.length) return null;

    let notation = "";
    let prevChord = null;
    beatSlice.forEach((beat, localIndex) => {
      let chord = String(beat.chord || ".").trim() || ".";
      let token;
      if (chord === ".") token = ".";
      else if (localIndex === 0) token = chord;
      else if (chord === prevChord) token = "-";
      else token = chord;

      if (m.grouped) {
        const count = Math.max(1, Number(m.groups[localIndex] || 1));
        if (token === ".") notation += ".".repeat(count);
        else if (token === "-") notation += "-".repeat(count);
        else notation += token + "-".repeat(Math.max(0, count - 1));
      } else {
        notation += token;
      }
      prevChord = chord;
    });
    return {
      notation,
      start: Number(beatSlice[0].start || 0),
      end: Number(beatSlice[beatSlice.length-1].end || beatSlice[beatSlice.length-1].start || 0),
    };
  }

  function measuresForWindow(t0, t1) {
    const m = meter();
    const count = Math.ceil(beats.length / m.beatsPerMeasure);
    const out = [];
    for (let i=0;i<count;i++) {
      const item = measureNotation(i, m);
      if (!item) continue;
      if (item.end < t0 || item.start > t1) continue;
      out.push(item);
    }
    return out;
  }

  function renderChords(line, time) {
    chordsNode.innerHTML = "";
    if (!line) return;
    const t0 = line.start;
    const t1 = Math.max(t0 + .01, line.end);
    const measures = measuresForWindow(t0 - .4, t1 + .4);
    measures.forEach((measure) => {
      const marker = document.createElement("span");
      marker.className = "chord-marker";
      if (time >= measure.start && time < measure.end) marker.classList.add("active");
      const pos = Math.max(0, Math.min(100, ((measure.start - t0) / (t1 - t0)) * 100));
      marker.style.left = pos + "%";
      marker.textContent = measure.notation;
      chordsNode.appendChild(marker);
    });
  }

  function renderConductor(time, force=false) {
    const idx = lineAt(time);
    if (idx < 0) {
      lineIndex = -1;
      prevLine.innerHTML = "";
      currentLine.innerHTML = "";
      nextLine.innerHTML = "";
      chordsNode.innerHTML = "";
      return;
    }
    if (force || idx !== lineIndex) lineIndex = idx;
    renderLine(prevLine, lines[idx-1], time, false);
    renderLine(currentLine, lines[idx], time, true);
    renderLine(nextLine, lines[idx+1], time, false);
    renderChords(lines[idx], time);
  }

  function applyTrack(index) {
    if (!ready || !nodes[index] || !context) return;
    const gain = trackState[index].enabled ? trackState[index].volume : 0;
    nodes[index].gain.gain.setTargetAtTime(gain, context.currentTime, .015);
  }

  async function ensureReady() {
    if (ready) {
      if (context.state === "suspended") await context.resume();
      return;
    }
    playBtn.disabled = true;
    playBtn.textContent = "Chargement audio…";
    context = new (window.AudioContext || window.webkitAudioContext)({latencyHint:"interactive"});
    masterGain = context.createGain();
    masterGain.gain.value = Number(masterSlider.value || 1);
    masterGain.connect(context.destination);

    for (let i=0;i<tracksDef.length;i++) {
      const def = tracksDef[i];
      const response = await fetch(String(def.url || ""), {cache:"force-cache"});
      if (!response.ok) throw new Error("HTTP média " + response.status);
      const buf = await context.decodeAudioData(await response.arrayBuffer());
      decoded.push(buf);
      const gain = context.createGain();
      gain.connect(masterGain);
      nodes.push({gain});
      if (i === 0) duration = Number(buf.duration || 0);
    }

    seek.max = String(Math.max(.001, duration));
    ready = true;
    trackState.forEach((_,i)=>applyTrack(i));
    playBtn.disabled = false;
    playBtn.textContent = "▶ Lecture";
  }

  function stopSources() {
    sources.forEach((s) => {
      try { s.stop(); } catch (_) {}
      try { s.disconnect(); } catch (_) {}
    });
    sources = [];
  }

  function startSources(offset) {
    stopSources();
    const when = context.currentTime + .03;
    sources = decoded.map((buffer,index) => {
      const src = context.createBufferSource();
      src.buffer = buffer;
      src.connect(nodes[index].gain);
      const safe = Math.max(0, Math.min(Number(offset)||0, Math.max(0, buffer.duration-.001)));
      src.start(when, safe);
      return src;
    });
    position = Math.max(0, Math.min(duration, Number(offset)||0));
    startedAt = when;
    playing = true;
  }

  async function playAll() {
    await ensureReady();
    if (context.state === "suspended") await context.resume();
    if (playing) return;
    if (position >= duration-.01) position = 0;
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
    renderConductor(0, true);
  }

  function seekTo(value) {
    position = Math.max(0, Math.min(duration, Number(value)||0));
    if (playing) startSources(position);
    renderConductor(position, true);
  }

  tracksDef.forEach((def,index) => {
    const row = document.createElement("div");
    row.className = "track";

    const name = document.createElement("strong");
    name.textContent = String(def.label || def.name || "Piste");

    const onLabel = document.createElement("label");
    const on = document.createElement("input");
    on.type = "checkbox";
    on.checked = trackState[index].enabled;
    on.addEventListener("change", () => {
      trackState[index].enabled = on.checked;
      applyTrack(index);
    });
    onLabel.append(on, document.createTextNode(" Actif"));

    const vol = document.createElement("input");
    vol.type = "range"; vol.min="0"; vol.max="1.25"; vol.step=".01";
    vol.value = String(trackState[index].volume);
    vol.addEventListener("input", () => {
      trackState[index].volume = Number(vol.value);
      applyTrack(index);
    });

    row.append(name, onLabel, vol);
    tracksNode.appendChild(row);
  });

  masterSlider.addEventListener("input", () => {
    const value = Number(masterSlider.value || 1);
    masterValue.textContent = Math.round(value * 100) + "%";
    if (masterGain && context) masterGain.gain.setTargetAtTime(value, context.currentTime, .015);
  });

  playBtn.addEventListener("click", () => playAll().catch((e) => {
    playBtn.disabled = false;
    playBtn.textContent = "▶ Lecture";
    console.error(e);
  }));
  pauseBtn.addEventListener("click", pauseAll);
  stopBtn.addEventListener("click", stopAll);
  seek.addEventListener("input", () => seekTo(Number(seek.value || 0)));

  function tick() {
    if (disposed) return;
    const t = currentTime();
    seek.value = String(t);
    timeLabel.textContent = fmt(t) + " / " + fmt(duration);
    renderConductor(t);
    if (playing && t >= duration-.01) stopAll();
    raf = requestAnimationFrame(tick);
  }

  renderConductor(0, true);
  tick();

  return function() {
    disposed = true;
    if (raf !== null) cancelAnimationFrame(raf);
    stopSources();
    try { if (context) context.close(); } catch (_) {}
  };
}
"""

_COMPONENT = st.components.v2.component(
    "ezscore_karaoke_stem_player",
    html=_HTML,
    css=_CSS,
    js=_JS,
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
    """Drop-in replacement for stem_webaudio.render_player.

    Before lyrics exist, it behaves as a STEM mixer.
    As soon as Whisper words exist, it builds the HQ rhythm/harmony timeline
    and shows a karaoke-style lyrics+chords conductor.
    """
    previews = prepare_browser_previews(source, stems, preview_dir)

    tracks: list[dict[str, Any]] = []

    def pack(name: str, label: str, path: Path, enabled: bool, volume: float) -> None:
        preview = previews[name]
        tracks.append(
            {
                "name": name,
                "label": label,
                "url": register_media_url(
                    preview,
                    coordinates=f"{key}:karaoke:{name}",
                    mimetype="audio/mpeg",
                ),
                "enabled": enabled,
                "volume": volume,
            }
        )

    pack("original", "Original", source, True, 0.75)
    defaults = {
        "vocals": (True, 0.90),
        "drums": (False, 0.75),
        "bass": (False, 0.75),
        "other": (False, 0.75),
    }
    labels = {
        "vocals": "Chant",
        "drums": "Batterie",
        "bass": "Basse",
        "other": "Other",
    }
    for name in STEM_NAMES:
        if name in stems:
            enabled, volume = defaults[name]
            pack(name, labels[name], stems[name], enabled, volume)

    player_words = list(words or [])
    conductor: dict[str, Any] = {
        "beats": [],
        "meter_default": _meter_defaults(preview_dir),
    }

    if player_words:
        try:
            vocal_cache = _vocal_whisper_cache_path(preview_dir)
            if vocal_cache.is_file():
                player_words = _ensure_vocal_whisper_supplement(
                    source, stems, preview_dir, player_words
                )
            else:
                with st.spinner(
                    "Complément paroles sur le stem voix "
                    "(vocalises / omissions Whisper)…"
                ):
                    player_words = _ensure_vocal_whisper_supplement(
                        source, stems, preview_dir, player_words
                    )
        except Exception as exc:
            st.warning(
                "Complément vocal indisponible ; la transcription originale "
                f"reste utilisée : {exc}"
            )

        try:
            with st.spinner(
                "Préparation du conducteur paroles + accords "
                "(rythme + harmonie HQ)…"
            ):
                conductor = _build_conductor_timeline(source, stems, preview_dir)
        except Exception as exc:
            st.warning(
                "Le lecteur paroles reste disponible, mais la timeline d'accords "
                f"n'a pas pu être préparée : {exc}"
            )

    st.caption(
        "Conducteur : paroles Whisper + accords/mesures sur l'horloge audio. "
        "La signature et le groupement sont modifiables sans relancer Whisper."
        if player_words
        else
        "Lecteur STEM prêt. Le conducteur apparaîtra après l'analyse des paroles."
    )

    _COMPONENT(
        data={
            "tracks": tracks,
            "words": player_words,
            "beats": list(conductor.get("beats", []) or []),
            "meter_default": dict(conductor.get("meter_default", {}) or {}),
            "storage_key": str(key),
        },
        key=key,
        width="stretch",
        height=650 if player_words else 430,
    )
