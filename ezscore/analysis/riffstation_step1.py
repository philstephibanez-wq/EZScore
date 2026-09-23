"""Canonical Step 1 musical timeline for EZScore.

Step 1 is deliberately lyrics-free: Riffstation-style harmonic/rhythmic audit
plus STEM playback.  This module owns data only.  It does not render UI and it
does not alter Step 2 assets.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import librosa
import numpy as np

from ezscore.analysis.chords_quality import (
    analyze_chords_absolute,
    chord_for_interval,
    quality_chord_engine_available,
)
from ezscore.analysis.rhythm_quality import (
    analyze_beats as analyze_quality_beats,
    quality_rhythm_engine_available,
)

CACHE_VERSION = "ezscore-step1-riffstation-v1"
SUPPORTED_SIGNATURES = (
    "2/4",
    "3/4",
    "4/4",
    "5/4",
    "6/8",
    "7/8",
    "9/8",
    "12/8",
)


def cache_path(work_dir: Path) -> Path:
    return Path(work_dir) / "riffstation_step1.json"


def parse_signature(value: str) -> tuple[int, int]:
    text = str(value or "").strip()
    if "/" not in text:
        raise ValueError(f"Signature invalide: {text!r}")
    left, right = text.split("/", 1)
    if not left.isdigit() or not right.isdigit():
        raise ValueError(f"Signature invalide: {text!r}")
    numerator = int(left)
    denominator = int(right)
    if numerator < 1 or denominator not in {1, 2, 4, 8, 16, 32}:
        raise ValueError(f"Signature invalide: {text!r}")
    return numerator, denominator


def timeline_beats_per_measure(signature: str) -> int:
    numerator, denominator = parse_signature(signature)
    if denominator >= 8 and numerator > 3:
        if numerator % 3 == 0:
            return numerator // 3
        if numerator == 5:
            return 2
        if numerator == 7:
            return 3
    return numerator


def effective_signature(*, selected: str, detected: str) -> str:
    selected_text = str(selected or "").strip()
    if selected_text and selected_text != "Auto":
        parse_signature(selected_text)
        return selected_text

    detected_text = str(detected or "").strip()
    if not detected_text:
        raise RuntimeError(
            "Time signature détectée absente. EZScore refuse d'inventer une métrique."
        )
    parse_signature(detected_text)
    return detected_text


def load(work_dir: Path) -> dict[str, Any] | None:
    path = cache_path(work_dir)
    if not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if str(payload.get("version", "")) != CACHE_VERSION:
        return None
    detected = str(payload.get("detected_signature", "") or "").strip()
    parse_signature(detected)
    beats = list(payload.get("beats", []) or [])
    if len(beats) < 2:
        raise RuntimeError("Cache Step 1 invalide: timeline de beats insuffisante.")
    return payload


def _sample_onset(envelope: np.ndarray, frame: float) -> float:
    if envelope.size == 0:
        return 0.0
    x = float(np.clip(frame, 0.0, envelope.size - 1.0))
    i0 = int(math.floor(x))
    i1 = min(envelope.size - 1, i0 + 1)
    frac = x - i0
    return float((1.0 - frac) * envelope[i0] + frac * envelope[i1])


def _subdivision_compound_score(
    onset_env: np.ndarray,
    beat_frames: np.ndarray,
) -> float:
    """Positive values favour ternary subdivision over binary subdivision."""
    ternary: list[float] = []
    binary: list[float] = []
    for left, right in zip(beat_frames[:-1], beat_frames[1:]):
        span = float(right - left)
        if span < 3.0:
            continue
        ternary.extend(
            [
                _sample_onset(onset_env, left + span / 3.0),
                _sample_onset(onset_env, left + 2.0 * span / 3.0),
            ]
        )
        binary.append(_sample_onset(onset_env, left + span / 2.0))
    if not ternary or not binary:
        return 0.0
    t = float(np.median(np.asarray(ternary, dtype=float)))
    b = float(np.median(np.asarray(binary, dtype=float)))
    scale = max(1e-9, float(np.median(onset_env)) + float(np.std(onset_env)))
    return (t - b) / scale


def detect_time_signature(
    drums_path: Path,
    beat_times: list[float] | np.ndarray,
) -> dict[str, Any]:
    """Estimate meter without changing canonical beat timestamps.

    Beat periodicity estimates tactus beats per bar.  A second subdivision test
    separates simple 2/3/4 from compound 6/8, 9/8 and 12/8.
    """
    beats = np.asarray(beat_times, dtype=float).reshape(-1)
    beats = beats[np.isfinite(beats)]
    if beats.size < 12:
        raise RuntimeError(
            "Pas assez de beats pour calculer une time signature fiable."
        )

    y, sr = librosa.load(str(drums_path), sr=22050, mono=True)
    hop = 512
    onset = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop)
    frames = librosa.time_to_frames(beats, sr=sr, hop_length=hop).astype(float)
    frames = np.clip(frames, 0, max(0, len(onset) - 1))
    strengths = np.asarray([_sample_onset(onset, x) for x in frames], dtype=float)

    median = float(np.median(strengths))
    mad = float(np.median(np.abs(strengths - median)))
    if mad <= 1e-9:
        mad = float(np.std(strengths))
    if mad <= 1e-9:
        raise RuntimeError(
            "Accents rythmiques insuffisants pour calculer la time signature."
        )
    z = (strengths - median) / mad

    # Meter is evaluated on tactus beats; compound meters are distinguished
    # later by their internal subdivision.
    hypotheses = {
        "2": 2,
        "3": 3,
        "4": 4,
        "5": 5,
        "7": 7,
    }
    raw_scores: dict[str, float] = {}
    best_phases: dict[str, int] = {}

    positions = np.arange(len(z))
    for label, width in hypotheses.items():
        best_score = -1e9
        best_phase = 0
        for phase in range(width):
            down_mask = ((positions - phase) % width) == 0
            if int(np.sum(down_mask)) < 2 or int(np.sum(~down_mask)) < 2:
                continue
            down = z[down_mask]
            other = z[~down_mask]
            accent = float(np.mean(down) - np.mean(other))

            # Reward regularity of the candidate downbeat accents.
            regularity = 1.0 / (1.0 + float(np.std(down)))
            score = accent + 0.25 * regularity
            if score > best_score:
                best_score = score
                best_phase = phase
        raw_scores[label] = float(best_score)
        best_phases[label] = int(best_phase)

    ranked = sorted(raw_scores.items(), key=lambda item: item[1], reverse=True)
    if not ranked or not np.isfinite(ranked[0][1]):
        raise RuntimeError("Impossible de calculer la time signature.")

    tactus_label = ranked[0][0]
    top_score = float(ranked[0][1])
    second_score = float(ranked[1][1]) if len(ranked) > 1 else top_score
    gap = max(0.0, top_score - second_score)
    confidence = max(0.0, min(1.0, 0.5 + 0.22 * gap))

    compound_score = _subdivision_compound_score(onset, frames)
    if tactus_label == "2":
        signature = "6/8" if compound_score > 0.10 else "2/4"
    elif tactus_label == "3":
        signature = "9/8" if compound_score > 0.10 else "3/4"
    elif tactus_label == "4":
        signature = "12/8" if compound_score > 0.10 else "4/4"
    elif tactus_label == "5":
        signature = "5/4"
    elif tactus_label == "7":
        signature = "7/8"
    else:
        raise RuntimeError("Résultat métrique interne incohérent.")

    parse_signature(signature)
    return {
        "signature": signature,
        "confidence": float(confidence),
        "phase": int(best_phases[tactus_label]),
        "tactus_beats_per_measure": int(hypotheses[tactus_label]),
        "compound_subdivision_score": float(compound_score),
        "scores": {key: float(value) for key, value in raw_scores.items()},
        "engine": "madmom-beats+drum-accent-meter-v1",
    }


def analyze(
    *,
    source: Path,
    drums_path: Path,
    work_dir: Path,
    force: bool = False,
) -> dict[str, Any]:
    """Build and persist the Step 1 source-of-truth musical timeline."""
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    if not force:
        cached = load(work_dir)
        if cached is not None:
            return cached

    if not quality_rhythm_engine_available():
        raise RuntimeError(
            "Analyse rythmique HQ indisponible: paquet `madmom-infer` absent."
        )
    if not quality_chord_engine_available():
        raise RuntimeError(
            "Analyse harmonique HQ indisponible: paquet `lv-chordia` absent."
        )

    rhythm = analyze_quality_beats(Path(drums_path))
    beat_times = np.asarray(rhythm.get("beats", []), dtype=float).reshape(-1)
    if beat_times.size < 2:
        raise RuntimeError("Timeline rythmique vide.")

    chord_payload = analyze_chords_absolute(
        Path(source),
        cache_path=work_dir / "riffstation_chords_lv_chordia.json",
        force=force,
    )
    chord_segments = list(chord_payload.get("segments", []) or [])
    if not chord_segments:
        raise RuntimeError("Timeline harmonique lv-chordia vide.")

    tempo = float(rhythm.get("tempo", 0.0) or 0.0)
    if tempo <= 0.0:
        intervals = np.diff(beat_times)
        intervals = intervals[intervals > 1e-6]
        if intervals.size == 0:
            raise RuntimeError("Tempo introuvable à partir des beats.")
        tempo = 60.0 / float(np.median(intervals))

    beats: list[dict[str, Any]] = []
    for index, start in enumerate(beat_times):
        if index + 1 < beat_times.size:
            end = float(beat_times[index + 1])
        else:
            end = float(start) + 60.0 / tempo
        chord, raw_chord, overlap = chord_for_interval(
            chord_segments,
            float(start),
            float(end),
        )
        beats.append(
            {
                "index": int(index),
                "start": round(float(start), 6),
                "end": round(float(end), 6),
                "chord": str(chord or "."),
                "chord_raw": str(raw_chord or ""),
                "chord_overlap": round(float(overlap), 6),
            }
        )

    meter = detect_time_signature(Path(drums_path), beat_times)
    payload = {
        "version": CACHE_VERSION,
        "timebase": "original_audio_seconds",
        "tempo": float(tempo),
        "detected_signature": str(meter["signature"]),
        "meter_detection": meter,
        "beats": beats,
        "beat_count": len(beats),
        "analysis_engines": {
            "rhythm": str(rhythm.get("engine", "")),
            "harmony": str(chord_payload.get("engine", "")),
            "meter": str(meter.get("engine", "")),
        },
    }
    cache_path(work_dir).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return payload
