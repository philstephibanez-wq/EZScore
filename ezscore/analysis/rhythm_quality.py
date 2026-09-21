"""High-quality beat/tactus tracking for EZScore analysis.

The tracker is deliberately meter-agnostic here: it produces beat timestamps
from the audio. Signature/grouping is applied later by EZScore and therefore
cannot move these canonical timestamps.

R1 compatibility note:
Use madmom-infer's documented public task API instead of importing package
internals.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np


ENGINE = "madmom-infer-detect-beats"


def _madmom():
    try:
        import madmom_infer as mm
    except Exception as exc:
        raise RuntimeError(
            "Moteur rythmique absent : installez `madmom-infer==0.2.0`."
        ) from exc

    detect_beats = getattr(mm, "detect_beats", None)
    if not callable(detect_beats):
        version = str(getattr(mm, "__version__", "inconnue") or "inconnue")
        raise RuntimeError(
            "API madmom-infer incompatible "
            f"(version détectée : {version}). "
            "EZScore requiert l'API publique `detect_beats`; "
            "installez `madmom-infer==0.2.0`."
        )
    return mm


def quality_rhythm_engine_available() -> bool:
    try:
        mm = _madmom()
        return callable(getattr(mm, "detect_beats", None))
    except Exception:
        return False


def analyze_beats(audio_path: Path) -> dict[str, Any]:
    path = Path(audio_path)
    if not path.is_file():
        raise FileNotFoundError(str(path))

    mm = _madmom()

    try:
        detected = mm.detect_beats(str(path))
    except Exception as exc:
        raise RuntimeError(
            "madmom-infer n'a pas pu extraire les beats du STEM Batterie : "
            f"{type(exc).__name__}: {exc}"
        ) from exc

    beats = np.asarray(detected, dtype=float).reshape(-1)
    beats = beats[np.isfinite(beats)]
    beats = np.unique(np.round(beats, 6))

    if beats.size < 2:
        raise RuntimeError(
            "madmom-infer n'a pas détecté assez de pulsations "
            "pour construire la timeline."
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
