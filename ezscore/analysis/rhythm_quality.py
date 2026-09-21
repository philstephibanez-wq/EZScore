"""High-quality beat/tactus tracking for EZScore analysis.

Compatibility target: madmom-infer 0.2.0.

R2 deliberately uses only classes documented as shipped in 0.2.0:
- RNNDownBeatProcessor
- DBNDownBeatTrackingProcessor

The decoder returns rows ``[time_seconds, beat_number_in_bar]``.
EZScore consumes only the first column here; meter is applied later and never
moves these absolute timestamps.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np


ENGINE = "madmom-infer-rnn-downbeat-dbn"


def _processors():
    try:
        from madmom_infer.features.downbeats import (
            DBNDownBeatTrackingProcessor,
            RNNDownBeatProcessor,
        )
    except Exception as exc:
        raise RuntimeError(
            "madmom-infer 0.2.0 est installé mais son pipeline "
            "RNNDownBeatProcessor / DBNDownBeatTrackingProcessor "
            "n'est pas importable."
        ) from exc
    return RNNDownBeatProcessor, DBNDownBeatTrackingProcessor


def quality_rhythm_engine_available() -> bool:
    try:
        _processors()
        return True
    except Exception:
        return False


def analyze_beats(audio_path: Path) -> dict[str, Any]:
    path = Path(audio_path)
    if not path.is_file():
        raise FileNotFoundError(str(path))

    RNNDownBeatProcessor, DBNDownBeatTrackingProcessor = _processors()

    try:
        activations = RNNDownBeatProcessor()(str(path))
        decoded = DBNDownBeatTrackingProcessor(
            beats_per_bar=[2, 3, 4, 5, 6, 7, 8, 9, 12],
            fps=100,
        )(activations)
    except Exception as exc:
        raise RuntimeError(
            "madmom-infer n'a pas pu extraire les pulsations du STEM Batterie : "
            f"{type(exc).__name__}: {exc}"
        ) from exc

    decoded = np.asarray(decoded, dtype=float)

    if decoded.ndim == 1:
        beat_times = decoded.reshape(-1)
    elif decoded.ndim >= 2 and decoded.shape[1] >= 1:
        beat_times = decoded[:, 0].reshape(-1)
    else:
        beat_times = np.asarray([], dtype=float)

    beat_times = beat_times[np.isfinite(beat_times)]
    beat_times = np.unique(np.round(beat_times, 6))

    if beat_times.size < 2:
        raise RuntimeError(
            "madmom-infer n'a pas détecté assez de pulsations "
            "pour construire la timeline."
        )

    intervals = np.diff(beat_times)
    intervals = intervals[intervals > 1e-6]
    if intervals.size == 0:
        raise RuntimeError("Timeline rythmique invalide : intervalles nuls.")

    median_interval = float(np.median(intervals))
    tempo = 60.0 / median_interval

    return {
        "engine": ENGINE,
        "timebase": "original_audio_seconds",
        "tempo": float(tempo),
        "beat_count": int(beat_times.size),
        "beats": [float(x) for x in beat_times.tolist()],
    }
