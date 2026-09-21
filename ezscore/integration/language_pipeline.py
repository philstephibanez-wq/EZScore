from __future__ import annotations

"""Canonical lyrics-language integration for the STEM analysis surface.

The language detector sees audio only.  Textual song metadata is deliberately
absent from this module.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import torch
import whisper

from ezscore.analysis.stems import cached_stem_paths
from ezscore.analysis.whisper_policy import (
    LANGUAGE_POLICY_ENGINE,
    LANGUAGE_POLICY_VERSION,
    detect_language_profile,
)


SPEECH_CACHE_SCHEMA_VERSION = 4


def _cache_is_current(
    payload: dict[str, Any],
    *,
    audio_hash: str | None = None,
) -> bool:
    policy = dict(payload.get("language_policy", {}) or {})
    words = list(payload.get("words", []) or [])
    language = str(payload.get("language", "") or "").strip().lower()

    if audio_hash is not None:
        if str(payload.get("audio_hash", "") or "") != str(audio_hash):
            return False

    return bool(
        int(payload.get("speech_cache_schema_version", 0) or 0)
        == SPEECH_CACHE_SCHEMA_VERSION
        and str(payload.get("status", "") or "") == "complete"
        and language
        and words
        and int(payload.get("word_count", 0) or 0) == len(words)
        and int(policy.get("version", 0) or 0)
        == LANGUAGE_POLICY_VERSION
        and str(policy.get("engine", "") or "")
        == LANGUAGE_POLICY_ENGINE
        and str(policy.get("source", "") or "")
        == "audio_signal_only"
    )


def speech_cache_is_current(stem_lab, audio_hash: str) -> bool:
    try:
        payload = stem_lab._load_speech(audio_hash)
    except Exception:
        return False
    return bool(
        payload
        and _cache_is_current(
            dict(payload),
            audio_hash=str(audio_hash),
        )
    )


def _dependent_cache_paths(stem_lab, audio_hash: str) -> list[Path]:
    work = Path(stem_lab._speech_cache_path(audio_hash)).parent
    return [
        work / "whisper_vocals_small.json",
        work / "whisper_backing_small.json",
        work / "choir_words_from_vocals.json",
        work / "choir_analysis.json",
        work / "karaoke_conductor.json",
        work / "structure_analysis.json",
    ]


def invalidate_canonical_speech(
    stem_lab,
    audio_hash: str,
    *,
    include_master: bool,
) -> None:
    """Invalidate the canonical transcript and every artifact derived from it.

    Chord-analysis caches are deliberately preserved because they are
    independent from lyrics.  Structure/choir/conductor artifacts are removed
    because their semantic content depends on the canonical transcript.
    """
    paths = _dependent_cache_paths(stem_lab, audio_hash)
    if include_master:
        paths.insert(0, Path(stem_lab._speech_cache_path(audio_hash)))

    for path in paths:
        try:
            path.unlink()
        except FileNotFoundError:
            pass


def _extract_words(result: dict[str, Any]) -> list[dict[str, Any]]:
    words: list[dict[str, Any]] = []
    result_language = str(result.get("language", "") or "").strip().lower()

    for segment in result.get("segments", []) or []:
        segment_language = str(
            segment.get("language", "") or result_language
        ).strip().lower()

        for word in segment.get("words", []) or []:
            text = str(word.get("word", "") or "").strip()
            start = float(word.get("start", 0.0) or 0.0)
            end = float(word.get("end", start) or start)
            if not text or end <= start:
                continue
            words.append({
                "start": start,
                "end": end,
                "text": text,
                "language": segment_language,
            })

    return words


def _vocal_detection_audio(audio_hash: str, original_samples: np.ndarray) -> np.ndarray:
    """Prefer separated vocals; fall back to original PCM.

    The hash is only a technical cache key used to locate the stem.  No title,
    filename, artist or textual metadata is consulted.
    """
    try:
        stems = cached_stem_paths(str(audio_hash))
        vocals = stems.get("vocals")
        if vocals and Path(vocals).is_file():
            return np.asarray(
                whisper.load_audio(str(vocals)),
                dtype=np.float32,
            ).reshape(-1)
    except Exception:
        pass

    return np.asarray(original_samples, dtype=np.float32).reshape(-1)


def transcribe_original_audio_only(
    stem_lab,
    source: Path,
    audio_hash: str,
) -> dict[str, Any]:
    """Transcribe original audio while detecting language from vocal PCM.

    Transactional rule:
    the old canonical transcript and all dependent artifacts are removed before
    analysis starts. If analysis is interrupted or fails, no stale semantic
    artifact remains eligible for display.
    """
    invalidate_canonical_speech(
        stem_lab,
        audio_hash,
        include_master=True,
    )

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = stem_lab._whisper_small(device)

    # Decode once, then discard the path as linguistic input.
    original_samples = np.asarray(
        whisper.load_audio(str(source)),
        dtype=np.float32,
    ).reshape(-1)

    detector_samples = _vocal_detection_audio(
        audio_hash,
        original_samples,
    )
    profile = detect_language_profile(model, detector_samples)

    transcribe_kwargs: dict[str, Any] = {
        "word_timestamps": True,
        "fp16": (device == "cuda"),
        "verbose": False,
    }

    primary_language = str(
        profile.get("primary", "") or ""
    ).strip().lower()
    if not primary_language:
        raise RuntimeError(
            "Langue vocale indéterminable à partir du signal audio. "
            "Transcription annulée avant Whisper."
        )

    # No fallback to Whisper's global automatic language detector.
    transcribe_kwargs["language"] = primary_language

    # Important invariant: Whisper receives PCM, never the MP3 filename.
    result = model.transcribe(
        original_samples,
        **transcribe_kwargs,
    )

    words = _extract_words(result)
    result_language = str(
        result.get("language", "") or profile.get("primary", "") or ""
    ).strip().lower()

    if not result_language or not words:
        raise RuntimeError(
            "Transcription canonique incomplète : aucune écriture de cache."
        )

    payload = {
        "speech_cache_schema_version": SPEECH_CACHE_SCHEMA_VERSION,
        "status": "complete",
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "engine": "openai-whisper",
        "model": "small",
        "source": "original_audio_pcm",
        "audio_hash": str(audio_hash),
        "language": result_language,
        "language_policy": {
            "version": LANGUAGE_POLICY_VERSION,
            "engine": LANGUAGE_POLICY_ENGINE,
            "source": "audio_signal_only",
        },
        "language_profile": profile,
        "text": str(result.get("text", "") or "").strip(),
        "words": words,
        "word_count": len(words),
    }

    cache_path = Path(stem_lab._speech_cache_path(audio_hash))
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = cache_path.with_suffix(".tmp")
    temp_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temp_path.replace(cache_path)
    return payload


def install(stem_lab) -> None:
    """Patch the STEM surface without modifying its large implementation."""
    original_load = stem_lab._load_speech

    if getattr(original_load, "_ezscore_audio_only_language", False):
        return

    def load_speech_versioned(audio_hash: str):
        payload = original_load(audio_hash)
        if payload is None:
            return None

        # Old caches may contain a stale/wrong language decision.  They are
        # deliberately ignored once the language engine changes.
        if not _cache_is_current(dict(payload), audio_hash=str(audio_hash)):
            return None
        return payload

    load_speech_versioned._ezscore_audio_only_language = True

    def transcribe_audio_only(source: Path, audio_hash: str):
        return transcribe_original_audio_only(
            stem_lab,
            source,
            audio_hash,
        )

    transcribe_audio_only._ezscore_audio_only_language = True

    stem_lab._load_speech = load_speech_versioned
    stem_lab._transcribe_original = transcribe_audio_only
