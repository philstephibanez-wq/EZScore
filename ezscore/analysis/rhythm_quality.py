"""High-quality beat/tactus tracking for EZScore analysis.

The tracker is meter-agnostic at the public contract: it returns canonical beat
timestamps on the original-audio timebase.  madmom-infer has shipped two
compatible public APIs across releases (`features.beats` and
`features.downbeats`).  EZScore accepts both APIs but never falls back to a
lower-quality rhythm engine.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

import numpy as np


ENGINE_BEATS = "madmom-infer-rnn-beat-dbn"
ENGINE_DOWNBEATS_COMPAT = "madmom-infer-rnn-downbeat-dbn-compat"


def _module_available(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ModuleNotFoundError, AttributeError, ValueError):
        return False


def quality_rhythm_engine_available() -> bool:
    if not _module_available("madmom_infer"):
        return False
    return (
        _module_available("madmom_infer.features.beats")
        or _module_available("madmom_infer.features.downbeats")
    )


def _normalize_beats(values) -> np.ndarray:
    beats = np.asarray(values, dtype=float).reshape(-1)
    beats = beats[np.isfinite(beats)]
    beats = np.unique(np.round(beats, 6))
    if beats.size < 2:
        raise RuntimeError(
            "madmom-infer n'a pas détecté assez de pulsations pour construire la timeline."
        )
    return beats


def _analyse_with_beats_api(path: Path) -> tuple[np.ndarray, str]:
    from madmom_infer.features.beats import (  # type: ignore
        DBNBeatTrackingProcessor,
        RNNBeatProcessor,
    )

    activations = RNNBeatProcessor()(str(path))
    beats = DBNBeatTrackingProcessor(fps=100)(activations)
    return _normalize_beats(beats), ENGINE_BEATS


def _analyse_with_downbeats_api(path: Path) -> tuple[np.ndarray, str]:
    """Compatibility path for madmom-infer releases exposing downbeats only.

    This is still the madmom-infer neural/DBN stack, not a librosa or heuristic
    fallback.  Only the beat timestamps are consumed here; meter remains owned
    by the downstream EZScore meter analysis.
    """
    from madmom_infer.features.downbeats import (  # type: ignore
        DBNDownBeatTrackingProcessor,
        RNNDownBeatProcessor,
    )

    activations = RNNDownBeatProcessor()(str(path))
    decoded = np.asarray(
        DBNDownBeatTrackingProcessor(beats_per_bar=[2, 3, 4], fps=100)(activations),
        dtype=float,
    )
    if decoded.ndim != 2 or decoded.shape[1] < 1:
        raise RuntimeError("Sortie madmom-infer downbeats invalide.")
    return _normalize_beats(decoded[:, 0]), ENGINE_DOWNBEATS_COMPAT


def analyze_beats(audio_path: Path) -> dict[str, Any]:
    path = Path(audio_path)
    if not path.is_file():
        raise FileNotFoundError(str(path))

    if not _module_available("madmom_infer"):
        raise RuntimeError(
            "Moteur rythmique haute qualité absent : installez `madmom-infer`. "
            "EZScore refuse un fallback silencieux."
        )

    errors: list[str] = []
    beats: np.ndarray | None = None
    engine = ""

    if _module_available("madmom_infer.features.beats"):
        try:
            beats, engine = _analyse_with_beats_api(path)
        except Exception as exc:
            errors.append(f"features.beats: {type(exc).__name__}: {exc}")

    if beats is None and _module_available("madmom_infer.features.downbeats"):
        try:
            beats, engine = _analyse_with_downbeats_api(path)
        except Exception as exc:
            errors.append(f"features.downbeats: {type(exc).__name__}: {exc}")

    if beats is None:
        detail = " · ".join(errors) if errors else (
            "ni madmom_infer.features.beats ni madmom_infer.features.downbeats n'est disponible"
        )
        raise RuntimeError(
            "madmom-infer est présent mais aucune API rythmique compatible n'est exploitable : "
            + detail
        )

    intervals = np.diff(beats)
    intervals = intervals[intervals > 1e-6]
    if intervals.size == 0:
        raise RuntimeError("Timeline rythmique invalide : intervalles nuls.")

    median_interval = float(np.median(intervals))
    tempo = 60.0 / median_interval

    return {
        "engine": engine,
        "timebase": "original_audio_seconds",
        "tempo": float(tempo),
        "beat_count": int(beats.size),
        "beats": [float(x) for x in beats.tolist()],
    }
