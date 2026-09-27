from __future__ import annotations

from dataclasses import dataclass
import numpy as np
import librosa

CANDIDATES = ("2/4", "3/4", "4/4", "6/8")

@dataclass(frozen=True)
class MeterResult:
    signature: str
    phase: int
    confidence: float
    scores: dict[str, float]


def _z(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    if x.size == 0:
        return x
    return (x - np.mean(x)) / (np.std(x) + 1e-9)


def _at_beats(feature: np.ndarray, beat_frames: np.ndarray) -> np.ndarray:
    if feature.size == 0:
        return np.zeros(len(beat_frames), dtype=float)
    idx = np.clip(np.asarray(beat_frames, dtype=int), 0, len(feature) - 1)
    return _z(feature[idx])


def _bass_feature(y: np.ndarray | None, sr: int, hop: int, beat_frames: np.ndarray) -> np.ndarray:
    if y is None or len(y) == 0:
        return np.zeros(len(beat_frames), dtype=float)
    cqt = np.abs(librosa.cqt(y=y, sr=sr, hop_length=hop,
                             fmin=librosa.note_to_hz("C1"), n_bins=36, bins_per_octave=12))
    low = np.mean(cqt[:24], axis=0)
    change = np.r_[0.0, np.maximum(0.0, np.diff(low))]
    return _at_beats(low + 0.75 * change, beat_frames)


def _harmony_change(y: np.ndarray, sr: int, hop: int, beat_frames: np.ndarray) -> np.ndarray:
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=hop)
    if chroma.shape[1] < 2:
        return np.zeros(len(beat_frames), dtype=float)
    chroma /= np.maximum(np.linalg.norm(chroma, axis=0, keepdims=True), 1e-9)
    delta = np.zeros(chroma.shape[1], dtype=float)
    delta[1:] = 1.0 - np.sum(chroma[:, 1:] * chroma[:, :-1], axis=0)
    return _at_beats(delta, beat_frames)


def _coherence(signal: np.ndarray, period: int, phase: int) -> float:
    n = len(signal)
    if n < period * 3:
        return -1e6
    bars = [signal[start:start + period] for start in range(phase, n - period + 1, period)]
    if len(bars) < 3:
        return -1e6
    matrix = np.vstack(bars)
    profile = np.mean(matrix, axis=0)
    pnorm = np.linalg.norm(profile) + 1e-9
    consistency = np.mean([
        np.dot(row, profile) / ((np.linalg.norm(row) + 1e-9) * pnorm)
        for row in matrix
    ])
    pos = (np.arange(n) - phase) % period
    down = signal[pos == 0]
    rest = signal[pos != 0]
    accent = float(np.mean(down) - np.mean(rest)) if down.size and rest.size else 0.0
    # Accent is deliberately capped: syncopated/reggae material must not force beat 1.
    accent = float(np.clip(accent, -1.0, 1.0))
    return float(0.72 * consistency + 0.28 * accent)


def detect_meter(*, harmonic_y: np.ndarray, bass_y: np.ndarray | None,
                 onset: np.ndarray, beat_frames: np.ndarray,
                 sr: int, hop: int) -> MeterResult:
    beat_frames = np.asarray(beat_frames, dtype=int)
    if len(beat_frames) < 8:
        return MeterResult("4/4", 0, 0.0, {"4/4": 0.0})

    drums = _at_beats(onset, beat_frames)
    bass = _bass_feature(bass_y, sr, hop, beat_frames)
    harmony = _harmony_change(harmonic_y, sr, hop, beat_frames)

    fused = 0.62 * drums + 0.25 * bass + 0.13 * harmony
    periods = {"2/4": 2, "3/4": 3, "4/4": 4, "6/8": 6}
    best: dict[str, tuple[float, int]] = {}

    for sig, period in periods.items():
        candidates = []
        for phase in range(period):
            score = (
                0.50 * _coherence(fused, period, phase)
                + 0.30 * _coherence(drums, period, phase)
                + 0.13 * _coherence(bass, period, phase)
                + 0.07 * _coherence(harmony, period, phase)
            )
            if sig == "4/4":
                score += 0.02
            if sig == "6/8":
                pos = (np.arange(len(drums)) - phase) % 6
                compound = drums[(pos == 0) | (pos == 3)]
                other = drums[(pos != 0) & (pos != 3)]
                if compound.size and other.size:
                    score += 0.16 * float(np.clip(np.mean(compound) - np.mean(other), -1.0, 1.0))
            candidates.append((float(score), phase))
        best[sig] = max(candidates, key=lambda item: item[0])

    ordered = sorted(best.items(), key=lambda item: item[1][0], reverse=True)
    signature, (top, phase) = ordered[0]
    second = ordered[1][1][0] if len(ordered) > 1 else top
    confidence = float(np.clip(0.5 + top - second, 0.0, 1.0))
    return MeterResult(signature, int(phase), confidence,
                       {sig: round(value[0], 5) for sig, value in best.items()})
