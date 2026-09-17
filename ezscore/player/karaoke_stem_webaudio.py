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


def _supplement_only_words(
    original_words: list[dict[str, Any]],
    merged_words: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return words present only in the vocal-stem supplementation.

    Matching is temporal first because punctuation/casing can differ between
    Whisper passes. These words are displayed on the provisional Chœurs lane.
    """
    original = [
        {
            "start": float(w.get("start", 0.0) or 0.0),
            "end": float(w.get("end", w.get("start", 0.0)) or 0.0),
            "text": str(w.get("text", "") or "").strip(),
        }
        for w in original_words
        if str(w.get("text", "") or "").strip()
    ]

    additions: list[dict[str, Any]] = []
    for word in merged_words:
        text_value = str(word.get("text", "") or "").strip()
        if not text_value:
            continue
        start = float(word.get("start", 0.0) or 0.0)
        end = float(word.get("end", start) or start)
        center = (start + end) / 2.0

        matched = False
        for ref in original:
            # A supplemental token that lands inside/very near an original word
            # is not a distinct backing-vocal event.
            if ref["start"] - 0.18 <= center <= ref["end"] + 0.18:
                matched = True
                break

        if not matched:
            additions.append(
                {"start": start, "end": end, "text": text_value}
            )

    return additions



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

  <div class="source-presets">
    <strong>Source</strong>
    <button class="preset-original" type="button">Original</button>
    <button class="preset-stems" type="button">Mix STEM</button>
    <span class="source-state">Original</span>
  </div>

  <div class="mixer">
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
  </div>

  <div class="meter-box">
    <strong>Mesure</strong>
    <input class="meter-num" type="number" min="1" step="1" value="4">
    <span>/</span>
    <input class="meter-den" type="number" min="1" step="1" value="4">
    <label>Groupement <input class="meter-group" type="text" placeholder="auto"></label>
    <span class="meter-state"></span>
  </div>

  <div class="karaoke">
    <div class="playhead"></div>
    <div class="future-hint">temps courant</div>

    <div class="timeline-row chord-row">
      <div class="timeline-label">Accords</div>
      <div class="timeline-viewport chord-viewport">
        <div class="timeline-track chord-track"></div>
      </div>
    </div>

    <div class="timeline-row lyric-row lead-row">
      <div class="timeline-label">Chant</div>
      <div class="timeline-viewport lyric-viewport">
        <div class="timeline-track lyric-track"></div>
      </div>
    </div>

    <div class="timeline-row lyric-row backing-row">
      <div class="timeline-label">Chœurs</div>
      <div class="timeline-viewport backing-viewport">
        <div class="timeline-track backing-track"></div>
      </div>
    </div>
  </div>

  <div class="hint">
    Une seule horloge WebAudio · Original ou mix STEM · EQ 3 bandes · accords + Chant + Chœurs synchronisés.
  </div>
</div>
"""

_CSS = r"""
:host { display:block; width:100%; }
.ezk-root {
  box-sizing:border-box;
  width:100%;
  border:1px solid color-mix(in srgb, var(--st-text-color) 24%, transparent);
  border-radius:12px;
  padding:12px;
  background:color-mix(in srgb, var(--st-text-color) 3%, transparent);
  color:var(--st-text-color);
  font-family:var(--st-font);
}

.transport {
  display:flex; gap:8px; align-items:center; flex-wrap:wrap;
}
.transport button,
.source-presets button,
.eq-reset {
  min-height:32px;
  border-radius:7px;
  border:1px solid color-mix(in srgb, var(--st-text-color) 35%, transparent);
  background:color-mix(in srgb, var(--st-text-color) 8%, transparent);
  color:var(--st-text-color);
  cursor:pointer;
  padding:4px 9px;
}
.time {
  margin-left:auto;
  font-size:12px;
  opacity:.75;
  font-variant-numeric:tabular-nums;
}
.seek { width:100%; margin:10px 0 12px; }

.source-presets {
  display:flex;
  align-items:center;
  gap:8px;
  flex-wrap:wrap;
  margin:0 0 10px 0;
  padding:7px 9px;
  border-radius:8px;
  background:color-mix(in srgb, var(--st-text-color) 5%, transparent);
}
.source-state {
  margin-left:auto;
  font-size:11px;
  opacity:.70;
}

.mixer {
  padding:9px;
  margin-bottom:10px;
  border-radius:9px;
  background:color-mix(in srgb, var(--st-text-color) 4%, transparent);
}
.mixer-head, .track {
  display:grid;
  grid-template-columns:minmax(82px,1.15fr) 52px minmax(110px,1.35fr)
                        minmax(90px,1fr) minmax(90px,1fr) minmax(90px,1fr) 66px;
  gap:8px;
  align-items:center;
}
.mixer-head {
  font-size:11px;
  font-weight:800;
  opacity:.65;
  padding:0 4px 5px;
}
.tracks { display:grid; gap:3px; }
.track {
  padding:5px 4px;
  border-top:1px solid color-mix(in srgb, var(--st-text-color) 12%, transparent);
}
.track-name { font-weight:800; }
.track-toggle {
  display:flex;
  align-items:center;
  gap:5px;
  font-size:11px;
}
.control-cell {
  display:grid;
  grid-template-columns:1fr auto;
  gap:5px;
  align-items:center;
}
.control-cell input[type="range"] { width:100%; min-width:0; }
.volume-control input[type="range"], .master-control { accent-color:#4da3ff; }
.low-control input[type="range"] { accent-color:#e67e22; }
.mid-control input[type="range"] { accent-color:#9b59b6; }
.high-control input[type="range"] { accent-color:#2ecc71; }
.control-value {
  width:42px;
  text-align:right;
  font-size:10px;
  opacity:.72;
  font-variant-numeric:tabular-nums;
}
.eq-reset { font-size:10px; min-height:28px; }

.master-row {
  display:grid;
  grid-template-columns:82px 48px 1fr;
  gap:8px;
  align-items:center;
  margin-top:10px;
  padding-top:9px;
  border-top:1px solid color-mix(in srgb, var(--st-text-color) 18%, transparent);
}
.master-name { font-weight:900; }
.master-value {
  font-size:11px;
  opacity:.75;
  font-variant-numeric:tabular-nums;
}
.master-volume { width:100%; }

.meter-box {
  display:flex;
  align-items:center;
  gap:6px;
  flex-wrap:wrap;
  font-size:12px;
  margin:4px 0 12px;
  padding:7px 9px;
  border-radius:8px;
  background:color-mix(in srgb, var(--st-text-color) 5%, transparent);
}
.meter-box input {
  background:color-mix(in srgb, var(--st-text-color) 5%, transparent);
  color:var(--st-text-color);
  border:1px solid color-mix(in srgb, var(--st-text-color) 25%, transparent);
  border-radius:5px;
  padding:3px 5px;
}
.meter-num,.meter-den { width:52px; }
.meter-group { width:92px; }
.meter-state { opacity:.68; margin-left:auto; }

.karaoke {
  position:relative;
  min-height:238px;
  overflow:hidden;
  border-radius:10px;
  padding:14px 12px 12px;
  background:color-mix(in srgb, var(--st-text-color) 5%, transparent);
}
.future-hint {
  position:absolute;
  left:calc(38% + 8px);
  top:5px;
  z-index:6;
  font-size:9px;
  opacity:.42;
  pointer-events:none;
}
.playhead {
  position:absolute;
  left:38%;
  top:12px;
  bottom:12px;
  width:2px;
  z-index:5;
  background:color-mix(in srgb, #ffffff 58%, transparent);
  box-shadow:0 0 0 1px color-mix(in srgb, #000000 18%, transparent);
  pointer-events:none;
}
.timeline-row {
  display:grid;
  grid-template-columns:64px 1fr;
  align-items:center;
  min-height:70px;
}
.timeline-label {
  position:relative;
  z-index:6;
  font-size:11px;
  font-weight:800;
  opacity:.78;
  padding-right:8px;
  color:var(--st-text-color);
}
.timeline-viewport {
  position:relative;
  overflow:hidden;
  height:66px;
}
.timeline-track {
  position:absolute;
  left:0;
  top:0;
  height:100%;
  will-change:transform;
  transform:translate3d(0,0,0);
}
.chord-track,.lyric-track,.backing-track { white-space:nowrap; }

.lyric-token {
  position:absolute;
  top:18px;
  display:inline-block;
  font-size:27px;
  font-weight:760;
  opacity:.34;
  transition:opacity 70ms linear;
}
.lyric-token.past { opacity:.60; }
.lyric-token.current {
  opacity:1;
  font-weight:900;
  text-decoration:underline;
  text-decoration-thickness:3px;
  text-underline-offset:6px;
}
.lead-row .lyric-token { color:#f4f4f4; }
.backing-row .lyric-token {
  font-size:22px;
  color:#d49bff;
  opacity:.46;
}
.backing-row .lyric-token.current {
  color:#f0c8ff;
  opacity:1;
}

.chord-marker {
  position:absolute;
  top:14px;
  display:inline-block;
  font-family:Consolas,"Courier New",monospace;
  font-size:20px;
  font-weight:900;
  padding:3px 6px;
  border-radius:5px;
  background:color-mix(in srgb, #4da3ff 20%, #15181d);
  border:1px solid color-mix(in srgb, #4da3ff 28%, transparent);
  transition:background 70ms linear, border-color 70ms linear;
}
.chord-marker.active {
  background:color-mix(in srgb, #4da3ff 42%, #15181d);
  border-color:color-mix(in srgb, #4da3ff 72%, transparent);
}
.hint { margin-top:10px; font-size:11px; opacity:.66; }

@media(max-width:950px) {
  .mixer-head { display:none; }
  .track { grid-template-columns:1fr 58px; }
  .track-name { grid-column:1; }
  .track-toggle { grid-column:2; justify-self:end; }
  .control-cell, .eq-reset { grid-column:1 / -1; }
  .eq-reset { justify-self:start; }
}
"""

_JS = r"""
export default function(component) {
  const data = component.data || {};
  const root = component.parentElement;

  const defs = Array.isArray(data.tracks) ? data.tracks : [];
  const words = Array.isArray(data.words) ? data.words : [];
  const leadInput = Array.isArray(data.lead_words) ? data.lead_words : words;
  const backingInput = Array.isArray(data.backing_words) ? data.backing_words : [];
  const beats = Array.isArray(data.beats) ? data.beats : [];
  const meterDefault = data.meter_default || {signature:"4/4", grouping:""};

  const playButton = root.querySelector(".play");
  const pauseButton = root.querySelector(".pause");
  const stopButton = root.querySelector(".stop");
  const seek = root.querySelector(".seek");
  const timeLabel = root.querySelector(".time");

  const presetOriginal = root.querySelector(".preset-original");
  const presetStems = root.querySelector(".preset-stems");
  const sourceState = root.querySelector(".source-state");

  const tracksNode = root.querySelector(".tracks");
  const masterVolume = root.querySelector(".master-volume");
  const masterValue = root.querySelector(".master-value");

  const numInput = root.querySelector(".meter-num");
  const denInput = root.querySelector(".meter-den");
  const groupingInput = root.querySelector(".meter-group");
  const meterState = root.querySelector(".meter-state");

  const leadViewport = root.querySelector(".lyric-viewport");
  const leadTrack = root.querySelector(".lyric-track");
  const chordViewport = root.querySelector(".chord-viewport");
  const chordTrack = root.querySelector(".chord-track");
  const backingRow = root.querySelector(".backing-row");
  const backingViewport = root.querySelector(".backing-viewport");
  const backingTrack = root.querySelector(".backing-track");

  const trackState = defs.map((track) => ({
    enabled:Boolean(track.enabled),
    volume:Number(track.volume ?? .8),
    low:Number(track.low ?? 0),
    mid:Number(track.mid ?? 0),
    high:Number(track.high ?? 0),
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

  const anchorRatio = .38;

  function fmt(seconds) {
    const t = Math.max(0, Number(seconds) || 0);
    const m = Math.floor(t / 60);
    return m + ":" + String(Math.floor(t % 60)).padStart(2,"0");
  }

  function currentTime() {
    if (!playing || !context) return position;
    return Math.max(
      0,
      Math.min(duration, position + (context.currentTime - startedAtContextTime))
    );
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
    if (!Number.isFinite(avg) || avg <= .0001) return 1.0;
    return Math.max(.72, Math.min(1.25, 1 / avg));
  }

  function applyTrackState(index, smooth=true) {
    if (!ready || !trackNodes[index] || !context) return;
    const state = trackState[index];
    const nodes = trackNodes[index];
    const now = context.currentTime;

    const setValue = (param, value) => {
      if (smooth) param.setTargetAtTime(value, now, .015);
      else param.value = value;
    };

    setValue(nodes.lowGain.gain, dbToLinear(state.low));
    setValue(nodes.midGain.gain, dbToLinear(state.mid));
    setValue(nodes.highGain.gain, dbToLinear(state.high));
    const enabledGain = state.enabled ? state.volume : 0;
    setValue(nodes.trackGain.gain, enabledGain * compensationFor(state));
  }

  function applyMasterState(smooth=true) {
    if (!ready || !masterGain || !context) return;
    const now = context.currentTime;
    if (smooth) masterGain.gain.setTargetAtTime(masterState, now, .015);
    else masterGain.gain.value = masterState;
  }

  function sourceModeLabel() {
    const originalIndex = defs.findIndex(d => d.name === "original");
    const originalOn = originalIndex >= 0 && trackState[originalIndex].enabled;
    const stemOn = defs.some((d,i) => d.name !== "original" && trackState[i].enabled);
    if (originalOn && !stemOn) return "Original";
    if (!originalOn && stemOn) return "Mix STEM";
    if (originalOn && stemOn) return "Original + STEM";
    return "Muet";
  }

  function refreshSourceState() {
    sourceState.textContent = sourceModeLabel();
  }

  function setPreset(mode) {
    defs.forEach((def,index) => {
      if (mode === "original") {
        trackState[index].enabled = def.name === "original";
      } else {
        trackState[index].enabled = def.name !== "original";
      }
      const checkbox = root.querySelector(`[data-track-on="${index}"]`);
      if (checkbox) checkbox.checked = trackState[index].enabled;
      applyTrackState(index);
    });
    refreshSourceState();
  }

  // -------- Meter / presentation only --------
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

  function parseGrouping(n,d,text) {
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
    const groups = parseGrouping(n,d,groupingInput.value);
    const grouped = d >= 8 && groups.some(x => x > 1);
    return {
      n,d,groups,grouped,
      beatsPerMeasure: grouped ? groups.length : n
    };
  }

  let renderedMeterKey = "";
  function persistMeter() {
    const m = meter();
    try {
      localStorage.setItem(storageKey, JSON.stringify({
        numerator:m.n,
        denominator:m.d,
        grouping:groupingInput.value
      }));
    } catch (_) {}
    meterState.textContent =
      m.n + "/" + m.d + " · " +
      (groupingInput.value.trim() || m.groups.join("+"));
    renderedMeterKey = "";
  }

  [numInput,denInput,groupingInput].forEach(el => {
    el.addEventListener("change", persistMeter);
    el.addEventListener("input", persistMeter);
  });

  // -------- Continuous lyrics geometry --------
  function normalizedWords(input) {
    return (Array.isArray(input) ? input : [])
      .map(w => ({
        text:String(w.text || "").trim(),
        start:Number(w.start || 0),
        end:Number(w.end || w.start || 0),
      }))
      .filter(w => w.text && Number.isFinite(w.start) && Number.isFinite(w.end))
      .sort((a,b)=>a.start-b.start || a.end-b.end);
  }

  const leadWords = normalizedWords(leadInput);
  const backingWords = normalizedWords(backingInput);
  const masterWords = normalizedWords([...leadWords,...backingWords]);

  let masterVisualX = [];
  function buildMasterGeometry() {
    let cursor = 0;
    masterVisualX = [];
    masterWords.forEach(w => {
      masterVisualX.push(cursor);
      cursor += Math.max(34, w.text.length * 15 + 18);
    });
    return Math.max(1, cursor + 260);
  }
  const masterWidth = buildMasterGeometry();

  function visualXForTime(time) {
    if (!masterWords.length) return 0;
    const t = Number(time || 0);
    if (masterWords.length === 1) return masterVisualX[0];

    const first = masterWords[0];
    if (t <= first.start) {
      const span = Math.max(.25, first.start);
      const p = Math.max(0, Math.min(1, t / span));
      const preview = Math.min(360, Math.max(180, leadViewport.clientWidth * .32));
      return masterVisualX[0] - preview * (1-p);
    }

    let low=0, high=masterWords.length-1, left=0;
    while (low <= high) {
      const mid=(low+high)>>1;
      if (masterWords[mid].start <= t) {
        left=mid; low=mid+1;
      } else high=mid-1;
    }

    if (left >= masterWords.length-1) {
      const last = masterWords[masterWords.length-1];
      return masterVisualX[masterVisualX.length-1] +
        Math.min(260, Math.max(0,t-last.start)*28);
    }

    const a=masterWords[left], b=masterWords[left+1];
    const ta=a.start, tb=Math.max(ta+.04,b.start);
    const p=Math.max(0,Math.min(1,(t-ta)/(tb-ta)));
    return masterVisualX[left] +
      (masterVisualX[left+1]-masterVisualX[left])*p;
  }

  function createLane(track, sourceWords) {
    track.innerHTML = "";
    track.style.width = masterWidth + "px";
    return sourceWords.map(w => {
      const span=document.createElement("span");
      span.className="lyric-token";
      span.textContent=w.text;
      span.style.left=visualXForTime(w.start)+"px";
      track.appendChild(span);
      return span;
    });
  }

  const leadNodes=createLane(leadTrack,leadWords);
  const backingNodes=createLane(backingTrack,backingWords);
  backingRow.style.display = backingWords.length ? "grid" : "none";

  function activeWordIndex(sourceWords,time) {
    if (!sourceWords.length) return -1;
    let low=0, high=sourceWords.length-1, answer=-1;
    while (low<=high) {
      const mid=(low+high)>>1;
      if (sourceWords[mid].start<=time) {
        answer=mid; low=mid+1;
      } else high=mid-1;
    }
    if (answer<0) return -1;
    const w=sourceWords[answer];
    return time <= Math.max(w.end,w.start+.06) ? answer : -1;
  }

  function translateLyricTimeline(track,viewport,time) {
    if (!track || !viewport) return;
    const anchor=viewport.clientWidth*anchorRatio;
    track.style.transform =
      "translate3d(" + (anchor-visualXForTime(time)).toFixed(2) + "px,0,0)";
  }

  // -------- Chords / measure presentation --------
  function measureNotation(measureIndex,m) {
    const startBeat=measureIndex*m.beatsPerMeasure;
    if (startBeat>=beats.length) return null;
    const beatSlice=beats.slice(startBeat,startBeat+m.beatsPerMeasure);
    if (!beatSlice.length) return null;

    let notation="";
    let prevChord=null;
    beatSlice.forEach((beat,localIndex) => {
      const chord=String(beat.chord || ".").trim() || ".";
      let token;
      if (chord === ".") token=".";
      else if (localIndex===0) token=chord;
      else if (chord===prevChord) token="-";
      else token=chord;

      if (m.grouped) {
        const count=Math.max(1,Number(m.groups[localIndex] || 1));
        if (token === ".") notation += ".".repeat(count);
        else if (token === "-") notation += "-".repeat(count);
        else notation += token + "-".repeat(Math.max(0,count-1));
      } else notation += token;

      prevChord=chord;
    });

    return {
      notation,
      start:Number(beatSlice[0].start || 0),
      end:Number(beatSlice[beatSlice.length-1].end || beatSlice[beatSlice.length-1].start || 0),
    };
  }

  let chordMeasures=[];
  let chordNodes=[];
  const measureSlotWidth=138;

  function rebuildChordTimeline() {
    const m=meter();
    const key=m.n+"/"+m.d+"|"+m.groups.join("+");
    if (key===renderedMeterKey && chordNodes.length) return;

    renderedMeterKey=key;
    chordTrack.innerHTML="";
    chordMeasures=[];
    chordNodes=[];

    const count=Math.ceil(beats.length/m.beatsPerMeasure);
    for (let i=0;i<count;i++) {
      const item=measureNotation(i,m);
      if (!item) continue;
      item.visualX=i*measureSlotWidth;
      chordMeasures.push(item);

      const marker=document.createElement("span");
      marker.className="chord-marker";
      marker.textContent=item.notation;
      marker.style.left=item.visualX+"px";
      marker.style.width=(measureSlotWidth-12)+"px";
      marker.style.boxSizing="border-box";
      marker.style.overflow="hidden";
      chordTrack.appendChild(marker);
      chordNodes.push(marker);
    }
    chordTrack.style.width=
      Math.max(1,chordMeasures.length*measureSlotWidth+220)+"px";
  }

  function chordVisualXForTime(time) {
    if (!chordMeasures.length) return 0;
    const t=Number(time || 0);
    if (t<=chordMeasures[0].start) return chordMeasures[0].visualX;

    for (let i=0;i<chordMeasures.length;i++) {
      const m=chordMeasures[i];
      if (t>=m.start && t<Math.max(m.end,m.start+.02)) {
        const p=Math.max(0,Math.min(1,(t-m.start)/Math.max(.02,m.end-m.start)));
        return m.visualX+p*measureSlotWidth;
      }
    }
    return chordMeasures[chordMeasures.length-1].visualX+measureSlotWidth;
  }

  function renderConductor(time) {
    rebuildChordTimeline();

    const chordAnchor=chordViewport.clientWidth*anchorRatio;
    chordTrack.style.transform =
      "translate3d(" + (chordAnchor-chordVisualXForTime(time)).toFixed(2) + "px,0,0)";

    translateLyricTimeline(leadTrack,leadViewport,time);
    if (backingWords.length) {
      translateLyricTimeline(backingTrack,backingViewport,time);
    }

    const currentLead=activeWordIndex(leadWords,time);
    leadNodes.forEach((node,i) => {
      node.classList.toggle("past", time>leadWords[i].end);
      node.classList.toggle("current", i===currentLead);
    });

    const currentBacking=activeWordIndex(backingWords,time);
    backingNodes.forEach((node,i) => {
      node.classList.toggle("past", time>backingWords[i].end);
      node.classList.toggle("current", i===currentBacking);
    });

    chordNodes.forEach((node,i) => {
      const m=chordMeasures[i];
      node.classList.toggle("active",Boolean(m && time>=m.start && time<m.end));
    });
  }

  persistMeter();
  renderConductor(0);

  // -------- Mixer UI --------
  function makeSlider(index,field,min,max,step,suffix,categoryClass="") {
    const wrap=document.createElement("div");
    wrap.className="control-cell" + (categoryClass ? " "+categoryClass : "");

    const slider=document.createElement("input");
    slider.type="range";
    slider.min=String(min);
    slider.max=String(max);
    slider.step=String(step);
    slider.value=String(trackState[index][field]);

    const value=document.createElement("span");
    value.className="control-value";

    function renderValue() {
      const v=Number(slider.value);
      value.textContent = suffix==="dB"
        ? (v>0?"+":"")+v.toFixed(0)+" dB"
        : Math.round(v*100)+"%";
    }

    slider.addEventListener("input",() => {
      trackState[index][field]=Number(slider.value);
      renderValue();
      applyTrackState(index);
    });

    renderValue();
    wrap.append(slider,value);
    return {wrap,slider,renderValue};
  }

  const rowControls=[];
  defs.forEach((def,index) => {
    const row=document.createElement("div");
    row.className="track";

    const name=document.createElement("div");
    name.className="track-name";
    name.textContent=String(def.label || def.name || "Piste");

    const toggleLabel=document.createElement("label");
    toggleLabel.className="track-toggle";
    const on=document.createElement("input");
    on.type="checkbox";
    on.checked=trackState[index].enabled;
    on.dataset.trackOn=String(index);
    on.addEventListener("change",() => {
      trackState[index].enabled=on.checked;
      applyTrackState(index);
      refreshSourceState();
    });
    toggleLabel.append(on,document.createTextNode(" Actif"));

    const volume=makeSlider(index,"volume",0,1.25,.01,"","volume-control");
    const low=makeSlider(index,"low",-12,12,1,"dB","low-control");
    const mid=makeSlider(index,"mid",-12,12,1,"dB","mid-control");
    const high=makeSlider(index,"high",-12,12,1,"dB","high-control");

    const reset=document.createElement("button");
    reset.className="eq-reset";
    reset.type="button";
    reset.textContent="Reset EQ";
    reset.addEventListener("click",() => {
      trackState[index].low=0;
      trackState[index].mid=0;
      trackState[index].high=0;
      low.slider.value="0";
      mid.slider.value="0";
      high.slider.value="0";
      low.renderValue(); mid.renderValue(); high.renderValue();
      applyTrackState(index);
    });

    row.append(
      name,toggleLabel,volume.wrap,low.wrap,mid.wrap,high.wrap,reset
    );
    tracksNode.appendChild(row);
    rowControls.push({on,volume,low,mid,high});
  });

  presetOriginal.addEventListener("click",()=>setPreset("original"));
  presetStems.addEventListener("click",()=>setPreset("stems"));

  masterVolume.addEventListener("input",() => {
    masterState=Number(masterVolume.value || 1);
    masterValue.textContent=Math.round(masterState*100)+"%";
    applyMasterState();
  });

  refreshSourceState();

  // -------- WebAudio engine / proven 3-band crossover --------
  async function ensureReady() {
    if (ready) {
      if (context.state==="suspended") await context.resume();
      return;
    }

    playButton.disabled=true;
    playButton.textContent="Chargement audio…";

    context=new (window.AudioContext || window.webkitAudioContext)({
      latencyHint:"interactive"
    });
    masterGain=context.createGain();
    masterGain.gain.value=masterState;
    masterGain.connect(context.destination);

    decoded=[];
    trackNodes=[];

    for (let i=0;i<defs.length;i++) {
      const response=await fetch(String(defs[i].url || ""),{cache:"force-cache"});
      if (!response.ok) {
        throw new Error("HTTP média "+response.status+" pour "+String(defs[i].label || defs[i].name));
      }

      const buffer=await context.decodeAudioData(await response.arrayBuffer());
      decoded.push(buffer);

      const lowLP=context.createBiquadFilter();
      lowLP.type="lowpass";
      lowLP.frequency.value=250;
      lowLP.Q.value=.707;

      const midHP=context.createBiquadFilter();
      midHP.type="highpass";
      midHP.frequency.value=250;
      midHP.Q.value=.707;

      const midLP=context.createBiquadFilter();
      midLP.type="lowpass";
      midLP.frequency.value=4000;
      midLP.Q.value=.707;

      const highHP=context.createBiquadFilter();
      highHP.type="highpass";
      highHP.frequency.value=4000;
      highHP.Q.value=.707;

      const lowGain=context.createGain();
      const midGain=context.createGain();
      const highGain=context.createGain();
      const bandSum=context.createGain();
      const trackGain=context.createGain();

      lowLP.connect(lowGain); lowGain.connect(bandSum);
      midHP.connect(midLP); midLP.connect(midGain); midGain.connect(bandSum);
      highHP.connect(highGain); highGain.connect(bandSum);
      bandSum.connect(trackGain);
      trackGain.connect(masterGain);

      trackNodes.push({
        lowLP,midHP,midLP,highHP,
        lowGain,midGain,highGain,bandSum,trackGain
      });

      if (i===0) duration=Number(buffer.duration || 0);
    }

    seek.max=String(Math.max(.001,duration));
    ready=true;
    trackState.forEach((_,i)=>applyTrackState(i,false));
    applyMasterState(false);

    playButton.disabled=false;
    playButton.textContent="▶ Lecture";
  }

  function stopSources() {
    sources.forEach(source => {
      try { source.stop(); } catch (_) {}
      try { source.disconnect(); } catch (_) {}
    });
    sources=[];
  }

  function startSources(offset) {
    stopSources();
    const when=context.currentTime+.030;

    sources=decoded.map((buffer,index) => {
      const source=context.createBufferSource();
      source.buffer=buffer;

      // Same source fans out into the three crossover branches.
      source.connect(trackNodes[index].lowLP);
      source.connect(trackNodes[index].midHP);
      source.connect(trackNodes[index].highHP);

      const safeOffset=Math.max(
        0,
        Math.min(Number(offset)||0,Math.max(0,buffer.duration-.001))
      );
      source.start(when,safeOffset);
      return source;
    });

    position=Math.max(0,Math.min(duration,Number(offset)||0));
    startedAtContextTime=when;
    playing=true;
  }

  async function playAll() {
    await ensureReady();
    if (context.state==="suspended") await context.resume();
    if (playing) return;
    if (position>=duration-.01) position=0;
    startSources(position);
  }

  function pauseAll() {
    if (!playing) return;
    position=currentTime();
    playing=false;
    stopSources();
  }

  function stopAll() {
    playing=false;
    stopSources();
    position=0;
    seek.value="0";
    renderConductor(0);
    timeLabel.textContent="0:00 / "+fmt(duration);
  }

  function seekTo(value) {
    position=Math.max(0,Math.min(duration,Number(value)||0));
    if (playing) startSources(position);
    renderConductor(position);
  }

  playButton.addEventListener("click",()=>playAll().catch(e => {
    playButton.disabled=false;
    playButton.textContent="▶ Lecture";
    console.error(e);
  }));
  pauseButton.addEventListener("click",pauseAll);
  stopButton.addEventListener("click",stopAll);
  seek.addEventListener("input",()=>seekTo(Number(seek.value || 0)));

  function tick() {
    if (disposed) return;
    const t=currentTime();
    seek.value=String(t);
    timeLabel.textContent=fmt(t)+" / "+fmt(duration);
    renderConductor(t);
    if (playing && t>=duration-.01) stopAll();
    raf=requestAnimationFrame(tick);
  }

  tick();

  return function() {
    disposed=true;
    if (raf!==null) cancelAnimationFrame(raf);
    stopSources();
    try { if (context) context.close(); } catch (_) {}
  };
}
"""

_COMPONENT = st.components.v2.component(
    "ezscore_karaoke_stem_player_r9",
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
    # Single unified player: original + all persisted canonical STEMs.
    # Every buffer is started on the same WebAudio clock and offset.
    previews = prepare_browser_previews(source, stems, preview_dir)

    tracks: list[dict[str, Any]] = []

    def pack(
        name: str,
        label: str,
        path: Path,
        *,
        enabled: bool,
        volume: float,
    ) -> None:
        preview = previews[name]
        tracks.append(
            {
                "name": name,
                "label": label,
                "url": register_media_url(
                    preview,
                    coordinates=f"{key}:unified:{name}",
                    mimetype="audio/mpeg",
                ),
                "enabled": enabled,
                "volume": volume,
                "low": 0.0,
                "mid": 0.0,
                "high": 0.0,
            }
        )

    # Default = original only. "Mix STEM" switches this off and enables stems.
    pack("original", "Original", source, enabled=True, volume=1.0)

    labels = {
        "vocals": "Chant",
        "drums": "Batterie",
        "bass": "Basse",
        "other": "Other",
    }
    defaults = {
        "vocals": 0.90,
        "drums": 0.75,
        "bass": 0.75,
        "other": 0.75,
    }
    for name in STEM_NAMES:
        path = stems.get(name)
        if path is not None and name in previews:
            pack(
                name,
                labels.get(name, name.title()),
                path,
                enabled=False,
                volume=defaults.get(name, 0.75),
            )

    lead_words = list(words or [])
    player_words = list(lead_words)
    backing_words: list[dict[str, Any]] = []
    conductor: dict[str, Any] = {
        "beats": [],
        "meter_default": _meter_defaults(preview_dir),
    }

    if player_words:
        try:
            vocal_cache = _vocal_whisper_cache_path(preview_dir)
            if vocal_cache.is_file():
                player_words = _ensure_vocal_whisper_supplement(
                    source, stems, preview_dir, lead_words
                )
            else:
                with st.spinner(
                    "Complément paroles sur le stem voix "
                    "(vocalises / omissions Whisper)…"
                ):
                    player_words = _ensure_vocal_whisper_supplement(
                        source, stems, preview_dir, lead_words
                    )
            backing_words = _supplement_only_words(
                lead_words,
                player_words,
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
        "Lecteur unique : Original ou mix STEM avec EQ 3 bandes · Chant + Chœurs + "
        "accords synchronisés sur la même horloge. La signature et le groupement "
        "modifient la présentation sans changer les timestamps audio."
        if player_words
        else
        "Lecteur STEM prêt. Le conducteur apparaîtra après l'analyse des paroles."
    )

    # Re-analysis works from the persisted source audio; no MP3 re-import.
    if player_words:
        audio_hash = preview_dir.parent.name
        controls = st.columns(3)

        with controls[0]:
            if st.button(
                "↻ Ré-analyser paroles",
                width="stretch",
                key=f"{key}_reanalyze_lyrics",
                help="Relance Whisper sur l'audio déjà stocké, sans réimport.",
            ):
                original_cache = preview_dir.parent / "whisper_original_small.json"
                vocal_cache = _vocal_whisper_cache_path(preview_dir)
                for cache in (original_cache, vocal_cache):
                    if cache.is_file():
                        cache.unlink()

                from ezscore.ui.stem_lab_analysis import _transcribe_original
                with st.spinner("Ré-analyse Whisper sur l'audio existant…"):
                    _transcribe_original(source, audio_hash)
                st.rerun()

        with controls[1]:
            if st.button(
                "↻ Ré-analyser accords",
                width="stretch",
                key=f"{key}_reanalyze_chords",
                help="Recalcule rythme + harmonie depuis l'audio/stems déjà stockés.",
            ):
                for cache in (
                    _conductor_cache_path(preview_dir),
                    preview_dir.parent / "chord_analysis_lv_chordia.json",
                ):
                    if cache.is_file():
                        cache.unlink()
                with st.spinner("Ré-analyse rythme + accords sur les fichiers existants…"):
                    _build_conductor_timeline(source, stems, preview_dir)
                st.rerun()

        with controls[2]:
            if st.button(
                "↻ Ré-analyser tout",
                type="primary",
                width="stretch",
                key=f"{key}_reanalyze_all",
                help="Relance paroles + complément vocal + rythme + accords sans réimporter l'audio.",
            ):
                for cache in (
                    preview_dir.parent / "whisper_original_small.json",
                    _vocal_whisper_cache_path(preview_dir),
                    _conductor_cache_path(preview_dir),
                    preview_dir.parent / "chord_analysis_lv_chordia.json",
                ):
                    if cache.is_file():
                        cache.unlink()

                from ezscore.ui.stem_lab_analysis import _transcribe_original
                with st.spinner("Ré-analyse complète depuis l'audio déjà enregistré…"):
                    speech = _transcribe_original(source, audio_hash)
                    refreshed_words = list(speech.get("words", []) or [])
                    _ensure_vocal_whisper_supplement(
                        source, stems, preview_dir, refreshed_words
                    )
                    _build_conductor_timeline(source, stems, preview_dir)
                st.rerun()

    _COMPONENT(
        data={
            "tracks": tracks,
            "words": player_words,
            "lead_words": lead_words,
            "backing_words": backing_words,
            "beats": list(conductor.get("beats", []) or []),
            "meter_default": dict(conductor.get("meter_default", {}) or {}),
            "storage_key": str(key),
        },
        key=key,
        width="stretch",
        height=900 if player_words else 620,
    )
