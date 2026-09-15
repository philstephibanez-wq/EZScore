"""Experimental vocal melody analysis for EZScore.

This module is deliberately additive:
- it never changes chord / lyric / phoneme timestamps;
- it writes its own cache under data/analysis/vocal_pitch;
- visual block refinement is optional and only runs when explicitly requested.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import librosa
import numpy as np


APP_DIR = Path(__file__).resolve().parents[2]
VOCAL_CACHE_DIR = APP_DIR / "data" / "analysis" / "vocal_pitch"
VOCAL_CACHE_DIR.mkdir(parents=True, exist_ok=True)

VOCAL_SCHEMA_VERSION = 3
VOCAL_ANALYSIS_ENGINE = "pyin-v3-adaptive-voicing"
VOCAL_MEDIAN_WIDTH = 7
VOCAL_NOTE_HYSTERESIS_CENTS = 70.0
VOCAL_NOTE_CHANGE_STABLE_MS = 100.0

# Voicing sensitivity: slightly more permissive, but weak frames are only
# recovered when their energy and melodic continuity support them.
VOCAL_CONFIDENCE_DEMUCS = 0.48
VOCAL_CONFIDENCE_MIX = 0.66
VOCAL_WEAK_CONFIDENCE_MARGIN = 0.10
VOCAL_CONTINUITY_WINDOW_FRAMES = 4
VOCAL_CONTINUITY_MAX_SEMITONES = 1.25
VOCAL_RMS_FLOOR_RATIO = 0.55

# Monitoring-only compensation. The analytical vocal timeline itself is never
# shifted; browser playback starts vocal MIDI 40 ms earlier for A/B listening.
VOCAL_MONITOR_OFFSET_SECONDS = -0.040

DEFAULT_VOCAL_PROGRAM = 53  # GM Voice Oohs, zero-based

VOCAL_MIDI_INSTRUMENTS = {
    "Alto Sax": 65,
    "Tenor Sax": 66,
    "Soprano Sax": 64,
    "Baritone Sax": 67,
    "Voice Oohs": 53,
    "Acoustic Grand Piano": 0,
}


def demucs_available() -> bool:
    try:
        return importlib.util.find_spec("demucs") is not None
    except Exception:
        return False


def _cache_path(audio_hash: str) -> Path:
    safe = "".join(ch for ch in str(audio_hash or "").lower() if ch in "0123456789abcdef")
    if not safe:
        safe = hashlib.sha256(str(audio_hash).encode("utf-8")).hexdigest()
    return VOCAL_CACHE_DIR / f"{safe}.json"


def load_vocal_analysis(audio_hash: str) -> dict[str, Any] | None:
    path = _cache_path(audio_hash)
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if int(payload.get("schema_version", 0) or 0) != VOCAL_SCHEMA_VERSION:
        return None
    return payload


def save_vocal_analysis(audio_hash: str, payload: dict[str, Any]) -> Path:
    path = _cache_path(audio_hash)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    tmp.replace(path)
    return path


def delete_vocal_analysis(audio_hash: str) -> None:
    path = _cache_path(audio_hash)
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def _write_audio_temp(audio_bytes: bytes, extension: str, directory: Path) -> Path:
    suffix = str(extension or ".mp3").lower()
    if not suffix.startswith("."):
        suffix = "." + suffix
    path = directory / f"source{suffix}"
    path.write_bytes(audio_bytes)
    return path


def _run_demucs_vocals(source: Path, directory: Path) -> tuple[Path | None, str | None]:
    if not demucs_available():
        return None, "Demucs non installé"

    out_dir = directory / "demucs"
    cmd = [
        sys.executable,
        "-m",
        "demucs",
        "--two-stems",
        "vocals",
        "-n",
        "htdemucs",
        "-o",
        str(out_dir),
        str(source),
    ]
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=900,
            check=False,
        )
    except Exception as exc:
        return None, f"Demucs: {exc}"

    if proc.returncode != 0:
        tail = "\n".join((proc.stdout or "").splitlines()[-6:])
        return None, f"Demucs code {proc.returncode}: {tail}"

    candidates = list(out_dir.glob("*/source/vocals.wav"))
    if not candidates:
        candidates = list(out_dir.glob("**/vocals.wav"))
    if not candidates:
        return None, "Demucs terminé sans piste vocals.wav"

    return candidates[0], None


def _median_filter(values: np.ndarray, width: int = 5) -> np.ndarray:
    result = values.copy()
    half = max(1, int(width) // 2)
    for i in range(len(values)):
        lo = max(0, i - half)
        hi = min(len(values), i + half + 1)
        window = values[lo:hi]
        finite = window[np.isfinite(window)]
        if finite.size:
            result[i] = float(np.median(finite))
    return result


def _merge_short_gaps(notes: list[dict[str, Any]], max_gap: float = 0.08) -> list[dict[str, Any]]:
    if not notes:
        return []
    merged = [dict(notes[0])]
    for note in notes[1:]:
        previous = merged[-1]
        gap = float(note["start"]) - float(previous["end"])
        if int(note["midi"]) == int(previous["midi"]) and gap <= max_gap:
            d0 = max(0.001, float(previous["end"]) - float(previous["start"]))
            d1 = max(0.001, float(note["end"]) - float(note["start"]))
            previous["end"] = float(note["end"])
            previous["confidence"] = (
                float(previous["confidence"]) * d0 + float(note["confidence"]) * d1
            ) / (d0 + d1)
            previous["duration"] = float(previous["end"]) - float(previous["start"])
        else:
            merged.append(dict(note))
    return merged



def _recover_continuous_weak_voicing(
    *,
    f0: np.ndarray,
    voiced_flag: np.ndarray,
    voiced_prob: np.ndarray,
    rms: np.ndarray,
    confidence_floor: float,
    strong_valid: np.ndarray,
    window_frames: int = VOCAL_CONTINUITY_WINDOW_FRAMES,
    max_semitones: float = VOCAL_CONTINUITY_MAX_SEMITONES,
    weak_margin: float = VOCAL_WEAK_CONFIDENCE_MARGIN,
    rms_floor_ratio: float = VOCAL_RMS_FLOOR_RATIO,
) -> np.ndarray:
    """Recover quiet sung frames without broadly lowering the detector gate.

    A weak pYIN frame is accepted only when:
    - pYIN still considers it voiced;
    - confidence is near the normal threshold;
    - its RMS is not in the very quiet tail of the vocal stem/mix;
    - a nearby strong frame carries a compatible pitch.

    This mainly restores note attacks/tails that were being clipped while
    rejecting isolated low-confidence detections.
    """
    strong_valid = np.asarray(strong_valid, dtype=bool)
    recovered = strong_valid.copy()

    finite_rms = rms[np.isfinite(rms)]
    if finite_rms.size:
        # Relative to this song/stem, never an absolute dB threshold.
        rms_reference = float(np.percentile(finite_rms, 35.0))
        rms_floor = max(1e-8, rms_reference * float(rms_floor_ratio))
    else:
        rms_floor = 0.0

    weak_floor = max(0.0, float(confidence_floor) - float(weak_margin))
    pitch_midi = np.full(len(f0), np.nan, dtype=float)
    finite_f0 = np.isfinite(f0) & (f0 > 0.0)
    pitch_midi[finite_f0] = librosa.hz_to_midi(f0[finite_f0])

    strong_indices = np.flatnonzero(strong_valid)
    if strong_indices.size == 0:
        return recovered

    for i in range(len(f0)):
        if recovered[i]:
            continue
        if not bool(voiced_flag[i]):
            continue
        if not np.isfinite(voiced_prob[i]) or float(voiced_prob[i]) < weak_floor:
            continue
        if not np.isfinite(pitch_midi[i]):
            continue
        if i >= len(rms) or not np.isfinite(rms[i]) or float(rms[i]) < rms_floor:
            continue

        lo = max(0, i - int(window_frames))
        hi = min(len(f0), i + int(window_frames) + 1)
        nearby = strong_indices[(strong_indices >= lo) & (strong_indices < hi)]
        if nearby.size == 0:
            continue

        nearest = int(
            nearby[np.argmin(np.abs(nearby.astype(int) - int(i)))]
        )
        if not np.isfinite(pitch_midi[nearest]):
            continue

        if abs(float(pitch_midi[i]) - float(pitch_midi[nearest])) <= float(max_semitones):
            recovered[i] = True

    return recovered


def _segment_notes(
    times: np.ndarray,
    midi_float: np.ndarray,
    voiced_prob: np.ndarray,
    hop_seconds: float,
    min_duration: float = 0.09,
    median_width: int = VOCAL_MEDIAN_WIDTH,
    hysteresis_cents: float = VOCAL_NOTE_HYSTERESIS_CENTS,
    stable_change_ms: float = VOCAL_NOTE_CHANGE_STABLE_MS,
) -> list[dict[str, Any]]:
    """Convert F0 frames to sung MIDI notes without turning vibrato into notes.

    The F0 detector keeps its full precision. Only note segmentation is made
    slightly less reactive:
    - a 7-frame median filter smooths local pitch wobble;
    - the current MIDI note is kept inside a 70-cent hysteresis band;
    - a candidate new note must remain stable for ~100 ms before the boundary
      is accepted.

    When a real note change is confirmed, its start is backdated to the first
    stable candidate frame, so the anti-vibrato filter does not add 100 ms of
    audible latency to the exported/player MIDI.
    """
    if len(times) == 0:
        return []

    smoothed = _median_filter(midi_float, width=max(3, int(median_width)))
    stable_frames = max(
        1,
        int(math.ceil((float(stable_change_ms) / 1000.0) / max(hop_seconds, 1e-6))),
    )
    hysteresis_semitones = max(0.50, float(hysteresis_cents) / 100.0)

    notes = []
    start_idx = None
    current = None
    candidate = None
    candidate_start = None

    def reset_candidate():
        nonlocal candidate, candidate_start
        candidate = None
        candidate_start = None

    def close(end_idx: int):
        nonlocal start_idx, current
        if start_idx is None or current is None:
            start_idx = None
            current = None
            reset_candidate()
            return

        if end_idx < start_idx:
            start_idx = None
            current = None
            reset_candidate()
            return

        start = float(times[start_idx])
        end = float(times[min(end_idx, len(times) - 1)] + hop_seconds)
        duration = max(0.0, end - start)
        if duration >= min_duration:
            segment = midi_float[start_idx:end_idx + 1]
            probs = voiced_prob[start_idx:end_idx + 1]
            valid_pitch = segment[np.isfinite(segment)]
            valid_prob = probs[np.isfinite(probs)]
            median_pitch = (
                float(np.median(valid_pitch))
                if valid_pitch.size
                else float(current)
            )
            confidence = (
                float(np.mean(valid_prob))
                if valid_prob.size
                else 0.0
            )
            midi_note = int(np.clip(round(median_pitch), 0, 127))
            notes.append({
                "start": round(start, 6),
                "end": round(end, 6),
                "duration": round(duration, 6),
                "midi": midi_note,
                "pitch_median": round(median_pitch, 4),
                "cents": round((median_pitch - midi_note) * 100.0, 2),
                "note": librosa.midi_to_note(midi_note, unicode=False),
                "confidence": round(confidence, 4),
            })

        start_idx = None
        current = None
        reset_candidate()

    for i, value in enumerate(smoothed):
        if not np.isfinite(value):
            if start_idx is not None:
                close(i - 1)
            continue

        proposed = int(np.rint(value))

        if start_idx is None:
            start_idx = i
            current = proposed
            reset_candidate()
            continue

        # Stay on the current note while the smoothed F0 remains inside the
        # hysteresis band. This is the main vibrato protection.
        if abs(float(value) - float(current)) < hysteresis_semitones:
            reset_candidate()
            continue

        # F0 really moved away from the current note. A new MIDI note is only
        # accepted if the same candidate persists long enough.
        if proposed == current:
            reset_candidate()
            continue

        if candidate != proposed:
            candidate = proposed
            candidate_start = i
            continue

        if candidate_start is None:
            candidate_start = i
            continue

        if (i - candidate_start + 1) < stable_frames:
            continue

        # Real transition confirmed. Preserve the true transition position:
        # close the previous note just before the candidate began and start the
        # new note at candidate_start, not at the confirmation frame.
        new_start = int(candidate_start)
        close(new_start - 1)
        start_idx = new_start
        current = proposed
        reset_candidate()

    if start_idx is not None:
        close(len(times) - 1)

    return _merge_short_gaps(notes)


def analyze_vocal_pitch(
    *,
    audio_bytes: bytes,
    extension: str,
    audio_hash: str,
    prefer_demucs: bool = True,
    sample_rate: int = 16000,
) -> dict[str, Any]:
    """Extract a monophonic sung-note timeline on the original audio timebase.

    Demucs is preferred when available. If it is unavailable or fails, pYIN runs
    on the original mix and the result is explicitly marked as a fallback.
    """
    with tempfile.TemporaryDirectory(prefix="ezscore_vocal_") as tmp_name:
        tmp = Path(tmp_name)
        source = _write_audio_temp(audio_bytes, extension, tmp)

        analysis_path = source
        source_kind = "mix-pyin"
        demucs_error = None

        if prefer_demucs:
            vocals_path, demucs_error = _run_demucs_vocals(source, tmp)
            if vocals_path is not None:
                analysis_path = vocals_path
                source_kind = "demucs-vocals-pyin"

        y, sr = librosa.load(str(analysis_path), sr=int(sample_rate), mono=True)
        if y.size == 0:
            raise RuntimeError("Audio vide après chargement.")

        frame_length = 2048
        hop_length = 256

        f0, voiced_flag, voiced_prob = librosa.pyin(
            y,
            fmin=librosa.note_to_hz("C2"),
            fmax=librosa.note_to_hz("C6"),
            sr=sr,
            frame_length=frame_length,
            hop_length=hop_length,
            fill_na=np.nan,
        )

        f0 = np.asarray(f0, dtype=float)
        voiced_flag = np.asarray(voiced_flag, dtype=bool)
        voiced_prob = np.asarray(voiced_prob, dtype=float)
        times = librosa.times_like(f0, sr=sr, hop_length=hop_length)

        confidence_floor = (
            VOCAL_CONFIDENCE_DEMUCS
            if source_kind.startswith("demucs")
            else VOCAL_CONFIDENCE_MIX
        )

        strong_valid = (
            voiced_flag
            & np.isfinite(f0)
            & np.isfinite(voiced_prob)
            & (voiced_prob >= confidence_floor)
        )

        # RMS is aligned on the same hop as pYIN. It is used only as a
        # relative support signal for weak frames, never as a hard absolute
        # loudness gate.
        rms = librosa.feature.rms(
            y=y,
            frame_length=frame_length,
            hop_length=hop_length,
            center=True,
        )[0]
        if len(rms) < len(f0):
            rms = np.pad(
                rms,
                (0, len(f0) - len(rms)),
                mode="edge" if len(rms) else "constant",
            )
        elif len(rms) > len(f0):
            rms = rms[:len(f0)]

        valid = _recover_continuous_weak_voicing(
            f0=f0,
            voiced_flag=voiced_flag,
            voiced_prob=voiced_prob,
            rms=np.asarray(rms, dtype=float),
            confidence_floor=confidence_floor,
            strong_valid=strong_valid,
        )

        midi_float = np.full(len(f0), np.nan, dtype=float)
        midi_float[valid] = librosa.hz_to_midi(f0[valid])

        notes = _segment_notes(
            times=times,
            midi_float=midi_float,
            voiced_prob=voiced_prob,
            hop_seconds=float(hop_length) / float(sr),
        )

        # Reject implausible isolated pitch specks in mix fallback.
        if source_kind == "mix-pyin":
            notes = [
                note
                for note in notes
                if float(note["duration"]) >= 0.12
                and float(note["confidence"]) >= 0.68
            ]

        payload = {
            "schema_version": VOCAL_SCHEMA_VERSION,
            "engine": VOCAL_ANALYSIS_ENGINE,
            "audio_hash": str(audio_hash),
            "timebase": "audio_seconds",
            "source": source_kind,
            "demucs_available": demucs_available(),
            "demucs_error": demucs_error,
            "sample_rate": int(sr),
            "hop_length": int(hop_length),
            "confidence_floor": float(confidence_floor),
            "voicing": {
                "demucs_confidence": float(VOCAL_CONFIDENCE_DEMUCS),
                "mix_confidence": float(VOCAL_CONFIDENCE_MIX),
                "weak_confidence_margin": float(VOCAL_WEAK_CONFIDENCE_MARGIN),
                "continuity_window_frames": int(VOCAL_CONTINUITY_WINDOW_FRAMES),
                "continuity_max_semitones": float(VOCAL_CONTINUITY_MAX_SEMITONES),
                "rms_floor_ratio": float(VOCAL_RMS_FLOOR_RATIO),
            },
            "segmentation": {
                "median_width": int(VOCAL_MEDIAN_WIDTH),
                "hysteresis_cents": float(VOCAL_NOTE_HYSTERESIS_CENTS),
                "stable_change_ms": float(VOCAL_NOTE_CHANGE_STABLE_MS),
            },
            "note_count": len(notes),
            "notes": notes,
        }
        save_vocal_analysis(audio_hash, payload)
        return payload



def build_vocal_midi_events(
    notes: list[dict[str, Any]],
    *,
    program: int = DEFAULT_VOCAL_PROGRAM,
    monitor_offset_seconds: float = VOCAL_MONITOR_OFFSET_SECONDS,
) -> list[dict[str, Any]]:
    """Build browser events from the persisted vocal-note timeline.

    `monitor_offset_seconds` is listening compensation only. Persisted analysis
    timestamps and exported vocal MIDI remain on the canonical audio timebase.
    """
    events: list[dict[str, Any]] = [{
        "time": 0.0,
        "status": 0xC1,
        "data1": int(program) & 0x7F,
        "data2": None,
        "kind": "program",
    }]

    for index, note in enumerate(notes or []):
        raw_start = max(0.0, float(note.get("start", 0.0) or 0.0))
        raw_end = max(
            raw_start + 0.04,
            float(note.get("end", raw_start + 0.04) or raw_start + 0.04),
        )
        offset = float(monitor_offset_seconds or 0.0)
        start = max(0.0, raw_start + offset)
        end = max(start + 0.04, raw_end + offset)
        midi_note = int(
            np.clip(int(note.get("midi", 60) or 60), 0, 127)
        )
        confidence = float(note.get("confidence", 0.75) or 0.75)
        velocity = int(
            np.clip(round(58 + 48 * confidence), 42, 110)
        )

        events.append({
            "time": start,
            "status": 0x91,
            "data1": midi_note,
            "data2": velocity,
            "kind": "note_on",
            "note_index": index,
        })
        events.append({
            "time": end,
            "status": 0x81,
            "data1": midi_note,
            "data2": 0,
            "kind": "note_off",
            "note_index": index,
        })

    priority = {"program": 0, "note_off": 1, "note_on": 2}
    events.sort(
        key=lambda event: (
            float(event["time"]),
            priority.get(str(event["kind"]), 9),
            int(event.get("data1", 0) or 0),
        )
    )
    return events


def _vlq(value: int) -> bytes:
    value = max(0, int(value))
    chunks = [value & 0x7F]
    value >>= 7
    while value:
        chunks.append((value & 0x7F) | 0x80)
        value >>= 7
    return bytes(reversed(chunks))


def build_vocal_midi_file(
    notes: list[dict[str, Any]],
    *,
    program: int = DEFAULT_VOCAL_PROGRAM,
    tempo: float = 120.0,
) -> bytes:
    """Create a monophonic MIDI file whose timing remains in audio seconds."""
    ppq = 480
    tempo = max(20.0, float(tempo or 120.0))
    us_per_quarter = int(round(60_000_000.0 / tempo))
    ticks_per_second = ppq * tempo / 60.0

    events = [
        (0, 0, b"\xFF\x51\x03" + us_per_quarter.to_bytes(3, "big")),
        (0, 0, b"\xFF\x03\x14EZScore Vocal Melody"),
        (0, 0, bytes([0xC0, int(program) & 0x7F])),
    ]

    for note in notes or []:
        start = max(0.0, float(note.get("start", 0.0) or 0.0))
        end = max(start + 0.04, float(note.get("end", start + 0.04) or start + 0.04))
        midi_note = int(np.clip(int(note.get("midi", 60) or 60), 0, 127))
        confidence = float(note.get("confidence", 0.75) or 0.75)
        velocity = int(np.clip(round(55 + 55 * confidence), 40, 112))

        t0 = int(round(start * ticks_per_second))
        t1 = int(round(end * ticks_per_second))
        events.append((t0, 2, bytes([0x90, midi_note, velocity])))
        events.append((t1, 1, bytes([0x80, midi_note, 0])))

    events.sort(key=lambda item: (item[0], item[1]))
    track = bytearray()
    previous_tick = 0
    for tick, _order, payload in events:
        track.extend(_vlq(int(tick) - previous_tick))
        track.extend(payload)
        previous_tick = int(tick)

    track.extend(b"\x00\xFF\x2F\x00")

    return (
        b"MThd"
        + struct.pack(">IHHH", 6, 0, 1, ppq)
        + b"MTrk"
        + struct.pack(">I", len(track))
        + bytes(track)
    )


def _note_values_in_interval(
    notes: list[dict[str, Any]],
    t0: float,
    t1: float,
) -> list[float]:
    result = []
    for note in notes or []:
        n0 = float(note.get("start", 0.0) or 0.0)
        n1 = float(note.get("end", n0) or n0)
        if n1 < t0 or n0 > t1:
            continue
        result.append(float(note.get("pitch_median", note.get("midi", 60)) or 60))
    return result


def _melody_contour(
    notes: list[dict[str, Any]],
    t0: float,
    t1: float,
    bins: int = 24,
) -> np.ndarray | None:
    duration = float(t1) - float(t0)
    if duration <= 0.05:
        return None

    edges = np.linspace(float(t0), float(t1), int(bins) + 1)
    values = np.full(int(bins), np.nan, dtype=float)

    for i in range(int(bins)):
        vals = _note_values_in_interval(notes, edges[i], edges[i + 1])
        if vals:
            values[i] = float(np.median(vals))

    finite = np.isfinite(values)
    coverage = float(np.mean(finite)) if len(values) else 0.0
    if coverage < 0.28:
        return None

    x = np.arange(len(values), dtype=float)
    values[~finite] = np.interp(x[~finite], x[finite], values[finite])
    values -= float(np.median(values))
    return np.clip(values, -18.0, 18.0)


def _contour_similarity(
    notes: list[dict[str, Any]],
    a0: float,
    a1: float,
    b0: float,
    b1: float,
) -> float | None:
    ca = _melody_contour(notes, a0, a1)
    cb = _melody_contour(notes, b0, b1)
    if ca is None or cb is None:
        return None
    distance = float(np.mean(np.abs(ca - cb)))
    return float(np.clip(1.0 - distance / 12.0, 0.0, 1.0))


def _boundary_novelty(
    notes: list[dict[str, Any]],
    measures: list[dict[str, Any]],
    pos: int,
    radius: int = 4,
) -> float:
    if pos <= 0 or pos >= len(measures):
        return 1.0
    left0 = max(0, pos - int(radius))
    right1 = min(len(measures), pos + int(radius))

    left_t0 = float(measures[left0]["debut"])
    left_t1 = float(measures[pos - 1]["fin"])
    right_t0 = float(measures[pos]["debut"])
    right_t1 = float(measures[right1 - 1]["fin"])

    similarity = _contour_similarity(
        notes,
        left_t0,
        left_t1,
        right_t0,
        right_t1,
    )
    if similarity is None:
        return 0.0
    return 1.0 - similarity


def refine_sections_with_vocal(
    sections: list[dict[str, Any]],
    measures: list[dict[str, Any]],
    vocal_notes: list[dict[str, Any]],
    *,
    max_shift_measures: int = 2,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Conservatively refine R33 boundaries using sung-melody novelty.

    This function never creates arbitrary new periodic boundaries. It may move
    an existing R33 boundary by at most ±2 measures, and only when vocal novelty
    is clearly stronger than at the original boundary.
    """
    sections = [dict(section) for section in (sections or [])]
    measures = list(measures or [])
    vocal_notes = list(vocal_notes or [])

    if len(sections) < 2 or len(measures) < 8 or len(vocal_notes) < 8:
        return sections, {"used": False, "moved": 0, "reason": "insufficient-data"}

    by_number = {
        int(measure.get("numero", index + 1)): index
        for index, measure in enumerate(measures)
    }

    boundary_positions = []
    for section in sections[1:]:
        start_no = int(section.get("measure_start", 0) or 0)
        if start_no in by_number:
            boundary_positions.append(by_number[start_no])

    if not boundary_positions:
        return sections, {"used": False, "moved": 0, "reason": "no-boundaries"}

    moved = []
    refined_positions = []
    previous_pos = 0

    for boundary_index, original_pos in enumerate(boundary_positions):
        next_original = (
            boundary_positions[boundary_index + 1]
            if boundary_index + 1 < len(boundary_positions)
            else len(measures)
        )

        current_score = _boundary_novelty(vocal_notes, measures, original_pos)
        best_pos = original_pos
        best_score = current_score

        for delta in range(-int(max_shift_measures), int(max_shift_measures) + 1):
            candidate = original_pos + delta
            if candidate <= previous_pos + 3:
                continue
            if candidate >= next_original - 3:
                continue
            score = _boundary_novelty(vocal_notes, measures, candidate)
            if score > best_score:
                best_score = score
                best_pos = candidate

        # Move only on clear evidence. Otherwise preserve R33 exactly.
        if (
            best_pos != original_pos
            and best_score >= 0.48
            and best_score >= current_score + 0.12
        ):
            refined_positions.append(best_pos)
            moved.append({
                "from_measure": int(measures[original_pos]["numero"]),
                "to_measure": int(measures[best_pos]["numero"]),
                "vocal_novelty_before": round(current_score, 4),
                "vocal_novelty_after": round(best_score, 4),
            })
            previous_pos = best_pos
        else:
            refined_positions.append(original_pos)
            previous_pos = original_pos

    all_positions = [0] + refined_positions + [len(measures)]
    result = []

    first_original_start = float(sections[0].get("time_start", measures[0]["debut"]))
    last_original_end = float(sections[-1].get("time_end", measures[-1]["fin"]))

    for index in range(len(all_positions) - 1):
        a = int(all_positions[index])
        b = int(all_positions[index + 1])
        if b <= a:
            continue

        source = dict(sections[min(index, len(sections) - 1)])
        group = measures[a:b]
        source["index"] = index
        source["measure_start"] = int(group[0]["numero"])
        source["measure_end"] = int(group[-1]["numero"])
        source["time_start"] = float(group[0]["debut"])
        source["time_end"] = float(group[-1]["fin"])
        source["measure_patterns"] = [
            str(measure.get("notation", "") or "").strip()
            for measure in group
        ]
        source["vocal_refined"] = bool(moved)
        result.append(source)

    if result:
        result[0]["time_start"] = min(float(result[0]["time_start"]), first_original_start)
        result[-1]["time_end"] = max(float(result[-1]["time_end"]), last_original_end)

    return result, {
        "used": True,
        "moved": len(moved),
        "moves": moved,
    }
