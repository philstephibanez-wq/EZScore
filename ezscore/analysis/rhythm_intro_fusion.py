from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import librosa
import numpy as np


@dataclass(frozen=True)
class FusionResult:
    beats: tuple[float, ...]
    sources: tuple[str, ...]
    tempo: float
    engine: str
    intro_mix_beat_count: int
    first_drum_beat: float | None


def _clean_beats(values) -> np.ndarray:
    beats = np.asarray(list(values or []), dtype=float).reshape(-1)
    beats = beats[np.isfinite(beats)]
    beats = beats[beats >= 0.0]
    return np.unique(np.round(beats, 6))


def _median_interval(beats: np.ndarray) -> float | None:
    if beats.size < 2:
        return None
    intervals = np.diff(beats)
    intervals = intervals[intervals > 1e-5]
    if intervals.size == 0:
        return None
    return float(np.median(intervals))


def _regular_suffix_before(
    mix_beats: np.ndarray,
    *,
    before: float,
    target_interval: float,
) -> np.ndarray:
    prefix = mix_beats[mix_beats < before - 0.03]
    if prefix.size == 0:
        return prefix

    low = target_interval * 0.68
    high = target_interval * 1.32
    gap = float(before - prefix[-1])
    if not (low <= gap <= high):
        return np.asarray([], dtype=float)

    start = prefix.size - 1
    while start > 0:
        interval = float(prefix[start] - prefix[start - 1])
        if not (low <= interval <= high):
            break
        start -= 1

    suffix = prefix[start:]
    if suffix.size < 3:
        return np.asarray([], dtype=float)
    return suffix


def merge_intro_beats(
    *,
    drums: dict[str, Any] | None,
    mix: dict[str, Any] | None,
    instrumental_prefix: bool,
) -> FusionResult:
    drum_beats = _clean_beats((drums or {}).get("beats", []))
    mix_beats = _clean_beats((mix or {}).get("beats", []))

    if drum_beats.size:
        drum_interval = _median_interval(drum_beats)
        if drum_interval is None:
            raise RuntimeError("Timeline batterie invalide.")

        first_drum = float(drum_beats[0])
        intro = np.asarray([], dtype=float)

        if (
            instrumental_prefix
            and mix_beats.size >= 3
            and first_drum > max(1.0, drum_interval * 1.5)
        ):
            intro = _regular_suffix_before(
                mix_beats,
                before=first_drum,
                target_interval=drum_interval,
            )

        merged = np.concatenate([intro, drum_beats])
        sources = ["mix"] * int(intro.size) + ["drums"] * int(drum_beats.size)

        tempo = float((drums or {}).get("tempo") or (60.0 / drum_interval))
        engine = str((drums or {}).get("engine", "drums"))
        if intro.size:
            engine += "+mix-intro"

        return FusionResult(
            beats=tuple(float(x) for x in merged.tolist()),
            sources=tuple(sources),
            tempo=tempo,
            engine=engine,
            intro_mix_beat_count=int(intro.size),
            first_drum_beat=first_drum,
        )

    if instrumental_prefix and mix_beats.size >= 2:
        interval = _median_interval(mix_beats)
        if interval is None:
            raise RuntimeError("Timeline mix invalide.")
        return FusionResult(
            beats=tuple(float(x) for x in mix_beats.tolist()),
            sources=tuple("mix" for _ in mix_beats),
            tempo=float((mix or {}).get("tempo") or (60.0 / interval)),
            engine=str((mix or {}).get("engine", "mix")) + "+mix-only",
            intro_mix_beat_count=int(mix_beats.size),
            first_drum_beat=None,
        )

    raise RuntimeError(
        "Aucune pulsation instrumentale fiable détectée. "
        "Le pré-roll chant reste non métrique ; aucune mesure n'est inventée."
    )


def _rms_prefix(path: Path, duration: float) -> float:
    if not path.is_file() or duration <= 0.05:
        return 0.0

    y, _ = librosa.load(
        str(path),
        sr=16000,
        mono=True,
        duration=float(duration),
    )
    if y.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(y, dtype=np.float64))))


def has_instrumental_prefix(
    stems: dict[str, Path],
    *,
    duration: float,
) -> bool:
    seconds = max(0.25, min(float(duration), 45.0))

    vocals = _rms_prefix(Path(stems["vocals"]), seconds)
    instrumental_parts = [
        _rms_prefix(Path(stems[name]), seconds)
        for name in ("drums", "bass", "other")
        if name in stems
    ]
    if not instrumental_parts:
        return False

    instrumental = float(
        np.sqrt(sum(value * value for value in instrumental_parts))
    )

    if instrumental < 0.001:
        return False

    if vocals > 1e-6 and instrumental / vocals < 0.18:
        return False

    return True
