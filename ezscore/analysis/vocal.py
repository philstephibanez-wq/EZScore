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

VOCAL_SCHEMA_VERSION = 1
VOCAL_ANALYSIS_ENGINE = "pyin-v1"
DEFAULT_VOCAL_PROGRAM = 53  # GM Voice Oohs, zero-based


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


def _segment_notes(
    times: np.ndarray,
    midi_float: np.ndarray,
    voiced_prob: np.ndarray,
    hop_seconds: float,
    min_duration: float = 0.09,
) -> list[dict[str, Any]]:
    if len(times) == 0:
        return []

    smoothed = _median_filter(midi_float, width=5)
    quantized = np.full(len(smoothed), np.nan, dtype=float)
    finite = np.isfinite(smoothed)
    quantized[finite] = np.rint(smoothed[finite])

    notes = []
    start_idx = None
    current = None

    def close(end_idx: int):
        nonlocal start_idx, current
        if start_idx is None or current is None:
            start_idx = None
            current = None
            return

        start = float(times[start_idx])
        end = float(times[min(end_idx, len(times) - 1)] + hop_seconds)
        duration = max(0.0, end - start)
        if duration >= min_duration:
            segment = midi_float[start_idx:end_idx + 1]
            probs = voiced_prob[start_idx:end_idx + 1]
            valid_pitch = segment[np.isfinite(segment)]
            valid_prob = probs[np.isfinite(probs)]
            median_pitch = float(np.median(valid_pitch)) if valid_pitch.size else float(current)
            confidence = float(np.mean(valid_prob)) if valid_prob.size else 0.0
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

    for i, value in enumerate(quantized):
        if not np.isfinite(value):
            if start_idx is not None:
                close(i - 1)
            continue

        q = int(value)
        if start_idx is None:
            start_idx = i
            current = q
            continue

        if q != current:
            close(i - 1)
            start_idx = i
            current = q

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

        confidence_floor = 0.55 if source_kind.startswith("demucs") else 0.72
        valid = (
            voiced_flag
            & np.isfinite(f0)
            & np.isfinite(voiced_prob)
            & (voiced_prob >= confidence_floor)
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
                and float(note["confidence"]) >= 0.76
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
            "note_count": len(notes),
            "notes": notes,
        }
        save_vocal_analysis(audio_hash, payload)
        return payload


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
