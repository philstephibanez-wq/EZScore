from __future__ import annotations

"""Canonical music timeline for Analyse.

This module does NOT create a second cache or a second UI route.
It materializes the already-existing EZScore beat/chord analysis earlier in the
workflow and stores it in the already-existing ``structure_analysis.json``.

Pipeline:
    drums STEM -> librosa beat tracker already used by EZScore
    original   -> existing lv-chordia chord engine/cache
    -> structure_analysis.json["beat_timeline"]

Block/measure segmentation remains a later operation and consumes the exact
same timestamps.
"""

import json
from pathlib import Path
from typing import Any, Callable

import librosa
import numpy as np

from ezscore.analysis.chords_quality import (
    analyze_chords_absolute,
    chord_for_interval,
)


TIMEBASE = "original_audio_seconds"
ENGINE_RHYTHM = "librosa-beat-ezscore"


def _notify(callback: Callable[[str], None] | None, message: str) -> None:
    if callback is not None:
        callback(message)


def _valid_existing(payload: dict[str, Any] | None) -> bool:
    if not isinstance(payload, dict):
        return False
    beats = list(payload.get("beat_timeline", []) or [])
    if len(beats) < 2:
        return False
    return all(
        isinstance(item, dict)
        and ("time" in item or "start" in item)
        for item in beats
    )



def _beat_time(item: dict[str, Any]) -> float:
    value = item.get("time", item.get("start", 0.0))
    return float(value or 0.0)


def _positive_median_interval(beats: list[dict[str, Any]]) -> float:
    times = np.asarray(
        [_beat_time(item) for item in beats],
        dtype=float,
    )
    times = times[np.isfinite(times)]
    if times.size < 2:
        return 0.0
    intervals = np.diff(times)
    intervals = intervals[intervals > 1e-6]
    if intervals.size == 0:
        return 0.0
    return float(np.median(intervals))


def _needs_preroll_backfill(payload: dict[str, Any] | None) -> bool:
    if not _valid_existing(payload):
        return False
    beats = list(payload.get("beat_timeline", []) or [])
    interval = _positive_median_interval(beats)
    if interval <= 0.0:
        return False
    first = _beat_time(beats[0])
    # If more than roughly one beat is missing before the first detected beat,
    # the musical grid does not cover the song pre-roll.
    return first > interval * 1.25


def _prepend_phase_locked_beats(
    *,
    beats: list[dict[str, Any]],
    chord_segments: list[dict[str, Any]],
    harmony_engine: str,
) -> tuple[list[dict[str, Any]], int, float]:
    """Extend an existing detected grid backwards without moving any beat.

    Existing timestamps are copied byte-for-byte as floats. New points are
    phase-locked to the median detected interval and stop before t=0.
    Harmony for each added beat is queried from the existing lv-chordia
    segments; it is never copied from a neighbouring detected beat.
    """
    if len(beats) < 2:
        return list(beats), 0, 0.0

    interval = _positive_median_interval(beats)
    if interval <= 0.0:
        return list(beats), 0, 0.0

    first_time = _beat_time(beats[0])
    prepend_times: list[float] = []
    candidate = first_time - interval

    while candidate > 1e-6:
        prepend_times.append(float(candidate))
        candidate -= interval

    prepend_times.reverse()
    if not prepend_times:
        return list(beats), 0, interval

    added: list[dict[str, Any]] = []
    all_times = prepend_times + [first_time]

    for index, start in enumerate(prepend_times):
        end = float(all_times[index + 1])
        chord, raw_chord, overlap = chord_for_interval(
            chord_segments,
            float(start),
            float(end),
        )
        added.append(
            {
                "index": int(index),
                "time": round(float(start), 6),
                "strength": 0.0,
                "chord": str(chord),
                "chord_raw": str(raw_chord),
                "chord_overlap": round(float(overlap), 6),
                "rhythm_engine": f"{ENGINE_RHYTHM}+phase-preroll",
                "harmony_engine": str(harmony_engine or ""),
                "preroll_extrapolated": True,
            }
        )

    # Re-index only. Existing time/chord values are preserved.
    merged = added + [dict(item) for item in beats]
    for index, item in enumerate(merged):
        item["index"] = int(index)

    return merged, len(added), interval


def _repair_existing_preroll(
    stem_lab,
    audio_hash: str,
    payload: dict[str, Any],
    *,
    progress: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Backfill a late-starting existing grid without rerunning beat tracking."""
    beats = list(payload.get("beat_timeline", []) or [])
    if not _needs_preroll_backfill(payload):
        return payload

    song = stem_lab._song_for_hash(audio_hash)
    source = stem_lab._source_path(audio_hash, song)
    if source is None or not Path(source).is_file():
        raise RuntimeError(
            "Audio original introuvable pour compléter le pré-roll harmonique."
        )

    _notify(
        progress,
        "Pré-roll · prolongation de la grille existante vers t=0…",
    )

    # force=False reuses the existing lv-chordia cache when present.
    chord_payload = analyze_chords_absolute(
        Path(source),
        cache_path=stem_lab._chord_cache_path(audio_hash),
        force=False,
    )
    chord_segments = list(chord_payload.get("segments", []) or [])
    if not chord_segments:
        raise RuntimeError(
            "Timeline harmonique lv-chordia vide : pré-roll impossible."
        )

    merged, added_count, interval = _prepend_phase_locked_beats(
        beats=beats,
        chord_segments=chord_segments,
        harmony_engine=str(chord_payload.get("engine", "") or ""),
    )

    if added_count <= 0:
        return payload

    first_detected_time = _beat_time(beats[0])
    repaired = dict(payload)
    repaired["beat_timeline"] = merged
    repaired["timeline_preroll"] = {
        "mode": "phase_backfill_v1",
        "added_beat_count": int(added_count),
        "interval_seconds": round(float(interval), 9),
        "first_detected_beat_time": round(float(first_detected_time), 6),
        "first_timeline_beat_time": round(float(_beat_time(merged[0])), 6),
        "existing_detected_beats_moved": False,
    }

    path = stem_lab._structure_cache_path(audio_hash)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(repaired, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    _notify(
        progress,
        f"Pré-roll · {added_count} beats ajoutés sans déplacer les beats détectés.",
    )
    return repaired

def ensure_music_timeline(
    stem_lab,
    audio_hash: str,
    *,
    progress: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Load or build the canonical beat/chord timeline exactly once."""

    existing = stem_lab._load_structure(audio_hash)
    if _valid_existing(existing):
        current = dict(existing or {})
        if _needs_preroll_backfill(current):
            return _repair_existing_preroll(
                stem_lab,
                audio_hash,
                current,
                progress=progress,
            )
        return current

    stems = stem_lab.cached_stem_paths(audio_hash)
    drums = stems.get("drums")
    if drums is None or not Path(drums).is_file():
        raise RuntimeError(
            "STEM Batterie absent : impossible de construire la timeline musicale."
        )

    song = stem_lab._song_for_hash(audio_hash)
    source = stem_lab._source_path(audio_hash, song)
    if source is None or not Path(source).is_file():
        raise RuntimeError(
            "Audio original introuvable pour l'analyse harmonique."
        )

    # ------------------------------------------------------------
    # 1/2 Rhythm — reuse the proven librosa beat tracker already
    # present in EZScore.py. No madmom dependency, no fallback chain.
    # ------------------------------------------------------------
    _notify(progress, "1/2 · Détection des beats sur le STEM Batterie…")

    y, sr = librosa.load(
        str(drums),
        sr=22050,
        mono=True,
    )
    if y is None or len(y) < sr:
        raise RuntimeError("STEM Batterie vide ou trop court.")

    # Drums is already a percussion stem; HPSS is intentionally unnecessary.
    tempo_raw, beat_frames = librosa.beat.beat_track(
        y=y,
        sr=sr,
        hop_length=512,
    )
    tempo = float(np.asarray(tempo_raw).squeeze())
    frames = np.asarray(beat_frames, dtype=int).reshape(-1)

    if frames.size < 2:
        raise RuntimeError("Pas assez de beats détectés sur le STEM Batterie.")

    beat_times = np.asarray(
        librosa.frames_to_time(
            frames,
            sr=sr,
            hop_length=512,
        ),
        dtype=float,
    )
    beat_times = beat_times[np.isfinite(beat_times)]
    beat_times = np.unique(np.round(beat_times, 6))

    if beat_times.size < 2:
        raise RuntimeError("Timeline de beats insuffisante après normalisation.")

    # Keep the detected grid phase but extend it backwards through an
    # instrumental/vocal pre-roll where the drum stem had no detectable hits.
    detected_first_time = float(beat_times[0])
    detected_interval = float(np.median(np.diff(beat_times)))
    preroll_times: list[float] = []
    candidate = detected_first_time - detected_interval
    while candidate > 1e-6:
        preroll_times.append(float(candidate))
        candidate -= detected_interval
    if preroll_times:
        beat_times = np.concatenate(
            [
                np.asarray(list(reversed(preroll_times)), dtype=float),
                beat_times,
            ]
        )

    # ------------------------------------------------------------
    # 2/2 Harmony — keep the existing lv-chordia engine and its cache.
    # ------------------------------------------------------------
    _notify(progress, "2/2 · Raccord des accords lv-chordia sur les beats…")

    chord_payload = analyze_chords_absolute(
        Path(source),
        cache_path=stem_lab._chord_cache_path(audio_hash),
        force=False,
    )
    chord_segments = list(chord_payload.get("segments", []) or [])
    if not chord_segments:
        raise RuntimeError("Timeline harmonique lv-chordia vide.")

    median_interval = float(np.median(np.diff(beat_times)))
    beat_timeline: list[dict[str, Any]] = []

    for index, start in enumerate(beat_times):
        end = (
            float(beat_times[index + 1])
            if index + 1 < len(beat_times)
            else float(start) + median_interval
        )
        chord, raw_chord, overlap = chord_for_interval(
            chord_segments,
            float(start),
            float(end),
        )
        beat_timeline.append(
            {
                "index": int(index),
                "time": round(float(start), 6),
                "strength": 0.0,
                "chord": str(chord),
                "chord_raw": str(raw_chord),
                "chord_overlap": round(float(overlap), 6),
                "rhythm_engine": ENGINE_RHYTHM,
                "harmony_engine": str(chord_payload.get("engine", "") or ""),
            }
        )

    payload = dict(existing or {})
    payload.update(
        {
            "tempo": float(tempo),
            "beat_timeline": beat_timeline,
            "timebase": TIMEBASE,
            "timeline_stage": "beats+chords",
            "timeline_preroll": {
                "mode": "phase_backfill_v1",
                "added_beat_count": int(len(preroll_times)),
                "interval_seconds": round(float(detected_interval), 9),
                "first_detected_beat_time": round(float(detected_first_time), 6),
                "first_timeline_beat_time": round(float(beat_times[0]), 6),
                "existing_detected_beats_moved": False,
            },
            "analysis_engines": {
                **dict(payload.get("analysis_engines", {}) or {}),
                "rhythm": ENGINE_RHYTHM,
                "harmony": str(chord_payload.get("engine", "") or ""),
                "harmony_dictionary": str(
                    chord_payload.get("dictionary", "") or ""
                ),
            },
            "chord_segment_count": int(
                chord_payload.get(
                    "segment_count",
                    len(chord_segments),
                )
                or len(chord_segments)
            ),
        }
    )

    path = stem_lab._structure_cache_path(audio_hash)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return payload
