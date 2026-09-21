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


def ensure_music_timeline(
    stem_lab,
    audio_hash: str,
    *,
    progress: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Load or build the canonical beat/chord timeline exactly once."""

    existing = stem_lab._load_structure(audio_hash)
    if _valid_existing(existing):
        return dict(existing or {})

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
