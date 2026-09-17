"""High-quality beat/tactus tracking for EZScore analysis.

The tracker is deliberately meter-agnostic here: it produces beat timestamps
from the audio.  Signature/grouping is applied later by EZScore and therefore
cannot move these canonical timestamps.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

import numpy as np


ENGINE = "madmom-infer-rnn-dbn"


def quality_rhythm_engine_available() -> bool:
    try:
        return importlib.util.find_spec("madmom_infer") is not None
    except Exception:
        return False


def analyze_beats(audio_path: Path) -> dict[str, Any]:
    path = Path(audio_path)
    if not path.is_file():
        raise FileNotFoundError(str(path))

    if not quality_rhythm_engine_available():
        raise RuntimeError(
            "Moteur rythmique haute qualité absent : installez `madmom-infer`. "
            "EZScore refuse de revenir silencieusement à librosa.beat."
        )

    from madmom_infer.features.beats import (
        DBNBeatTrackingProcessor,
        RNNBeatProcessor,
    )

    activations = RNNBeatProcessor()(str(path))
    beats = np.asarray(
        DBNBeatTrackingProcessor(fps=100)(activations),
        dtype=float,
    ).reshape(-1)

    beats = beats[np.isfinite(beats)]
    beats = np.unique(np.round(beats, 6))
    if beats.size < 2:
        raise RuntimeError(
            "madmom-infer n'a pas détecté assez de pulsations pour construire la timeline."
        )

    intervals = np.diff(beats)
    intervals = intervals[intervals > 1e-6]
    if intervals.size == 0:
        raise RuntimeError("Timeline rythmique invalide : intervalles nuls.")

    median_interval = float(np.median(intervals))
    tempo = 60.0 / median_interval

    return {
        "engine": ENGINE,
        "timebase": "original_audio_seconds",
        "tempo": float(tempo),
        "beat_count": int(beats.size),
        "beats": [float(x) for x in beats.tolist()],
    }
