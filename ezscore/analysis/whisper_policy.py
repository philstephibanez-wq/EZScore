from __future__ import annotations

"""Whisper multi-window language policy for EZScore."""

from functools import wraps
from pathlib import Path

import numpy as np


_INSTALLED = False


def _consensus_language(model, audio):
    import whisper

    if isinstance(audio, (str, Path)):
        samples = whisper.load_audio(str(audio))
    else:
        samples = np.asarray(audio, dtype=np.float32)

    samples = np.asarray(samples, dtype=np.float32).reshape(-1)
    if samples.size < whisper.audio.N_SAMPLES // 4:
        return None, {}

    window = whisper.audio.N_SAMPLES
    max_start = max(0, samples.size - window)
    starts = sorted({
        0,
        int(max_start * 0.20),
        int(max_start * 0.45),
        int(max_start * 0.70),
        int(max_start * 0.90),
    })

    energies = []
    for start in starts:
        chunk = samples[start:start + window]
        energy = (
            float(np.sqrt(np.mean(np.square(chunk), dtype=np.float64)))
            if chunk.size else 0.0
        )
        energies.append(energy)

    positive = [x for x in energies if x > 1e-7]
    if not positive:
        return None, {}

    floor = max(1e-7, float(np.percentile(positive, 30)) * 0.45)
    peak_energy = max(positive)
    aggregate = {}
    used = 0

    for start, energy in zip(starts, energies):
        if energy < floor:
            continue

        chunk = whisper.pad_or_trim(samples[start:start + window])
        mel = whisper.log_mel_spectrogram(
            chunk,
            n_mels=model.dims.n_mels,
        ).to(model.device)

        _tokens, probs = model.detect_language(mel)
        weight = max(0.05, min(1.0, energy / peak_energy))

        for lang, prob in probs.items():
            aggregate[lang] = aggregate.get(lang, 0.0) + float(prob) * weight
        used += 1

    if not aggregate or used == 0:
        return None, {}

    total = sum(aggregate.values()) or 1.0
    normalized = {key: value / total for key, value in aggregate.items()}
    selected = max(normalized, key=normalized.get)
    return selected, normalized


def install_whisper_language_policy() -> None:
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
        if kwargs.get("language"):
            return original(self, audio, *args, **kwargs)

        try:
            language, probs = _consensus_language(self, audio)
            if language:
                kwargs["language"] = language
            result = original(self, audio, *args, **kwargs)
            if isinstance(result, dict):
                result["ezscore_language_consensus"] = {
                    "selected": language or "",
                    "top": sorted(
                        probs.items(),
                        key=lambda item: item[1],
                        reverse=True,
                    )[:5],
                }
            return result
        except Exception:
            return original(self, audio, *args, **kwargs)

    wrapped._ezscore_language_policy = True
    whisper.Whisper.transcribe = wrapped
    _INSTALLED = True
