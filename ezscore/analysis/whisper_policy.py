from __future__ import annotations

"""Audio-only Whisper language policy for EZScore.

Hard invariant:
    language decisions are derived from decoded PCM samples only.

Filename, title, artist, tags, directory names and other textual metadata are
never inspected by this module and are never forwarded to Whisper.transcribe
when automatic language detection is active.
"""

from functools import wraps
from pathlib import Path
from typing import Any

import numpy as np


LANGUAGE_POLICY_VERSION = 3
LANGUAGE_POLICY_ENGINE = "ezscore-audio-only-language-v3"

# Whisper language detection uses 30 s windows.
_MAX_WINDOWS = 7
_MIN_AUDIO_FRACTION = 0.20
_MIN_RMS = 1e-7
_DOMINANT_SHARE = 0.72
_DOMINANT_MARGIN = 0.22
_MIXED_SECOND_SHARE = 0.18
_MIXED_WINDOW_SHARE = 0.25

_INSTALLED = False


def _as_audio_samples(audio: Any) -> np.ndarray:
    """Decode input to mono float32 PCM.

    A path may be used only as an I/O locator.  Its text is discarded
    immediately after decoding and never participates in language inference.
    """
    import whisper

    if isinstance(audio, (str, Path)):
        samples = whisper.load_audio(str(audio))
    else:
        samples = np.asarray(audio, dtype=np.float32)

    return np.asarray(samples, dtype=np.float32).reshape(-1)


def _window_starts(sample_count: int, window: int) -> list[int]:
    if sample_count <= 0:
        return []
    if sample_count <= window:
        return [0]

    max_start = sample_count - window
    count = min(
        _MAX_WINDOWS,
        max(3, int(np.ceil(sample_count / float(window)))),
    )
    return sorted({
        int(round(max_start * i / max(1, count - 1)))
        for i in range(count)
    })


def _rms(chunk: np.ndarray) -> float:
    if chunk.size == 0:
        return 0.0
    return float(
        np.sqrt(np.mean(np.square(chunk), dtype=np.float64))
    )


def detect_language_profile(
    model,
    audio,
) -> dict[str, Any]:
    """Return an auditable language profile derived only from PCM audio."""
    import whisper

    samples = _as_audio_samples(audio)
    minimum = int(whisper.audio.N_SAMPLES * _MIN_AUDIO_FRACTION)
    if samples.size < minimum:
        return {
            "version": LANGUAGE_POLICY_VERSION,
            "engine": LANGUAGE_POLICY_ENGINE,
            "source": "audio_signal_only",
            "primary": "",
            "confidence": 0.0,
            "mixed": False,
            "top": [],
            "windows": [],
        }

    window = int(whisper.audio.N_SAMPLES)
    starts = _window_starts(samples.size, window)

    energies = []
    for start in starts:
        energies.append(
            _rms(samples[start:min(samples.size, start + window)])
        )

    positive = [value for value in energies if value > _MIN_RMS]
    if not positive:
        return {
            "version": LANGUAGE_POLICY_VERSION,
            "engine": LANGUAGE_POLICY_ENGINE,
            "source": "audio_signal_only",
            "primary": "",
            "confidence": 0.0,
            "mixed": False,
            "top": [],
            "windows": [],
        }

    energy_floor = max(
        _MIN_RMS,
        float(np.percentile(positive, 25)) * 0.35,
    )
    peak_energy = max(positive)

    aggregate: dict[str, float] = {}
    window_rows: list[dict[str, Any]] = []
    winner_weights: dict[str, float] = {}

    for start, energy in zip(starts, energies):
        if energy < energy_floor:
            continue

        chunk = whisper.pad_or_trim(
            samples[start:min(samples.size, start + window)]
        )
        mel = whisper.log_mel_spectrogram(
            chunk,
            n_mels=model.dims.n_mels,
        ).to(model.device)

        _tokens, probs = model.detect_language(mel)
        ordered = sorted(
            ((str(lang), float(prob)) for lang, prob in probs.items()),
            key=lambda item: item[1],
            reverse=True,
        )
        if not ordered:
            continue

        winner, winner_prob = ordered[0]
        runner_prob = ordered[1][1] if len(ordered) > 1 else 0.0

        # Instrumental/noisy windows tend to have flatter language
        # distributions.  Certainty therefore contributes to the weight,
        # instead of selecting windows by loudness alone.
        certainty = max(0.05, winner_prob - runner_prob)
        energy_weight = max(
            0.05,
            min(1.0, energy / max(peak_energy, _MIN_RMS)),
        )
        weight = energy_weight * certainty

        for lang, prob in ordered:
            aggregate[lang] = (
                aggregate.get(lang, 0.0) + prob * weight
            )

        winner_weights[winner] = (
            winner_weights.get(winner, 0.0) + weight
        )

        window_rows.append({
            "start_seconds": round(
                float(start) / float(whisper.audio.SAMPLE_RATE),
                3,
            ),
            "winner": winner,
            "winner_probability": round(winner_prob, 6),
            "runner_up_probability": round(runner_prob, 6),
            "rms": round(float(energy), 8),
            "weight": round(float(weight), 8),
        })

    total = sum(aggregate.values())
    if total <= 0.0:
        normalized: dict[str, float] = {}
    else:
        normalized = {
            lang: value / total
            for lang, value in aggregate.items()
        }

    top = sorted(
        normalized.items(),
        key=lambda item: item[1],
        reverse=True,
    )
    primary = top[0][0] if top else ""
    confidence = float(top[0][1]) if top else 0.0
    second_share = float(top[1][1]) if len(top) > 1 else 0.0

    winner_total = sum(winner_weights.values()) or 1.0
    secondary_window_share = 0.0
    if primary:
        secondary_window_share = (
            sum(
                value
                for lang, value in winner_weights.items()
                if lang != primary
            )
            / winner_total
        )

    mixed = bool(
        primary
        and second_share >= _MIXED_SECOND_SHARE
        and secondary_window_share >= _MIXED_WINDOW_SHARE
    )

    dominant = bool(
        primary
        and not mixed
        and confidence >= _DOMINANT_SHARE
        and (confidence - second_share) >= _DOMINANT_MARGIN
    )

    return {
        "version": LANGUAGE_POLICY_VERSION,
        "engine": LANGUAGE_POLICY_ENGINE,
        "source": "audio_signal_only",
        "primary": primary,
        "confidence": round(confidence, 6),
        "mixed": mixed,
        "dominant": dominant,
        "top": [
            [lang, round(float(prob), 6)]
            for lang, prob in top[:5]
        ],
        "windows": window_rows,
    }


def install_whisper_language_policy() -> None:
    """Install an audio-only wrapper around Whisper.transcribe.

    Even when the caller passes ``C:\\music\\French_song.mp3``, the wrapped
    Whisper call receives only PCM samples.  The path string cannot influence
    decoding, prompting or language selection.
    """
    global _INSTALLED
    if _INSTALLED:
        return

    import whisper

    original = whisper.Whisper.transcribe
    if getattr(original, "_ezscore_language_policy", False):
        _INSTALLED = True
        return

    @wraps(original)
    def wrapped(self, audio, *args, **kwargs):
        samples = None
        try:
            samples = _as_audio_samples(audio)

            # An explicit language is an explicit caller decision.  We still
            # remove the path from the downstream call.
            if kwargs.get("language"):
                return original(self, samples, *args, **kwargs)

            profile = detect_language_profile(self, samples)

            # Force only a strong monolingual result.  Ambiguous/mixed content
            # stays in Whisper auto mode rather than imposing one language on
            # the complete song.
            if profile.get("dominant") and profile.get("primary"):
                kwargs["language"] = str(profile["primary"])

            result = original(self, samples, *args, **kwargs)
            if isinstance(result, dict):
                result["ezscore_language_profile"] = profile
            return result
        except Exception:
            # Preserve analysis availability, but if PCM decoding succeeded
            # never reintroduce the filename/path into Whisper.
            fallback_audio = samples if samples is not None else audio
            return original(self, fallback_audio, *args, **kwargs)

    wrapped._ezscore_language_policy = True
    wrapped._ezscore_language_policy_version = LANGUAGE_POLICY_VERSION
    whisper.Whisper.transcribe = wrapped
    _INSTALLED = True
